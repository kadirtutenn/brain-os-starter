---
type: Knowledge
description: Consolidation policy — the session→lesson→skill distillation pipeline, reconsolidation, suppression, pruning, and the archive rule.
tags: [living-brain, memory, consolidation, distillation]
timestamp: 2026-01-01
status: active
version: 0.1
provenance:
  - living-brain-v0.1 spec
---

# Consolidation Policy

Distillation pipeline: **Session → Lesson → (useful in 2+ tasks) Skill**.
Executor: `brain-manager` (single writer).

## Lesson candidate

```text
action_change_score ≥ 0.60 AND generalizability ≥ 0.50 AND evidence_confidence ≥ 0.60
```

By default NO new file is opened; a `## slug` is updated inside the relevant
`Lessons/<area>/problems.md` or `patterns.md` + the `Lessons/INDEX.md` keyword
line (constitution 15).

## Durable lesson

```text
One strong failure-preventing constraint
OR the same pattern in two independent tasks
OR a multi-source-verified cause-effect
```

## Skill promotion

```yaml
promotion:
  minimum_independent_successes: 2
  minimum_confidence: 0.75
  maximum_open_contradictions: 0
  minimum_reuse_probability: 0.50
```

## Reconsolidation (contradiction)

When new evidence conflicts with old knowledge, the new "truth" is not simply
added: scope, date, environment, and evidence are compared → the old knowledge is
narrowed, made `suppressed`/`deprecated`, or made conditional. World-model side →
[[world-model]].

## Suppression

```text
failure_count ≥ 2 AND success_count == 0
OR contradiction_confidence ≥ 0.80
```

## Pruning

```text
weight < 0.10 AND last_use > 90 days AND success_count == 0 AND unique_information == false
```

Critical historical records are **not deleted, they are archived**. Pruning is
maintenance, not loss.

Weight mechanics → [[synaptic-policy]]. Sleep loop flow → [[offline-consolidation]].
