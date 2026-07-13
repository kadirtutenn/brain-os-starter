---
type: Knowledge
description: Perception policy — observation encoding and the epistemic status model (observed/inferred/predicted/imagined/desired/counterfactual/unknown).
tags: [living-brain, cognition, perception, epistemic]
timestamp: 2026-01-01
status: active
version: 0.1
provenance:
  - living-brain-v0.1 spec
---

# Perception Policy

Every input (tool output, user message, file, test result) is first **encoded**:
it carries the task-relevant essence + an epistemic label, not the raw content.

## Epistemic status model

Every important piece of content is marked with one of:

```text
observed        — directly observed (tool/test/user/file)
inferred        — derived from an observation
predicted        — a forecast about the future
imagined         — simulated / hypothetical
desired          — a goal state
counterfactual   — a "what if" scenario
unknown          — unknown, explicitly marked
```

Constitution: observation, inference, prediction, imagination, and goal are kept
**separate**; a prediction/simulation cannot be stored as an observation (rules 1, 10).

## Example

```yaml
epistemic_status: observed
claim: The API returned "missing argument name: platform".
confidence: 0.99
```

```yaml
epistemic_status: inferred
claim: The endpoint probably requires a platform=... parameter.
confidence: 0.72
```

## Confidence interpretation

| Value | Meaning |
|---:|---|
| 0.00–0.24 | Weak speculation |
| 0.25–0.49 | Plausible, unverified |
| 0.50–0.69 | Moderate confidence |
| 0.70–0.84 | Strong evidence |
| 0.85–0.94 | Multiple confirmations |
| 0.95–1.00 | Direct, repeated, reliable |

`1.00` is reserved for logical certainty or immutable local contracts. External
system behavior usually stays < 0.99.

Feeds into salience → [[attention-and-salience]]. Encoded observations flow here
as events → [[global-workspace]].
