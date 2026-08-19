# Brain MCP

Brain MCP exposes the deterministic retrieval and gated write layers over
FastMCP streamable HTTP. The transport is optional; the Store and local CLI are
stdlib-only.

## Primary tools

| Tool | Purpose |
|---|---|
| `brain_context` | Server-side FTS5/sparse/hybrid retrieval and budgeted context packing. |
| `brain_continue` | Continue a caller-scoped context handle and return deltas. |
| `brain_expand` | Expand a ref to section, adjacent, or full-concept scope. |
| `brain_status` | Report generations, counts, staleness, and FTS status. |
| `brain_report_usage` | Record explicit useful refs and verified outcomes. |

Low-level `search`, `find_*`, `get_*`, and `recent_changes` remain available for
debugging/compatibility. Write tools retain the validation, secret, single-writer,
protected-target proposal, provenance, triple-update, and authored git commit
gates. There is no delete tool.

## Authentication

Every MCP endpoint request is protected at the transport boundary by a custom
opaque-token verifier. It reloads `BRAIN_TOKEN_FILE` for every verification:

```text
token:username:user
admin-token:username:admin
```

The verified caller becomes write provenance and receipt ownership. Raw tokens
are never copied into Markdown or retrieval telemetry. Health routes are not MCP
routes and intentionally expose only boolean/readiness state.

## Local run

```sh
BRAIN_STORE_PATH="$HOME/Brain" \
BRAIN_RUNTIME_PATH="$HOME/.brain-runtime" \
BRAIN_CACHE_PATH="$HOME/.brain-runtime/cache" \
BRAIN_TOKEN_FILE="/secure/path/brain.tokens" \
BRAIN_MCP_HOST=127.0.0.1 \
BRAIN_MCP_PORT=8848 \
mcp/install.sh --run
```

## Health

- `/health/live` proves only that the process can serve HTTP.
- `/health/ready` checks Store access, token readability, SQLite/FTS schema,
  zero stale files, and writable cache state without exposing content or paths.

## Production

Use `deployment/compose.yml` and `deployment/deploy-brain.sh`. Production binds
`127.0.0.1:8085`; nginx serves the public TLS endpoint. The authenticated smoke
test uses the public route and verifies `brain_status`, bounded `brain_context`,
metrics, and unauthenticated rejection.
