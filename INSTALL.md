# Install — Brain OS on a new machine, for a new user

This sets up the whole system for one person on one machine. It is idempotent:
re-running is safe.

## Prerequisites

- **Python 3** (stdlib only — no packages to install). Check: `python3 --version`.
- **Claude Code** installed, so `~/.claude/` exists (or will after first run). The
  installer creates `~/.claude/hooks`, `~/.claude/skills`, `~/.claude/agents` as needed.
- **Obsidian** (optional but recommended) for the graph view of the vault.
- **git** (optional) if you want to version the vault.

## Paths this system uses

- **Vault** — where your Brain lives. You choose this (e.g. `~/Brain`). Set it as
  `BRAIN_VAULT_PATH`; the hook reads that env var.
- **`~/.claude/`** — Claude Code config home (`CLAUDE_DIR`, override for a sandbox).
- **`~/.brain-runtime/`** — the runtime store for the Living Brain engine. Created
  on demand; never committed. Override with `BRAIN_RUNTIME`.

## Step 1 — get the vault

Option A (fresh vault from the template):

```sh
./scripts/new_vault.sh "$HOME/Brain"
```

Option B (you already have a distributed bundle): just note its path.

## Step 2 — run the installer

```sh
BRAIN_VAULT_PATH="$HOME/Brain" ./scripts/install.sh
```

What it does:

1. Rewrites `{{BRAIN_ROOT}}` / `{{WORKSPACE_ROOT}}` / `{{CLAUDE_HOME}}` placeholders
   in the vault to this machine's real paths.
2. Copies `hooks/brain_context.py` into `~/.claude/hooks/` and registers it in
   `settings.json` (with `BRAIN_VAULT_PATH` baked into the command).
3. Registers `hooks/rules.py` (runs from this repo).
4. Installs the `reasoning-core` skill into `~/.claude/skills/`.
5. Installs the `brain-manager` and `context-builder` agents into `~/.claude/agents/`.

`settings.json` is backed up to `settings.json.bak-brain-install` first.

## Step 3 — verify

Open a new Claude Code session and send any prompt. The injected context should
begin with:

```
--- Brain Dashboard ---
--- Working Rules ---
```

Then run the engine self-test (optional, proves the runtime layer works):

```sh
python3 "$HOME/Brain/AI/Runtime/brain_engine.py"
# expected: RESULT: ALL PHASES PASS (5/5)
```

Open `$HOME/Brain` as a vault in Obsidian to browse the graph.

## Manual setup (without the installer)

If you prefer to wire it by hand, add two `UserPromptSubmit` hooks to
`~/.claude/settings.json` — see `settings.example.json` for the exact shape:

- `brain_context.py` with `BRAIN_VAULT_PATH` set to your vault.
- `rules.py` from this repo.

Then copy `skills/reasoning-core/` into `~/.claude/skills/` and `agents/*.md` into
`~/.claude/agents/`.

## Turning it off

- Mute the rules injection for a session: `BRAIN_RULES_BYPASS=1` (rules stay in
  force; only the reminder is silenced).
- Fully disable: remove the two hook entries from `settings.json` (restore the
  `.bak-brain-install` backup).

## Using it day to day

- Just work. The Dashboard and matched lessons ride along on every prompt.
- To learn something durably: tell the agent to "run a retrospective" / "close the
  session". `brain-manager` writes a session handoff, appends any lessons, and does
  the triple update (Dashboard + index + log).
- Read/write discipline lives in `vault-template/PROTOCOL.md` (copied into your vault).
