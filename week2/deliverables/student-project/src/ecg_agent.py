# ecg_agent.py — Wearable ECG Triage Agent
# Week 2 extension of Week 1 belief-based ECG triage agent
#
# Extends the agent with:
# 1. Formal belief update using P(evidence | state), then renormalize
# 2. Active clue selection using expected entropy reduction
# 3. Cost-based stopping rule — when to act vs wait vs retake
#
# Diagnostic hidden states (assumed population prior for wearable ST-elevation alerts):
#   stemi, artifact, hyperventilation
# Measurement quality is SEPARATE (binary): readable | unreadable
#   — not a fourth diagnostic hypothesis
#
# All priors and likelihoods in this file are ASSUMPTIONS, not measured data.
#
# Key design findings:
# - Pure expected cost minimization gives escalation threshold of 0.04%
# - Alert fatigue modeled as cumulative false-alarm cost (24h rolling window)
# - Hard safety floor at 35% STEMI probability overrides fatigue
# - Gap between mathematical (0.04%) and operational (35%) threshold
#   is where alert fatigue lives
# - Max wait safety prevents indefinite WAIT loops
# - WAIT = still among cardiac stories, gather more evidence
# - RETAKE = measurement unreadable; request a new reading (does not change
#   diagnostic truth)
#
# Every function takes plain dictionaries in and gives
# plain dictionaries back. No class, no state between calls.

from math import log2


# --- v1: prior belief over diagnostic hidden states -------------------------
# Diagnostic prior and measurement quality are INDEPENDENT.
# Clean whole-number % ≈ original 5:50:30 ratio — deliberate assumptions.
# Do NOT renormalize using the 15% unreadable rate — that is separate.
INITIAL_UNREADABLE_RATE = 0.15  # measurement-quality assumption (readable 85%)


def start_belief():
    return {
        "stemi":            0.06,  # 6%
        "artifact":         0.59,  # 59%
        "hyperventilation": 0.35,  # 35%
    }


# --- v2: update belief when new evidence arrives ----------------------------
# Multiplies current belief by P(evidence | state) then renormalizes.
# Key name "odds" is historical; values are conditional probabilities.
# Assumes conditional independence between evidence clues.
def update(belief, odds):
    scored = {w: belief[w] * odds[w] for w in belief}
    total = sum(scored.values())
    return {w: v / total for w, v in scored.items()}


# --- v3: measure uncertainty in bits ----------------------------------------
# Shannon entropy. Maximum for 3 states = log2(3) ≈ 1.585 bits.
# if p > 0 guards against log2(0) which is undefined (negative infinity)
def doubt(belief):
    return -sum(p * log2(p) for p in belief.values() if p > 0)


# --- v4: clue definitions ---------------------------------------------------
# Each clue has:
#   name     — identifier
#   price    — cost of asking (time cost during potential STEMI, ~$2)
#   chances  — assumed P(answer) used for expected entropy (not P(answer|state))
#   odds     — P(answer | state). yes + no = 1.0 WITHIN each diagnostic state.
#
# Likelihoods for stemi/artifact/hyperventilation are UNCHANGED from the
# previous tables. The old unreadable column was removed (not a diagnostic state).
# mishandling / heavy_exercise no longer "raise unreadable" in the belief —
# measurement quality is handled by the binary SQA gate instead.

chest_pain_clue = {
    "name": "chest_pain",
    "price": 2,
    "chances": {"yes": 0.2, "no": 0.8},
    "odds": {
        "yes": {"stemi": 0.75, "artifact": 0.10, "hyperventilation": 0.30},
        "no":  {"stemi": 0.25, "artifact": 0.90, "hyperventilation": 0.70},
    }
}

mishandling_clue = {
    "name": "mishandling",
    "price": 2,
    "chances": {"yes": 0.7, "no": 0.3},
    "odds": {
        "yes": {"stemi": 0.10, "artifact": 0.90, "hyperventilation": 0.20},
        "no":  {"stemi": 0.90, "artifact": 0.10, "hyperventilation": 0.80},
    }
}

