---
type: Knowledge
description: World model — typed entity/edge graph, contradiction rule, and reconsolidation representing "what is happening right now".
tags: [living-brain, cognition, world-model]
timestamp: 2026-01-01
status: active
version: 0.1
provenance:
  - living-brain-v0.1 spec
---

# World Model

The world model is made of typed edges — the answer to "what is happening in the
outside world right now".

## Entity schema

```json
{
  "id": "entity:orders-api", "type": "api_endpoint", "state": "available",
  "attributes": { "rate_limit_observed": false, "provides": ["shipmentDate"] },
  "confidence": 0.89, "last_verified": "2026-01-01",
  "evidence_refs": ["Sessions/2026-01-01-example.md"]
}
```

## Edge schema

```json
{
  "source": "entity:orders-api", "relation": "provides",
  "target": "field:shipmentDate", "weight": 0.86, "confidence": 0.91,
  "scope": ["orders", "delivery"], "epistemic_status": "observed", "status": "active"
}
```

## Contradiction rule

Within the same scope, `A --provides--> B` and `A --does_not_provide--> B` cannot
stay active together.

When a contradiction appears:
1. Compare the scope of the two pieces of evidence.
2. Separate date and environment.
3. Make the relation conditional if needed.
4. If unresolved, both become `testing`.
5. It enters the workspace as a conflict.

Reconsolidation: when new evidence conflicts with old knowledge, the new "truth"
is not simply added; the old is narrowed / suppressed / made conditional →
[[consolidation-policy]]. A large prediction error produces a world-model update
candidate → [[decision-policy]].
