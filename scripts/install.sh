#!/bin/sh
# install.sh — set up the Brain OS on a new machine for a new user.
#
# Prerequisite: you have a Brain Store (either scaffolded with
# scripts/new_store.sh, copied from brain-store/, or a distributed bundle).
#
# Usage:
#   BRAIN_STORE_PATH="$HOME/Brain" ./scripts/install.sh
# Optional env:
#   CLAUDE_DIR       (default: ~/.claude) — Claude Code config home.
#   WORKSPACE_ROOT   (default: ~/Documents/GitHub) — used only for {{WORKSPACE_ROOT}}
#                    placeholder rewrites, if present in the Store.
#
# What it does (all idempotent; settings.json is backed up first):
#   1. Rewrites {{BRAIN_ROOT}} / {{WORKSPACE_ROOT}} / {{CLAUDE_HOME}} placeholders
#      inside the Store to this machine's real paths.
#   2. Installs the context and lifecycle hooks into CLAUDE_DIR/hooks/ and
#      registers them in settings.json with BRAIN_STORE_PATH set.
#   3. Registers the rules.py hook (runs from this repo).
#   4. Installs the reasoning-core skill into CLAUDE_DIR/skills/.
#   5. Installs the brain-manager and context-builder agents into CLAUDE_DIR/agents/.
# Bypass rule injection anytime with BRAIN_RULES_BYPASS=1 (rules stay in force).
set -e

if [ -z "$BRAIN_STORE_PATH" ] && [ -n "$BRAIN_VAULT_PATH" ]; then
    echo "WARNING: BRAIN_VAULT_PATH is deprecated; use BRAIN_STORE_PATH"
    BRAIN_STORE_PATH="$BRAIN_VAULT_PATH"
fi
[ -n "$BRAIN_STORE_PATH" ] || { echo "ERROR: set BRAIN_STORE_PATH (your Brain Store directory)"; exit 1; }
[ -d "$BRAIN_STORE_PATH" ] || { echo "ERROR: not a directory: $BRAIN_STORE_PATH"; exit 1; }
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
WORKSPACE_ROOT_VAL="${WORKSPACE_ROOT:-$HOME/Documents/GitHub}"

echo "1/5 rewriting placeholders in the Brain Store..."
BRAIN_STORE_PATH="$BRAIN_STORE_PATH" CLAUDE_DIR="$CLAUDE_DIR" WORKSPACE_ROOT_VAL="$WORKSPACE_ROOT_VAL" python3 - <<'PY'
import os
brain = os.environ["BRAIN_STORE_PATH"]
rew = [("{{BRAIN_ROOT}}", brain),
       ("{{WORKSPACE_ROOT}}", os.environ["WORKSPACE_ROOT_VAL"]),
       ("{{CLAUDE_HOME}}", os.environ["CLAUDE_DIR"])]
n = 0
for root, dirs, files in os.walk(brain):
    dirs[:] = [d for d in dirs if not d.startswith(".")]
    for fn in files:
        if not fn.endswith(".md"):
            continue
        p = os.path.join(root, fn)
        c = open(p, encoding="utf-8").read()
        c2 = c
        for old, new in rew:
            c2 = c2.replace(old, new)
        if c2 != c:
            open(p, "w", encoding="utf-8").write(c2)
            n += 1
print("   files rewritten:", n)
PY

echo "2/5 installing brain_context hook..."
mkdir -p "$CLAUDE_DIR/hooks"
cp "$REPO/hooks/brain_context.py" "$CLAUDE_DIR/hooks/brain_context.py"
cp "$REPO/hooks/session_capture.py" "$CLAUDE_DIR/hooks/session_capture.py"

echo "3/5 registering hooks in settings.json (backing up first)..."
BRAIN_STORE_PATH="$BRAIN_STORE_PATH" CLAUDE_DIR="$CLAUDE_DIR" REPO="$REPO" python3 - <<'PY'
import json, os, shutil
cdir = os.environ["CLAUDE_DIR"]; repo = os.environ["REPO"]
brain = os.environ["BRAIN_STORE_PATH"]
p = os.path.join(cdir, "settings.json")
d = {}
if os.path.exists(p):
    shutil.copy2(p, p + ".bak-brain-install")
    d = json.load(open(p))
ups = d.setdefault("hooks", {}).setdefault("UserPromptSubmit", [])
def ensure(cmd, msg):
    if any(cmd in h.get("command", "") for g in ups for h in g.get("hooks", [])):
        return
    ups.append({"hooks": [{"type": "command", "command": cmd,
                           "statusMessage": msg, "once": True}]})
ensure('PYTHONPATH="%s" BRAIN_STORE_PATH="%s" python3 "%s/hooks/brain_context.py"' % (repo, brain, cdir),
       "Loading Brain...")
ensure('python3 "%s/hooks/rules.py"' % repo, "Loading rules...")
life = 'BRAIN_STORE_PATH="%s" python3 "%s/hooks/session_capture.py"' % (brain, cdir)
for event in ("SessionEnd", "PreCompact"):
    groups = d.setdefault("hooks", {}).setdefault(event, [])
    if not any(life in h.get("command", "") for g in groups for h in g.get("hooks", [])):
        groups.append({"hooks": [{"type": "command", "command": life,
                                   "statusMessage": "Saving Brain session..."}]})
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
print("   settings.json updated:", p)
PY

echo "4/5 installing reasoning-core skill..."
mkdir -p "$CLAUDE_DIR/skills/reasoning-core"
cp "$REPO/skills/reasoning-core/SKILL.md" "$CLAUDE_DIR/skills/reasoning-core/SKILL.md"

echo "5/5 installing agents..."
mkdir -p "$CLAUDE_DIR/agents"
cp "$REPO/agents/brain-manager.md" "$CLAUDE_DIR/agents/brain-manager.md"
cp "$REPO/agents/context-builder.md" "$CLAUDE_DIR/agents/context-builder.md"

echo ""
echo "DONE. Verify: open a new Claude Code session; the first prompt should show"
echo "'--- Brain Dashboard ---' and '--- Working Rules ---' context blocks."
echo "Open this Brain Store in Obsidian if desired: $BRAIN_STORE_PATH"
