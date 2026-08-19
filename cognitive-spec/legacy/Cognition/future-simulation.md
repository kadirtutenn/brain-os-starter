---
type: Knowledge
description: Future simulation — option generation, branch schema, probability guard, and decision-relevance stopping.
tags: [living-brain, cognition, simulation, planning]
timestamp: 2026-01-01
status: active
version: 0.1
provenance:
  - living-brain-v0.1 spec
---

# Future Simulation

Simulations are in `predicted`/`imagined` epistemic status; they cannot be
recorded as past memories (rule 10).

## Future types

```text
forecast · action_outcome · counterfactual · desired_future · epistemic_experiment
```

## Option generation

```yaml
option_generation:
  default_raw_options: 5
  max_raw_options: 8
  minimum_distinct_strategies: 2
  always_include_no_action_when_relevant: true
  always_include_information_gathering_when_uncertainty_high: true
```

## Limits

```yaml
simulation_limits:
  raw_options: 8
  shortlisted_options: 3
  deep_simulation_options: 2
  max_depth_standard: 3
  max_depth_high_risk: 5
  max_branches_per_option: 3
  max_counterfactuals: 1
```

## Branch schema

```json
{
  "simulation_id": "sim-001", "option_id": "...", "epistemic_status": "predicted",
  "branches": [
    { "outcome": "success", "probability": 0.65, "goal_progress": 0.70, "risk": 0.10, "cost": 0.20 },
    { "outcome": "partial", "probability": 0.25, "goal_progress": 0.35, "risk": 0.20, "cost": 0.25 },
    { "outcome": "failure", "probability": 0.10, "goal_progress": 0.00, "risk": 0.30, "cost": 0.20 }
  ]
}
```

## Probability guard

```yaml
estimated_probability: 0.60
plausible_range: [0.40, 0.75]
confidence: 0.45
```

With single-evidence forecasts, precision does not exceed two decimals;
probability and confidence are separate fields.

## Decision-relevance stopping

Simulation stops when:
- The score gap between the best and second option ≥ 0.20
- A new branch's chance of changing the ranking < 0.10
- Information gain is below its cost
- A risk threshold is exceeded
- The budget is spent
- The next step is reversible and low-cost

Simulations live in the runtime `simulations.jsonl` → [[runtime-contract]]. The
result feeds the decision → [[decision-policy]].
