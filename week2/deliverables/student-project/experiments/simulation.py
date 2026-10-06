#!/usr/bin/env python3
"""
Week 2 simulation: Policy 0 (Always Escalate) vs Policy 1 (AI agent).

All priors, likelihoods, and costs are ASSUMPTIONS from ecg_agent.py.
This script validates policy behaviour given those tables — it does not
validate the likelihoods themselves.

Model (student decisions):
- diagnostic_truth ∈ {stemi, artifact, hyperventilation}
- measurement_quality ∈ {readable, unreadable} — separate from diagnosis
- INITIAL_UNREADABLE_RATE = 0.15 (was the old fourth prior mass)
- RETAKE changes measurement quality only; never changes diagnostic_truth
- TP/FN/FP/TN evaluated against diagnostic_truth for ALL patients
- Unresolved unreadability reported as an operational metric
- SEED=42; shared cohort; wait_count vs retake_count separated
- Unreadable (SQA) escalations do NOT increment false-alarm fatigue yet
"""

from __future__ import annotations

import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import ecg_agent as ag

N_PATIENTS = 1000
SEED = 42  # fixed seed — shared cohort, reproducible experiment
MAX_WAIT = 5
DIAGNOSTIC_STATES = ("stemi", "artifact", "hyperventilation")


def sample_diagnostic_truth(rng: random.Random) -> str:
    prior = ag.start_belief()
    states = list(prior.keys())
    weights = [prior[s] for s in states]
    return rng.choices(states, weights=weights, k=1)[0]


def sample_initial_measurement(rng: random.Random) -> str:
    if rng.random() < ag.INITIAL_UNREADABLE_RATE:
        return "unreadable"
    return "readable"


def sample_answer(clue: dict, diagnostic_truth: str, rng: random.Random) -> str:
    """Sample clue outcome from P(answer | diagnostic_truth)."""
    answers = list(clue["odds"].keys())
    weights = [clue["odds"][a][diagnostic_truth] for a in answers]
    return rng.choices(answers, weights=weights, k=1)[0]


def sample_retake_outcome(rng: random.Random) -> str:
    """Measurement-quality only; independent of diagnostic truth."""
    outcomes = list(ag.RETAKE_CHANCES.keys())
    weights = [ag.RETAKE_CHANCES[o] for o in outcomes]
    return rng.choices(outcomes, weights=weights, k=1)[0]


def generate_patient_answers(diagnostic_truth: str, rng: random.Random) -> dict:
    return {
        clue["name"]: sample_answer(clue, diagnostic_truth, rng)
        for clue in ag.clues
    }


def decision_cost(diagnostic_truth: str, action: str) -> float:
    """Handoff cost model: escalate $200, missed STEMI $500k, else $0. No delay fees."""
    is_stemi = diagnostic_truth == "stemi"
    if action == "ESCALATE":
        return ag.prices["escalation_cost"]
    if action == "DISMISS":
        return ag.prices["missed_stemi"] if is_stemi else 0.0
    raise ValueError(f"terminal action must be ESCALATE or DISMISS, got {action}")


def classify(diagnostic_truth: str, action: str) -> str:
    """TP/FN/FP/TN against diagnostic truth — includes initially-unreadable patients."""
    is_stemi = diagnostic_truth == "stemi"
    if is_stemi and action == "ESCALATE":
        return "TP"
    if is_stemi and action == "DISMISS":
        return "FN"
    if (not is_stemi) and action == "ESCALATE":
        return "FP"
    if (not is_stemi) and action == "DISMISS":
        return "TN"
    raise ValueError((diagnostic_truth, action))


def run_policy0(diagnostic_truth: str) -> tuple[str, float, str]:
    action = "ESCALATE"
    return action, decision_cost(diagnostic_truth, action), classify(
        diagnostic_truth, action
    )


