---
type: Knowledge
description: Living Brain v0.1 core architecture — three layers, the cognitive loop, constitutional rules, and the token-economy gate.
tags: [living-brain, cognition, architecture, token-optimization]
timestamp: 2026-01-01
status: active
version: 0.1
provenance:
  - living-brain-v0.1 spec
---

# Living Brain v0.1 — Cognitive Architecture

Guiding principle: **a big Brain is not a big context.** Durable knowledge may be
broad; what is activated at any one moment must be small, task-shaped, and measured.

This file is the operational summary. The runnable mechanics of the phases below
live in `AI/Runtime/brain_engine.py` (stdlib-only, not wired to any hook).

## Three layers

```text
Living Brain
= Durable Brain      (the Obsidian store — persistent, git, OKF frontmatter)
+ Runtime Mind       (in-session transient cognition — ~/.brain-runtime/)
+ Offline Consolidation (sleep/consolidation — session → lesson → skill)
```

- **Durable Brain:** human-readable, git-tracked, OKF frontmatter. Holds lessons,
  skills, projects, hypotheses, session handoffs. Does NOT store runtime activations.
- **Runtime Mind:** working memory, active goals, memory activations, candidate
  decisions, simulations, eligibility traces, live risk/confidence/token pressure.
  Lives outside the repo → [[runtime-contract]].
- **Offline Consolidation:** at session end, distills experience into durable,
  small, high-quality knowledge → [[offline-consolidation]].

## Subsystems (summary)

| Module           | Question                                | File                        |
| ---------------- | --------------------------------------- | --------------------------- |
| Durable Brain    | What do I know?                         | Durable Brain               |
| Runtime Mind     | What is active right now?               | [[state-schema]]            |
| Salience         | What should I pay attention to?         | [[attention-and-salience]]  |
| Goal System      | What am I trying to change?             | [[goal-system]]             |
| World Model      | What is happening right now?            | [[world-model]]             |
| Self Model       | What can I do, what am I bound by?      | [[self-model]]              |
| Future Simulator | What might happen after this action?    | [[future-simulation]]       |
| Decision Engine  | Which action is best now?               | [[decision-policy]]         |
| Prediction Error | Difference between expected and observed| [[decision-episode-schema]] |
| Consolidation    | How does this change me for good?       | [[offline-consolidation]]   |
| Token Economy    | How little thinking is enough?          | [[metacognition]]           |

## Awake loop (the cognitive cycle)

```text
observation → perception.encode
→ salience.score  (goals, internal_state)
   salience < 0.25 → minimal log, stop
   salience ≥ 0.55 → take into workspace
→ memory_router.route (limit 12)
→ progressive_retrieve (token budget)
→ form_assembly (max 8 nodes)
→ option_generator (max 8) → cheap_rank → shortlist 3
→ future_simulator (max 2 deep, depth = runtime)
→ action_selector.select
→ executor.execute_and_observe
→ learning_engine.update (eligibility traces)
→ workspace.apply_delta
```

## Immutable constitutional rules

1. Observation, interpretation, prediction, imagination, and goal are kept separate.
2. Being in the Brain is not enough to enter context.
3. Entering context does not mean being correct.
4. Repetition does not make a piece of knowledge more true.
5. A decision whose outcome was not observed is not counted as successful.
6. Durable learning carries provenance and verification.
7. Runtime thoughts are not written directly to the Durable Brain.
8. User goals outrank implicit model goals.
9. Under high uncertainty, small and reversible actions are chosen.
10. Future simulations cannot be recorded as past memories.
11. No module can override the token-optimization rules.
12. The system cannot change its own ownership/authority/safety rules alone.
13. The single-writer principle applies to the Brain (main session only).
14. Every durable file change requires the triple: timestamp + index + log.
15. A "new lesson" does not open a new file by default; it updates a slug in the
    relevant `problems.md`/`patterns.md`.

## Ultimate optimization objective

```text
Cognitive Efficiency = Verified Decision Quality ÷ Total Cognitive Cost
```
