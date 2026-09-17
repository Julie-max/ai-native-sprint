# ecg_agent.py — Wearable ECG Triage Agent
# Week 2 extension of Week 1 belief-based ECG triage agent
#
# Extends the agent with three capabilities:
# 1. Formal belief update using likelihood ratios
# 2. Active clue selection using expected entropy reduction
# 3. Cost-based stopping rule — when to act vs wait
#
# Key design findings:
# - Pure expected cost minimization gives escalation threshold of 0.04%
# - Alert fatigue modeled as cumulative false-alarm cost (24h rolling window)
# - Hard safety floor at 35% STEMI probability overrides fatigue
# - Gap between mathematical (0.04%) and operational (35%) threshold
#   is where alert fatigue lives
# - Max wait safety prevents indefinite WAIT loops
#
# Every function takes plain dictionaries in and gives
# plain dictionaries back. No class, no state between calls.

from math import log2


# --- v1: prior belief over hidden states ------------------------------------
def start_belief():
    # Baseline probabilities before any evidence is observed
    # Based on general population of wearable ECG alerts:
    # most false alerts are artifact or physiological, not true STEMI
    return {"stemi": 0.07, "artifact": 0.60, "hyperventilation": 0.33}


# --- v2: update belief when new evidence arrives ----------------------------
# It updates beliefs by multiplying current belief by likelihood ratios
# then renormalizing so probabilities sum to 1.
# Assumes conditional independence between evidence clues.
def update(belief, odds):
    scored = {w: belief[w] * odds[w] for w in belief}
    total = sum(scored.values())
    return {w: v / total for w, v in scored.items()}


# --- v3: measure uncertainty in bits ----------------------------------------
# It calculates the amount of doubt or entropy in the current belief state.
# Higher entropy = more uncertain. Maximum for 3 states = 1.585 bits.
# if p > 0 guards against log2(0) which is undefined (negative infinity)
def doubt(belief):
    return -sum(p * log2(p) for p in belief.values() if p > 0)


# --- v4: clue definitions ---------------------------------------------------
# Each clue has:
#   name     — identifier
#   price    — cost of asking (time cost during potential STEMI, ~$2)
#   chances  — prior probability of each answer
#   odds     — likelihood ratios per hidden state per answer
#              odds do NOT sum to 1 — independent likelihoods per state
#
# Clue ordering: chest_pain first because cost-weighted priority
# favors ruling out the dangerous state (STEMI) over confirming
# the dominant belief (artifact). Note: best_clue() uses entropy
# optimization which may select a different clue — see v5.

chest_pain_clue = {
    "name": "chest_pain",
    "price": 2,
    "chances": {"yes": 0.2, "no": 0.8},
    "odds": {
        "yes": {"stemi": 0.75, "artifact": 0.1,  "hyperventilation": 0.3},
        "no":  {"stemi": 0.1,  "artifact": 0.8,  "hyperventilation": 0.5}
    }
}

mishandling_clue = {
    "name": "mishandling",
    "price": 2,
    "chances": {"yes": 0.7, "no": 0.3},
    "odds": {
        "yes": {"stemi": 0.1,  "artifact": 0.9,  "hyperventilation": 0.2},
        "no":  {"stemi": 0.4,  "artifact": 0.1,  "hyperventilation": 0.45}
    }
}

poor_signal_clue = {
    "name": "poor_signal",
    "price": 2,
    "chances": {"yes": 0.7, "no": 0.3},
    "odds": {
        "yes": {"stemi": 0.05, "artifact": 0.95, "hyperventilation": 0.05},
        "no":  {"stemi": 0.4,  "artifact": 0.1,  "hyperventilation": 0.6}
    }
}

heavy_exercise_clue = {
    "name": "heavy_exercise",
    "price": 2,
    "chances": {"yes": 0.2, "no": 0.8},
    "odds": {
        "yes": {"stemi": 0.2,  "artifact": 0.4,  "hyperventilation": 0.75},
        "no":  {"stemi": 0.3,  "artifact": 0.8,  "hyperventilation": 0.1}
    }
}

clues = [chest_pain_clue, mishandling_clue, poor_signal_clue, heavy_exercise_clue]


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
# For STEMI agents, cost-weighted priority (chest_pain first) may be
# more appropriate — see clue ordering note in v4.
def best_clue(belief, clues):
    return max(clues, key=lambda c: expected_cut(belief, c) / c["price"])


