#!/usr/bin/env python3
"""Week 2 policy comparison on simulated ECG triage cases.

Simulation generates a hidden state from the Week 2 priors, then generates
clue answers from the agent's likelihood tables (normalized per state).
This validates policy behaviour given those likelihoods. It cannot validate
the likelihoods themselves.

Seed: 42. All policies see the identical 150 cases.
"""

from __future__ import annotations

import csv
import json
import random
import sys
from collections import Counter, defaultdict
from math import log2
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import ecg_agent as ag  # noqa: E402

SEED = 42
N_CASES = 150
FATIGUE_VOI = 5  # environment where waiting can beat escalating
CLUE_PRICE = 2.0
RESULTS = ROOT / "results"
POSITIVE = "stemi"


def p_answer_given_state(clue, state):
    weights = {ans: clue["odds"][ans][state] for ans in clue["odds"]}
    total = sum(weights.values())
    return {ans: w / total for ans, w in weights.items()}


def sample_from(dist, rng):
    items = list(dist.items())
    r = rng.random()
    acc = 0.0
    for key, p in items:
        acc += p
        if r <= acc:
            return key
    return items[-1][0]


def generate_cases(n, seed):
    rng = random.Random(seed)
    cases = []
    for i in range(n):
        truth = sample_from(ag.start_belief(), rng)
        answers = {}
        for clue in ag.clues:
            answers[clue["name"]] = sample_from(p_answer_given_state(clue, truth), rng)
        cases.append({"id": i, "truth": truth, "answers": answers})
    return cases


def update_all(belief, answers):
    for clue in ag.clues:
        belief = ag.update(belief, clue["odds"][answers[clue["name"]]])
    return belief


def terminal_from_map(belief):
    top = max(belief, key=belief.get)
    return "ESCALATE" if top == POSITIVE else "DISMISS"


def terminal_from_threshold(belief, escalate_cost=None):
    miss = belief[POSITIVE] * ag.prices["missed_stemi"]
    esc = ag.prices["escalation_cost"] if escalate_cost is None else escalate_cost
    return "ESCALATE" if miss > esc else "DISMISS"


def cost_weighted_clue(belief, remaining):
    """Pick the clue that most reduces expected act-cost after seeing it."""

    def expected_act(clue):
        total = 0.0
        for answer, chance in clue["chances"].items():
            post = ag.update(belief, clue["odds"][answer])
            total += chance * min(
                post[POSITIVE] * ag.prices["missed_stemi"],
                ag.prices["escalation_cost"],
            )
        return total

    return min(remaining, key=expected_act)


def run_sequential(case, fatigue, selector, max_wait=5):
    belief = ag.start_belief()
    remaining = list(ag.clues)
    asked = []
    wait_count = 0
    trace = []

    while remaining:
        clue = selector(belief, remaining)
        action, costs = ag.decide(
            belief, ag.prices, clue, fatigue, wait_count=wait_count, max_wait=max_wait
        )
        cost_log = {}
        if isinstance(costs, dict):
            for k, v in costs.items():
                if v == float("inf"):
                    cost_log[k] = "inf"
                elif isinstance(v, float):
                    cost_log[k] = round(v, 4)
                else:
                    cost_log[k] = v
        trace.append(
            {
                "wait_count": wait_count,
                "clue": clue["name"],
                "action_before_ask": action,
                "p_stemi": belief[POSITIVE],
                "entropy": ag.doubt(belief),
                "costs": cost_log,
            }
        )
        if action != "WAIT":
            return {
                "action": action,
                "belief": belief,
                "asked": asked,
                "questions": len(asked),
                "trace": trace,
            }

        answer = case["answers"][clue["name"]]
        belief = ag.update(belief, clue["odds"][answer])
        asked.append({"name": clue["name"], "answer": answer})
        remaining = [c for c in remaining if c["name"] != clue["name"]]
        wait_count += 1

    action = terminal_from_threshold(
        belief,
        escalate_cost=ag.escalation_cost_with_fatigue(
            ag.prices["escalation_cost"], fatigue, belief[POSITIVE]
        ),
    )
    return {
        "action": action,
        "belief": belief,
        "asked": asked,
        "questions": len(asked),
        "trace": trace,
        "forced_after_clues": True,
    }


