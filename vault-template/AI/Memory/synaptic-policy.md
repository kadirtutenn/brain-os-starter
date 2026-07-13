---
type: Knowledge
description: Synaptic policy — connection weights, learning rate, weight update, independence factor, and the memory activation formula.
tags: [living-brain, memory, synaptic, learning]
timestamp: 2026-01-01
status: active
version: 0.1
provenance:
  - living-brain-v0.1 spec
---

# Synaptic Policy

Weights and update rules for typed synapses between memory nodes. State lives in
`~/.brain-runtime/synaptic-state.sqlite`.

## Initial weights

| Situation | w |
|---|---:|
| Seen together in the same session | 0.10 |
| Model-inferred plausible relation | 0.20 |
| Worked in one verified task | 0.40 |
| Verified in two independent tasks | 0.65 |
| ≥3 independent confirmations | 0.80 |
| Strong, direct, repeatedly verified | 0.90 |
| Maximum recommended | 0.95 |

`1.00` is never used; openness to new evidence is preserved.

## Learning rate

```yaml
plasticity:
  positive_learning_rate: 0.10
  negative_learning_rate: 0.14        # higher negative: wrong paths are suppressed fast
  coactivation_learning_rate: 0.03
  decay_rate_daily: 0.002
  refractory_penalty: 0.40
  deprecated_penalty: 0.60
  project_mismatch_penalty: 0.35
```

## Weight update

```text
Δw = learning_rate × reward × eligibility × confidence × independence_factor
w_new = clamp(w_old + Δw, 0.0, 0.95)
```

Eligibility/reward → [[decision-policy]].

## Independence factor

| Evidence | Value |
|---|---:|
| Repeat of the same tool output | 0.10 |
| Similar test in the same session | 0.30 |
| Other item/data the same day | 0.50 |
| Different session + different example | 0.75 |
| Different source / independent verifier | 1.00 |

Prevents the same evidence from counting as a "new confirmation" over and over
(constitution 4).

## Memory activation formula

```text
A(node) = base + semantic_similarity + tag_match + description_match
        + explicit_link + project_context + recency + coactivation + reliability + novelty
        - contradiction_inhibition - project_mismatch - deprecated_penalty
        - token_cost_penalty - refractory_penalty        (clamp 0.0–1.0)
```

```yaml
activation_weights:
  base_activation: 0.04
  semantic_similarity: 0.25
  tag_match: 0.10
  description_match: 0.10
  explicit_link_signal: 0.13
  project_context_signal: 0.15
  recency_signal: 0.05
  coactivation_signal: 0.06
  reliability_signal: 0.08
  novelty_signal: 0.04
  contradiction_inhibition: 0.40
  project_mismatch: 0.35
  deprecated_penalty: 0.60
  token_cost_penalty: 0.15
  refractory_penalty: 0.40
```

## Progressive retrieval thresholds

```yaml
retrieval_thresholds:
  ignore_below: 0.35
  index_only: 0.35
  frontmatter: 0.50
  matching_section: 0.65
  adjacent_sections: 0.78
  full_concept: 0.88
```

Dynamic threshold: `base 0.50 + context_pressure_adj + memory_noise_adj +
low_value_task_adj - explicit_user_reference(-0.15)`. Detail → [[metacognition]].

Node/synapse types → [[memory-types]]. Suppression/pruning → [[consolidation-policy]].
