---
type: Knowledge
description: Memory node model — node granularity, node types, synapse types, and the node identity convention.
tags: [living-brain, memory, node, graph]
timestamp: 2026-01-01
status: active
version: 0.1
provenance:
  - living-brain-v0.1 spec
---

# Memory Types

## Node granularity

A memory node need not be a whole file; it can be heading-level. Node identity:

```text
<relative-path>#<slug>
```

Examples:
```text
Knowledge/System/orders-api.md#shipment-date
Lessons/process/problems.md#stale-plan-execution
Sessions/2026-01-01-example.md#api-failure
```

## Node types

```text
episode · fact · lesson · pattern · skill · procedure · constraint
hypothesis · goal · identity · world-state · decision · risk · commitment
```

## Synapse types

```text
supports · contradicts · causes · prevents · enables · requires · predicts
similar_to · used_by · part_of · derived_from · supersedes · alternative_to
risk_of · goal_of · evidence_for
```

## Synapse example

```json
{
  "source": "Lessons/process/problems.md#missing-parameter",
  "target": "Knowledge/System/orders-api.md#shipment-date",
  "relation": "supports", "weight": 0.76, "polarity": "excitatory",
  "confidence": 0.82, "scope": ["orders", "api"], "status": "active"
}
```

Weight and learning → [[synaptic-policy]]. Activation → [[synaptic-policy]] (activation formula).
