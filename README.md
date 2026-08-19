# Brain OS Starter

Brain OS is deterministic shared-memory infrastructure for multiple external AI
agents. It stores durable knowledge as OKF Markdown and returns compact,
budgeted context through SQLite FTS5, sparse technical-token ranking,
fingerprints, and caller-scoped context receipts.

Brain OS is not an AI runtime. The core does not call an LLM, embedding model,
reranker, summarizer, or external AI API. External agents do the semantic work;
Brain OS parses, indexes, ranks, packs, versions, and serves shared knowledge.

## Architecture

| Path | Responsibility |
|---|---|
| `brain-store/` | Durable source of truth: Projects, Agents, Knowledge, Lessons, Skills, Insights, Sessions, tasks, protocol, indexes, and log. |
| `runtime/` | Deterministic parser, structure-first chunker, FTS5 index, BrainVector sparse features, hybrid ranking, caches, receipts, telemetry, and CLI. |
| `cognitive-spec/` | Contracts for retrieval, memory, learning, context, and task/session state. |
| `mcp/` | Bearer-protected FastMCP transport and gated Store writes. |
| `deployment/` | Docker Compose, Openship contract, health checks, VPS migration, backup, and smoke test. |

SQLite state is a disposable projection. OKF frontmatter and Markdown in the
Brain Store remain the only durable metadata authority.

## Quick start

```sh
# Create a new Brain Store without overwriting an existing directory.
./scripts/new_store.sh "$HOME/Brain"

# Build and verify the deterministic retrieval projection.
BRAIN_STORE_PATH="$HOME/Brain" ./brain index rebuild
BRAIN_STORE_PATH="$HOME/Brain" ./brain index verify

# Retrieve compact context under a provider-independent budget.
BRAIN_STORE_PATH="$HOME/Brain" ./brain context \
  "current API decision and relevant lessons" --max-context-units 800

# Install the local Claude Code hook/skill/agents.
BRAIN_STORE_PATH="$HOME/Brain" ./scripts/install.sh
```

`BRAIN_STORE_PATH` is canonical. `BRAIN_VAULT_PATH` is accepted temporarily as
a deprecated compatibility alias.

## Retrieval maintenance

```sh
./brain index status
./brain index refresh
./brain index rebuild
./brain index migrate
./brain index verify
./brain evaluate evaluation/retrieval-golden.json
```

The default local database is `~/.brain-runtime/retrieval.sqlite`. Override
rebuildable and disposable paths with `BRAIN_RUNTIME_PATH` and
`BRAIN_CACHE_PATH`.

## MCP

The primary read primitives are `brain_context`, `brain_continue`, and
`brain_expand`. Low-level search/get tools remain for compatibility and
debugging. Every MCP request is transport-authenticated from the dynamically
reloaded token file; caller identity becomes provenance without storing raw
tokens.

```sh
BRAIN_STORE_PATH="$HOME/Brain" \
BRAIN_TOKEN_FILE="/absolute/path/to/tokens" \
mcp/install.sh --run
```

See [mcp/README.md](mcp/README.md) for tool and token details.

## Production

Production keeps durable, rebuildable, and disposable data separate:

```text
/srv/brain/store     durable OKF Markdown + git
/srv/brain/tokens    durable bearer identities
/srv/brain/runtime   rebuildable SQLite/state/telemetry
/srv/brain/cache     disposable caches
```

The Compose service binds only to `127.0.0.1:8085`; nginx owns the public MCP
route. The deployment contract neither mounts nor depends on Openship Redis.
See [deployment/README.md](deployment/README.md). A real VPS deployment is not
proven merely by local tests or a running container: both health probes, index
verification, and the authenticated public-route smoke test must pass.
