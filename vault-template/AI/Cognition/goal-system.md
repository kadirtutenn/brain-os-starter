---
type: Knowledge
description: Goal system — goal levels (L0-L6), priority formula, source authority, and lifecycle.
tags: [living-brain, cognition, goals]
timestamp: 2026-01-01
status: active
version: 0.1
provenance:
  - living-brain-v0.1 spec
---

# Goal System

## Levels

```text
L0 Constitution        L1 User commitment      L2 Persistent project goal
L3 Session goal        L4 Plan objective       L5 Immediate action
L6 Exploratory hypothesis
```

Constitution: user goals outrank implicit model goals (rule 8).

## Priority formula

```text
GoalPriority =
  source_authority + expected_impact + urgency + dependency_unlock
+ commitment_strength + information_value - cost - risk - conflict_penalty
```

```yaml
goal_weights:
  source_authority: 0.25
  expected_impact: 0.20
  urgency: 0.12
  dependency_unlock: 0.12
  commitment_strength: 0.10
  information_value: 0.06
  cost: 0.05
  risk: 0.07
  conflict_penalty: 0.15
```

## Source authority

| Source | Value |
|---|---:|
| Constitution | 1.00 |
| Explicit user request | 0.95 |
| User's persistent project | 0.85 |
| Derived from the active task | 0.65 |
| Model-proposed helper goal | 0.40 |
| Free exploration | 0.20 |

## Lifecycle

```text
proposed → authorized → active → (blocked/suspended) → achieved → verified → archived/cancelled
```

## Goal JSON

```json
{
  "id": "goal-...", "level": "L2", "source": "user", "status": "active",
  "desired_state": "...", "current_state": "...", "gap": 0.72, "priority": 0.88,
  "success_conditions": ["..."], "allowed_autonomy": "implementation_and_testing",
  "dependencies": [], "risks": ["..."]
}
```

Active goals live in the runtime → [[state-schema]] (`active-goals.json`).
Relationship to decisions → [[decision-policy]].