poor_signal_clue = {
    "name": "poor_signal",
    "price": 2,
    "chances": {"yes": 0.7, "no": 0.3},
    "odds": {
        "yes": {"stemi": 0.05, "artifact": 0.95, "hyperventilation": 0.05},
        "no":  {"stemi": 0.95, "artifact": 0.05, "hyperventilation": 0.95},
    }
}

heavy_exercise_clue = {
    "name": "heavy_exercise",
    "price": 2,
    "chances": {"yes": 0.2, "no": 0.8},
    "odds": {
        "yes": {"stemi": 0.20, "artifact": 0.40, "hyperventilation": 0.75},
        "no":  {"stemi": 0.80, "artifact": 0.60, "hyperventilation": 0.25},
    }
}

clues = [chest_pain_clue, mishandling_clue, poor_signal_clue, heavy_exercise_clue]

# RETAKE is measurement-quality only — not a diagnostic clue.
# Does NOT Bayesian-update diagnostic belief.
# chances preserved from prior assumption (not measured data).
RETAKE_CHANCES = {
    "readable": 0.75,          # assumption: most retakes succeed
    "still_unreadable": 0.25,
}


# --- v5: clue selection -----------------------------------------------------
# expected_cut computes the weighted average entropy reduction from asking
# a clue — weighted by how likely each answer is before we ask.
# This is the EXPECTED reduction, averaged across all possible answers.
def expected_cut(belief, clue):
    after = 0.0
    for answer, chance in clue["chances"].items():
        after += chance * doubt(update(belief, clue["odds"][answer]))
    return doubt(belief) - after


# best_clue picks the clue with highest entropy reduction per price paid.
# Note: this is entropy-optimal, not cost-weighted optimal.
def best_clue(belief, clues):
    return max(clues, key=lambda c: expected_cut(belief, c) / c["price"])


# --- v6: cost of waiting for one more clue ----------------------------------
# Computes expected cost of asking one clue then acting optimally
# among dismiss vs escalate. Future escalate must match decide():
#   fatigue(base, current false_alarms_24h, posterior P(STEMI))
#   + (1 - posterior P(STEMI)) * inconvenience_cost
# false_alarms_24h is the observed history — not invented in hypothetical branches.
# delay_cost is the fixed time cost paid just by asking — time is muscle.
def cost_if_we_wait(belief, prices, clue, false_alarms_24h):
    total = 0.0
    for answer, chance in clue["chances"].items():
        post = update(belief, clue["odds"][answer])
        danger = post["stemi"]
        dismiss = danger * prices["missed_stemi"]
        escalate = (
            escalation_cost_with_fatigue(
                prices["escalation_cost"], false_alarms_24h, danger
            )
            + (1 - danger) * prices["inconvenience_cost"]
        )
        total += chance * min(dismiss, escalate)
    return prices["delay_cost"] + total


def cost_if_we_retake_no_diag_update(belief, prices, false_alarms_24h):
    """RETAKE when readable: pay delay, diagnostic belief unchanged (no info)."""
    danger = belief["stemi"]
    dismiss = danger * prices["missed_stemi"]
    escalate = (
        escalation_cost_with_fatigue(
            prices["escalation_cost"], false_alarms_24h, danger
        )
        + (1 - danger) * prices["inconvenience_cost"]
    )
    return prices["delay_cost"] + min(dismiss, escalate)


# --- v6b: alert fatigue model -----------------------------------------------
# Escalation cost that increases as false alarms in last 24h accumulate.
# Safety floor: if P(STEMI) > 35%, escalation always happens at base cost
# regardless of fatigue. The 35% threshold is an operational constraint,
# not a mathematical breakeven (which is ~0.04%).
def escalation_cost_with_fatigue(base_cost, false_alarms_24h,
                                  P_stemi, decay_rate=0.1):
    trust = max(0, 1 - decay_rate * false_alarms_24h)
    if trust > 0:
        return base_cost / trust
    else:
        if P_stemi > 0.35:
            return base_cost
        else:
            return float('inf')


