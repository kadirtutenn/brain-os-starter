# Architecture

How the whole system fits together — the layers, the data flow, and the file map.
Read this once to understand the design; the operational rules live in
`vault-template/PROTOCOL.md`.

## 1. The core idea

An agent's context window is small and expensive; its potential memory is large.
The system's whole job is to keep those two facts from colliding:

> **A big Brain is not a big context.**

So knowledge is stored broadly and durably (markdown files), but retrieval is
progressive and budgeted: index → frontmatter → matching heading → full concept,
and only as far as a relevance score justifies. Nothing is loaded "just in case".

## 2. Three layers

### Durable Brain — the vault
Human-readable markdown, git-tracked, one concept per file, each with OKF
frontmatter (`type`, `description`, `tags`, `timestamp`). This is the part you
open in Obsidian. It holds lessons, skills, knowledge, projects, hypotheses, and
session handoffs. It does **not** hold transient runtime state.

### Runtime Mind — `~/.brain-runtime/`
Per-session cognition: working memory, active goals, memory activations, candidate
options, simulations, eligibility traces, synaptic weights. It lives outside the
repo (no git noise, no forced index/log updates) and is rebuildable from an
append-only event ledger + snapshot. The runnable mechanics are in
`vault-template/AI/Runtime/brain_engine.py` (stdlib-only, 5-phase, self-testing).

### Offline Consolidation — the learning loop
At session end, `brain-manager` replays the session, distills at most a handful of
action-changing lessons, updates synaptic weights, suppresses failed paths, prunes
dead ones, and writes the handoff. This is how the memory gets *better*, not just
*bigger*.

## 3. What happens on every prompt

```
you type a prompt
      │
      ▼
UserPromptSubmit hooks fire (once per session):
  rules.py         → injects "--- Working Rules ---"  (what's allowed)
  brain_context.py → injects "--- Brain Dashboard ---" (always)
                   + the best-matching distilled Lessons (keyword match vs Lessons/INDEX.md)
                   + the single best-matching concept (frontmatter scan)
      │
      ▼
the agent works, using reasoning-core discipline (DoD → recon → slice →
next-action loop → verification gate)
      │
      ▼
at session end: "run a retrospective" → brain-manager consolidates
      → session handoff + Dashboard + Sessions/index + log  (the "triple update")
```

The hook is the load-bearing automation. `brain_context.py` depends on two file
names existing: `Dashboard.md` (injected verbatim) and `Lessons/INDEX.md` (parsed
for keyword lines of the form `- [[target]] — kw1, kw2`). Don't rename those.

## 4. The reasoning + rules + learning stack

- **reasoning-core** (`skills/reasoning-core/SKILL.md`) — HOW to work on any hard
  task: write a Definition of Done first, recon before planning, build the smallest
  end-to-end slice, run the next-action loop after every step, pass a verification
  gate before claiming "done", and capture lessons. Domain-agnostic.
- **working-rules** (`rules/working-rules.md`) — WHAT is allowed: approval gates for
  irreversible actions, secret hygiene, test ordering, token economy, memory
  discipline. Edit this to fit your team.
- **learning loop** (PROTOCOL §3) — Session → Lesson → (useful in 2+ tasks) → a
  promoted heuristic or Skill. Invalidated entries are suppressed/archived, not
  deleted. Pruning is maintenance, not loss.

## 5. The Living Brain cognitive layer (`vault-template/AI/`)

This is the ambitious, optional-to-engage layer: a set of policy files describing a
full cognitive loop, plus a runnable engine implementing the quantitative parts.

- `AI/Cognition/` — the prose architecture: `perception`, `attention-and-salience`,
  `global-workspace`, `goal-system`, `decision-policy`, `future-simulation`,
  `world-model`, `self-model`, `metacognition`, `offline-consolidation`, tied
  together by `cognitive-architecture`.
- `AI/Runtime/` — schemas for the runtime store (`event`, `state`,
  `decision-episode`) + `runtime-contract` + `brain_engine.py`.
- `AI/Memory/` — `synaptic-policy` (weights, activation formula, thresholds),
  `memory-types` (node/synapse graph), `consolidation-policy` (distillation), and
  `model_reasoning_memory` (cross-session heuristics + task log).

The engine (`brain_engine.py`) makes the numbers real and testable: an activation
score with progressive-retrieval thresholds, decision episodes with prediction
error, synaptic weight updates gated by eligibility and independence, and
suppression/pruning. Run `python3 brain_engine.py` for a 5/5 self-test. It is
**not** wired to any hook — it's the substrate you build session tooling on, and
running it changes nothing about a live session by itself.

## 6. Optional: the MCP server as a vault gateway

Everything above assumes the session hooks reading a local vault. `mcp/` adds an
**optional** gateway onto the Durable Brain layer for remote or multi-client
access — one central vault, many callers — without changing anything for a purely
local agent. It exposes the same OKF vault as MCP tools: read tools
(`get_dashboard`, `get_concept`, `search`, …) are open and side-effect-free,
while writes go through the gated pipeline (single-writer lock →
frontmatter validation → secret gate → edit → triple update → authored git
commit) and there is deliberately no delete tool. This preserves the boundaries
from §8: single writer, vault as source of truth, no live sync. It runs on
`fastmcp` over HTTP with bearer-token auth; the stdlib-only `core.py` holds the
logic and is testable on its own. Details in `mcp/README.md`.

## 7. File map

```
brain-os-starter/
├── README.md               ← start here
├── INSTALL.md              ← setup on a new machine
├── ARCHITECTURE.md         ← this file
├── system-prompt.md        ← system prompt for API/SDK agents
├── settings.example.json   ← reference hook wiring
├── hooks/
│   ├── brain_context.py    ← injects Dashboard + lessons + concept (needs BRAIN_VAULT_PATH)
│   └── rules.py            ← injects working-rules.md
├── rules/working-rules.md
├── skills/reasoning-core/SKILL.md
├── agents/{brain-manager,context-builder}.md
├── okf/okf-spec-v0.1.md
├── scripts/{new_vault.sh, install.sh}
└── vault-template/         ← the Brain skeleton (copied to your vault)
    ├── Dashboard.md  index.md  PROTOCOL.md  log.md  Tasks.md  REFERENCE.md
    ├── Sessions/     (index + session-template)
    ├── Lessons/      (INDEX + process/ + data/)
    ├── Skills/  Knowledge/  Agents/  Projects/  Hypotheses/
    └── AI/
        ├── Cognition/  (11 modules + index)
        ├── Runtime/    (README, 4 schemas, brain_engine.py)
        ├── Memory/     (synaptic-policy, memory-types, consolidation-policy, model_reasoning_memory)
        └── Skills/reasoning-core/SKILL.md   (canonical copy in the vault)
```

## 8. Deliberate boundaries (v1)

- **No bidirectional sync.** The vault is the single source of truth; distribute it
  as a git repo or a tarball, not a live-synced drive.
- **Single writer.** Only the main session writes to the Brain. Sub-agents are
  read-only — they return findings, the main session records them.
- **The runtime is disposable.** Anything in `~/.brain-runtime/` can be deleted; the
  Durable Brain is what matters and what you back up.
