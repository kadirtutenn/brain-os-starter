# Brain OS Starter

Deterministic shared-memory infrastructure for multiple external AI agents.
Durable knowledge lives as OKF Markdown in a git-backed **Brain Store**; a
disposable SQLite FTS5 projection serves compact, budgeted context over an
authenticated MCP endpoint. The core never calls an LLM, embedding model, or
external AI API — external agents do the semantic work; Brain OS parses,
indexes, ranks, packs, versions, and serves shared knowledge.

Use this repo to run **your own** Brain OS on **your own** server. Nothing here
is tied to a specific installation: every host-specific value (public domain,
tokens, paths) is supplied out of band via environment variables at deploy time.

## What you get

| Path | What it is |
|---|---|
| `brain-store/` | Template durable store: Projects, Agents, Knowledge, Lessons, Skills, Insights, Sessions, protocol, indexes, log. |
| `runtime/` | Deterministic parser, structure-first chunker, FTS5 index, sparse features, hybrid ranking, caches, receipts, CLI. |
| `cognitive-spec/` | Contracts for retrieval, memory, learning, context, task/session state. |
| `mcp/` | Bearer-protected FastMCP transport and gated Store writes. |
| `deployment/` | Docker Compose, health checks, VPS deploy/migrate, backup, smoke test. |

SQLite state is a rebuildable projection. The Markdown store is the only
durable authority — delete the runtime/cache and you lose latency, not knowledge.

## Prerequisites

- A Linux VPS (or any host) with **Docker + Docker Compose v2** and **git**.
- **Python 3.11+** with SQLite FTS5 support (for local indexing / CLI use).
- Root or sudo access on the target host for the production layout.

## 1. Try it locally (no server needed)

```sh
git clone <this-repo> && cd brain-os-starter

# Scaffold a fresh store from the template (refuses to overwrite):
./scripts/new_store.sh "$HOME/Brain"

# Build and verify the retrieval projection:
BRAIN_STORE_PATH="$HOME/Brain" ./brain index rebuild
BRAIN_STORE_PATH="$HOME/Brain" ./brain index verify

# Ask for compact context:
BRAIN_STORE_PATH="$HOME/Brain" ./brain context \
  "current API decision and relevant lessons" --max-context-units 800
```

The default local database is `~/.brain-runtime/retrieval.sqlite`. Override
with `BRAIN_RUNTIME_PATH` and `BRAIN_CACHE_PATH`. `BRAIN_STORE_PATH` is
canonical; `BRAIN_VAULT_PATH` is a deprecated alias.

## 2. Run the MCP server locally

Generate an out-of-band bearer token, persist only its SHA-256 digest, and keep
the raw value in your secret store. Create a private tokens file:

```sh
TOKEN="$(openssl rand -hex 32)"
echo "sha256\$(printf '%s' "$TOKEN" | sha256sum | cut -d' ' -f1):you:admin" \
  > "$HOME/.brain-tokens" && chmod 600 "$HOME/.brain-tokens"
echo "Share this bearer with your agents: $TOKEN"
```

Start the server (token file is reloaded on every request — add/revoke users
without restarting):

```sh
BRAIN_STORE_PATH="$HOME/Brain" \
BRAIN_TOKEN_FILE="$HOME/.brain-tokens" \
mcp/install.sh --run
```

See [mcp/README.md](mcp/README.md) for tools (`brain_context`, `brain_continue`,
`brain_expand`, gated writes) and token format details.

## 3. Deploy to your own VPS

Production keeps durable, rebuildable, and disposable data separate:

```text
/srv/brain/store     durable OKF Markdown + git
/srv/brain/tokens    durable bearer identities (sha256$hash:user:role)
/srv/brain/runtime   rebuildable SQLite/state/telemetry
/srv/brain/cache     disposable caches
```

The Compose service binds only to `127.0.0.1:8085`; your own nginx/reverse
proxy owns the public route and TLS. The deployment contract does not mount or
depend on any external Redis.

On the VPS, as root:

