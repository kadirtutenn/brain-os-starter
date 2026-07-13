# rules.py — UserPromptSubmit hook that injects your working rules into every session.
#
# Source: rules/working-rules.md (relative to this file). Edit that file to
# change the rules; this hook just pipes it into the session context.
# Bypass: set BRAIN_RULES_BYPASS=1 to silence the injection (this only mutes
# the reminder — the rules and any CLAUDE.md approval requirements still apply).
# Register in ~/.claude/settings.json under hooks.UserPromptSubmit (once: true).
import json
import os
import sys

RULES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "..", "rules", "working-rules.md")


def main():
    if os.environ.get("BRAIN_RULES_BYPASS") == "1":
        return
    try:
        sys.stdin.read()  # drain the pipe; hook input is unused
    except Exception:
        pass
    try:
        with open(RULES, "r", encoding="utf-8") as f:
            rules = f.read()
    except Exception:
        return
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "--- Working Rules ---\n" + rules,
        }
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
