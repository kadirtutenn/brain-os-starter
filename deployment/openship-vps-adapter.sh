#!/bin/sh
# VPS adapter for the self-hosted Openship CLI.
#
# The deployment pipeline passes deployment/openship.json as the only argument.
# This adapter validates the frozen contract and uses Openship's supported
# folder-upload API. Openship 0.1.11's CLI omits project route data in this
# flow, so the helper carries the already verified custom domain explicitly
# while the repo contract continues to leave public endpoint ownership to nginx.
set -eu

MANIFEST="${1:?usage: openship-vps-adapter.sh deployment/openship.json}"
OPENSHIP_BIN="${OPENSHIP_BIN:-/root/.bun/bin/openship}"
PROJECT_ID="${OPENSHIP_PROJECT_ID:-proj_q34DOZe8Kkzlopmf}"
APP_DIR="$(CDPATH= cd -- "$(dirname -- "$MANIFEST")/.." && pwd)"
CUSTOM_DOMAIN="${OPENSHIP_CUSTOM_DOMAIN:-brain.openskillsagent.com}"
CUSTOM_PORT="${OPENSHIP_CUSTOM_PORT:-8085}"
HELPER="$APP_DIR/deployment/openship-folder-deploy.py"

[ -x "$OPENSHIP_BIN" ] || { echo "Openship CLI is not executable: $OPENSHIP_BIN" >&2; exit 1; }
[ -f "$APP_DIR/docker-compose.yml" ] \
    || { echo "Root docker-compose.yml is required for Openship deployment" >&2; exit 1; }
[ -f "$HELPER" ] || { echo "Openship folder helper is missing: $HELPER" >&2; exit 1; }

python3 - "$MANIFEST" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    manifest = json.load(handle)

expected = {
    "deployTarget": "local",
    "buildStrategy": "local",
    "runtimeMode": "docker",
    "publicEndpoints": [],
    "serviceDeploymentMode": "services",
}
for key, value in expected.items():
    if manifest.get(key) != value:
        raise SystemExit(f"invalid Openship contract: {key}={manifest.get(key)!r}")
PY

DEPLOYMENT_ID="$(python3 "$HELPER" --app-dir "$APP_DIR" --project "$PROJECT_ID" \
    --domain "$CUSTOM_DOMAIN" --port "$CUSTOM_PORT")"
[ -n "$DEPLOYMENT_ID" ] || { echo "Openship returned an empty deployment id" >&2; exit 1; }

"$OPENSHIP_BIN" logs "$DEPLOYMENT_ID" --follow &
LOG_PID=$!
STATUS=unknown
ATTEMPT=0
while [ "$ATTEMPT" -lt 300 ]; do
    STATUS="$("$OPENSHIP_BIN" --json deployment get "$DEPLOYMENT_ID" | python3 -c '
import json, sys
value = json.load(sys.stdin)
if isinstance(value, dict) and "data" in value:
    value = value["data"]
print(value.get("status", "unknown"))
')"
    case "$STATUS" in
        ready|failed|cancelled|rejected) break ;;
    esac
    ATTEMPT=$((ATTEMPT + 1))
    sleep 2
done
kill "$LOG_PID" 2>/dev/null || true
wait "$LOG_PID" 2>/dev/null || true
[ "$STATUS" = "ready" ] \
    || { echo "Openship deployment $DEPLOYMENT_ID finished with status: $STATUS" >&2; exit 1; }