def entropy_selector(belief, remaining):
    return ag.best_clue(belief, remaining)


def decision_cost(truth, action):
    if action == "ESCALATE":
        return 0.0 if truth == POSITIVE else ag.prices["escalation_cost"]
    if action == "DISMISS":
        return ag.prices["missed_stemi"] if truth == POSITIVE else 0.0
    raise ValueError(action)


def is_correct(truth, action):
    if truth == POSITIVE:
        return action == "ESCALATE"
    return action == "DISMISS"


def metrics(rows):
    n = len(rows)
    tp = sum(1 for r in rows if r["truth"] == POSITIVE and r["action"] == "ESCALATE")
    fp = sum(1 for r in rows if r["truth"] != POSITIVE and r["action"] == "ESCALATE")
    fn = sum(1 for r in rows if r["truth"] == POSITIVE and r["action"] != "ESCALATE")
    tn = sum(1 for r in rows if r["truth"] != POSITIVE and r["action"] == "DISMISS")
    acc = sum(1 for r in rows if r["correct"]) / n
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    dcost = sum(r["decision_cost"] for r in rows)
    icost = sum(r["info_cost"] for r in rows)
    questions = sum(r["questions"] for r in rows) / n
    human = sum(1 for r in rows if r["action"] == "ESCALATE") / n
    brier = None
    if any(r.get("p_stemi") is not None for r in rows):
        brier = sum((r["p_stemi"] - (1.0 if r["truth"] == POSITIVE else 0.0)) ** 2 for r in rows) / n
    return {
        "n": n,
        "accuracy": acc,
        "precision": prec,
        "recall": rec,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "decision_cost": dcost,
        "info_cost": icost,
        "total_cost": dcost + icost,
        "questions_avg": questions,
        "human_review_rate": human,
        "brier": brier,
        "stemi_caught": tp,
        "stemi_missed": fn,
        "false_alarms": fp,
    }


def evaluate_policy(name, cases, decide_fn):
    rows = []
    for case in cases:
        out = decide_fn(case)
        action = out["action"]
        questions = out.get("questions", 0)
        row = {
            "id": case["id"],
            "policy": name,
            "truth": case["truth"],
            "action": action,
            "questions": questions,
            "info_cost": questions * CLUE_PRICE,
            "decision_cost": decision_cost(case["truth"], action),
            "correct": is_correct(case["truth"], action),
            "p_stemi": out.get("belief", {}).get(POSITIVE) if out.get("belief") else out.get("p_stemi"),
            "entropy": ag.doubt(out["belief"]) if out.get("belief") else None,
            "asked": out.get("asked", []),
        }
        rows.append(row)
    return rows, metrics(rows)


def clue_value_table(belief):
    rows = []
    h = ag.doubt(belief)
    for clue in ag.clues:
        ig = ag.expected_cut(belief, clue)
        wait = ag.cost_if_we_wait(belief, ag.prices, clue, false_alarms_24h=0)
        rows.append(
            {
                "name": clue["name"],
                "price": clue["price"],
                "entropy_before": h,
                "expected_ig": ig,
                "bits_per_dollar": ig / clue["price"],
                "expected_cost_if_wait": wait,
            }
        )
    return rows


