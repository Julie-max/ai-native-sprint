# LinkedIn Post — Week 1
## To be published after preprint is complete

Draft:

Most wearable ECG alerts are wrong. Not because the algorithm is bad —
because accuracy is the wrong metric.

I've been building a belief-based triage agent for wearable ECG patches
that asks a different question: not "is this STEMI?" but "what is the
expected cost of each action given what I know right now?"

The numbers are striking. A missed STEMI costs ~$500,000 in ICU,
surgery, and mortality risk. An unnecessary escalation costs ~$200.
That's a 2,500:1 cost asymmetry. A classifier that's 95% accurate
but wrong on the costly 5% is not 95% useful — it's dangerous.

The agent has three actions: dismiss, hold, or escalate. It holds
when uncertain — gathering more evidence rather than guessing. It
only dismisses when STEMI probability drops below 0.02%. It escalates
above 35%.

Not replacing doctors. Replacing the dumb threshold alarm that fires
the same way for electrode artifact and true STEMI alike.

Week 1 preprint: [link]
Repository: https://github.com/Julie-max/ai-native-sprint

#AIinHealthcare #MachineLearning #CardiacMonitoring #BiomedicalEngineering
