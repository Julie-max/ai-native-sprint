# Handoff

CURRENT GOAL:
Student reviews clean 6%/59%/35% prior results. No further Cursor work
until next handoff.

CURRENT STATE:
- Diagnostic prior locked: stemi 0.06, artifact 0.59, hyperventilation 0.35
- INITIAL_UNREADABLE_RATE=0.15 independent (not renormalized into diagnosis)
- Sim seed=42: P0 recall 1.0 cost $200k; P1 recall 0.620 cost $9.53M FN=19

FLAGS:
1. Policy 1 still FN-dominated on total cost
2. Sampled truth counts 50/570/380 vs expected ~60/590/350 (RNG variance)

FILES CHANGED:
- week2/.../src/ecg_agent.py (prior + comments only)
- week2/.../experiments/simulation.py (expect-counts comment only)
- cursor-handoff.md
- .ai/HANDOFF.md

DO NOT REDO:
- Reintroduce unreadable into diagnostic belief
- Renormalize prior with the 15% unreadable rate
- Modify DECISIONS.md without request
- Retune costs to beautify Policy 1
