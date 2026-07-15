# brain_context.py — UserPromptSubmit hook that injects the Brain into a session.
#
# It runs in one of three modes (BRAIN_CONTEXT_MODE env var, or first CLI arg):
#   static     — inject the Dashboard verbatim only (the always-loaded "active
#                state" panel). Wire this hook with once:true so the stable
#                prefix is paid once per session and stays cache-eligible.
#   retrieval  — inject only the prompt-relevant lessons/concepts. Wire this
#                hook WITHOUT once:true so it re-matches on every prompt.
#   (unset)    — full behavior: Dashboard + lessons + concepts in one shot
#                (backward-compatible with the single-hook setup).
#
# On each prompt (retrieval / full):
#   1. Scans Lessons/INDEX.md keyword lines and stages the lessons whose
#      keywords best match the prompt (up to MAX_LESSONS): for each match only
#      the frontmatter description + the matching '## slug' section(s) are
#      injected, not the whole file.
#   2. Scans every concept's frontmatter (type/description/tags) and injects the
#      single best-matching concept beyond lessons (Skill/Knowledge/Runbook...).
#
# The assembled context is capped at MAX_CONTEXT_CHARS: the Dashboard is added
# first, then lessons/concepts in score order until the budget is exhausted;
# the last part is truncated to fit.
#
# Configure the vault location with the BRAIN_VAULT_PATH environment variable.
# Register in ~/.claude/settings.json under hooks.UserPromptSubmit — see
# settings.example.json for the two-hook (static once:true + retrieval) layout.
# scripts/install.sh does this for you.
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
MAX_CONTEXT_CHARS = 6000
SKIP_TYPES = {"Hub", "Dashboard", "Template", "Reference", "Task Board", "Session"}
STOP = {"the", "and", "for", "with", "this", "that", "from", "into", "your"}


def read(path, limit=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read(limit) if limit else f.read()
    except Exception:
        return ""


def get_mode():
    if len(sys.argv) > 1 and sys.argv[1] in ("static", "retrieval"):
        return sys.argv[1]
    return os.environ.get("BRAIN_CONTEXT_MODE", "").strip().lower()


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
    low = prompt.lower()
    words = set(re.findall(r"[a-z0-9_]+", low))
    scored = []
    for line in idx.splitlines():
        m = re.search(r"\[\[([^\]]+)\]\]\s*[—-]+\s*(.+)$", line)
        if not m:
            continue
        target, kws = m.group(1), m.group(2).lower()
        keys = [k.strip() for k in re.split(r"[,/]", kws) if k.strip()]
        score = sum(1 for k in keys
                    if re.search(r"\b" + re.escape(k) + r"\b", low)
                    or any(p == k for p in words))
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


def stage_lesson(path, pwords):
    fm = frontmatter(path) or {}
    desc = fm.get("description", "").strip()
    body = read(path)
    if body.startswith("---\n"):
        e = body.find("\n---", 4)
        if e != -1:
            body = body[e + 4:]
    sections = re.split(r"(?m)^(?=##\s)", body)
    matched = []
    for sec in sections:
        stripped = sec.strip()
        if not stripped.startswith("##"):
            continue
        sec_words = set(re.findall(r"[a-z0-9_.-]+", stripped.lower()))
        if pwords & sec_words:
            matched.append(stripped)
    chunk = []
    if desc:
        chunk.append(desc)
    if matched:
        chunk.append("\n\n".join(matched))
    text = "\n\n".join(chunk).strip()
    return text[:MAX_CHARS]


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


def assemble(parts, cap):
    out, total = [], 0
    for text in parts:
        if not text:
            continue
        if total >= cap:
            break
        remaining = cap - total
        if len(text) > remaining:
            text = text[:remaining]
        out.append(text)
        total += len(text)
    return "\n\n".join(out)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    prompt = (data.get("prompt") or "") if isinstance(data, dict) else ""
    mode = get_mode()

    parts = []
    if mode in ("", "static"):
        parts.append("--- Brain Dashboard ---\n" + read(DASHBOARD))
    if mode in ("", "retrieval"):
        pwords = prompt_words(prompt)
        lessons = matched_lessons(prompt)
        for target, path in lessons:
            chunk = stage_lesson(path, pwords)
            if chunk:
                parts.append("--- Lesson: %s ---\n%s" % (target, chunk))
        for path in matched_concepts(prompt, {p for _, p in lessons}):
            rel = os.path.relpath(path, BRAIN)
            body = read(path)[:CONCEPT_CHARS]
            if body:
                parts.append("--- Concept: %s ---\n%s" % (rel, body))

    ctx = assemble(parts, MAX_CONTEXT_CHARS)
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