def mutual_information(clue, prior):
    """I(State; Answer) from likelihoods and prior. Analytically, not simulated."""
    h_prior = ag.doubt(prior)
    # P(answer) = sum_s P(s) P(a|s)
    p_a = defaultdict(float)
    p_s_given_a = {}
    answers = list(clue["odds"])
    for a in answers:
        pa = 0.0
        unnorm = {}
        for s, ps in prior.items():
            pas = p_answer_given_state(clue, s)[a]
            joint = ps * pas
            unnorm[s] = joint
            pa += joint
        p_a[a] = pa
        p_s_given_a[a] = {s: (v / pa if pa else 0.0) for s, v in unnorm.items()}
    h_cond = sum(p_a[a] * ag.doubt(p_s_given_a[a]) for a in answers if p_a[a] > 0)
    return h_prior - h_cond, dict(p_a), p_s_given_a


def js_divergence(p, q):
    m = {k: 0.5 * (p[k] + q[k]) for k in p}
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def kl(p, q):
    total = 0.0
    for k, pk in p.items():
        if pk <= 0:
            continue
        qk = q[k]
        if qk <= 0:
            return float("inf")
        total += pk * log2(pk / qk)
    return total


def failures(rows, limit=12):
    bad = [r for r in rows if not r["correct"]]
    # Prefer a mix of missed STEMIs and false alarms
    missed = [r for r in bad if r["truth"] == POSITIVE]
    alarms = [r for r in bad if r["action"] == "ESCALATE"]
    mixed = []
    seen = set()
    for pool in (missed, alarms, bad):
        for r in pool:
            if r["id"] not in seen:
                mixed.append(r)
                seen.add(r["id"])
            if len(mixed) >= limit:
                return mixed
    return mixed


