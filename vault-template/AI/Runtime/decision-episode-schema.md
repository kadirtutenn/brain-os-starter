---
type: Knowledge
description: Decision episode schema — options, prediction, verification plan, and outcome/prediction-error record.
tags: [living-brain, runtime, decision-episode]
timestamp: 2026-01-01
status: active
version: 0.1
provenance:
  - living-brain-v0.1 spec
---

# Decision Episode Schema

Every important decision is recorded as an episode; a decision whose outcome was
not observed is not counted as complete (rule 5).

## Open episode

```json
{
  "decision_id": "decision-uuid",
  "timestamp": "2026-01-01T12:00:00+00:00",
  "goal_id": "goal-api-first-rewrite",
  "problem": "The legacy shipping endpoint is heavily rate-limited.",
  "state_before_ref": "snapshot:state-004",
  "options": [
    { "id": "keep-legacy", "summary": "Continue current endpoint.", "score": 0.22 },
    { "id": "switch-api", "summary": "Replace with the orders API.", "score": 0.78 },
    { "id": "html-fallback", "summary": "Use HTML shipping data.", "score": 0.41 }
  ],
  "chosen_option": "switch-api",
  "prediction": { "success_probability": 0.65, "plausible_range": [0.45, 0.80], "confidence": 0.60 },
  "verification_plan": ["Test 20 representative items", "Compare output schema", "Keep legacy fallback until pass"],
  "memory_refs": ["Knowledge/System/orders-api.md#shipment-date"],
  "outcome": null, "prediction_error": null, "status": "open"
}
```

## After the outcome

```json
{
  "outcome": { "coverage": 0.95, "schema_compatible": true, "rate_limit_observed": false },
  "prediction_error": 0.08,
  "decision_quality": 0.86,
  "status": "verified"
}
```

Scoring and reward → [[decision-policy]]. Session summary counterpart:
`## 5. Decision episodes` (see session-template).
