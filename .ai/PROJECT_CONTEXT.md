# Project Context

## Purpose

Student deliverable repository for Antern's AI-Native Placement Sprint.
The vehicle problem is a **Wearable ECG Triage Agent** — chosen to demonstrate
AI-native engineering skills: probabilistic reasoning, cost-asymmetric decisions,
AI-assisted design, and public shipping.

The real course goal is placement: build a visible engineering trail
(preprints, GitHub, LinkedIn, Reddit) that demonstrates you can think and ship
like an AI-native engineer.

## Problem Statement

> The agent observes ST segment morphology, age, prior cardiac history,
> and reported symptoms from a wearable ECG patch. It must dismiss, WAIT,
> or escalate because True STEMI, electrode artifact, or hyperventilation
> is not known. (Week 1 named the middle action HOLD; Week 2 code uses WAIT.)

## Architecture

### Hidden states
Week 1 / current code (3 states, assumed, treated as a population prior for
wearable ST-elevation alerts, not measured):
- True STEMI 7%
- Electrode artifact 60% (readable but fake ST)
- Hyperventilation 33%

Week 2 design (now in `ecg_agent.py`, all assumed):
- True STEMI 5%
- Electrode artifact 50% (readable but fake ST)
- Hyperventilation 30%
- Unreadable 15% (no trustworthy ST; action = RETAKE)

### Actions
- ESCALATE — alert clinician immediately
- HOLD / WAIT — gather more evidence (not a hidden state)
- DISMISS — treat as false alarm
- RETAKE — new tracing; placeholder cost, not derived

### Cost model
- Missed STEMI: $500,000
- Unnecessary escalation: $200
- Delay (per clue): $2
- Cost asymmetry ratio: 2,500:1
- Mathematical escalation threshold: 0.04% (expected cost breakeven)
- Operational safety floor: 35% (human-operator constraint)

### Week 2 extensions (implemented in ecg_agent.py)
- Bayesian belief update via likelihood ratios + renormalization
- Shannon entropy to measure uncertainty (bits)
- Active clue selection: max expected entropy reduction / price
- Cost-based act-vs-wait stopping rule
- Alert fatigue model: escalation cost rises with 24h false alarm count
- Safety floor: P(STEMI) > 35% always escalates regardless of fatigue
- Max-wait override: after 5 clues, force ESCALATE

## Key Technologies

- Python 3, stdlib only (`math`) — no ML frameworks
- LaTeX (IJCAI-style article class) for preprints
- Git + GitHub (`https://github.com/Julie-max/ai-native-sprint`)

## Repository Layout

```
week1/deliverables/student-project/
├── README.md
├── research-file.md
├── agent-design.md
├── test-cases.md
├── discussion-record.md
├── review-record.md
├── decisions/probability-decision-record.md
├── paper/main.tex + main.pdf + figures/
└── social/linkedin-post.md + x-thread.md

week2/deliverables/student-project/
├── src/ecg_agent.py          ← only file that exists
├── decisions/                ← EMPTY (needs belief-update-record.md)
└── paper/                    ← EMPTY (needs main.tex + compiled PDF)
```

## Course Deliverable Requirements (per course brief)

### Week 1 — complete
- Research file, agent design, 20 test cases, decision record,
  discussion record, review record, IJCAI preprint, social posts

### Week 2 — code done, documents missing
Primary deliverable: **one self-contained IJCAI-style PDF preprint**
Required sections: Abstract, Intro, Related Work, Probabilistic View,
Information-Theoretic View, Information Selection, Decision Policy,
Experiment (≥100 cases, ≥2 policies + baseline), Results, Failure
Analysis, Human Discussions, Limitations, New Questions, AI-use
statement, References, Appendix (20 core questions).
Also required: 5 LinkedIn posts, updated discussion-record.md,
decisions/decision-record.md, README.md

### Weeks 3–6 — learning only
Week 4 traction deliverable: 4–5 LinkedIn posts/week, Reddit
discussions, 2–4 LinkedIn comments/day (tracked via Pangram).

## Important Constraints

- Do not fabricate experiment numbers — label hypotheticals
- No unread citations
- Conditional independence assumed in chained clue updates (known limitation)
- The `.gitignore` already excludes LaTeX aux/log/out files
- Week 2 paper must stand alone without requiring the code to be read