```sh
# Place this repo at /srv/brain/app and scaffold the store:
git clone <this-repo> /srv/brain/app
install -d -m 0750 -o 10001 -g 10001 /srv/brain/{store,runtime,cache}
/srv/brain/app/scripts/new_store.sh /srv/brain/store

# Create the durable token file (one hashed line per user):
install -m 0600 -o 10001 -g 10001 /dev/null /srv/brain/tokens
# ... add sha256$<digest>:<user>:<role> lines as shown in mcp/tokens.example

# Deploy. Host-specific values are REQUIRED env vars — none live in the repo:
sudo BRAIN_ROOT=/srv/brain BRAIN_APP_PATH=/srv/brain/app \
  BRAIN_PUBLIC_MCP_URL='https://<your-domain>/mcp' \
  BRAIN_SMOKE_TOKEN='<a raw bearer from your tokens file>' \
  OPENSHIP_DEPLOY_ADAPTER=<path-to-your-adapter> \
  /srv/brain/app/deployment/deploy-brain.sh --deploy
```

`deploy-brain.sh` is locked to the provisioned host: it refuses to run unless
it is root **and** `BRAIN_ROOT` is set, so a leaked copy of this repo cannot
drive a deployment by accident. It validates preflight (paths, ownership, git
worktree, readable token file, writable runtime/cache), builds and restarts the
Compose service, refreshes and verifies the index, waits on `/health/live` and
`/health/ready`, runs an authenticated smoke test through your public route,
and tags a timestamped rollback image. Container logs are capped at
`10 MB × 3` files so they cannot fill your disk.

Rollback without touching store data, tokens, or your proxy:

```sh
sudo BRAIN_ROOT=/srv/brain \
  BRAIN_ROLLBACK_IMAGE='brain-os:rollback-YYYYMMDDTHHMMSSZ' \
  BRAIN_SMOKE_TOKEN='<a raw bearer>' \
  BRAIN_PUBLIC_MCP_URL='https://<your-domain>/mcp' \
  /srv/brain/app/deployment/deploy-brain.sh --rollback
```

Full contract, adapter expectations, and recovery notes:
[deployment/README.md](deployment/README.md).

## Verify a production deploy

A deployment is only proven when all of these pass:

```sh
curl -fsS http://127.0.0.1:8085/health/live
curl -fsS http://127.0.0.1:8085/health/ready
BRAIN_PUBLIC_MCP_URL='https://<your-domain>/mcp' \
BRAIN_SMOKE_TOKEN='<a raw bearer>' \
  python3 deployment/mcp_smoke.py
```

An unauthenticated MCP request must be rejected with 401.

## Maintenance

```sh
./brain index status     # chunk counts, stale files, schema version
./brain index refresh    # re-index only changed files
./brain index rebuild    # full rebuild of the projection
./brain index verify     # integrity: FTS counts, orphans, staleness
./brain evaluate         # golden retrieval dataset
pytest -q                # unit + contract suite
```

If the readiness probe reports stale files after external writes to the store,
run `./brain index refresh` — readiness requires a clean index.

## Configuration reference

| Variable | Meaning | Default |
|---|---|---|
| `BRAIN_STORE_PATH` | Durable store path (canonical). | required |
| `BRAIN_RUNTIME_PATH` | Rebuildable SQLite/state. | `~/.brain-runtime` |
| `BRAIN_CACHE_PATH` | Disposable caches. | `<runtime>/cache` |
| `BRAIN_TOKEN_FILE` | Bearer token file (reloaded per request). | required for MCP |
| `BRAIN_MCP_HOST` / `BRAIN_MCP_PORT` | MCP bind address. | `127.0.0.1` / `8848` |
| `BRAIN_PUBLIC_MCP_URL` | Public MCP URL for readiness/smoke (deploy-time, required). | — |
| `BRAIN_SMOKE_TOKEN` | Raw bearer used only by the post-deploy smoke test. | — |
| `BRAIN_UID` / `BRAIN_GID` | Container identity owning store/tokens. | `10001` / `10001` |

Raw bearer values are never persisted to the store or telemetry; only their
SHA-256 digests are kept in the token file.

## Architecture & contracts

- [ARCHITECTURE.md](ARCHITECTURE.md) — retrieval pipeline, fingerprints,
  receipts, learning boundary, isolation.
- [INSTALL.md](INSTALL.md) — local hook/skill/agent install for Claude Code.
- [cognitive-spec/](cognitive-spec/) — the OKF and behavior contracts.

Brain OS stores durable knowledge and serves compact context. It deliberately
does not perform semantic rewriting, store hidden reasoning, or call any model
provider.
