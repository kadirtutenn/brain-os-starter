# server.py — FastMCP server exposing the Brain Store over streamable HTTP.
#
# Every MCP tool, including reads, authenticates through BearerGate. The raw
# bearer value is never written to Store content or retrieval telemetry.
#
# Environment:
#   BRAIN_STORE_PATH   filesystem root of the Brain Store (canonical)
#   BRAIN_VAULT_PATH   deprecated compatibility alias
#   BRAIN_RUNTIME_PATH rebuildable runtime directory
#   BRAIN_CACHE_PATH   disposable cache directory
#   BRAIN_MCP_TOKENS   path to the bearer-token file (see auth.py)
#   BRAIN_MCP_HOST     bind host   (default 127.0.0.1)
#   BRAIN_MCP_PORT     bind port   (default 8848)
import os
import sys

# This directory holds core.py/auth.py as top-level modules. Adding it to the
# path lets the server run from anywhere without being a Python package named
# "mcp" (which would shadow the PyPI `mcp` SDK that fastmcp depends on).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token
from starlette.requests import Request
from starlette.responses import JSONResponse

import auth
import core
from runtime.config import resolve_store_path

STORE = str(resolve_store_path())

mcp = FastMCP(
    name="Brain OS",
    auth=auth.build_token_verifier(),
    instructions=(
        "Deterministic shared memory over an OKF Markdown Brain Store. Start "
        "with brain_context and expand only the returned refs when needed. "
        "Every tool requires a bearer token; "
        "rules/Dashboard/PROTOCOL changes go through new_rule + admin approval."
    ),
)


def _caller():
    """Resolve the calling identity from the request's bearer token.

    Returns the {"name", "email", "is_admin"} dict from auth.authenticate,
    letting auth.AuthError propagate so FastMCP reports it to the client.
    """
    token = get_access_token()
    if token is None:
        raise auth.AuthError("missing authenticated caller")
    claims = token.claims or {}
    return {
        "name": claims.get("name") or token.client_id,
        "email": claims.get("email") or "%s@example.com" % token.client_id,
        "is_admin": bool(claims.get("is_admin")),
        "caller_id": claims.get("caller_id") or token.client_id,
        "agent_id": claims.get("agent_id") or token.subject or token.client_id,
        "permissions": list(token.scopes),
    }


# --- HIGH-LEVEL RETRIEVAL tools -------------------------------------------

@mcp.tool
def brain_context(
    query: str, project: str = "", agent: str = "", mode: str = "compact",
    max_context_units: int = 1200, context_handle: str = "",
    filters: dict | None = None,
) -> dict:
    """Return compact, ranked context under a deterministic caller budget."""
    caller = _caller()
    return core.brain_context(
        STORE, query, project, agent or caller["agent_id"], mode,
        max_context_units, context_handle, filters or {}, caller["caller_id"],
    )


@mcp.tool
def brain_continue(
    context_handle: str, query: str, project: str = "", agent: str = "",
    mode: str = "compact", max_context_units: int = 1200,
    filters: dict | None = None,
) -> dict:
    """Continue a context handle and return only changed/not-yet-seen content."""
    caller = _caller()
    return core.brain_continue(
        STORE, context_handle, query, project, agent or caller["agent_id"],
        mode, max_context_units, filters or {}, caller["caller_id"],
    )


@mcp.tool
def brain_expand(
    ref: str, level: str = "section", context_handle: str = "",
    max_context_units: int = 2400,
) -> dict:
    """Expand a fingerprint/chunk to section, adjacent, or full_concept scope."""
    caller = _caller()
    return core.brain_expand(
        STORE, ref, level, context_handle, max_context_units, caller["caller_id"]
    )


@mcp.tool
def brain_status() -> dict:
    """Return Brain Store/index generation and staleness status."""
    _caller()
    return core.brain_status(STORE)


@mcp.tool
def brain_report_usage(
    useful_refs: list[str], verified: bool = False, retrieval_run_id: str = ""
) -> dict:
    """Report useful refs and optional verified success for learning telemetry."""
    caller = _caller()
    return core.brain_report_usage(
        STORE, caller["caller_id"], useful_refs, verified, retrieval_run_id
    )


# --- LOW-LEVEL COMPATIBILITY READ tools -----------------------------------

@mcp.tool
def get_dashboard() -> str:
    """Return Dashboard.md verbatim (the always-loaded active-state panel)."""
    _caller()
    return core.get_dashboard(STORE)


@mcp.tool
def get_index(path: str = "") -> str:
    """Return a Markdown directory map of the Store under an optional subpath."""
    _caller()
    return core.get_index(STORE, path)


@mcp.tool
def get_concept(concept_id: str) -> dict:
    """Fetch one concept (id/type/description/tags/body) by Store-relative path."""
    _caller()
    return core.get_concept(STORE, concept_id)


