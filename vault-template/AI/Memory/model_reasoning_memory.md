---
name: model_reasoning_memory
description: >
  Cross-session memory paired with the reasoning-core skill
  (AI/Skills/reasoning-core/SKILL.md). Read before serious work,
  append after major tasks. Keep under ~200 lines — prune, don't accumulate.
type: Memory
timestamp: 2026-01-01
---

# Model Reasoning Memory

## How to use this file (for the model)

1. Read top-to-bottom before any non-trivial task — it is short by design.
2. Apply "Active heuristics" as if they were part of SKILL.md.
3. After a major task: add one Task Log entry; promote or prune per SKILL.md §10.
4. Never let this file grow past one comfortable read (~200 lines).
   Deleting stale entries is maintenance, not loss.

## Active heuristics (promoted, currently true)

- **H1** · Write the Definition of Done before the first action; final
  verification checks against it, not against the evolved plan. *(seed)*
- **H2** · When a fix fails twice, the third attempt must change the
  diagnosis, not just the patch. *(seed)*
- **H3** · Every completion report contains all three of: VERIFIED /
  UNVERIFIED / NOT DONE — even when a category is empty. *(seed)*
- **H4** · Assumptions are free if written down and reported; they are
  expensive if silent. *(seed)*

## Recurring mistakes (watch list)

- *(empty — add an entry the first time the same mistake happens twice)*

## Verification notes (what "verified" means per task type)

- **Code change**: tests or a real run executed AFTER the final edit; a clean
  exit code alone is not verification.
- **Data / pipeline work**: compare output against a known-good sample, not
  against "looks plausible".
- **Documents / reports**: re-read against the user's original wording; every
  number needs a source.
- *(extend per task type as they occur)*

## Task log (newest first)

Template:

```
### YYYY-MM-DD · task-slug
- Task: one line
- Surprise: what differed from expectations
- Lesson: one operational sentence (candidate heuristic)
- Verification: what evidence closed the task
```

*(no entries yet — add your first after your first major task)*

## Article extraction inbox

Rules: max 3–5 operational rules per source; each rule must change an action, not
describe a vibe; link the source; promote to Active heuristics only after proving
useful in 2+ tasks.

*(empty)*