def run_policy1(
    diagnostic_truth: str,
    answers: dict,
    initial_measurement: str,
    false_alarms_24h: int,
    rng: random.Random,
) -> tuple[str, float, str, int, str]:
    """
    Full decide loop with binary measurement-quality SQA.

    Returns action, cost, bucket, updated false_alarms_24h, final measurement.
    SQA escalations (still unreadable) do not increment fatigue.
    """
    belief = ag.start_belief()
    measurement = initial_measurement
    wait_count = 0
    retake_count = 0
    remaining = list(ag.clues)

    while True:
        # Duplicate SQA gate kept (handoff: do not silently remove).
        if (measurement == "unreadable"
                and retake_count < ag.MAX_RETAKES):
            action = "RETAKE"
            costs = {"reason": "SQA gate: measurement unreadable"}
        else:
            if not remaining and measurement == "readable":
                action = "ESCALATE"
                costs = {"reason": "no clues left"}
            else:
                clue = ag.best_clue(belief, remaining) if remaining else ag.clues[0]
                action, costs = ag.decide(
                    belief,
                    ag.prices,
                    clue,
                    false_alarms_24h,
                    wait_count=wait_count,
                    max_wait=MAX_WAIT,
                    retake_count=retake_count,
                    measurement_quality=measurement,
                )

        if wait_count >= MAX_WAIT and action == "WAIT":
            action = "ESCALATE"
            costs = {"reason": "max wait exceeded, uncertainty remains"}

        if action in ("ESCALATE", "DISMISS"):
            cost = decision_cost(diagnostic_truth, action)
            bucket = classify(diagnostic_truth, action)
            # Unreadable escalations do not contribute to fatigue yet.
            if bucket == "FP" and measurement == "readable":
                false_alarms_24h += 1
            return action, cost, bucket, false_alarms_24h, measurement

        if action == "WAIT":
            if measurement != "readable":
                raise RuntimeError("WAIT while measurement unreadable — SQA should fire")
            if not remaining:
                action = "ESCALATE"
                cost = decision_cost(diagnostic_truth, action)
                bucket = classify(diagnostic_truth, action)
                if bucket == "FP" and measurement == "readable":
                    false_alarms_24h += 1
                return action, cost, bucket, false_alarms_24h, measurement
            clue = ag.best_clue(belief, remaining)
            ans = answers[clue["name"]]
            belief = ag.update(belief, clue["odds"][ans])
            remaining = [c for c in remaining if c["name"] != clue["name"]]
            wait_count += 1
            continue

        if action == "RETAKE":
            # Measurement-quality only — diagnostic_truth NEVER changes.
            outcome = sample_retake_outcome(rng)
            if outcome == "readable":
                measurement = "readable"
            else:
                measurement = "unreadable"
            retake_count += 1
            continue

        raise RuntimeError(f"unknown action {action} costs={costs}")


def summarize(label: str, buckets: Counter, total_cost: float,
              unresolved_unreadable: int) -> dict:
    tp, fn, fp, tn = buckets["TP"], buckets["FN"], buckets["FP"], buckets["TN"]
    denom = tp + fn
    recall = (tp / denom) if denom else 0.0
    return {
        "label": label,
        "recall": recall,
        "total_cost": total_cost,
        "fp": fp,
        "escalations": tp + fp,
        "tp": tp,
        "fn": fn,
        "tn": tn,
        "n": tp + fn + fp + tn,
        "unresolved_unreadable": unresolved_unreadable,
    }


