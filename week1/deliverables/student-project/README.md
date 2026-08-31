# Wearable ECG Triage Agent
## Week 1 Deliverable — Belief Engine Course

### Problem Statement

The agent observes ST segment morphology, age, prior cardiac history,
and reported symptoms. It must select to dismiss, HOLD, or escalate
to a clinician — because True STEMI, electrode artifact, or
hyperventilation is not known.

### Key Design Decisions

- Cost asymmetry: 2,500:1 (missed STEMI vs unnecessary escalation)
- Dismiss threshold: 0.02% STEMI probability
- Escalate threshold: 35% STEMI probability
- HOLD zone: everything between thresholds

### Files

| File | Description |
|---|---|
| research-file.md | Problem research and motivation |
| agent-design.md | Formal 7-component agent specification |
| test-cases.md | 20 test scenarios across all hidden states |
| decisions/probability-decision-record.md | Worked cost-reasoning examples |
| discussion-record.md | Reddit and X community discussions |
| paper/main.tex | LaTeX preprint |
| social/ | LinkedIn and X posts |

### Dataset

MIT-BIH Arrhythmia Database — physionet.org
