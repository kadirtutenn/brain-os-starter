# auth.py — bearer-token authentication for the Brain MCP server.
#
# Tokens live in a plaintext file whose path comes from the BRAIN_MCP_TOKENS
# environment variable. One credential per line:
#
#     <token>:<username>:<role>
#
# where <role> is either "user" or "admin". Blank lines and lines starting
# with "#" are ignored. See tokens.example for the on-disk format — never
# commit real tokens.
#
# authenticate(bearer) maps a presented bearer credential to a caller
# identity dict {"name", "email", "is_admin"} that the write tools pass on
# to mcp.core as `author`. Unknown or malformed credentials raise AuthError.
import os

VALID_ROLES = {"user", "admin"}
DEFAULT_EMAIL_DOMAIN = "example.com"


class AuthError(Exception):
    """Raised when a bearer credential is missing, malformed, or unknown."""


def _tokens_path():
    path = os.environ.get("BRAIN_MCP_TOKENS")
    if not path:
        raise AuthError("BRAIN_MCP_TOKENS is not set")
    return path


def _strip_bearer(bearer):
    if not bearer:
        raise AuthError("missing bearer credential")
    value = bearer.strip()
    if value.lower().startswith("bearer "):
        value = value[len("bearer "):].strip()
    if not value:
        raise AuthError("empty bearer credential")
    return value


def load_tokens(path=None):
    """Parse the tokens file into {token: (username, role)}.

    Malformed lines and unknown roles are skipped rather than aborting the
    whole load, so one bad line cannot lock everyone out.
    """
    path = path or _tokens_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except OSError as exc:
        raise AuthError("cannot read tokens file: %s" % exc)

    table = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(":")
        if len(parts) != 3:
            continue
        token, username, role = (p.strip() for p in parts)
        role = role.lower()
        if not token or not username or role not in VALID_ROLES:
            continue
        table[token] = (username, role)
    return table


def authenticate(bearer, path=None):
    """Resolve a bearer credential to {"name", "email", "is_admin"}.

    Raises AuthError on an unknown, empty, or malformed credential. The
    Authorization header value ("Bearer <token>") or a bare token are both
    accepted.
    """
    token = _strip_bearer(bearer)
    table = load_tokens(path)
    entry = table.get(token)
    if entry is None:
        raise AuthError("unknown token")
    username, role = entry
    return {
        "name": username,
        "email": "%s@%s" % (username, DEFAULT_EMAIL_DOMAIN),
        "is_admin": role == "admin",
    }