def print_report(p0: dict, p1: dict, truth_counts: Counter,
                 measurement_counts: Counter) -> None:
    print("=== 1000-Patient Simulation Results ===")
    print()
    print(f"Fixed seed: {SEED}")
    print(f"Diagnostic truth counts (expect ~60/590/350 at 6%/59%/35%): "
          f"{dict(truth_counts)}")
    print(f"Initial measurement counts (expect ~850 readable / ~150 unreadable): "
          f"{dict(measurement_counts)}")
    print()
    for p in (p0, p1):
        print(f"{p['label']}:")
        print(f"  Recall:               {p['recall']:.3f}")
        print(f"  Total Cost:          ${p['total_cost']:,.0f}")
        print(f"  False Positives:     {p['fp']}")
        print(f"  Total Escalations:   {p['escalations']}  (TP+FP)")
        print(f"  (TP={p['tp']} FN={p['fn']} FP={p['fp']} TN={p['tn']} "
              f"| n={p['n']})")
        print(f"  Unresolved unread.:  {p['unresolved_unreadable']}  "
              f"(terminal still unreadable; still in TP/FN/FP/TN)")
        print()
    saved = p0["total_cost"] - p1["total_cost"]
    fp_reduction = p0["fp"] - p1["fp"]
    print(f"Cost saved by AI agent: ${saved:,.0f}")
    print(f"FP reduction: {fp_reduction} fewer unnecessary escalations")


def main() -> None:
    rng = random.Random(SEED)

    # Shared cohort first: diagnostic truth + answers + initial measurement.
    # Policy 1 retake draws continue on this same rng after the cohort is fixed.
    cohort = []
    truth_counts: Counter = Counter()
    measurement_counts: Counter = Counter()
    for _ in range(N_PATIENTS):
        diagnostic_truth = sample_diagnostic_truth(rng)
        answers = generate_patient_answers(diagnostic_truth, rng)
        measurement = sample_initial_measurement(rng)
        cohort.append({
            "truth": diagnostic_truth,
            "answers": answers,
            "measurement": measurement,
        })
        truth_counts[diagnostic_truth] += 1
        measurement_counts[measurement] += 1

    p0_buckets: Counter = Counter()
    p0_cost = 0.0
    p0_unresolved = 0
    p1_buckets: Counter = Counter()
    p1_cost = 0.0
    p1_unresolved = 0
    false_alarms_24h = 0

    for patient in cohort:
        diagnostic_truth = patient["truth"]
        answers = patient["answers"]
        initial_measurement = patient["measurement"]

        action0, cost0, bucket0 = run_policy0(diagnostic_truth)
        p0_buckets[bucket0] += 1
        p0_cost += cost0
        # Policy 0 always escalates; if started unreadable, still "unresolved"
        # only in the sense that P0 never retakes — report initial unreadable
        # for P0 as operational context via measurement_counts, not here.

        action1, cost1, bucket1, false_alarms_24h, final_meas = run_policy1(
            diagnostic_truth, answers, initial_measurement,
            false_alarms_24h, rng,
        )
        p1_buckets[bucket1] += 1
        p1_cost += cost1
        if final_meas == "unreadable":
            p1_unresolved += 1

    p0 = summarize("Policy 0 — Always Escalate", p0_buckets, p0_cost, p0_unresolved)
    p1 = summarize("Policy 1 — AI Agent", p1_buckets, p1_cost, p1_unresolved)
    print_report(p0, p1, truth_counts, measurement_counts)

    print()
    print("--- validation ---")
    print(f"seed={SEED} (fixed)  final false_alarms_24h={false_alarms_24h}")
    print(f"shared cohort size={len(cohort)}")
    print(f"diagnostic belief states={sorted(ag.start_belief().keys())}")
    print(f"'unreadable' in diagnostic belief? "
          f"{'unreadable' in ag.start_belief()}")
    print(f"P0 n == 1000? {p0['n'] == N_PATIENTS}")
    print(f"P1 n == 1000? {p1['n'] == N_PATIENTS}")
    print(f"P0 FP + TN == non-STEMI? "
          f"{p0['fp'] + p0['tn']} == "
          f"{truth_counts['artifact'] + truth_counts['hyperventilation']}")
    print(f"Policy 0 recall == 1.0? {p0['recall'] == 1.0}")
    print(f"Policy 1 cost < Policy 0 cost? {p1['total_cost'] < p0['total_cost']}")


if __name__ == "__main__":
    main()
