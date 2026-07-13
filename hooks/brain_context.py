# brain_context.py — UserPromptSubmit hook that injects the Brain into every session.
#
# What it does, on each prompt:
#   1. Injects the Dashboard verbatim (the always-loaded "active state" panel).
#   2. Scans Lessons/INDEX.md keyword lines and injects the lessons whose
#      keywords best match the prompt (up to MAX_LESSONS).
#   3. Scans every concept's frontmatter (type/description/tags) and injects the
#      single best-matching concept beyond lessons (Skill/Knowledge/Runbook...).
#
# Configure the vault location with the BRAIN_VAULT_PATH environment variable.
# Register in ~/.claude/settings.json under hooks.UserPromptSubmit (once: true
# recommended). scripts/install.sh does this for you.
import json
import os
import re
import sys

BRAIN = os.environ.get("BRAIN_VAULT_PATH", os.path.expanduser("~/Brain"))
DASHBOARD = os.path.join(BRAIN, "Dashboard.md")
INDEX = os.path.join(BRAIN, "Lessons", "INDEX.md")
MAX_LESSONS = 2
MAX_CONCEPTS = 1
MAX_CHARS = 4000
CONCEPT_CHARS = 2500
SKIP_TYPES = {"Hub", "Dashboard", "Template", "Reference", "Task Board", "Session"}
STOP = {"the", "and", "for", "with", "this", "that", "from", "into", "your"}


def read(path, limit=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read(limit) if limit else f.read()
    except Exception:
        return ""


def prompt_words(prompt):
    return set(w for w in re.findall(r"[a-z0-9_.-]+", prompt.lower())
               if len(w) > 3 and w not in STOP)


def resolve(target):
    t = target.split("|", 1)[0].strip()
    if not t.endswith(".md"):
        t += ".md"
    p = os.path.join(BRAIN, "Lessons", t)
    return p if os.path.exists(p) else None


def matched_lessons(prompt):
    idx = read(INDEX)
    words = set(re.findall(r"[a-z0-9_]+", prompt.lower()))
    scored = []
    for line in idx.splitlines():
        m = re.search(r"\[\[([^\]]+)\]\]\s*[—-]+\s*(.+)$", line)
        if not m:
            continue
        target, kws = m.group(1), m.group(2).lower()
        keys = [k.strip() for k in re.split(r"[,/]", kws) if k.strip()]
        score = sum(1 for k in keys if k in prompt.lower() or any(p == k for p in words))
        if score:
            path = resolve(target)
            if path:
                scored.append((score, target, path))
    scored.sort(key=lambda x: -x[0])
    out, seen = [], set()
    for _, target, path in scored:
        if path in seen:
            continue
        seen.add(path)
        out.append((target, path))
        if len(out) >= MAX_LESSONS:
            break
    return out


def frontmatter(path):
    head = read(path, 800)
    if not head.startswith("---\n"):
        return None
    end = head.find("\n---", 4)
    if end == -1:
        return None
    fm = {}
    for line in head[4:end].splitlines():
        m = re.match(r"^([A-Za-z_]+):\s*(.+)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip().strip('"')
    return fm


def matched_concepts(prompt, exclude_paths):
    words = prompt_words(prompt)
    if not words:
        return []
    scored = []
    for root, dirs, files in os.walk(BRAIN):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fn in files:
            if not fn.endswith(".md") or fn in ("index.md", "INDEX.md", "log.md"):
                continue
            path = os.path.join(root, fn)
            if path in exclude_paths or path == DASHBOARD:
                continue
            fm = frontmatter(path)
            if not fm or fm.get("type") in SKIP_TYPES:
                continue
            hay = (fm.get("description", "") + " " + fm.get("tags", "") + " "
                   + os.path.splitext(fn)[0]).lower()
            hay_words = set(re.findall(r"[a-z0-9_.-]+", hay))
            score = len(words & hay_words)
            if score >= 2:
                scored.append((score, path))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:MAX_CONCEPTS]]


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    prompt = (data.get("prompt") or "") if isinstance(data, dict) else ""

    parts = ["--- Brain Dashboard ---\n" + read(DASHBOARD)]
    lessons = matched_lessons(prompt)
    for target, path in lessons:
        body = read(path)[:MAX_CHARS]
        if body:
            parts.append("--- Lesson: %s ---\n%s" % (target, body))
    for path in matched_concepts(prompt, {p for _, p in lessons}):
        rel = os.path.relpath(path, BRAIN)
        body = read(path)[:CONCEPT_CHARS]
        if body:
            parts.append("--- Concept: %s ---\n%s" % (rel, body))

    ctx = "\n\n".join(parts)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": ctx,
        }
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