@mcp.tool
def search(query: str, type: str | None = None, limit: int = 10) -> list[dict]:
    """Locate concepts by query; frontmatter-weighted, sorted by relevance, capped at limit.
    Optional exact type filter (case-sensitive): Skill, Lesson, Session, Reference, Knowledge, Project, Hypothesis."""
    _caller()
    return core.search(STORE, query, type=type, limit=limit)


@mcp.tool
def find_concept(query: str, type: str | None = None, limit: int = 10) -> list[dict]:
    """Compatibility alias for low-level concept search."""
    _caller()
    return core.find_concept(STORE, query, type=type, limit=limit)


@mcp.tool
def find_skill(keyword: str, limit: int = 10) -> list[dict]:
    """Shortcut for search(type='Skill'): find Skill concepts by keyword."""
    _caller()
    return core.find_skill(STORE, keyword, limit=limit)


@mcp.tool
def find_lesson(keyword: str, limit: int = 10) -> list[dict]:
    """Match keyword lines in Lessons/INDEX.md and return the linked lessons."""
    _caller()
    return core.find_lesson(STORE, keyword, limit=limit)


@mcp.tool
def recent_changes(n: int = 10) -> list[str]:
    """Return the last n non-empty lines of log.md (most recent activity)."""
    _caller()
    return core.recent_changes(STORE, n)


# --- WRITE tools (identity resolved from bearer token) --------------------

@mcp.tool
def new_lesson(area: str, slug: str, content: str, keywords: list[str]) -> str:
    """Append a lesson to an existing Lessons/{area} file and index its keywords."""
    return core.new_lesson(STORE, area, slug, content, keywords, author=_caller())


@mcp.tool
def new_skill(name: str, content: str) -> str:
    """Create Skills/{slug}.md with valid OKF frontmatter."""
    return core.new_skill(STORE, name, content, author=_caller())


@mcp.tool
def update_concept(concept_id: str, patch: str) -> str:
    """Apply a patch to an existing concept identified by its Store-relative path."""
    return core.update_concept(STORE, concept_id, patch, author=_caller())


@mcp.tool
def log_session(handoff: str) -> str:
    """Write a session handoff to Sessions/{date} and run the triple update."""
    return core.log_session(STORE, handoff, author=_caller())


@mcp.tool
def new_rule(text: str, rationale: str) -> str:
    """Enqueue a rule-change proposal (does not write rules/); returns proposal id."""
    return core.new_rule(STORE, text, rationale, author=_caller())


@mcp.tool
def propose_concept_update(concept_id: str, replacement: str, rationale: str) -> str:
    """Queue a full replacement for protected Dashboard.md or PROTOCOL.md."""
    return core.propose_concept_update(
        STORE, concept_id, replacement, rationale, author=_caller()
    )


@mcp.tool
def approve_proposal(proposal_id: str) -> str:
    """Apply a queued proposal; requires the caller to hold the admin role."""
    caller = _caller()
    return core.approve_proposal(
        STORE, proposal_id, is_admin=caller["is_admin"], admin_author=caller
    )


# Health routes are operational probes, not MCP requests. They never reveal
# tokens, Store content, or filesystem-sensitive details.
@mcp.custom_route("/health/live", methods=["GET"])
async def health_live(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


@mcp.custom_route("/health/ready", methods=["GET"])
async def health_ready(_request: Request) -> JSONResponse:
    try:
        status = core.brain_status(STORE)
        token_file = os.environ.get("BRAIN_TOKEN_FILE") or os.environ.get("BRAIN_MCP_TOKENS", "")
        auth_ready = bool(token_file and os.path.isfile(token_file) and os.access(token_file, os.R_OK))
        cache_path = os.environ.get("BRAIN_CACHE_PATH", os.path.expanduser("~/.brain-runtime/cache"))
        cache_ready = os.path.isdir(cache_path) and os.access(cache_path, os.W_OK)
        ready = (
            status["fts_available"] and status["schema_version"] > 0
            and status["stale_file_count"] == 0 and auth_ready and cache_ready
        )
        payload = {
            "status": "ready" if ready else "not_ready",
            "store": {"accessible": os.path.isdir(STORE),
                      "git_repository": os.path.isdir(os.path.join(STORE, ".git"))},
            "auth": {"token_file_readable": auth_ready},
            "retrieval": {"database_open": True, "fts_available": status["fts_available"],
                          "schema_current": status["schema_version"] > 0},
            "index": {"ready": status["chunk_count"] > 0,
                      "stale_files": status["stale_file_count"]},
            "cache": {"writable": cache_ready},
        }
        return JSONResponse(payload, status_code=200 if ready else 503)
    except Exception:
        return JSONResponse({"status": "not_ready"}, status_code=503)


if __name__ == "__main__":
    host = os.environ.get("BRAIN_MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("BRAIN_MCP_PORT", "8848"))
    mcp.run(transport="http", host=host, port=port)
