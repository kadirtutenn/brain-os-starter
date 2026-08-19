#!/bin/sh
# Deterministic production pipeline. This script must run on the Brain VPS.
# Openship integration is supplied by an installation-specific adapter whose
# sole argument is deployment/openship.json; the adapter must exit non-zero on
# any failed build/deployment step and must not mutate Openship auth or Redis.
set -eu

MODE="${1:---deploy}"
ROOT="${BRAIN_ROOT:-/srv/brain}"
STORE="$ROOT/store"
LEGACY_STORE="$ROOT/vault"
RUNTIME="$ROOT/runtime"
CACHE="$ROOT/cache"
BACKUPS="$ROOT/backups"
TOKENS="${BRAIN_TOKEN_FILE:-$ROOT/tokens}"
APP="${BRAIN_APP_PATH:-$ROOT/app}"
COMPOSE="$APP/deployment/compose.yml"
MANIFEST="$APP/deployment/openship.json"
PUBLIC_URL="${BRAIN_PUBLIC_MCP_URL:-https://brain.openskillsagent.com/mcp}"
HEALTH_BASE="${BRAIN_HEALTH_BASE_URL:-http://127.0.0.1:8085}"
OPENSHIP_ADAPTER="${OPENSHIP_DEPLOY_ADAPTER:-}"
BRAIN_UID="${BRAIN_UID:-10001}"
BRAIN_GID="${BRAIN_GID:-10001}"

fail() { echo "ERROR: $*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"; }

preflight() {
    need docker
    need git
    need tar
    need curl
    docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 plugin is required"
    docker compose version --short 2>/dev/null | grep -Eq '^v?2\.' || fail "Docker Compose v1 is not supported"
    [ -d "$STORE" ] || fail "Brain Store missing: $STORE"
    [ -d "$STORE/.git" ] || fail "Brain Store is not a healthy git worktree: $STORE"
    [ "$(stat -c %u "$STORE")" = "$BRAIN_UID" ] \
        || fail "Brain Store owner must match BRAIN_UID=$BRAIN_UID"
    git -C "$STORE" status >/dev/null 2>&1 || fail "Brain Store git check failed"
    [ -r "$TOKENS" ] || fail "token file is not readable: $TOKENS"
    [ "$(stat -c %u "$TOKENS")" = "$BRAIN_UID" ] \
        || fail "token file owner must match BRAIN_UID=$BRAIN_UID"
    [ -d "$RUNTIME" ] && [ -w "$RUNTIME" ] || fail "runtime path is not writable: $RUNTIME"
    [ -d "$CACHE" ] && [ -w "$CACHE" ] || fail "cache path is not writable: $CACHE"
    [ -f "$COMPOSE" ] || fail "compose file missing: $COMPOSE"
    [ -f "$MANIFEST" ] || fail "Openship manifest missing: $MANIFEST"
    [ -n "${BRAIN_SMOKE_TOKEN:-}" ] || fail "BRAIN_SMOKE_TOKEN is required for authenticated readiness"
    [ -n "$OPENSHIP_ADAPTER" ] && [ -x "$OPENSHIP_ADAPTER" ] || fail "OPENSHIP_DEPLOY_ADAPTER must name an executable adapter"
    docker inspect openship-redis >/dev/null 2>&1 || fail "openship-redis not found; refusing to alter Openship topology"
    curl --fail --silent --show-error "${OPENSHIP_HEALTH_URL:-http://127.0.0.1:3000/health}" >/dev/null \
        || fail "Openship API health check failed"
    echo "preflight: PASS"
}

bootstrap() {
    install -d -m 0750 "$ROOT" "$BACKUPS"
    install -d -m 0750 -o "$BRAIN_UID" -g "$BRAIN_GID" "$RUNTIME" "$RUNTIME/locks" "$CACHE"
    [ ! -e "$LEGACY_STORE" ] || [ -L "$LEGACY_STORE" ] \
        || [ -e "$STORE" ] || fail "legacy /vault exists; run --migrate-store explicitly"
}

migrate_store() {
    [ -d "$LEGACY_STORE" ] || fail "legacy Store not found: $LEGACY_STORE"
    [ ! -e "$STORE" ] || fail "both legacy and canonical Store paths exist; refusing to diverge them"
    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    install -d -m 0750 "$BACKUPS"
    tar -czf "$BACKUPS/pre-store-migration-$stamp.tar.gz" -C "$ROOT" vault tokens
    mv "$LEGACY_STORE" "$STORE"
    chown -R "$BRAIN_UID:$BRAIN_GID" "$STORE"
    ln -s "$STORE" "$LEGACY_STORE"
    git -C "$STORE" status >/dev/null 2>&1 || fail "migrated Store failed git verification"
    echo "migration: PASS (compatibility symlink retained)"
}

