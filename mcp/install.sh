#!/bin/sh
# install.sh — install and (optionally) run the Brain OS MCP server.
#
# The MCP server is the OPTIONAL component that lets remote agents reach a
# central vault over HTTP. The core engine (mcp/core.py) and the session hooks
# are stdlib-only and need none of this.
#
# Clone the repo, then from the repo root run ONE of:
#   mcp/install.sh                 create the venv + install deps, print run steps
#   mcp/install.sh --run           ... and start the server in the foreground
#   sudo mcp/install.sh --systemd  ... install a systemd service + env template (VPS)
#
# Environment:
#   BRAIN_MCP_VENV   venv location            (default: <repo>/.venv)
#   PYTHON           python interpreter        (default: python3)
#   BRAIN_VAULT_PATH vault root (required for --run and to prefill --systemd env)
#   BRAIN_MCP_HOST   bind host                 (default: 127.0.0.1)
#   BRAIN_MCP_PORT   bind port                 (default: 8848)
set -e

MODE="${1:-}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${BRAIN_MCP_VENV:-$REPO/.venv}"
PYTHON="${PYTHON:-python3}"
HOST="${BRAIN_MCP_HOST:-127.0.0.1}"
PORT="${BRAIN_MCP_PORT:-8848}"

# ---- 1. virtualenv + dependencies (idempotent) ------------------------------
if [ ! -x "$VENV/bin/python" ]; then
    echo "==> creating virtualenv at $VENV"
    "$PYTHON" -m venv "$VENV"
fi
echo "==> installing dependencies from mcp/requirements.txt"
"$VENV/bin/python" -m pip install -q --upgrade pip
"$VENV/bin/python" -m pip install -q -r "$REPO/mcp/requirements.txt"
echo "==> dependencies ready ($("$VENV/bin/python" -c 'import fastmcp; print("fastmcp", fastmcp.__version__)'))"

RUN_CMD="$VENV/bin/python $REPO/mcp/server.py"

case "$MODE" in
--run)
    [ -n "$BRAIN_VAULT_PATH" ] || { echo "ERROR: set BRAIN_VAULT_PATH to your vault root"; exit 1; }
    [ -d "$BRAIN_VAULT_PATH" ] || { echo "ERROR: not a directory: $BRAIN_VAULT_PATH"; exit 1; }
    echo "==> starting server on $HOST:$PORT (vault: $BRAIN_VAULT_PATH)"
    exec env BRAIN_VAULT_PATH="$BRAIN_VAULT_PATH" BRAIN_MCP_HOST="$HOST" BRAIN_MCP_PORT="$PORT" $RUN_CMD
    ;;
--systemd)
    # Requires root. Writes an env template (never overwriting an existing one),
    # installs the unit with this checkout's paths substituted, and starts it.
    ENV_FILE=/etc/brain-mcp.env
    UNIT=/etc/systemd/system/brain-mcp.service
    if [ ! -f "$ENV_FILE" ]; then
        echo "==> writing env template $ENV_FILE (edit it: set the vault path + real tokens)"
        cat > "$ENV_FILE" <<EOF
BRAIN_VAULT_PATH=${BRAIN_VAULT_PATH:-/srv/brain/vault}
# One entry per line is NOT used here; BRAIN_MCP_TOKENS points at a token FILE
# (format "token:username:role"), see mcp/tokens.example. Keep it chmod 600.
BRAIN_MCP_TOKENS=/etc/brain-mcp.tokens
BRAIN_MCP_HOST=$HOST
BRAIN_MCP_PORT=$PORT
EOF
        chmod 600 "$ENV_FILE"
    else
        echo "==> keeping existing $ENV_FILE"
    fi
    echo "==> installing $UNIT (paths -> $REPO, venv -> $VENV)"
    sed -e "s#/srv/brain/brain-os-starter/.venv#$VENV#g" \
        -e "s#/srv/brain/brain-os-starter#$REPO#g" \
        "$REPO/mcp/systemd/brain-mcp.service" > "$UNIT"
    systemctl daemon-reload
    systemctl enable --now brain-mcp.service
    echo "==> service status:"
    systemctl --no-pager status brain-mcp.service || true
    ;;
"")
    echo
    echo "Dependencies installed. To run the server:"
    echo "  BRAIN_VAULT_PATH=/path/to/your/Brain mcp/install.sh --run"
    echo "or start it directly:"
    echo "  BRAIN_VAULT_PATH=/path/to/your/Brain $RUN_CMD"
    echo "For a VPS daemon: sudo BRAIN_VAULT_PATH=/srv/brain/vault mcp/install.sh --systemd"
    ;;
*)
    echo "ERROR: unknown mode '$MODE' (use --run, --systemd, or no argument)"; exit 1
    ;;
esac
