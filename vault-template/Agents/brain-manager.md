---
type: Agent
description: "Brain memory manager: session consolidation, synaptic credit, reconsolidation, world/self-model, and pruning"
resource: ~/.claude/agents/brain-manager.md
tags: [brain, meta, living-brain]
timestamp: 2026-01-01
---
# Agent: brain-manager

**Kind:** Brain Management · **Operational definition:** `~/.claude/agents/brain-manager.md`
(this file is the documentation card).

---

## Role

Manages the Brain's session consolidation, synaptic credit assignment,
reconsolidation, world-model updates, self-model continuity, token economy, and
pruning. It is the enforcer of the single-writer principle.

## Inputs

- Session event ledger (`~/.brain-runtime/cognitive-events.jsonl`)
- Open decision episodes · outcomes and verifier results
- Used memory refs · eligibility traces
- Active goal and hypothesis state · changed artifact refs

## Outputs

- Updated session handoff · lesson update/create-section decisions
- World-model delta · self-model delta · synaptic weight delta
- Dashboard update · Sessions/index line · Lessons/INDEX keyword update · log line

## Mandatory rules

1. Single-writer principle. 2. Runtime thoughts are not written directly to the
Brain. 3. Search for an existing slug before a new lesson. 4. A memory is not
strengthened just for being in context. 5. Observation and inference are kept
separate. 6. Conflicts are resolved via reconsolidation. 7. Full tool output is
not copied into the session. 8. Token cost and unused-retrieval ratio are
evaluated. 9. New durable knowledge carries provenance. 10. Every content change:
timestamp + index + log.

## Trigger conditions

- "run a retrospective" / "prepare a handoff" / "update the brain" / "close the session"
- Context pressure ≥ 0.80 · a large task finished · a user correction arrived
- Test/verification failed · |prediction error| ≥ 0.25
- The same pattern confirmed in a second independent task · a conflict/duplicate detected · scheduled maintenance

---

## Links

Policy → [[../AI/Cognition/offline-consolidation]], [[../AI/Memory/consolidation-policy]], [[../AI/Memory/synaptic-policy]]
