#!/bin/sh
# new_vault.sh — scaffold a fresh Brain vault by copying the template skeleton.
#
# Usage:
#   ./scripts/new_vault.sh "$HOME/Brain"
# Copies vault-template/ to the target directory (refuses to overwrite an
# existing non-empty directory). After this, run install.sh with the same path.
set -e

TARGET="$1"
[ -n "$TARGET" ] || { echo "Usage: $0 <target-vault-path>"; exit 1; }
REPO="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$REPO/vault-template"

if [ -d "$TARGET" ] && [ -n "$(ls -A "$TARGET" 2>/dev/null)" ]; then
    echo "ERROR: target exists and is not empty: $TARGET"
    echo "Choose an empty/new path so nothing is overwritten."
    exit 1
fi

mkdir -p "$TARGET"
cp -R "$SRC/." "$TARGET/"
echo "Scaffolded a fresh vault at: $TARGET"
echo "Next: BRAIN_VAULT_PATH=\"$TARGET\" ./scripts/install.sh"
