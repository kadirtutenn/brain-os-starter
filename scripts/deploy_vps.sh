#!/bin/sh
# Compatibility entrypoint for the production deployment pipeline.
set -eu

REPO="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
echo "NOTE: scripts/deploy_vps.sh now delegates to deployment/deploy-brain.sh" >&2
exec "$REPO/deployment/deploy-brain.sh" "$@"
