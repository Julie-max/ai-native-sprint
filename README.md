# AI Native Sprint

Weekly deliverables for the Belief Engine course — AI Native Shipping Sprint.

## Structure

```
week1/
└── deliverables/
    └── student-project/
        ├── README.md
        ├── research-file.md
        ├── agent-design.md
        ├── test-cases.md
        ├── discussion-record.md
        ├── review-record.md
        ├── paper/
        │   ├── main.tex
        │   └── preprint.pdf
        ├── src/
        ├── data/
        ├── experiments/
        ├── results/
        ├── decisions/
        │   └── probability-decision-record.md
        └── social/
            ├── linkedin-post.md
            └── x-thread.md
```

## Week 1 — Wearable ECG Triage Agent

An agent that observes ST segment morphology, age, prior cardiac
history, and reported symptoms from a wearable ECG patch.
It selects dismiss, HOLD, or escalate because True STEMI,
electrode artifact, or hyperventilation is not known.
