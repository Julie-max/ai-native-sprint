# X Thread — Week 1

Tweet 1:
Most wearable ECG alerts are wrong. Not because the algorithm fails —
because accuracy is the wrong metric. Here's what I built instead 🧵

Tweet 2:
A missed STEMI costs ~$500,000. An unnecessary escalation costs ~$200.
That's 2,500:1 cost asymmetry. Any agent ignoring this ratio is
optimizing for the wrong thing.

Tweet 3:
My agent has 3 actions: dismiss, HOLD, escalate.
- Dismiss below 0.02% STEMI probability
- Escalate above 35%
- HOLD in between — gathering evidence, not guessing

Tweet 4:
The HOLD action is the key insight. A classifier is forced to output
a label even when maximally uncertain. The agent buys time.
Because in cardiac events, the cost of a wrong guess is asymmetric.

Tweet 5:
Not replacing doctors. Replacing the dumb threshold alarm on wearables
that fires identically for electrode artifact and true STEMI.
That's the status quo this agent improves on.

Tweet 6:
Full agent design + 20 test cases + probability decision record:
https://github.com/Julie-max/ai-native-sprint
Preprint: [link]

#AIHealth #ECG #BayesianReasoning #MachineLearning
