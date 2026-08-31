# Test Cases — Wearable ECG Triage Agent
## Week 1 Sprint

Format: ST Morphology | Age | History | Symptoms | True Hidden State | Agent Action

---

## True STEMI Cases

| # | ST Morphology | Age | History | Symptoms | True State | Agent Action | Reasoning |
|---|---|---|---|---|---|---|---|
| 2 | Elevation | 55 | Personal history | Chest pain | True STEMI | Escalate | Classic presentation — all signals point to STEMI |
| 6 | Elevation | 25 | Personal history | None | True STEMI | HOLD | Young age + no symptoms keeps probability below 35% |
| 7 | Elevation | 50 | None | Chest pain | True STEMI | Escalate | Chest pain + elevation crosses threshold |
| 8 | Depression | 45 | Family history | Difficulty breathing | True STEMI | Escalate | Multiple risk factors combined cross threshold |
| 10 | Elevation | 60 | None | Sweating profusely | True STEMI | Escalate | Diaphoresis + elevation at age 60 — clear emergency |
| 11 | Elevation | 23 | None | Sweating profusely | True STEMI | Escalate | Sweating outweighs age — symptom crosses threshold |
| 13 | Elevation | 50 | Personal history | Tightness in chest | True STEMI | Escalate | Full risk profile — immediate escalation |
| 16 | Depression | 60 | None | None | True STEMI | HOLD | No symptoms + no history — below 35% threshold |

---

## Electrode Artifact Cases

| # | ST Morphology | Age | History | Symptoms | True State | Agent Action | Reasoning |
|---|---|---|---|---|---|---|---|
| 1 | Elevation | 24 | None | None | Electrode artifact | HOLD | Cannot rule out STEMI without more evidence |
| 5 | Flat | 30 | None | None | Electrode artifact | Dismiss | Flat ST + no symptoms + no history — below 0.02% |
| 12 | Flat | 30 | Family history | None | Electrode artifact | Dismiss | Flat ST with no symptoms — history alone insufficient |
| 15 | Elevation | 25 | None | None | Electrode artifact | HOLD | Elevation keeps uncertainty high despite young age |
| 17 | Flat | 35 | Family history | None | Electrode artifact | Dismiss | Flat morphology + no symptoms tips below threshold |

---

## Hyperventilation Cases

| # | ST Morphology | Age | History | Symptoms | True State | Agent Action | Reasoning |
|---|---|---|---|---|---|---|---|
| 3 | Flat | 30 | None | None | Hyperventilation | Dismiss | All low-risk signals — clearly below 0.02% |
| 4 | Flat | 40 | None | Breathing difficulty | Hyperventilation | HOLD | Breathing difficulty creates uncertainty — gather more evidence |
| 9 | Flat | 30 | Personal history | None | Hyperventilation | HOLD | Personal history elevates STEMI probability above dismiss threshold |
| 14 | Flat | 30 | Family history | None | Hyperventilation | Dismiss | Flat ST + no symptoms — family history alone insufficient |

---

## Edge Cases — Near Threshold Boundaries

| # | ST Morphology | Age | History | Symptoms | True State | Agent Action | Reasoning |
|---|---|---|---|---|---|---|---|
| 18 | Elevation | 35 | Family history | None | Electrode artifact | HOLD | Family history + elevation creates borderline uncertainty — sits just above dismiss threshold |
| 19 | Flat | 70 | Personal history | Mild fatigue | True STEMI | HOLD | Age + history + fatigue elevate probability but flat ST keeps below 35% escalate threshold |
| 20 | Elevation | 28 | None | None | Hyperventilation | HOLD | Elevation alone in young patient with no symptoms — cannot dismiss, cannot escalate |

---

## Belief Update Chain — Case 1 Extended

Demonstrates how HOLD resolves through belief updating:

| Step | New Evidence | P(STEMI) | Action |
|---|---|---|---|
| Initial | Elevation, age 24, no history, no symptoms | 7% | HOLD |
| Update 1 | Patient confirms family cardiac history | 12% | HOLD |
| Update 2 | Patient reports onset of chest tightness | 28% | HOLD |
| Update 3 | Patient reports sweating and dizziness | 42% | **ESCALATE** |

---

## Summary Statistics

| Action | Count | % of cases |
|---|---|---|
| Escalate | 7 | 35% |
| HOLD | 9 | 45% |
| Dismiss | 5 | 25% |

Most cases land in HOLD — consistent with the agent's design
as a conservative evidence-gathering system biased against
premature dismissal.

---

*Week 1 Sprint — Belief Engine Course*
*Cases designed to cover all three hidden states and threshold boundaries*
