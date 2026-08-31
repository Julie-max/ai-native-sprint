# Probability Decision Record
## Wearable ECG Triage Agent — Week 1

---

## Core Cost Model

| Outcome | Cost |
|---|---|
| Missed true STEMI (false dismiss) | $500,000 (ICU + surgery + mortality risk) |
| Unnecessary escalation (false alert) | $200 (clinic visit + patient anxiety) |
| Cost asymmetry ratio | 2,500:1 |

---

## Threshold Derivation

### Dismiss Threshold — 0.02%

**Condition:** Expected cost of dismissing < Expected cost of escalating

At p = 0.0002 (0.02%):
- Expected cost of DISMISS: 0.0002 × $500,000 = **$100**
- Expected cost of ESCALATE: 0.9998 × $200 = **$199.96**

$100 < $199.96 → DISMISS is justified below 0.02%

### Escalate Threshold — 35%

**Condition:** Expected cost of waiting > Expected cost of escalating

At p = 0.35 (35%):
- Expected cost of HOLD/delay: 0.35 × $500,000 = **$175,000**
- Expected cost of ESCALATE: 0.65 × $200 = **$130**

$175,000 >> $130 → ESCALATE immediately above 35%

### HOLD Zone — 0.02% to 35%

Agent gathers more evidence. Belief state updates on new inputs.
No irreversible action taken until threshold is crossed.

---

## Decision Entry 1 — Baseline Scenario

**Scenario:** Young patient, no history, no symptoms, mild ST elevation on wearable patch.

### Observed Inputs

| Input | Value |
|---|---|
| ST morphology | Slight elevation |
| Age | 24 |
| Prior cardiac history | None |
| Reported symptoms | None |

### Belief State

| Hidden State | Probability |
|---|---|
| True STEMI | 7% |
| Electrode artifact | 60% |
| Hyperventilation | 33% |
| **Total** | **100%** |

### Decision

**Action: HOLD**

**Reasoning:**
- STEMI probability = 7%
- 7% sits between dismiss threshold (0.02%) and escalate threshold (35%)
- Expected cost of dismissing at 7%: 0.07 × $500,000 = **$35,000**
- Expected cost of escalating at 7%: 0.93 × $200 = **$186**
- Neither dismiss nor escalate is clearly optimal given uncertainty
- HOLD chosen to gather additional evidence before crossing either threshold
- Time cost of HOLD is minimal relative to $35,000 expected dismiss cost

---

## Decision Entry 2 — Belief Update: Positive Family History

**New evidence:** Patient reports hereditary cardiac condition in parents.

### Updated Belief State

| Hidden State | Probability |
|---|---|
| True STEMI | 12% |
| Electrode artifact | 52% |
| Hyperventilation | 36% |

### Decision

**Action: HOLD (continued)**

**Reasoning:**
- Family history shifts STEMI from 7% → 12%
- 12% still below escalate threshold of 35%
- But expected dismiss cost now: 0.12 × $500,000 = **$60,000**
- Agent continues HOLD, now with higher urgency
- Next evidence that crosses 35% triggers immediate escalation

---

## Decision Entry 3 — Belief Update: Device Mishandling Confirmed

**New evidence:** Patient confirms device was dropped and re-attached without cleaning.

### Updated Belief State

| Hidden State | Probability |
|---|---|
| True STEMI | 0.001% |
| Electrode artifact | 90% |
| Hyperventilation | ~10% |

### Decision

**Action: DISMISS**

**Reasoning:**
- Mishandling confirmation shifts STEMI to 0.001% — below dismiss threshold of 0.02%
- Expected cost of dismissing: 0.00001 × $500,000 = **$5**
- Expected cost of escalating: 0.99999 × $200 = **$200**
- $5 < $200 → DISMISS is now the lowest expected cost action
- First scenario where dismiss is justified
- Agent logs event for monitoring but takes no clinical action

---

## Key Insight

The agent never decides based on probability alone.
Every action is driven by: **Expected Cost = Probability × Cost of Being Wrong**

A 7% STEMI probability is not "small enough to dismiss."
It produces a $35,000 expected cost — which dwarfs the $186 cost of holding.

This is the core principle: **asymmetric costs make low probabilities dangerous.**

---

*Generated during Week 1 Sprint — Belief Engine Course*
*Agent: Wearable ECG ST-Segment Triage Agent*
*Student reasoning documented, not AI-generated decisions*
