---
type: Knowledge
description: Runtime state schemas — working-memory.json, active-goals.json, active-assemblies.json, and internal_state.
tags: [living-brain, runtime, state-schema, working-memory]
timestamp: 2026-01-01
status: active
version: 0.1
provenance:
  - living-brain-v0.1 spec
---

# State Schema

## working-memory.json

```json
{
  "session_id": "session-uuid",
  "focus": "Replace legacy shipping fetch",
  "active_goal_ids": ["goal-api-first-rewrite"],
  "state_summary": "Order detail migrated; shipping still legacy.",
  "next_action": "Map the orders-API response and test representative items.",
  "constraints": ["Preserve output schema", "Do not remove fallback before verification"],
  "hypotheses": [{ "id": "hyp-api-replacement", "claim": "...", "confidence": 0.74 }],
  "risks": ["Response coverage may vary by item type"],
  "memory_refs": ["Knowledge/System/orders-api.md#shipment-date"],
  "context_pressure": 0.51
}
```

Hard limits (see [[global-workspace]]): primary_goal 1, secondary 2, hypotheses 3,
constraints 3, risks 2, memory_refs 8, full_text_blocks 0.

## active-assemblies.json (item)

```json
{
  "assembly_id": "assembly-...", "goal_id": "goal-...", "summary": "...",
  "nodes": [{ "ref": "path#slug", "activation": 0.82, "role": "domain_knowledge" }],
  "coherence": 0.81, "expires": "session_end"
}
```

## internal_state (interoception)

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

Threshold behaviors → [[metacognition]]. `active-goals.json` schema →
[[goal-system]]. Store rules → [[runtime-contract]].
