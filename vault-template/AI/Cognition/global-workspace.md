---
type: Knowledge
description: Global workspace — cognitive event bus, working memory, and transient assemblies; the runtime's "consciousness screen".
tags: [living-brain, cognition, workspace, event-bus, working-memory]
timestamp: 2026-01-01
status: active
version: 0.1
provenance:
  - living-brain-v0.1 spec
---

# Global Workspace

Active cognition converges here: the event-bus stream + working memory +
transient assemblies. All of it lives in the runtime store, never written to the
Durable Brain (rule 7).

## Working memory limits (hard)

```yaml
workspace_limits:
  active_primary_goals: 1
  active_secondary_goals: 2
  active_hypotheses: 3
  critical_constraints: 3
  active_risks: 2
  selected_plan_steps_visible: 5
  memory_references: 8
  full_text_blocks: 0        # NO raw text blocks in the workspace
```

## Cognitive event bus — event types

```text
session.started · observation.received · perception.encoded · salience.detected
workspace.updated · memory.activated · memory.inhibited · assembly.formed
goal.proposed · goal.authorized · goal.updated · hypothesis.generated/updated
option.generated · future.simulated · decision.selected · action.executed
outcome.observed · prediction.error · memory.rewarded · memory.weakened
conflict.detected · lesson.candidate · consolidation.started/completed · session.closed
```

Schema and size limits → [[event-schema]]. Working memory JSON → [[state-schema]].

## Memory assembly

A set of nodes (max 8) that temporarily bind around a goal:

```json
{
  "assembly_id": "assembly-...",
  "goal_id": "goal-...",
  "summary": "...",
  "nodes": [{ "ref": "path#slug", "activation": 0.82, "role": "domain_knowledge" }],
  "coherence": 0.81,
  "expires": "session_end"
}
```

An assembly is **not persisted**; only the verified relationships inside it are
consolidated through the [[offline-consolidation]] gate.
