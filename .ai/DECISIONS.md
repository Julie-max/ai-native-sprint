# Decisions

---

Decision:
Use likelihood-ratio multiplication (not Bayes formula in full form) for belief updates.

Reason:
Likelihood ratios naturally handle evidence that doesn't partition the space.
Renormalizing after multiplication gives the correct posterior.
Avoids computing the normalizing constant explicitly.

Date:
Week 2 implementation

Alternatives considered:
Full Bayes formula with explicit P(evidence). Rejected: requires knowing P(e)
which is expensive to compute accurately with multiple hidden states.

Consequences:
Assumes conditional independence of clues. When multiple clues are chained,
errors compound. This is the primary known limitation of the Week 2 agent.

---

Decision:
Entropy-optimal clue selection (max expected entropy reduction / price),
NOT cost-weighted clue selection (max reduction in expected STEMI cost / price).

Reason:
Entropy measures information gain without requiring a cost model.
The two objectives can diverge: chest_pain might be cost-optimal (directly
reduces danger estimate) while poor_signal might be entropy-optimal
(maximally separates the three states). Both are defensible — the code
uses entropy-optimal and documents the distinction.

Date:
Week 2 implementation

Alternatives considered:
Cost-weighted clue selection. Still valid alternative — not implemented.

Consequences:
In STEMI context, cost-weighted might be preferable clinically.
The gap between objectives is a research-quality observation worth
including in the Week 2 paper.

---

Decision:
Two-threshold design: mathematical threshold (0.04%) vs operational floor (35%).

Reason:
Pure expected cost minimization gives p* = C_escalate / (C_escalate + C_missed_stemi)
= 200 / (200 + 500000) ≈ 0.04%. This is mathematically correct but operationally
unacceptable — a 0.04% threshold would escalate nearly every alert.
Human operators set a 35% floor as a practical constraint. The gap between
0.04% and 35% is where alert fatigue lives.

Date:
Week 1 design, formalized in Week 2 implementation

Alternatives considered:
Single threshold. Rejected: doesn't model the human-operator constraint.

Consequences:
Creates a "dead zone" between 0.04% and 35% where the agent must gather
evidence. Alert fatigue is modeled as the cost of repeated escalations
in this zone. This is the central design tension of the project.

---

Decision:
Alert fatigue modeled as escalation cost rising with 24h false alarm count
(trust decay: effective_cost = base_cost / max(0, 1 - rate * false_alarms)).
Safety floor: P(STEMI) > 35% always escalates at base cost regardless of fatigue.

Reason:
Addresses the AI review feedback that the original agent ignored the human
loop. Alert fatigue is a real clinical problem. Modeling it as cost increase
rather than probability change keeps the decision framework consistent.

Date:
Week 2 final implementation

Alternatives considered:
Model fatigue as reducing the likelihood that escalation is acted on
(i.e. change the action success probability). Rejected as more complex
and harder to calibrate without real data.

Consequences:
Alert fatigue is implemented but not validated against real clinical data.
The 24h rolling window and 0.1 decay rate are engineering choices, not
empirically derived. This must be declared as a limitation in the paper.

---

Decision:
Use one population prior for wearable ST-elevation alerts, not a new
7/60/33 pie per patient. The 24-year-old no-history case is a worked
example of that prior, not the source of the numbers. Origin: assumption.

Reason:
Week 2 simulation and ecg_agent.py need one start_belief(). Per-case priors
would be extra invented numbers with no data. Age/history/symptoms should
update the prior as evidence, not be baked in and then counted again.

Date:
2026-09-17 coaching sitting

Alternatives considered:
Case-specific priors. Rejected for now as more fiction, not more truth.

Consequences:
A 70-year-old hospital patient is a different population; that is a later
generalization issue. Double-counting age/history into prior AND clues is forbidden.

---

Decision:
Add residual hidden state `unreadable` (signal insufficient). Do not fold
poor contact / wrong lead / unreadable into artifact. Do not treat WAIT as
that state. Code stays 3-state until the student chooses four percentages
and asks for a code change.

Reason:
Artifact means readable but fake ST; unreadable means no trustworthy ST.
Dismissing unreadable can hide STEMI. The honest action is retake, which
the three-state agent cannot infer.

Date:
2026-09-17 coaching sitting

Alternatives considered:
Force every alert into three states; map unreadable to artifact. Student
initially leaned that way; rejected after the WAIT-vs-state distinction.

Consequences:
Four priors must sum to 1. Likelihoods for unreadable are required in Stage 2.
Paper must say the running code is still 3-state until updated.

---

Decision:
Likelihood tables are P(answer | state) with yes+no = 1.0 within each state,
not unnormalized likelihood ratios. Prior is 5/50/30/15 (assumption).
RETAKE is a named action. Retake expected cost is a placeholder:
retake_fee + (1 - P(unreadable)) * escalation_cost, not unreadable * escalation_cost.

Reason:
Student chose these numbers in Claude. The draft RETAKE = unreadable * $200
would win at the 15% prior ($30 vs escalate $200) and break the fatigue demo.
The placeholder is cheap only when unreadable is high (80% → RETAKE $90).

Date:
2026-09-17 code update from Claude handoff

Alternatives considered:
RETAKE = unreadable * escalation_cost (handoff draft). Rejected: always
RETAKE on a fresh alert. RETAKE = flat $200. Rejected: never beats ESCALATE
on ties (insertion order) so the 80% test would not fire RETAKE.

Consequences:
retake_cost = $50 is not derived. mishandling and heavy_exercise both load
unreadable (correlated). poor_signal is uninformative between STEMI and
hyperventilation by design. Code now has four states; old "code stays 3-state"
note above is obsolete.

---

Decision:
RETAKE is costed like WAIT: cost_if_we_wait(belief, prices, retake_clue).
retake_clue is NOT in the four-clue list. All retake numbers are assumptions.

Reason:
Student handoff 17 Sep evening. Retake outcome is about signal quality, not
diagnosis (cardiac likelihoods 0.5/0.5).

Date:
2026-09-17 evening

Consequences:
With current lookahead (after any evidence, act = min(dismiss, escalate) and
escalate is almost always $200), RETAKE costs $202 vs ESCALATE $200, so
RETAKE never wins. Student must reason this; implementer did not change it.
cost_if_we_wait uses delay_cost=$2, not retake_clue price=$5.
Open: wait_count on RETAKE; whether best_clue should see retake_clue.

---

Decision:
Add inconvenience_cost ($170) as explicit penalty in ESCALATE cost formula:
ESCALATE = escalation_cost + (1 - P(STEMI)) × inconvenience_cost
This makes WAIT cheaper than ESCALATE at low P(STEMI), forcing the
agent to gather evidence before acting.

Reason:
$200 clinic visit cost alone made ESCALATE always cheaper than WAIT ($202),
causing the agent to escalate without gathering any evidence — identical
to Always Escalate baseline. Inconvenience cost models patient panic ($70)
and wasted clinician attention ($100) — real costs absent from original model.

Date: Wednesday after Week 7

Alternatives considered:
Option A: flat $200 always (original — agent never gathers evidence)
Option B: (1-P) × $200 (ESCALATE still wins at prior)
Option C: $200 + (1-P) × $170 (chosen — WAIT wins at prior)

Consequences:
Agent now gathers evidence below 35% safety floor.
WAIT wins over ESCALATE until P(STEMI) crosses 98.8% mathematically,
but safety floor fires at 35% in practice.
$170 is an assumption — $70 patient panic + $100 clinician attention.
Needs empirical validation.