# --- v7: decide what action to take -----------------------------------------
#   ESCALATE — alert clinician immediately
#   DISMISS  — treat as false alarm, no clinical action
#   WAIT     — still among cardiac stories; ask another clue
#   RETAKE   — measurement unreadable; request a new reading
#
# Decision hierarchy (before cost comparison):
#   1. Measurement-quality gate (binary; SQA outranks max_wait / safety floor):
#      unreadable + retakes < MAX_RETAKES → RETAKE
#      unreadable + retakes >= MAX_RETAKES → ESCALATE (signal-quality review)
#   2. max_wait → ESCALATE  (wait_count = diagnostic WAIT actions only;
#      RETAKE uses retake_count / MAX_RETAKES and does not consume wait budget)
#   3. Safety floor: P(STEMI) > 0.35 → ESCALATE
#   4. Else cost / VOI among ESCALATE / DISMISS / WAIT / RETAKE
MAX_RETAKES = 2  # existing retake bound — do not change without student decision


def decide(belief, prices, clue, false_alarms_24h, wait_count=0, max_wait=5,
           retake_count=0, measurement_quality="readable"):
    danger = belief["stemi"]

    # Bounded SQA — binary measurement quality (student decision).
    if measurement_quality == "unreadable":
        if retake_count < MAX_RETAKES:
            return "RETAKE", {"reason": "SQA gate: measurement unreadable"}
        return "ESCALATE", {
            "reason": "SQA retake limit: hardware/signal-quality warning "
                      f"(retakes={retake_count} >= {MAX_RETAKES})"
        }

    if wait_count >= max_wait:
        return "ESCALATE", {"reason": "max wait exceeded, uncertainty remains"}

    if danger > 0.35:
        return "ESCALATE", {"reason": "safety floor P(STEMI) > 0.35"}

    costs = {
        # inconvenience_cost ($170) = patient panic ($70) + clinician attention ($100)
        # assumption — raises escalate cost at low P(STEMI) so WAIT can win first
        "ESCALATE": escalation_cost_with_fatigue(
                        prices["escalation_cost"],
                        false_alarms_24h,
                        danger
                    ) + (1 - danger) * prices["inconvenience_cost"],
        "DISMISS":  danger * prices["missed_stemi"],
        "WAIT":     cost_if_we_wait(belief, prices, clue, false_alarms_24h),
        # Readable path: RETAKE does not update diagnostic belief (measurement-only).
        "RETAKE":   cost_if_we_retake_no_diag_update(
                        belief, prices, false_alarms_24h),
    }
    return min(costs, key=costs.get), costs


# --- prices: cost model -----------------------------------------------------
prices = {
    "missed_stemi":       500000,  # cost of missing a true STEMI (ICU + mortality)
    "escalation_cost":    200,     # cost of escalating to clinician (clinic visit)
    "delay_cost":         2,       # currently added by cost_if_we_wait for WAIT
    "inconvenience_cost": 170,     # patient panic ($70) + clinician attention ($100)
                                   # assumption, not empirically derived
}
# Cost asymmetry ratio: 2,500:1 (missed STEMI vs unnecessary escalation)
# Mathematical escalation threshold: 0.04% (where costs break even)
# With inconvenience: WAIT beats ESCALATE until ~98.8% P(STEMI) by cost alone
# Operational escalation threshold: 35% (safety floor, human operator set)


