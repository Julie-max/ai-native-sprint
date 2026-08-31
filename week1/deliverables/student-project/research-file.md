# Research File — Wearable ECG Triage Agent
## Week 1 Sprint — Belief Engine Course

---

## Problem Statement

The agent observes ST segment morphology, age, prior cardiac history,
and reported symptoms. It must select to dismiss the alert, HOLD
(log and monitor), or escalate to a clinician — because True STEMI,
electrode artifact, or hyperventilation is not known.

---

## Why Existing Approaches Fail

A simple classifier would pick between two or three categories and
have an accuracy of 95% or something, but the 5% that the classifier
missed might be the highest cost factor. A classifier that is 95%
accurate but always wrong on true STEMI cases is not 95% useful —
it is actively dangerous. Accuracy hides cost asymmetry. The 92%
lie: a classifier that never predicts STEMI can be 92% accurate
because most alerts are not STEMI. That accuracy number means
nothing when the missed 8% is a patient dying at home.

---

## Key Dataset

The MIT-BIH Arrhythmia Database is a public dataset of 48 half-hour
ECG recordings from 47 patients, annotated beat-by-beat by
cardiologists, available free at physionet.org. It provides realistic
ECG signal data with ground truth labels for building and testing
the agent's belief states.

---

## Open Questions This Agent Addresses

- **Cost-aware decision making:** A classifier outputs a label.
  The agent asks — what is the expected cost of each action given
  current belief? A 7% STEMI probability is not safe to dismiss
  when the cost of missing it is $500,000.

- **Belief updating on new evidence:** The agent updates its hidden
  state probabilities when new inputs arrive — family history,
  device mishandling confirmation, symptom changes. A classifier
  gives one static output per input. The agent reasons over time.

- **High entropy holding:** When the agent cannot distinguish between
  hidden states with enough confidence, it holds rather than guessing.
  A classifier is forced to pick a label even when maximally uncertain.

---

## Dataset Simulation Plan

Since raw ECG signal processing is outside the scope of Week 1,
the agent will be tested on simulated feature vectors representing
the four input dimensions:

| Feature | Simulated range |
|---|---|
| ST morphology | elevation / depression / flat |
| Age | 18 — 80 |
| Prior cardiac history | none / family history / personal history |
| Reported symptoms | none / chest pain / exertion-related |

30 test cases will be constructed covering all three hidden states
and edge cases near the dismiss and escalate thresholds.

---

## Communities Consulted

| Community | Platform | Purpose |
|---|---|---|
| r/BiomedicalEngineers | Reddit | Validate cost ratio, electrode artifact rates |
| r/deeplearning | Reddit | Warmup comment on MI classification thesis |

### Key Reddit Feedback Received

**From u/500_Shames on r/BiomedicalEngineers:**
- Praised cost-ratio framing as the right way to think about this
- Challenged the definition of "wearable triage agent"
- Challenged comparison to doctor performance vs. status quo

---

## What Changed After Community Feedback

The Reddit feedback clarified two important things about the agent
design. First, why this is an agent and not just a rule-based
classification — the thresholds are fixed but the probabilities
update on new evidence, which is what makes it a belief engine
rather than an if-else statement. Second, the gap the agent is
filling — it is not trying to replace a doctor. It is replacing
a dumb single-threshold alarm on a wearable device that fires the
same way for electrode artifact and true STEMI alike. The agent
improves on that by distinguishing between hidden states and holding
for more evidence when uncertain, specifically in contexts where
a doctor is not immediately present or accessible.

---

## Cost Model Summary

| Parameter | Value | Reasoning |
|---|---|---|
| Missed STEMI cost | $500,000 | ICU + emergency surgery + mortality risk |
| Unnecessary escalation cost | $200 | Clinic visit + patient anxiety |
| Cost asymmetry ratio | 2,500:1 | |
| Dismiss threshold | 0.02% STEMI probability | Expected cost $100 < $199.96 |
| Escalate threshold | 35% STEMI probability | Expected cost $175,000 >> $130 |
| HOLD zone | 0.02% — 35% | Gather more evidence |

---

*Week 1 Sprint — Belief Engine Course*
*Research informed by community discussions and cost-reasoning sessions*
