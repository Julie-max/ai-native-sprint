# Formal Agent Design
## Wearable ECG Triage Agent — Week 1

---

## Agent Identity

**Name:** Wearable ECG Triage Agent
**Context:** Wearable ECG patch worn by patient outside clinical setting
**Purpose:** Replace dumb single-threshold alarms with belief-based
triage decisions when a doctor is not immediately present

---

## Component 1 — Percepts (What the agent observes)

The agent observes four inputs:

| Input | Type | Example values |
|---|---|---|
| ST segment morphology | Categorical | elevation / depression / flat |
| Age | Numeric | 18 — 80 years |
| Prior cardiac / medical history | Categorical | none / family history / personal history |
| Reported symptoms | Categorical | none / chest pain / exertion-related |

The agent cannot observe the raw ECG signal directly.
It observes derived features from the signal.

---

## Component 2 — Hidden States (What the agent can never directly observe)

Three mutually exclusive hidden states:

| Hidden State | Description |
|---|---|
| **True STEMI** | Genuine cardiac emergency — transmural ischemia requiring immediate intervention |
| **Electrode artifact** | Technical error — misplaced or disturbed electrode producing false ST change |
| **Hyperventilation** | Physiological but non-cardiac ST change — real signal, not a heart attack |

The agent never observes which state is true.
It maintains a probability distribution across all three.
All three probabilities must sum to 100%.

---

## Component 3 — Actions (What the agent can do)

Three possible actions:

| Action | Description | Designed for |
|---|---|---|
| **Escalate** | Immediately alert clinician | High STEMI probability |
| **HOLD** | Log event, gather more evidence, monitor | Uncertain — high entropy state |
| **Dismiss** | Treat alert as false alarm, no clinical action | Very low STEMI probability |

---

## Component 4 — Cost Function

| Wrong Action | True Hidden State | Cost |
|---|---|---|
| Dismiss | True STEMI | $500,000 (ICU + surgery + mortality risk) |
| Escalate | Electrode artifact | $200 (unnecessary clinic visit + anxiety) |
| Escalate | Hyperventilation | $200 (unnecessary clinic visit + anxiety) |
| HOLD delay | True STEMI | Time cost — ~1B cardiac cells per 30 min delay |

**Cost asymmetry ratio: 2,500:1**

The agent is strongly biased toward escalation over dismissal
because the cost of missing a true STEMI vastly exceeds the cost
of an unnecessary clinic visit.

---

## Component 5 — Policy (How the agent decides)

Fixed thresholds derived from expected cost calculations:

```
P(STEMI) < 0.02%   → DISMISS
P(STEMI) > 35%     → ESCALATE
Otherwise          → HOLD
```

**Threshold derivation:**

Dismiss threshold (0.02%):
- Expected cost of dismiss: 0.0002 × $500,000 = $100
- Expected cost of escalate: 0.9998 × $200 = $199.96
- $100 < $199.96 → dismiss justified below 0.02%

Escalate threshold (35%):
- Expected cost of delay: 0.35 × $500,000 = $175,000
- Expected cost of escalate: 0.65 × $200 = $130
- $175,000 >> $130 → escalate immediately above 35%

---

## Component 6 — Belief Update (How new evidence changes the agent)

When new evidence arrives, the agent updates the probability
distribution across hidden states. Thresholds remain fixed.
Only probabilities change.

**Example updates:**

| New evidence | Effect on P(STEMI) |
|---|---|
| Patient confirms family cardiac history | 7% → 12% |
| Patient confirms device was dropped/mishandled | 7% → 0.001% |
| Patient reports onset of chest pain | Increases toward escalate threshold |
| Patient reports relief after resting | Decreases toward dismiss threshold |

Each update is re-evaluated against the fixed policy thresholds.
If updated P(STEMI) crosses a threshold — action changes immediately.

---

## Component 7 — Termination Condition

The agent commits to a final action when:

1. **P(STEMI) crosses the escalate threshold (35%)** — agent escalates,
   no further evidence gathering
2. **P(STEMI) drops below the dismiss threshold (0.02%)** — agent
   dismisses, alert closed
3. **Maximum HOLD time exceeded** — agent escalates by default
   (time is muscle — indefinite holding is not permitted for
   cardiac events)

The agent does not terminate while in HOLD state unless a threshold
is crossed or maximum hold time is reached.

---

## Baseline Belief State (Prior)

For a new alert with no additional context:

| Hidden State | Prior Probability |
|---|---|
| True STEMI | 7% |
| Electrode artifact | 60% |
| Hyperventilation | 33% |

This prior reflects the general population of wearable ECG alerts —
most false alerts are artifact or physiological, not true STEMI.

---

*Week 1 Sprint — Belief Engine Course*
*Agent design derived from cost-reasoning and community feedback*
