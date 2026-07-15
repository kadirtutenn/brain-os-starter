# server.py — FastMCP server exposing the Brain vault over streamable HTTP.
#
# Every read and write function in mcp.core is registered as an MCP tool.
# The vault root is read once from BRAIN_VAULT_PATH. Read tools are open;
# write tools resolve the caller's identity from the request's
# "Authorization: Bearer <token>" header via auth.authenticate and pass it
# to core as `author`. All rules/Dashboard/PROTOCOL protection and admin
# checks are enforced inside core — this layer only supplies identity.
#
# Environment:
#   BRAIN_VAULT_PATH   filesystem root of the vault (required)
#   BRAIN_MCP_TOKENS   path to the bearer-token file (see auth.py)
#   BRAIN_MCP_HOST     bind host   (default 127.0.0.1)
#   BRAIN_MCP_PORT     bind port   (default 8848)
import os
import sys

# This directory holds core.py/auth.py as top-level modules. Adding it to the
# path lets the server run from anywhere without being a Python package named
# "mcp" (which would shadow the PyPI `mcp` SDK that fastmcp depends on).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_request

import auth
import core

VAULT = os.environ.get("BRAIN_VAULT_PATH", os.path.expanduser("~/Brain"))

mcp = FastMCP(
    name="Brain OS",
    instructions=(
        "Read/write access to an OKF Markdown knowledge vault. Start with "
        "get_dashboard for active state, search/find_* to locate concepts, "
        "and get_concept for full bodies. Writes require a bearer token; "
        "rules/Dashboard/PROTOCOL changes go through new_rule + admin approval."
    ),
)


def _caller():
    """Resolve the calling identity from the request's bearer token.

    Returns the {"name", "email", "is_admin"} dict from auth.authenticate,
    letting auth.AuthError propagate so FastMCP reports it to the client.
    """
    request = get_http_request()
    return auth.authenticate(request.headers.get("Authorization"))


# --- READ tools -----------------------------------------------------------

@mcp.tool
def get_dashboard() -> str:
    """Return Dashboard.md verbatim (the always-loaded active-state panel)."""
    return core.get_dashboard(VAULT)


@mcp.tool
def get_index(path: str = "") -> str:
    """Return a Markdown directory map of the vault under an optional subpath."""
    return core.get_index(VAULT, path)


@mcp.tool
def get_concept(concept_id: str) -> dict:
    """Fetch one concept (id/type/description/tags/body) by vault-relative path."""
    return core.get_concept(VAULT, concept_id)


@mcp.tool
def search(query: str, type: str | None = None, limit: int = 10) -> list[dict]:
    """Locate concepts by query; frontmatter-weighted, sorted by relevance, capped at limit.
    Optional exact type filter (case-sensitive): Skill, Lesson, Session, Reference, Knowledge, Project, Hypothesis."""
    return core.search(VAULT, query, type=type, limit=limit)


@mcp.tool
def find_skill(keyword: str, limit: int = 10) -> list[dict]:
    """Shortcut for search(type='Skill'): find Skill concepts by keyword."""
    return core.find_skill(VAULT, keyword, limit=limit)


@mcp.tool
def find_lesson(keyword: str, limit: int = 10) -> list[dict]:
    """Match keyword lines in Lessons/INDEX.md and return the linked lessons."""
    return core.find_lesson(VAULT, keyword, limit=limit)


@mcp.tool
def recent_changes(n: int = 10) -> list[str]:
    """Return the last n non-empty lines of log.md (most recent activity)."""
    return core.recent_changes(VAULT, n)


# --- WRITE tools (identity resolved from bearer token) --------------------

@mcp.tool
def new_lesson(area: str, slug: str, content: str, keywords: list[str]) -> str:
    """Append a lesson to an existing Lessons/{area} file and index its keywords."""
    return core.new_lesson(VAULT, area, slug, content, keywords, author=_caller())


@mcp.tool
def new_skill(name: str, content: str) -> str:
    """Create Skills/{slug}.md with valid OKF frontmatter."""
    return core.new_skill(VAULT, name, content, author=_caller())


@mcp.tool
def update_concept(concept_id: str, patch: str) -> str:
    """Apply a patch to an existing concept identified by its vault-relative path."""
    return core.update_concept(VAULT, concept_id, patch, author=_caller())


@mcp.tool
def log_session(handoff: str) -> str:
    """Write a session handoff to Sessions/{date} and run the triple update."""
    return core.log_session(VAULT, handoff, author=_caller())


@mcp.tool
def new_rule(text: str, rationale: str) -> str:
    """Enqueue a rule-change proposal (does not write rules/); returns proposal id."""
    return core.new_rule(VAULT, text, rationale, author=_caller())


@mcp.tool
def approve_proposal(proposal_id: str) -> str:
    """Apply a queued proposal; requires the caller to hold the admin role."""
    return core.approve_proposal(VAULT, proposal_id, is_admin=_caller()["is_admin"])


if __name__ == "__main__":
    host = os.environ.get("BRAIN_MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("BRAIN_MCP_PORT", "8848"))
    mcp.run(transport="http", host=host, port=port)