def _check_tables():
    prior = start_belief()
    assert "unreadable" not in prior
    assert set(prior) == {"stemi", "artifact", "hyperventilation"}
    assert abs(sum(prior.values()) - 1.0) < 1e-12, prior
    for clue in clues:
        for state in prior:
            yes = clue["odds"]["yes"][state]
            no = clue["odds"]["no"][state]
            assert abs(yes + no - 1.0) < 1e-12, (clue["name"], state, yes, no)
            assert "unreadable" not in clue["odds"]["yes"]
            assert "unreadable" not in clue["odds"]["no"]
    assert abs(sum(RETAKE_CHANCES.values()) - 1.0) < 1e-12


# --- example run ------------------------------------------------------------
if __name__ == "__main__":
    _check_tables()

    belief = start_belief()
    next_clue = best_clue(belief, clues)

    print(f"Initial belief: {belief}")
    print(f"States:         {sorted(belief.keys())}")
    print(f"Sum:            {sum(belief.values()):.4f}")
    print(f"Initial doubt:  {doubt(belief):.4f} bits")
    print(f"Best clue:      {next_clue['name']}")
    print(f"INITIAL_UNREADABLE_RATE (measurement): {INITIAL_UNREADABLE_RATE}")
    print()

    print("Alert fatigue effect on decisions (readable measurement):")
    for false_alarms in [0, 5, 10]:
        action, costs = decide(belief, prices, next_clue, false_alarms,
                               measurement_quality="readable")
        print(f"  False alarms 24h: {false_alarms:2d} → {action:8s} "
              f"| ESCALATE ${costs['ESCALATE']:>10.2f} "
              f"| DISMISS ${costs['DISMISS']:>10.2f} "
              f"| WAIT ${costs['WAIT']:>6.2f} "
              f"| RETAKE ${costs['RETAKE']:>6.2f}")

    print("\nMax wait override test:")
    action, costs = decide(belief, prices, next_clue,
                           false_alarms_24h=10, wait_count=5,
                           measurement_quality="readable")
    print(f"  wait_count=5, false_alarms=10 → {action}, {costs}")

    print("\nSafety floor test (hard P(STEMI) > 0.35 → ESCALATE):")
    below = {"stemi": 0.35, "artifact": 0.40, "hyperventilation": 0.25}
    above = {"stemi": 0.40, "artifact": 0.35, "hyperventilation": 0.25}
    action_b, costs_b = decide(below, prices, best_clue(below, clues),
                               false_alarms_24h=0,
                               measurement_quality="readable")
    action_a, costs_a = decide(above, prices, best_clue(above, clues),
                               false_alarms_24h=0,
                               measurement_quality="readable")
    print(f"  P(STEMI)=0.35 → {action_b}, {costs_b}")
    print(f"  P(STEMI)=0.40 → {action_a}, {costs_a}")

    print("\nHierarchy test (binary SQA before max_wait / safety floor):")
    high_stemi = {"stemi": 0.45, "artifact": 0.30, "hyperventilation": 0.25}
    low_stemi = start_belief()
    for n in (0, 1, 2):
        a, c = decide(high_stemi, prices, best_clue(high_stemi, clues), 0,
                      retake_count=n, measurement_quality="unreadable")
        print(f"  measurement=unreadable + stemi=0.45 + retakes={n} → {a}, {c}")
    a2, c2 = decide(high_stemi, prices, best_clue(high_stemi, clues), 0,
                    measurement_quality="readable")
    a3, c3 = decide(low_stemi, prices, best_clue(low_stemi, clues), 0,
                    measurement_quality="readable")
    print(f"  readable + stemi=0.45 → {a2}, {c2}")
    print(f"  readable + prior stemi → {a3}, {c3}")

    print("\nRetake measurement-quality only (diagnostic truth unchanged):")
    diag_truth = "stemi"
    measurement = "unreadable"
    print(f"  diagnostic_truth={diag_truth}, measurement={measurement}")
    # Simulate two failed then note escalate; one success leaves truth intact
    measurement = "readable"  # successful retake
    print(f"  after successful retake: measurement={measurement}, "
          f"diagnostic_truth still={diag_truth}")
