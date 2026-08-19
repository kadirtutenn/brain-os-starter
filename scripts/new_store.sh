#!/bin/sh
# new_store.sh — scaffold a fresh durable Brain Store.
#
# Usage:
#   ./scripts/new_store.sh "$HOME/Brain"
# Copies brain-store/ to the target directory (refuses to overwrite an
# existing non-empty directory). After this, run install.sh with the same path.
set -e

TARGET="$1"
[ -n "$TARGET" ] || { echo "Usage: $0 <target-store-path>"; exit 1; }
REPO="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$REPO/brain-store"

if [ -d "$TARGET" ] && [ -n "$(ls -A "$TARGET" 2>/dev/null)" ]; then
    echo "ERROR: target exists and is not empty: $TARGET"
    echo "Choose an empty/new path so nothing is overwritten."
    exit 1
fi

mkdir -p "$TARGET"
cp -R "$SRC/." "$TARGET/"
if command -v git >/dev/null 2>&1; then
    git -C "$TARGET" init -q
    git -C "$TARGET" config user.name "Brain Store Bootstrap"
    git -C "$TARGET" config user.email "brain-bootstrap@example.com"
    git -C "$TARGET" config commit.gpgsign false
    git -C "$TARGET" add -A
    git -C "$TARGET" commit -q -m "Initialize Brain Store"
fi
echo "Scaffolded a fresh Brain Store at: $TARGET"
echo "Next: BRAIN_STORE_PATH=\"$TARGET\" ./scripts/install.sh"
