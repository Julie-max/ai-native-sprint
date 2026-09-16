# ecg_agent.py — Wearable ECG Triage Agent
# Week 2 extension of Week 1 belief-based ECG triage agent
#
# Extends the agent with three capabilities:
# 1. Formal belief update using likelihood ratios
# 2. Active clue selection using expected entropy reduction
# 3. Cost-based stopping rule — when to act vs wait
#
# Every function takes plain dictionaries in and gives
# plain dictionaries back. No class, no state between calls.

from math import log2

# --- v1: prior belief over hidden states ------------------------------------
def start_belief():
    # Baseline probabilities before any evidence is observed
    return {"stemi": 0.07, "artifact": 0.60, "hyperventilation": 0.33}


# --- v2: update belief when new evidence arrives ----------------------------
# It updates beliefs by the latest odds after latest evidence
def update(belief, odds):
    scored = {w: belief[w] * odds[w] for w in belief}
    total = sum(scored.values())
    return {w: v / total for w, v in scored.items()}


# --- v3: measure uncertainty in bits ----------------------------------------
# It calculates the amount of doubt or entropy in the current belief state
# if p > 0 guards against log2(0) which is undefined (negative infinity)
def doubt(belief):
    return -sum(p * log2(p) for p in belief.values() if p > 0)


# --- v4: clue definitions ---------------------------------------------------
# Each clue has a name, price, chances of each answer, and
# likelihood ratios (odds) per hidden state per answer.
# Odds do NOT sum to 1 — they are independent likelihoods per state.
# Price = cost of asking the question (time cost during potential STEMI)

mishandling_clue = {
    "name": "mishandling",
    "price": 2,
    "chances": {
        "yes": 0.7,
        "no": 0.3
    },
    "odds": {
        "yes": {"stemi": 0.1, "artifact": 0.9, "hyperventilation": 0.2},
        "no":  {"stemi": 0.4, "artifact": 0.1, "hyperventilation": 0.45}
    }
}

chest_pain_clue = {
    "name": "chest_pain",
    "price": 2,
    "chances": {
        "yes": 0.2,
        "no": 0.8
    },
    "odds": {
        "yes": {"stemi": 0.75, "artifact": 0.1, "hyperventilation": 0.3},
        "no":  {"stemi": 0.1, "artifact": 0.8, "hyperventilation": 0.5}
    }
}

poor_signal_clue = {
    "name": "poor_signal",
    "price": 2,
    "chances": {
        "yes": 0.7,
        "no": 0.3
    },
    "odds": {
        "yes": {"stemi": 0.05, "artifact": 0.95, "hyperventilation": 0.05},
        "no":  {"stemi": 0.4, "artifact": 0.1, "hyperventilation": 0.6}
    }
}

heavy_exercise_clue = {
    "name": "heavy_exercise",
    "price": 2,
    "chances": {
        "yes": 0.2,
        "no": 0.8
    },
    "odds": {
        "yes": {"stemi": 0.2, "artifact": 0.4, "hyperventilation": 0.75},
        "no":  {"stemi": 0.3, "artifact": 0.8, "hyperventilation": 0.1}
    }
}

clues = [chest_pain_clue, mishandling_clue, poor_signal_clue, heavy_exercise_clue]
# Note: chest_pain first because cost-weighted priority favors ruling out
# the dangerous state (STEMI) over confirming the dominant belief (artifact)


# --- v5: clue selection -----------------------------------------------------
# It computes the weighted average entropy after asking the clue
def expected_cut(belief, clue):
    after = 0.0
    for answer, chance in clue["chances"].items():
        after += chance * doubt(update(belief, clue["odds"][answer]))
    return doubt(belief) - after

# It computes the best clue that maximises the reduction of entropy per price
def best_clue(belief, clues):
    return max(clues, key=lambda c: expected_cut(belief, c) / c["price"])


# --- v6: cost of waiting for one more clue ----------------------------------
def cost_if_we_wait(belief, prices, clue):
    # Computes expected cost of asking one clue then acting optimally
    # delay_cost is the fixed time cost paid just by waiting
    total = 0.0
    for answer, chance in clue["chances"].items():
        post = update(belief, clue["odds"][answer])
        danger = post["stemi"]
        dismiss = danger * prices["missed_stemi"]
        escalate = prices["escalation_cost"]
        total += chance * min(dismiss, escalate)
    return prices["delay_cost"] + total


# --- v7: decide what action to take -----------------------------------------
# It computes the decision to be taken that costs the minimum
def decide(belief, prices, clue):
    danger = belief["stemi"]
    costs = {
        "ESCALATE": prices["escalation_cost"],
        "DISMISS":  danger * prices["missed_stemi"],
        "WAIT":     cost_if_we_wait(belief, prices, clue),
    }
    return min(costs, key=costs.get), costs


# --- prices: cost model -----------------------------------------------------
prices = {
    "missed_stemi":    500000,  # cost of missing a true STEMI
    "escalation_cost": 200,     # cost of escalating to clinician
    "delay_cost":      2,       # cost of asking one question (time cost)
}
# Simplification: false_alarm_cost folded into escalation_cost
# A real-world extension would separate clinic visit cost from
# additional anxiety/repeat-testing cost of a false alarm


# --- example run ------------------------------------------------------------
if __name__ == "__main__":
    belief = start_belief()
    print(f"Initial belief: {belief}")
    print(f"Initial doubt: {doubt(belief):.4f} bits")

    next_clue = best_clue(belief, clues)
    print(f"Best clue to ask: {next_clue['name']}")

    action, costs = decide(belief, prices, next_clue)
    print(f"Decision: {action}")
    print(f"Costs: {costs}")
