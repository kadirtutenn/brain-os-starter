---
type: Knowledge
description: Metacognition — internal state/interoception, the neuromodulator control vector, token budget, and efficiency metrics.
tags: [living-brain, cognition, metacognition, interoception, token-economy]
timestamp: 2026-01-01
status: active
version: 0.1
provenance:
  - living-brain-v0.1 spec
---

# Metacognition

The system monitoring its own cognitive state and managing the token economy.

## Internal state (interoception)

```yaml
internal_state:
  context_pressure: 0.00
  uncertainty: 0.00
  task_load: 0.00
  tool_reliability: 1.00
  memory_noise: 0.00
  deadline_pressure: 0.00
  unresolved_conflicts: 0
  repeated_failure_count: 0
  user_waiting: false
```

### Thresholds and behavior

- **context_pressure ≥ 0.70:** retrieval thresholds +0.10; full-concept reads off
  (only with explicit justification); the workspace is compressed; unused
  assemblies are closed.
- **context_pressure ≥ 0.80:** brain-manager produces a handoff candidate;
  decision-episode snapshot; no new exploratory branches open.
- **uncertainty ≥ 0.65:** at least one verifier; +0.10 bonus for the reversible
  option; definitive claims banned; `unknown` fields kept open.
- **same strategy fails 2×:** strategy inhibition -0.40; alternative generation
  mandatory; a 3rd retry is banned without new evidence (change the diagnosis, not the patch).

## Neuromodulator control vector

```yaml
cognitive_modulators:
  valence: 0.00
  arousal: 0.00
  threat: 0.00
  novelty: 0.00
  curiosity: 0.00
  control: 1.00
  confidence: 0.50
  frustration: 0.00
  satisfaction: 0.00
```

```text
threat ↑        → risk penalty ↑, verification ↑, irreversible-action threshold ↑
curiosity ↑     → info-gain bonus ↑, exploratory quota ↑
frustration ↑   → repeat-strategy inhibition ↑, alternative generation ↑
confidence ↓    → prediction interval widens, verifier mandatory
satisfaction ↑  → successful-strategy weight ↑ (but verification is not skipped)
```

## Token budget

Task classes: `T0 trivial · T1 simple · T2 standard · T3 complex · T4 high-risk`.

Cognitive budget split (T0→T4, %): Perception 20/15/10/8/8 · Retrieval 0/10/20/20/18
· Workspace 30/20/15/12/12 · Simulation 0/0/10/22/18 · Planning 10/15/15/18/16 ·
Verification 10/15/15/15/23 · Response 30/25/15/5/5.

Retrieval quotas: max 12 index candidates, 6 frontmatter, 4 section, 1
full-concept; per session 2 / lesson 4 / skill 2 / knowledge 3 / project 2 nodes.

## Efficiency metrics (calibration targets)

```yaml
targets:
  unused_retrieval_ratio_max: 0.25
  duplicate_context_ratio_max: 0.10
  full_file_read_ratio_max: 0.10
  average_simulation_branches_max: 6
  session_to_lesson_compression_ratio_min: 10
  decision_reversal_rate_max: 0.20
```

Calibrate after the first ~20 real tasks. Retrieval threshold mechanics →
[[attention-and-salience]]. Progressive retrieval → [[cognitive-architecture]].
