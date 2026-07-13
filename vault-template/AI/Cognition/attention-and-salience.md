---
type: Knowledge
description: Attention and salience model — the score and thresholds that decide which observation gets processing power.
tags: [living-brain, cognition, salience, attention]
timestamp: 2026-01-01
status: active
version: 0.1
provenance:
  - living-brain-v0.1 spec
---

# Attention & Salience

Salience decides where the limited cognitive budget goes.

```text
Salience =
  goal_relevance + novelty + prediction_error + threat
+ user_emphasis + unresolved_conflict + expected_information_gain
- repetition - low_impact
```

## Default weights

```yaml
salience_weights:
  goal_relevance: 0.25
  novelty: 0.10
  prediction_error: 0.20
  threat: 0.15
  user_emphasis: 0.15
  unresolved_conflict: 0.10
  expected_information_gain: 0.05
  repetition_penalty: 0.10
  low_impact_penalty: 0.10
```

## Attention gate (awake loop)

```text
salience < 0.25 → minimal log only, do not process
salience ≥ 0.55 → move to the global workspace (active evaluation)
0.25 ≤ salience < 0.55 → light retrieval, watch
```

High salience → retrieval and the decision loop are triggered. Retrieval
thresholds shift with internal state → [[metacognition]] (context pressure,
memory noise). A scored observation goes to the workspace → [[global-workspace]].
