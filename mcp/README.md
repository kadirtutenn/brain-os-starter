# brain-mcp — the optional MCP server

`brain-mcp` is an **optional** server that exposes a Brain OS vault to any
[MCP](https://modelcontextprotocol.io) client (Claude Code, an Agent SDK app,
or another editor) over a network endpoint. It turns the same OKF vault the
session hooks read into a set of callable tools: search the Brain, read a
concept, and — through a gated pipeline — write lessons, skills, and session
handoffs back into it.

It is **separate from the hooks.** The core Brain OS (the `hooks/` context
injectors and the vault itself) is stdlib-only and needs nothing here. Use the
server when you want *remote* or *multi-client* access to one central vault —
for example a team sharing a vault on a VPS. If a single agent works a local
vault, the hooks alone are enough. See `../ARCHITECTURE.md` for how the durable
vault, the runtime, and the consolidation loop fit together; this server is a
gateway onto the "Durable Brain" layer described there.

## What it's made of

- `core.py` — pure-Python, stdlib-only logic: frontmatter parsing, search,
  the read functions, and the gated write pipeline. Independently importable
  and testable, no framework required.
- `server.py` — the thin MCP layer (built on `fastmcp`) that registers the
  tools below and serves them over streamable HTTP. This is the only part that
  needs `requirements.txt`.

## Tools

Read tools (no side effects):

| Tool | Purpose |
|---|---|
| `get_dashboard` | Return `Dashboard.md` verbatim. |
| `get_index` | Markdown directory map under an optional path. |
| `get_concept` | Full concept: id, type, description, tags, and body. |
| `search` | Ranked search; frontmatter weighted above body. |
| `find_skill` | Search restricted to Skill concepts. |
| `find_lesson` | Keyword-line lookup in `Lessons/INDEX.md`. |
| `find_concept` | General ranked search (alias of `search`). |
| `recent_changes` | The last N lines of `log.md`. |

Write tools (all go through the gated pipeline):

| Tool | Purpose |
|---|---|
| `new_lesson` | Append a lesson to an existing `Lessons/<area>` file + index it. |
| `new_skill` | Create a `Skills/<slug>.md` with valid OKF frontmatter. |
| `update_concept` | Patch an existing concept. |
| `log_session` | Write a session handoff + the triple update. |
| `new_rule` | Enqueue a rule proposal (does not write rules directly). |
| `approve_proposal` | Apply a queued proposal — admins only. |

There is deliberately **no delete tool.** Pruning is a maintenance action done
by a human on the vault, not something an agent can trigger remotely.

## The gated write pipeline

Every write follows the same ordered path, and any gate that fails aborts the
whole operation before anything touches disk:

```
acquire single-writer lock
  → validate_frontmatter   (type / description / tags / timestamp must be present)
  → secret_gate            (reject passwords, tokens, private keys, credentialed
                            connection strings, host+auth lines)
  → apply the edit
  → triple update          (append to log.md; optionally index.md + Dashboard note)
  → git commit             (authored as the calling identity)
  → return the concept id
```

The single-writer lock enforces the "single writer" boundary from the
architecture doc: concurrent writes serialise rather than corrupt the vault.
The secret gate has **no bypass flag** — there is no `--force` path — so a
secret-bearing write can never be committed through the server.

## Auth model

The server authenticates every request by a bearer token. Tokens are configured
out-of-band (via `BRAIN_MCP_TOKENS`, a comma-separated list of
`token:author` pairs) and each maps to an author identity used as the git commit
author. Authorization then depends on what is being written:

- **Lessons, sessions, skills** — any authenticated caller may write.
- **Rules, `PROTOCOL`, `Dashboard`** — cannot be written directly. A caller
  submits a proposal with `new_rule`; only an admin can `approve_proposal` to
  apply it.

An unknown or missing token is rejected before any tool runs.

## Deploy

1. Create a virtualenv and install the server deps:
   ```sh
   python3 -m venv .venv && . .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Provide configuration through an environment file. On a VPS this is
   `/etc/brain-mcp.env`, read by the systemd unit:
   ```sh
   BRAIN_VAULT_PATH=/srv/brain/vault
   BRAIN_MCP_TOKENS=token-for-alice:alice,token-for-bob:bob
   BRAIN_MCP_HOST=127.0.0.1
   BRAIN_MCP_PORT=8080
   ```
3. Install and start the service:
   ```sh
   sudo cp systemd/brain-mcp.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now brain-mcp.service
   ```
   The unit runs `python -m mcp.server` as a dedicated unprivileged user,
   restarts on failure, and reads everything from the environment file. Keep the
   listener on loopback and front it with a TLS-terminating reverse proxy for
   public access.

For the shared-vault housekeeping on the same VPS — a 15-minute git
auto-commit, a rotating daily backup, and a read-only mirror clients pull from —
run `../scripts/deploy_vps.sh`.

## Connect a client

Register the server with an MCP client using `.mcp.json.example` as a template
(replace `<VAULT_URL>` with the server endpoint and `<BEARER_TOKEN>` with one of
your configured tokens), or with the Claude CLI in one line:

```sh
claude mcp add brain-mcp <VAULT_URL> --header "Authorization: Bearer <BEARER_TOKEN>"
```

A typical `<VAULT_URL>` looks like `https://brain.example.com/mcp`.
