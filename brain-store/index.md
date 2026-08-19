---
type: Hub
description: "Brain Store root map and progressive-disclosure entry point"
tags: [brain-store, index]
timestamp: 2026-08-19
okf_version: "0.1"
---

# Brain Store

Use `brain_context` for normal retrieval and `brain_expand` for explicit depth.
This map is for human navigation and low-level compatibility reads.

## Root

- [Dashboard](Dashboard.md) — concise active state.
- [PROTOCOL](PROTOCOL.md) — read, write, learning, and multi-agent rules.
- [Tasks](Tasks.md) — active task board.
- [log](log.md) — durable Store change history.
- [REFERENCE](REFERENCE.md) — compatibility navigation hub.

## Durable namespaces

- [Projects/](Projects/) — project-specific knowledge and fingerprints.
- [Agents/](Agents/index.md) — observable capabilities, constraints, and workflows.
- [Knowledge/](Knowledge/index.md) — reusable documentation and facts.
- [Lessons/](Lessons/INDEX.md) — distilled action-changing lessons.
- [Skills/](Skills/index.md) — reusable procedures and skill cards.
- [Insights/](Insights/index.md) — evidence-backed candidates and hypotheses.
- [Sessions/](Sessions/index.md) — compressed handoffs, not raw transcripts.

Executable parsing, chunking, retrieval, ranking, caching, and state do not live
inside the Brain Store.
