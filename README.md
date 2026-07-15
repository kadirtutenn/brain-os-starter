# Brain OS Starter

A portable memory + reasoning operating system for AI coding agents (Claude Code
and any Agent SDK / API agent), built on an [Obsidian](https://obsidian.md) vault
and a small set of session hooks.

It gives an agent three things:

1. **A durable, human-readable memory** — an OKF v0.1 markdown bundle you can open
   in Obsidian and browse as a knowledge graph.
2. **Automatic context injection** — a hook that, on every prompt, injects the
   Dashboard, the most relevant distilled lessons, and the best-matching concept
   — without you pasting anything.
3. **A reasoning + learning discipline** — a `reasoning-core` skill (how to work),
   a working-rules layer (what's allowed), and a session→lesson→skill learning
   loop that makes the memory better over time.

Everything here is generic. There is no company, project, or personal data — swap
in your own as you use it.

## The three layers

```
Durable Brain            The Obsidian vault (this is your memory; git-tracked, markdown).
   +
Runtime Mind             Transient per-session cognition in ~/.brain-runtime/ (never
                         committed; rebuildable). Driven by AI/Runtime/brain_engine.py.
   +
Offline Consolidation    At session end, brain-manager distills the session into
                         lessons and updates the Dashboard/index/log.
```

The guiding principle: **a big Brain is not a big context.** The memory can grow
without bound; what gets loaded into any one prompt stays small and task-shaped.
See `ARCHITECTURE.md` for the full model.

## What's in this repo

| Path | What it is |
|---|---|
| `vault-template/` | The Brain skeleton — copy this to create a fresh vault. |
| `hooks/brain_context.py` | UserPromptSubmit hook: injects Dashboard + lessons + best concept. |
| `hooks/rules.py` | UserPromptSubmit hook: injects your working rules. |
| `rules/working-rules.md` | The team working-rules template (edit to taste). |
| `skills/reasoning-core/SKILL.md` | The reasoning discipline skill (installed to ~/.claude/skills). |
| `agents/` | `brain-manager` and `context-builder` agent definitions. |
| `okf/okf-spec-v0.1.md` | The knowledge-format spec the vault follows. |
| `system-prompt.md` | Canonical system prompt for API/SDK agents. |
| `scripts/new_vault.sh` | Scaffold a fresh vault from the template. |
| `scripts/install.sh` | Wire everything into ~/.claude (hooks, skill, agents, settings). |
| `settings.example.json` | Reference settings.json hook wiring. |
| `mcp/` | Optional MCP server exposing one central vault to remote/multi-client agents. |

## Quick start

```sh
# 1. Scaffold a vault (choose any empty path)
./scripts/new_vault.sh "$HOME/Brain"

# 2. Wire it into Claude Code (installs hooks, skill, agents; backs up settings.json)
BRAIN_VAULT_PATH="$HOME/Brain" ./scripts/install.sh

# 3. Open "$HOME/Brain" in Obsidian to get the graph view.
# 4. Start a new Claude Code session — the first prompt shows
#    "--- Brain Dashboard ---" and "--- Working Rules ---" context blocks.
```

Full walk-through, prerequisites, and manual setup: see `INSTALL.md`.

## Optional: central vault over MCP

The hooks above serve a local vault. When you instead want *remote* or
*multi-client* access to one shared vault — a team on a VPS, say — there is an
optional MCP server in `mcp/`. It exposes the same OKF vault as callable tools
(open read tools; writes through a gated single-writer pipeline). One command
from the repo root brings it up:

```sh
mcp/install.sh --run        # foreground, needs BRAIN_VAULT_PATH
sudo mcp/install.sh --systemd   # install + start as a VPS daemon
```

It is entirely optional and separate from the hooks — a single local agent needs
none of it. See `mcp/README.md` for the tool list, auth, and deploy details.

## Design credits

The knowledge format is [OKF v0.1](okf/okf-spec-v0.1.md). The cognitive layer
(`vault-template/AI/`) is a "Living Brain v0.1" design: a small runtime engine plus
markdown policy files describing perception, salience, a global workspace, goals,
decisions, future simulation, world/self models, metacognition, and consolidation.
