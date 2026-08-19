# Install Brain OS

## Local prerequisites

- Python 3 with SQLite FTS5 support;
- git for durable Store history;
- Obsidian only if you want a visual editor/graph;
- FastMCP dependencies only when running the optional network server.

## Create and index a Store

```sh
./scripts/new_store.sh "$HOME/Brain"
BRAIN_STORE_PATH="$HOME/Brain" ./brain index rebuild
BRAIN_STORE_PATH="$HOME/Brain" ./brain index verify
```

The Store is Markdown. The default rebuildable database is
`~/.brain-runtime/retrieval.sqlite`; caches are separate SQLite files under
`~/.brain-runtime/cache`.

## Install the local hook

```sh
BRAIN_STORE_PATH="$HOME/Brain" ./scripts/install.sh
```

The installer rewrites only documented placeholders in the selected Store,
backs up Claude Code settings, copies the hook/skill/agents, and registers a
hook command with this repo on `PYTHONPATH`. Indexed retrieval is used when the
runtime package is available; the old lexical path remains only as a copied-hook
compatibility fallback.

`BRAIN_VAULT_PATH` is a deprecated compatibility alias. New configuration must
use `BRAIN_STORE_PATH`.

## Run the optional MCP server

Create an out-of-band token file, permissioned for the service user:

```text
opaque-random-token:alice:user
different-random-token:admin-user:admin
```

Then:

```sh
BRAIN_STORE_PATH="$HOME/Brain" \
BRAIN_RUNTIME_PATH="$HOME/.brain-runtime" \
BRAIN_CACHE_PATH="$HOME/.brain-runtime/cache" \
BRAIN_TOKEN_FILE="/absolute/path/to/tokens" \
mcp/install.sh --run
```

The token file is read on every verification, so caller additions/revocations
do not require a server restart. Raw bearer values are not persisted in Store
content or telemetry.

## Verify

```sh
BRAIN_STORE_PATH="$HOME/Brain" ./brain index status
BRAIN_STORE_PATH="$HOME/Brain" ./brain evaluate
```

For local development, run the unit/contract suite with `pytest -q`. Production
verification additionally requires `/health/live`, `/health/ready`, an
authenticated `brain_context` call through the public nginx route, and rejection
of an unauthenticated MCP request.

## VPS

Use [deployment/README.md](deployment/README.md). Legacy `/srv/brain/vault` to
`/srv/brain/store` migration is a separate explicit operation with a critical
backup and compatibility symlink; the deploy command will not silently create
two writable Stores.
