---
type: Knowledge
description: Runtime store contract — the ~/.brain-runtime/ file layout, write discipline, and the Durable Brain separation.
tags: [living-brain, runtime, contract]
timestamp: 2026-01-01
status: active
version: 0.1
provenance:
  - living-brain-v0.1 spec
---

# Runtime Contract

Runtime data is **not** kept inside the Brain repo. Location:

```text
~/.brain-runtime/
├── cognitive-events.jsonl     # append-only event ledger
├── artifacts/                 # raw tool output, large payloads
├── synaptic-state.sqlite      # edge weights, success/failure counters
├── working-memory.json        # current workspace (delta update)
├── active-goals.json          # active goals
├── active-assemblies.json     # transient memory assemblies
├── simulations.jsonl          # future simulation branches
├── session-ledger.json        # session meta + event index
└── runtime-snapshot.json      # fast restore after a crash
```

## Write discipline

1. **One-way flow:** runtime → (consolidation gate) → Durable Brain. Raw runtime
   data is not written back to Markdown (rule 7).
2. **Append-only ledger:** `cognitive-events.jsonl` and `simulations.jsonl` are
   only appended to; past events are not edited.
3. **Delta update:** `working-memory.json` and `active-goals.json` are updated
   with small deltas instead of full rewrites.
4. **Large content to artifacts:** payloads over 2KB go under `artifacts/`; the
   event carries only a `payload_ref` (see [[event-schema]] `event_limits`).
5. **Replay:** if state is lost, it is rebuilt from `runtime-snapshot.json` +
   `cognitive-events.jsonl` replay.

## Durable Brain separation

These are **never** written to Markdown: transient activation, working memory,
candidate options, simulation branches, eligibility traces. They live in the
runtime store; only knowledge that passes the consolidation gate
([[offline-consolidation]]) is written to the Durable Brain.

Schemas: [[state-schema]] · [[event-schema]] · [[decision-episode-schema]].