def svg_bar(path, series, title, ylabel):
    width, height = 720, 360
    margin = {"l": 90, "r": 24, "t": 48, "b": 90}
    plot_w = width - margin["l"] - margin["r"]
    plot_h = height - margin["t"] - margin["b"]
    vals = [v for _, v in series]
    vmax = max(vals) if vals else 1
    if vmax == 0:
        vmax = 1
    bar_w = plot_w / max(len(series), 1) * 0.62
    gap = plot_w / max(len(series), 1)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2}" y="28" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="16">{title}</text>',
        f'<text x="18" y="{margin["t"] + plot_h/2}" transform="rotate(-90 18,{margin["t"] + plot_h/2})" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="12">{ylabel}</text>',
    ]
    for i, (label, val) in enumerate(series):
        x = margin["l"] + i * gap + (gap - bar_w) / 2
        h = 0 if vmax == 0 else val / vmax * plot_h
        y = margin["t"] + plot_h - h
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="#1f4e79"/>')
        parts.append(
            f'<text x="{x + bar_w/2:.1f}" y="{height - 18}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="11">{label}</text>'
        )
        parts.append(
            f'<text x="{x + bar_w/2:.1f}" y="{y - 6:.1f}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="10">{val:,.0f}</text>'
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    (ROOT / "paper" / "figures").mkdir(parents=True, exist_ok=True)

    cases = generate_cases(N_CASES, SEED)
    truth_counts = Counter(c["truth"] for c in cases)

    prior = ag.start_belief()
    clue_rows = clue_value_table(prior)
    mi_rows = []
    for clue in ag.clues:
        mi, p_a, _ = mutual_information(clue, prior)
        mi_rows.append({"name": clue["name"], "mutual_information": mi, "p_answer": p_a})

    policies = {}

    def p0_dismiss(_case):
        return {"action": "DISMISS", "questions": 0, "p_stemi": prior[POSITIVE]}

    def p0_alarm(_case):
        return {"action": "ESCALATE", "questions": 0, "p_stemi": prior[POSITIVE]}

    def p1_map(case):
        belief = update_all(prior, case["answers"])
        return {"action": terminal_from_map(belief), "questions": 0, "belief": belief}

    def p2_threshold(case):
        belief = update_all(prior, case["answers"])
        return {"action": terminal_from_threshold(belief), "questions": 0, "belief": belief}

    def p3_f0(case):
        return run_sequential(case, fatigue=0, selector=entropy_selector)

    def p3_entropy(case):
        return run_sequential(case, fatigue=FATIGUE_VOI, selector=entropy_selector)

    def p3_cost(case):
        return run_sequential(case, fatigue=FATIGUE_VOI, selector=cost_weighted_clue)

    specs = [
        ("P0_dismiss", p0_dismiss),
        ("P0_alarm", p0_alarm),
        ("P1_map", p1_map),
        ("P2_threshold", p2_threshold),
        ("P3_fatigue0", p3_f0),
        ("P3_entropy", p3_entropy),
        ("P3_cost", p3_cost),
    ]

    all_rows = []
    summary = {}
    for name, fn in specs:
        rows, met = evaluate_policy(name, cases, fn)
        all_rows.extend(rows)
        summary[name] = met
        print(f"{name:14s} acc={met['accuracy']:.3f} rec={met['recall']:.3f} "
              f"dcost={met['decision_cost']:,.0f} icost={met['info_cost']:,.0f} "
              f"q={met['questions_avg']:.2f} human={met['human_review_rate']:.3f} "
              f"fn={met['stemi_missed']} fp={met['false_alarms']}")

    # Failure dump for the VOI agent (the one under study)
    p3_rows = [r for r in all_rows if r["policy"] == "P3_entropy"]
    fail_rows = failures(p3_rows, limit=10)

    # Worked Bayes example on case 0, first entropy-optimal clue
    demo = cases[0]
    first = ag.best_clue(prior, ag.clues)
    ans = demo["answers"][first["name"]]
    post = ag.update(prior, first["odds"][ans])

    payload = {
        "seed": SEED,
        "n_cases": N_CASES,
        "truth_counts": dict(truth_counts),
        "priors": prior,
        "prior_entropy": ag.doubt(prior),
        "fatigue_for_voi": FATIGUE_VOI,
        "note": "Simulation uses the agent's own likelihood tables. It validates policy, not likelihoods.",
        "clue_entropy_value": clue_rows,
        "clue_mutual_information": mi_rows,
        "best_clue_at_prior": first["name"],
        "js_prior_vs_uniform": js_divergence(prior, {k: 1 / 3 for k in prior}),
        "worked_update": {
            "case_id": demo["id"],
            "truth": demo["truth"],
            "clue": first["name"],
            "answer": ans,
            "prior": prior,
            "posterior": post,
            "entropy_before": ag.doubt(prior),
            "entropy_after": ag.doubt(post),
        },
        "metrics": summary,
        "p3_entropy_failures": [
            {
                "id": r["id"],
                "truth": r["truth"],
                "action": r["action"],
                "p_stemi": r["p_stemi"],
                "questions": r["questions"],
                "asked": r["asked"],
                "kind": "missed_stemi" if r["truth"] == POSITIVE else "false_alarm",
            }
            for r in fail_rows
        ],
    }

    (RESULTS / "summary.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    with (RESULTS / "cases.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["id", "policy", "truth", "action", "questions", "info_cost", "decision_cost", "correct", "p_stemi"],
        )
        w.writeheader()
        for r in all_rows:
            w.writerow({k: r[k] for k in w.fieldnames})

    svg_bar(
        ROOT / "paper" / "figures" / "policy_decision_cost.svg",
        [(k.replace("_", "\n"), summary[k]["decision_cost"]) for k, _ in specs],
        "Decision cost by policy (150 simulated cases, seed 42)",
        "Decision cost (USD)",
    )
    svg_bar(
        ROOT / "paper" / "figures" / "policy_total_cost.svg",
        [(k.replace("_", "\n"), summary[k]["total_cost"]) for k, _ in specs],
        "Total cost (decision + information) by policy",
        "Total cost (USD)",
    )

    print("truth_counts", dict(truth_counts))
    print("wrote", RESULTS / "summary.json")


if __name__ == "__main__":
    main()
