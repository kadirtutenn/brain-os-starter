---
type: Knowledge
description: Decision policy — decision score, risk modes, reward/prediction error, and eligibility trace.
tags: [living-brain, cognition, decision, reward]
timestamp: 2026-01-01
status: active
version: 0.1
provenance:
  - living-brain-v0.1 spec
---

# Decision Policy

## Decision score

```text
DecisionScore =
  goal_progress + expected_utility + information_gain + reversibility
+ user_alignment + identity_consistency + confidence_adjusted_success
- resource_cost - risk - irreversible_damage - uncertainty_penalty - policy_violation
```

```yaml
decision_weights:
  goal_progress: 0.24
  expected_utility: 0.14
  information_gain: 0.10
  reversibility: 0.10
  user_alignment: 0.14
  identity_consistency: 0.08
  confidence_adjusted_success: 0.10
  resource_cost: 0.06
  risk: 0.12
  irreversible_damage: 0.20
  uncertainty_penalty: 0.08
  policy_violation: 1.00
```

If `policy_violation > 0` the option is **eliminated** (not just downweighted).
Any `CLAUDE.md` approval rules fall under policy_violation.

## Risk modes

| Mode | risk × | info_gain × | reversibility × | extra |
|---|---:|---:|---:|---|
| exploration | 0.75 | 1.40 | 1.10 | — |
| standard | 1.00 | 1.00 | 1.00 | — |
| production | 1.50 | 0.80 | 1.40 | verification_required |
| high_stakes | 2.00 | — | 1.75 | 2 verifiers + human approval on irreversible action |

## Reward (multi-dimensional outcome)

```text
Reward = 0.30·goal_progress + 0.25·accuracy + 0.10·information_gain
       + 0.15·user_feedback + 0.10·resource_efficiency + 0.10·policy_compliance
       - 0.25·harm            (clamp -1.0 … 1.0)
```

| Outcome | Reward | | Outcome | Reward |
|---|---:|---|---|---:|
| Test passed | +0.80 | | User asked for a correction | -0.55 |
| Verifier passed | +0.85 | | Test failed | -0.80 |
| User confirmed | +0.75 | | Rollback needed | -0.90 |
| Plausible, unverified | +0.20 | | Policy violation | -1.00 |

## Prediction error

```text
prediction_error = observed_value - predicted_value
```

|error| ≥ 0.25 → world-model update candidate, hypothesis confidence ↓, decision
retrospective, lesson candidate.

## Eligibility trace (credit assignment)

```text
eligibility = contribution_strength × temporal_proximity × causal_relevance
temporal_proximity = exp(-elapsed_steps / 5)
```

```yaml
direct_used_in_action: 1.00
influenced_decision: 0.80
used_in_verification: 0.65
background_context_only: 0.15
not_used: 0.00
```

Credit is only given when `eligibility ≥ 0.30` — a memory is not strengthened just
for being in context (rule 4). Weight update → [[synaptic-policy]]. Decision record
→ [[decision-episode-schema]]. Simulation → [[future-simulation]].
