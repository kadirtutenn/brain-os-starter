---
okf_version: "0.1"
description: "Brain bundle root map — the progressive-disclosure entry point"
timestamp: 2026-01-01
---

Read order: Dashboard (already injected by the hook) → this index (structure) →
[PROTOCOL](PROTOCOL.md) (rules) → only the concept you need. Before opening a
file, read its frontmatter with `head -8`.

# Root
* [Dashboard](Dashboard.md) - Active state panel; injected into every prompt by the hook.
* [PROTOCOL](PROTOCOL.md) - The read/write/learning protocol for all agents. READ THIS FIRST.
* [Tasks](Tasks.md) - Active task board (priority + status).
* [log](log.md) - Bundle change log; see "what changed" without opening files.
* [REFERENCE](REFERENCE.md) - Legacy hub (stub) — redirects to PROTOCOL and the indexes.

# Directories
* [Sessions/](Sessions/index.md) - Session handoff records, chronological. Template: [session-template](Sessions/session-template.md).
* [Lessons/](Lessons/INDEX.md) - Distilled lessons. INDEX lines are auto-injected by keyword match.
* [Skills/](Skills/index.md) - Skill cards and catalogs.
* [Knowledge/](Knowledge/index.md) - System/performance/research knowledge base.
* [Agents/](Agents/index.md) - Agent cards and trigger conditions.
* [Projects/](Projects/) - Per-project concept files (one file per active project).
* [Hypotheses/hypotheses](Hypotheses/hypotheses.md) - Hypothesis lifecycle board (proposed → testing → decided).

# Reasoning core
* [AI/Skills/reasoning-core/SKILL](AI/Skills/reasoning-core/SKILL.md) - Task decomposition, verification gate, next-action loop.
* [AI/Memory/model_reasoning_memory](AI/Memory/model_reasoning_memory.md) - Cross-session reasoning memory (heuristics + task log).

# Living Brain v0.1 (AI/Cognition · AI/Runtime · AI/Memory)
Entry point: [AI/Cognition/cognitive-architecture](AI/Cognition/cognitive-architecture.md).
* [AI/Cognition/index](AI/Cognition/index.md) - Cognitive module index (perception, salience, workspace, goal, decision, simulation, world/self model, metacognition, consolidation).
* [AI/Runtime/README](AI/Runtime/README.md) - Runtime store contract + schemas (event/state/decision-episode). Runtime data lives outside the repo: `~/.brain-runtime/`.
* [AI/Memory/synaptic-policy](AI/Memory/synaptic-policy.md) · [memory-types](AI/Memory/memory-types.md) · [consolidation-policy](AI/Memory/consolidation-policy.md) - Synaptic weights, node/synapse types, the distillation pipeline.