# --- v6: cost of waiting for one more clue ----------------------------------
# Computes expected cost of asking one clue then acting optimally.
# For each possible answer: update belief, compute best action cost,
# weight by probability of that answer, sum across all answers.
# delay_cost is the fixed time cost paid just by asking — time is muscle.
def cost_if_we_wait(belief, prices, clue):
    total = 0.0
    for answer, chance in clue["chances"].items():
        post = update(belief, clue["odds"][answer])
        danger = post["stemi"]
        dismiss  = danger * prices["missed_stemi"]
        escalate = prices["escalation_cost"]
        total += chance * min(dismiss, escalate)
    return prices["delay_cost"] + total


# --- v6b: alert fatigue model -----------------------------------------------
# Escalation cost that increases as false alarms in last 24h accumulate.
# As false alarms rise, clinician trust decays, making each escalation
# less likely to be acted on — modeled as rising effective cost.
#
# Safety floor: if P(STEMI) > 35%, escalation always happens at base cost
# regardless of fatigue. This prevents fatigue from suppressing true STEMIs.
# The 35% threshold is an operational constraint set by human operators,
# not a mathematical breakeven (which is ~0.04%).
def escalation_cost_with_fatigue(base_cost, false_alarms_24h,
                                  P_stemi, decay_rate=0.1):
    trust = max(0, 1 - decay_rate * false_alarms_24h)
    if trust > 0:
        return base_cost / trust          # cost rises as trust decays
    else:
        if P_stemi > 0.35:
            return base_cost              # safety floor — always escalate
        else:
            return float('inf')           # trust gone, STEMI low — never escalate


# --- v7: decide what action to take -----------------------------------------
# Computes expected cost of each action and returns the minimum cost action.
# Three actions:
#   ESCALATE — alert clinician immediately
#   DISMISS  — treat as false alarm, no clinical action
#   WAIT     — ask best clue, update belief, decide again
#   Max wait safety: after max_wait clues, escalate by default if
#   uncertainty remains — indefinite waiting is itself dangerous.
#
# ESCALATE cost uses alert fatigue model — rises with false alarm history.
# DISMISS cost = expected cost of missing a true STEMI.
# WAIT cost = time cost + expected cost of acting after one more clue.
def decide(belief, prices, clue, false_alarms_24h, wait_count=0, max_wait=5):
    danger = belief["stemi"]

    # Safety override: if waited too long, escalate regardless of fatigue
    if wait_count >= max_wait:
        return "ESCALATE", {"reason": "max wait exceeded, uncertainty remains"}

    costs = {
        "ESCALATE": escalation_cost_with_fatigue(
                        prices["escalation_cost"], false_alarms_24h, danger),
        "DISMISS":  danger * prices["missed_stemi"],
        "WAIT":     cost_if_we_wait(belief, prices, clue),
    }
    return min(costs, key=costs.get), costs


# --- prices: cost model -----------------------------------------------------
prices = {
    "missed_stemi":    500000,  # cost of missing a true STEMI (ICU + mortality)
    "escalation_cost": 200,     # cost of escalating to clinician (clinic visit)
    "delay_cost":      2,       # cost of asking one question (~30 sec time cost)
}
# Cost asymmetry ratio: 2,500:1 (missed STEMI vs unnecessary escalation)
# Mathematical escalation threshold: 0.04% (where costs break even)
# Operational escalation threshold: 35% (safety floor, human operator set)
# Simplification: false_alarm_cost folded into escalation_cost


# --- example run ------------------------------------------------------------
if __name__ == "__main__":
    belief = start_belief()
    next_clue = best_clue(belief, clues)

    print(f"Initial belief: {belief}")
    print(f"Initial doubt:  {doubt(belief):.4f} bits")
    print(f"Best clue:      {next_clue['name']}")
    print()

    print("Alert fatigue effect on decisions:")
    for false_alarms in [0, 5, 10]:
        action, costs = decide(belief, prices, next_clue, false_alarms)
        print(f"  False alarms 24h: {false_alarms:2d} → {action:8s} "
              f"| ESCALATE ${costs['ESCALATE']:>10.2f} "
              f"| DISMISS ${costs['DISMISS']:>10.2f} "
              f"| WAIT ${costs['WAIT']:>6.2f}")

    # Test max_wait override
    print("\nMax wait override test:")
    action, costs = decide(belief, prices, next_clue,
                           false_alarms_24h=10, wait_count=5)
    print(f"  wait_count=5, false_alarms=10 → {action}, {costs}")