backup() {
    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    tar -czf "$BACKUPS/brain-critical-$stamp.tar.gz" -C "$ROOT" store tokens
    echo "$BACKUPS/brain-critical-$stamp.tar.gz"
}

deploy() {
    bootstrap
    preflight
    redis_before="$(docker inspect --format '{{.State.StartedAt}}' openship-redis)"
    backup_path="$(backup)"
    rollback_image=""
    previous_image="$(docker compose -f "$COMPOSE" images -q brain-mcp 2>/dev/null || true)"
    if [ -n "$previous_image" ]; then
        rollback_image="brain-os:rollback-$(date -u +%Y%m%dT%H%M%SZ)"
        docker image tag "$previous_image" "$rollback_image"
    fi
    started="$(date +%s)"
    docker compose -f "$COMPOSE" config --quiet
    docker compose -f "$COMPOSE" build
    "$OPENSHIP_ADAPTER" "$MANIFEST"
    curl --fail --silent --show-error "$HEALTH_BASE/health/live" >/dev/null
    docker compose -f "$COMPOSE" exec -T brain-mcp /app/brain --store /brain/store \
        --runtime /brain/runtime --cache /brain/cache index migrate
    docker compose -f "$COMPOSE" exec -T brain-mcp /app/brain --store /brain/store \
        --runtime /brain/runtime --cache /brain/cache index refresh
    docker compose -f "$COMPOSE" exec -T brain-mcp /app/brain --store /brain/store \
        --runtime /brain/runtime --cache /brain/cache index verify
    curl --fail --silent --show-error "$HEALTH_BASE/health/ready" >/dev/null
    BRAIN_PUBLIC_MCP_URL="$PUBLIC_URL" docker compose -f "$COMPOSE" exec -T \
        -e BRAIN_PUBLIC_MCP_URL="$PUBLIC_URL" -e BRAIN_SMOKE_TOKEN brain-mcp \
        python /app/deployment/mcp_smoke.py
    redis_after="$(docker inspect --format '{{.State.StartedAt}}' openship-redis)"
    [ "$redis_before" = "$redis_after" ] || fail "openship-redis changed during deployment"
    duration="$(( $(date +%s) - started ))"
    printf '{"timestamp":"%s","duration_seconds":%s,"backup":"%s","rollback_image":"%s","store_commit":"%s"}\n' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$duration" "$backup_path" \
        "$rollback_image" \
        "$(git -C "$STORE" rev-parse HEAD)" >> "$RUNTIME/deployments.jsonl"
    echo "deployment: PASS"
}

rollback() {
    bootstrap
    need docker
    need curl
    docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 plugin is required"
    [ -n "${BRAIN_ROLLBACK_IMAGE:-}" ] || fail "BRAIN_ROLLBACK_IMAGE is required"
    [ -n "${BRAIN_SMOKE_TOKEN:-}" ] || fail "BRAIN_SMOKE_TOKEN is required"
    docker image inspect "$BRAIN_ROLLBACK_IMAGE" >/dev/null 2>&1 \
        || fail "rollback image is not present locally: $BRAIN_ROLLBACK_IMAGE"
    redis_before="$(docker inspect --format '{{.State.StartedAt}}' openship-redis)"
    BRAIN_IMAGE="$BRAIN_ROLLBACK_IMAGE" docker compose -f "$COMPOSE" config --quiet
    BRAIN_IMAGE="$BRAIN_ROLLBACK_IMAGE" docker compose -f "$COMPOSE" up -d \
        --no-build --force-recreate brain-mcp
    curl --fail --silent --show-error "$HEALTH_BASE/health/live" >/dev/null
    curl --fail --silent --show-error "$HEALTH_BASE/health/ready" >/dev/null
    BRAIN_PUBLIC_MCP_URL="$PUBLIC_URL" docker compose -f "$COMPOSE" exec -T \
        -e BRAIN_PUBLIC_MCP_URL="$PUBLIC_URL" -e BRAIN_SMOKE_TOKEN brain-mcp \
        python /app/deployment/mcp_smoke.py
    redis_after="$(docker inspect --format '{{.State.StartedAt}}' openship-redis)"
    [ "$redis_before" = "$redis_after" ] || fail "openship-redis changed during rollback"
    printf '{"timestamp":"%s","event":"rollback","image":"%s","store_commit":"%s"}\n' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$BRAIN_ROLLBACK_IMAGE" \
        "$(git -C "$STORE" rev-parse HEAD)" >> "$RUNTIME/deployments.jsonl"
    echo "rollback: PASS"
}

case "$MODE" in
    --preflight) bootstrap; preflight ;;
    --migrate-store) migrate_store ;;
    --deploy) deploy ;;
    --rollback) rollback ;;
    *) fail "usage: $0 [--preflight|--migrate-store|--deploy|--rollback]" ;;
esac
