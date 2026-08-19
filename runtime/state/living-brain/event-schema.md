---
type: Knowledge
description: Cognitive event bus event schema, event types, and size limits.
tags: [living-brain, runtime, event-schema, event-bus]
timestamp: 2026-01-01
status: active
version: 0.1
provenance:
  - living-brain-v0.1 spec
---

# Event Schema

Each line in `~/.brain-runtime/cognitive-events.jsonl` is one event.

## Base schema

```json
{
  "event_id": "evt-uuid",
  "timestamp": "2026-01-01T12:00:00+00:00",
  "type": "future.simulated",
  "source": "future-simulator",
  "session_id": "session-uuid",
  "goal_id": "goal-api-first-rewrite",
  "summary": "Switching to the orders API has the highest expected goal progress.",
  "payload_ref": "artifact:sim-001",
  "confidence": 0.72,
  "epistemic_status": "predicted",
  "evidence_refs": ["Knowledge/System/orders-api.md#shipment-date"],
  "related_memory_nodes": []
}
```

## Event types

```text
session.started · observation.received · perception.encoded · salience.detected
workspace.updated · memory.activated · memory.inhibited · assembly.formed
goal.proposed · goal.authorized · goal.updated · hypothesis.generated · hypothesis.updated
option.generated · future.simulated · decision.selected · action.executed
outcome.observed · prediction.error · memory.rewarded · memory.weakened
conflict.detected · lesson.candidate · consolidation.started · consolidation.completed · session.closed
```

## Size limits

```yaml
event_limits:
  summary_max_chars: 280
  inline_payload_max_bytes: 2048
  max_memory_refs: 8
  max_evidence_refs: 5
```

Large content is stored under `artifacts/`; the event carries a `payload_ref` →
[[runtime-contract]].
