---
type: Knowledge
description: The AI/Runtime folder — the Living Brain runtime store contract and schema index.
tags: [living-brain, runtime, index]
timestamp: 2026-01-01
status: active
version: 0.1
---

# AI/Runtime

The **schema definitions** for the Runtime Mind live here (Durable Brain,
git-tracked). The runtime **data** lives outside the repo: `~/.brain-runtime/`.

## Schemas

| File | Content |
|---|---|
| [[runtime-contract]] | Store location, file list, write/replay rules |
| [[event-schema]] | Cognitive event bus event schema + size limits |
| [[state-schema]] | working-memory / active-goals / internal_state schemas |
| [[decision-episode-schema]] | Decision episode schema (before + outcome) |
| `brain_engine.py` | Runnable engine for Phases 1-5 (stdlib-only; not wired to any hook) |

## brain_engine.py

The operational implementation of phases 1-5: `append_event`/`update_working_memory`/`resume_state`
(Phase 1), `activation`+`progressive_retrieve` (Phase 2), `open/close_decision`+prediction_error
(Phase 3), `update_weight`+eligibility+independence (Phase 4), `consolidate`
suppression/pruning (Phase 5). Verify: `python3 brain_engine.py` → self-test 5/5
PASS. Store: `~/.brain-runtime` (override with `BRAIN_RUNTIME`). Not wired to any
hook — running it does not change session behavior.

## Why the runtime lives outside the repo

- Avoids git diff noise.
- Avoids forcing a timestamp+index+log update on every activation.
- Keeps Markdown from being polluted with "electrical activity".
- Can be rebuilt after a crash via snapshot/event replay.

Architectural context → [[cognitive-architecture]].
