# core.py — the transport-agnostic engine behind the Brain MCP server.
#
# Pure Python, standard library only. No fastmcp, no pyyaml, no third-party
# packages — import this module anywhere without installing anything.
#
# A vault is addressed by its filesystem root path (a str). A "concept_id" is
# the path of a markdown file RELATIVE to that root (e.g. "Skills/example.md").
#
# READ functions return compact results (only get_concept returns a body).
# WRITE functions all run the SAME gated pipeline:
#     acquire single-writer lock -> validate_frontmatter -> secret_gate
#         -> apply edit -> _triple_update -> _git_commit(author) -> return id
# The gates and internals are importable and individually testable.
#
# Authorization policy enforced by the write functions:
#   lessons / sessions / skills      -> any authenticated author
#   rules / PROTOCOL / Dashboard     -> proposal + approve_proposal(is_admin=True)
#   there is NO delete function.
import contextlib
import datetime
import fcntl
import hashlib
import os
import re
import subprocess
import tempfile
import sys

# Keep the stdlib-only retrieval runtime importable when this file is executed
# from mcp/server.py (whose script directory would otherwise be the only local
# import root).
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from runtime.retrieval import RetrievalIndex


# --------------------------------------------------------------------------- #
# Exceptions
# --------------------------------------------------------------------------- #
class OKFValidationError(Exception):
    """A document violates the OKF frontmatter / structure rules."""


class SecretDetected(Exception):
    """Content that looks like a credential was blocked before writing."""


class AuthzError(Exception):
    """The caller is not authorized for the requested write."""


# --------------------------------------------------------------------------- #
# Reserved / load-bearing names
# --------------------------------------------------------------------------- #
RESERVED_FILES = {"index.md", "INDEX.md", "log.md", "Dashboard.md"}
_FM_WEIGHT = 3  # frontmatter (description + tags) outranks the body when scoring
_STOP = {"the", "and", "for", "with", "this", "that", "from", "into", "your"}


# --------------------------------------------------------------------------- #
# Small filesystem helpers
# --------------------------------------------------------------------------- #
def _read(path, limit=None):
    """Read a UTF-8 file; return "" if it cannot be read."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read(limit) if limit else f.read()
    except Exception:
        return ""


def _write(path, text):
    """Write UTF-8 text, creating parent directories as needed."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _today():
    """ISO date for stamping new content. Formatting only — no logic depends on it."""
    return datetime.date.today().isoformat()


def _slug(text):
    """Turn a title into a filesystem-friendly slug."""
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return s or "untitled"


def _relid(vault, path):
    """Return a concept id: the path relative to the vault, using / separators."""
    return os.path.relpath(path, vault).replace(os.sep, "/")


def _safe_join(root, *parts):
    """Join inside ``root`` and reject traversal/symlink escapes."""
    base = os.path.realpath(os.path.abspath(root))
    target = os.path.realpath(os.path.join(base, *parts))
    if os.path.commonpath([base, target]) != base:
        raise OKFValidationError("path escapes Brain Store")
    return target


def _resolve(vault, concept_id):
    """Map a concept id (with or without .md) to an absolute path."""
    cid = concept_id.replace("\\", "/").lstrip("/")
    if not cid.endswith(".md"):
        cid += ".md"
    return _safe_join(vault, *cid.split("/"))


# --------------------------------------------------------------------------- #
# Frontmatter (tiny stdlib parser — deliberately NOT pyyaml)
# --------------------------------------------------------------------------- #
def _parse_list(value):
    """Parse a `[a, b, c]` inline list into a list of strings."""
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return [v.strip().strip('"').strip("'") for v in value.split(",") if v.strip()]


def _parse_frontmatter(text):
    """Split a document into (frontmatter_dict, body).

    Returns ({}, text) when there is no leading `---` block. `tags` is parsed
    into a list; all other values are returned as strings.
    """
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    if lines[0].strip() != "---":
        return {}, text
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text
    fm = {}
    for line in lines[1:end]:
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if key == "tags":
            fm["tags"] = _parse_list(val)
        else:
            fm[key] = val.strip().strip('"').strip("'")
    return fm, "\n".join(lines[end + 1:])


# --------------------------------------------------------------------------- #
# Gates
# --------------------------------------------------------------------------- #
def validate_frontmatter(text):
    """Raise OKFValidationError unless a `---` block with non-blank
    type / description / tags / timestamp is present."""
    fm, _ = _parse_frontmatter(text)
    if not fm:
        raise OKFValidationError("missing frontmatter block")
    for key in ("type", "description", "tags", "timestamp"):
        val = fm.get(key)
        if key == "tags":
            if not val:
                raise OKFValidationError("blank or missing 'tags'")
        elif not val or not str(val).strip():
            raise OKFValidationError("blank or missing '%s'" % key)


_SECRET_KEY = re.compile(
    r"(?i)\b(passwd|password|secret|token|api[_-]?key|apikey|access[_-]?key|"
    r"private[_-]?key)\b\s*[:=]\s*\S"
)
_SECRET_PEM = re.compile(r"(?i)BEGIN[ A-Z0-9]*PRIVATE KEY")
_SECRET_CONN = re.compile(
    r"(?i)\b[a-z][a-z0-9+.-]*://[^\s:/@]+:[^\s:/@]+@"
)
_IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
_AUTH_WORD = re.compile(
    r"(?i)\b(password|passwd|pass|pwd|secret|token|apikey|api_key|key|auth|"
    r"credential|login)\b"
)


def secret_gate(text):
    """Raise SecretDetected on content that carries a credential.

    Blocks assigned secret-key names, PEM private-key blocks, credential-bearing
    connection strings, and any single line pairing an IPv4 address with an auth
    keyword. There is no --force path.
    """
    if _SECRET_KEY.search(text):
        raise SecretDetected("assigned secret key name detected")
    if _SECRET_PEM.search(text):
        raise SecretDetected("private key block detected")
    if _SECRET_CONN.search(text):
        raise SecretDetected("credentialed connection string detected")
    for line in text.splitlines():
        if _IPV4.search(line) and _AUTH_WORD.search(line):
            raise SecretDetected("ip address paired with credential on one line")


# --------------------------------------------------------------------------- #
# READ API
# --------------------------------------------------------------------------- #
def get_dashboard(vault):
    """Return Dashboard.md verbatim."""
    return _read(os.path.join(vault, "Dashboard.md"))


def get_index(vault, path=""):
    """Return the markdown directory map under `path`.

    Prefers an on-disk index.md / INDEX.md; otherwise generates a compact
    listing of the directory's markdown files and subdirectories.
    """
    directory = _safe_join(vault, *path.split("/")) if path else os.path.realpath(vault)
    for name in ("index.md", "INDEX.md"):
        candidate = os.path.join(directory, name)
        if os.path.isfile(candidate):
            return _read(candidate)
    out = ["# Index: %s" % (path or "/")]
    if os.path.isdir(directory):
        for fn in sorted(os.listdir(directory)):
            if fn.startswith("."):
                continue
            full = os.path.join(directory, fn)
            if os.path.isdir(full):
                out.append("* %s/ - directory" % fn)
            elif fn.endswith(".md"):
                fm, _ = _parse_frontmatter(_read(full))
                out.append("* [%s](%s) - %s" % (fn, fn, fm.get("description", "")))
    return "\n".join(out)


def get_concept(vault, concept_id):
    """Return a concept as {"id","type","description","tags","body"}."""
    path = _resolve(vault, concept_id)
    if not os.path.isfile(path):
        raise OKFValidationError("no such concept: %s" % concept_id)
    fm, body = _parse_frontmatter(_read(path))
    return {
        "id": _relid(vault, path),
        "type": fm.get("type", ""),
        "description": fm.get("description", ""),
        "tags": fm.get("tags", []),
        "body": body,
    }


def _query_words(query):
    """Lowercase, stopword-filtered query tokens."""
    return [w for w in re.findall(r"[a-z0-9_.-]+", (query or "").lower())
            if len(w) > 2 and w not in _STOP]


def _iter_concepts(vault):
    """Yield (abs_path, frontmatter, body) for every non-reserved concept file."""
    for root, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fn in files:
            if not fn.endswith(".md") or fn in RESERVED_FILES:
                continue
            path = os.path.join(root, fn)
            fm, body = _parse_frontmatter(_read(path))
            if not fm:
                continue
            yield path, fm, body


def search(vault, query, type=None, limit=10):
    """Full-vault search. Frontmatter (description + tags) is weighted above the
    body. Returns [{"id","description"}] ranked by relevance (most relevant
    first), <=limit. The internal relevance score is not exposed."""
    words = _query_words(query)
    if not words:
        return []
    scored = []
    for path, fm, body in _iter_concepts(vault):
        if type and fm.get("type") != type:
            continue
        fm_hay = (fm.get("description", "") + " " + " ".join(fm.get("tags", []))
                  + " " + os.path.splitext(os.path.basename(path))[0]).lower()
        body_hay = body.lower()
        score = sum(fm_hay.count(w) * _FM_WEIGHT + body_hay.count(w) for w in words)
        if score:
            scored.append((score, {
                "id": _relid(vault, path),
                "description": fm.get("description", ""),
            }))
    scored.sort(key=lambda r: -r[0])
    return [r for _, r in scored[:limit]]


def find_skill(vault, keyword, limit=10):
    """Search restricted to Skill concepts."""
    return search(vault, keyword, type="Skill", limit=limit)


def find_concept(vault, query, type=None, limit=10):
    """Alias of search."""
    return search(vault, query, type=type, limit=limit)


_INDEX_LINE = re.compile(r"\[\[([^\]]+)\]\]\s*[—-]+\s*(.+)$")


def find_lesson(vault, keyword, limit=10):
    """Match `- [[target]] — kw1, kw2` lines in Lessons/INDEX.md by keyword.

    Returns [{"id","description"}] where id is the wikilink target and
    description is the keyword line, ranked by match count (best first),
    <=limit. The internal match score is not exposed."""
    kw = (keyword or "").lower().strip()
    if not kw:
        return []
    text = _read(os.path.join(vault, "Lessons", "INDEX.md"))
    scored = []
    for line in text.splitlines():
        m = _INDEX_LINE.search(line)
        if not m:
            continue
        target, kws = m.group(1).split("|", 1)[0].strip(), m.group(2)
        keys = [k.strip().lower() for k in re.split(r"[,/]", kws) if k.strip()]
        score = sum(1 for k in keys if kw in k or k in kw)
        if score:
            scored.append((score, {"id": target, "description": kws.strip()}))
    scored.sort(key=lambda r: -r[0])
    return [r for _, r in scored[:limit]]


def recent_changes(vault, n=10):
    """Return newest activity entries from log.md, newest first."""
    lines = _read(os.path.join(vault, "log.md")).splitlines()
    activity = [ln for ln in lines if ln.lstrip().startswith("* **")]
    return activity[:max(0, n)]


# --------------------------------------------------------------------------- #
# HIGH-LEVEL DETERMINISTIC RETRIEVAL API
# --------------------------------------------------------------------------- #
def _retrieval(vault):
    """Return the canonical rebuildable retrieval projection for ``vault``."""
    runtime_root = os.environ.get("BRAIN_RUNTIME_PATH")
    cache_root = os.environ.get("BRAIN_CACHE_PATH")
    db_path = os.path.join(runtime_root, "retrieval.sqlite") if runtime_root else None
    return RetrievalIndex(vault, db_path=db_path, cache_path=cache_root)


def brain_context(
    vault, query, project="", agent="", mode="compact", max_context_units=1200,
    context_handle="", filters=None, caller_id="local",
):
    """Primary compact retrieval primitive used by external AI callers."""
    index = _retrieval(vault)
    status = index.status()
    if status["stale_file_count"] or not status["chunk_count"]:
        index.refresh()
    return index.context(
        query=query, project=project, agent=agent, mode=mode,
        max_context_units=max_context_units, context_handle=context_handle,
        filters=filters or {}, caller_id=caller_id,
    )


def brain_continue(
    vault, context_handle, query, project="", agent="", mode="compact",
    max_context_units=1200, filters=None, caller_id="local",
):
    """Continue a context receipt and return only content-version deltas."""
    return brain_context(
        vault, query, project, agent, mode, max_context_units,
        context_handle, filters, caller_id,
    )


def brain_expand(
    vault, ref, level="section", context_handle="", max_context_units=2400,
    caller_id="local",
):
    """Progressively expand a fingerprint/chunk reference."""
    return _retrieval(vault).expand(
        ref=ref, level=level, context_handle=context_handle,
        caller_id=caller_id, max_context_units=max_context_units,
    )


def brain_status(vault):
    """Return compact Store/index readiness without private content."""
    return _retrieval(vault).status()


def brain_report_usage(vault, caller_id, useful_refs, verified=False, retrieval_run_id=""):
    """Record explicit caller feedback for deterministic learning signals."""
    return _retrieval(vault).report_usage(
        caller_id=caller_id, useful_refs=useful_refs, verified=verified,
        retrieval_run_id=retrieval_run_id,
    )


# --------------------------------------------------------------------------- #
# WRITE pipeline internals
# --------------------------------------------------------------------------- #
@contextlib.contextmanager
def _writer_lock(vault):
    """Single-writer advisory lock for the whole vault (flock on a lockfile).

    The lockfile lives in the system temp dir, keyed by a hash of the vault
    path, so it never lands inside the vault itself (no Obsidian/git noise).
    """
    os.makedirs(vault, exist_ok=True)
    key = hashlib.sha256(os.path.abspath(vault).encode("utf-8")).hexdigest()[:16]
    lock_path = os.path.join(tempfile.gettempdir(), "brain-mcp-" + key + ".lock")
    handle = open(lock_path, "w")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def _require_author(author):
    """Every content write needs an authenticated author identity."""
    if not isinstance(author, dict) or not author.get("name") or not author.get("email"):
        raise AuthzError("an authenticated author is required")


def _is_protected(concept_id):
    """rules / PROTOCOL / Dashboard are proposal-only, never direct writes."""
    cid = concept_id.replace("\\", "/").lstrip("/")
    return cid in ("Dashboard.md", "PROTOCOL.md") or cid.startswith("rules/")


def _prepend_log_line(text, line):
    """Insert a log line under today's topmost date heading.

    A fresh date block is created above the previous top block when the day
    changes, preserving newest-first ordering for both humans and the
    ``recent_changes`` API.
    """
    lines = text.splitlines()
    today_heading = "## " + _today()
    for i, ln in enumerate(lines):
        if ln.startswith("## "):
            if ln == today_heading:
                lines.insert(i + 1, line)
            else:
                lines[i:i] = [today_heading, line, ""]
            return "\n".join(lines) + "\n"
    lines.extend(["", today_heading, line])
    return "\n".join(lines) + "\n"


def _replace_field(text, pattern, replacement):
    """Replace the first line matching `pattern` (a compiled regex) if present."""
    return pattern.sub(replacement, text, count=1)


_DASH_UPDATED = re.compile(r"(?m)^(-\s*\*\*Updated:\*\*).*$")
_DASH_STATUS = re.compile(r"(?m)^(-\s*\*\*Current status:\*\*).*$")


def _triple_update(vault, dashboard_note, index_line, log_line):
    """Append `log_line` to log.md; optionally add `index_line` to the root
    index.md and refresh the Dashboard active-state note."""
    log_path = os.path.join(vault, "log.md")
    _write(log_path, _prepend_log_line(_read(log_path), log_line))

    if index_line:
        idx_path = os.path.join(vault, "index.md")
        text = _read(idx_path)
        _write(idx_path, text.rstrip("\n") + "\n" + index_line + "\n")

    if dashboard_note is not None:
        dash_path = os.path.join(vault, "Dashboard.md")
        text = _read(dash_path)
        if text:
            text = _replace_field(text, _DASH_UPDATED, r"\1 %s" % _today())
            text = _replace_field(text, _DASH_STATUS, r"\1 %s" % dashboard_note)
            _write(dash_path, text)


def _git_commit(vault, message, author):
    """Best-effort `git add -A && git commit` attributed to the caller.

    A commit failure (e.g. the vault is not a git repo, or nothing changed)
    never loses the write that already landed on disk.
    """
    name = (author or {}).get("name") or "brain"
    email = (author or {}).get("email") or "brain@example.com"
    env = dict(os.environ, GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=email,
               GIT_COMMITTER_NAME=name, GIT_COMMITTER_EMAIL=email)
    try:
        subprocess.run(["git", "-C", vault, "add", "-A"],
                       env=env, check=False, capture_output=True)
        subprocess.run(["git", "-C", vault, "commit", "-m", message],
                       env=env, check=False, capture_output=True)
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# WRITE API
# --------------------------------------------------------------------------- #
def _insert_after_heading(text, heading, line):
    """Insert `line` right after `heading`; append a new section if absent."""
    lines = text.splitlines()
    out, done = [], False
    for ln in lines:
        out.append(ln)
        if not done and ln.strip() == heading:
            out.append(line)
            done = True
    if not done:
        out += ["", heading, line]
    return "\n".join(out) + "\n"


def _lesson_kind(content):
    """Pick problems.md vs patterns.md from an optional `kind:` hint."""
    m = re.search(r"(?im)^\s*kind\s*:\s*(problems?|patterns?)", content)
    if m and m.group(1).lower().startswith("pattern"):
        return "patterns"
    return "problems"


def new_lesson(vault, area, slug, content, keywords, author):
    """Append a `## slug` section to Lessons/{area}/{problems|patterns}.md and add
    a keyword line to Lessons/INDEX.md. Never creates a new lesson file — raises
    OKFValidationError if the area file is missing."""
    _require_author(author)
    with _writer_lock(vault):
        base = _lesson_kind(content)
        rel = "Lessons/%s/%s.md" % (area, base)
        if not re.match(r"^[A-Za-z0-9_-]+$", area or ""):
            raise OKFValidationError("invalid lesson area")
        path = _safe_join(vault, "Lessons", area, base + ".md")
        if not os.path.isfile(path):
            raise OKFValidationError("lesson file does not exist: %s" % rel)

        section_body = re.sub(
            r"(?im)^\s*kind\s*:\s*(problems?|patterns?)\s*$\n?", "", content).strip()
        secret_gate(slug + "\n" + section_body)

        existing = _read(path)
        validate_frontmatter(existing)
        section = "\n## %s\n%s\n" % (slug, section_body)
        _write(path, existing.rstrip("\n") + "\n" + section)

        idx_path = os.path.join(vault, "Lessons", "INDEX.md")
        idx = _read(idx_path)
        idx_line = "- [[%s/%s]] — %s" % (area, base, ", ".join(keywords))
        _write(idx_path, _insert_after_heading(idx, "## " + area, idx_line))

        _triple_update(vault, None, None,
                       "* **Update**: Lesson %s#%s recorded." % (rel, slug))
        _git_commit(vault, "brain: lesson %s#%s" % (rel, slug), author)
        return rel


def new_skill(vault, name, content, author):
    """Create Skills/{slug}.md with valid OKF frontmatter (generated if the
    supplied content has none)."""
    _require_author(author)
    with _writer_lock(vault):
        slug = _slug(name)
        rel = "Skills/%s.md" % slug
        path = os.path.join(vault, "Skills", slug + ".md")
        if os.path.isfile(path):
            raise OKFValidationError("skill already exists: %s" % rel)

        fm, _ = _parse_frontmatter(content)
        if not fm.get("type"):
            content = ('---\n'
                       'type: Skill\n'
                       'description: "%s"\n'
                       'tags: [skill]\n'
                       'timestamp: %s\n'
                       '---\n\n'
                       '# %s\n\n%s' % (name.replace('"', "'"), _today(),
                                       name, content.lstrip()))
        validate_frontmatter(content)
        secret_gate(content)
        _write(path, content if content.endswith("\n") else content + "\n")

        skills_idx = os.path.join(vault, "Skills", "index.md")
        if os.path.isfile(skills_idx):
            line = "* [%s](%s.md) - skill" % (name, slug)
            _write(skills_idx, _read(skills_idx).rstrip("\n") + "\n" + line + "\n")

        _triple_update(vault, None, None, "* **Creation**: Skill %s added." % rel)
        _git_commit(vault, "brain: new skill %s" % rel, author)
        return rel


def update_concept(vault, concept_id, patch, author):
    """Append `patch` to an existing concept and bump its timestamp. Rejects
    protected (rules / PROTOCOL / Dashboard) targets — those need a proposal."""
    _require_author(author)
    if _is_protected(concept_id):
        raise AuthzError("protected target: use new_rule + approve_proposal")
    with _writer_lock(vault):
        path = _resolve(vault, concept_id)
        if not os.path.isfile(path):
            raise OKFValidationError("no such concept: %s" % concept_id)
        secret_gate(patch)
        doc = _read(path).rstrip("\n") + "\n\n" + patch.strip() + "\n"
        doc = re.sub(r"(?m)^(timestamp:\s*).*$", r"\g<1>%s" % _today(), doc, count=1)
        validate_frontmatter(doc)
        _write(path, doc)
        rel = _relid(vault, path)
        _triple_update(vault, None, None, "* **Update**: %s updated." % rel)
        _git_commit(vault, "brain: update %s" % rel, author)
        return rel


def log_session(vault, handoff, author):
    """Write a session handoff to Sessions/{date[-topic]}.md and do the triple
    update (Sessions/index.md line + Dashboard active state + log line)."""
    _require_author(author)
    with _writer_lock(vault):
        validate_frontmatter(handoff)
        secret_gate(handoff)

        fm, _ = _parse_frontmatter(handoff)
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", fm.get("timestamp", "")) \
            or re.search(r"\d{4}-\d{2}-\d{2}", handoff)
        date = date_match.group(0) if date_match else _today()
        title = re.search(r"(?m)^#\s+(.+)$", handoff)
        topic = ""
        if title:
            raw = re.sub(r"^\s*\d{4}-\d{2}-\d{2}\s*[—:-]*\s*", "", title.group(1))
            topic = _slug(raw)
        stem = "%s-%s" % (date, topic) if topic and topic != date else date

        name = stem
        i = 2
        while os.path.isfile(os.path.join(vault, "Sessions", name + ".md")):
            name = "%s-%d" % (stem, i)
            i += 1
        rel = "Sessions/%s.md" % name
        _write(os.path.join(vault, "Sessions", name + ".md"),
               handoff if handoff.endswith("\n") else handoff + "\n")

        sess_idx = os.path.join(vault, "Sessions", "index.md")
        if os.path.isfile(sess_idx):
            line = "* [%s](%s.md) - %s" % (name, name, fm.get("description", ""))
            _write(sess_idx, _read(sess_idx).rstrip("\n") + "\n" + line + "\n")

        _triple_update(vault, "Session %s logged." % name, None,
                       "* **Update**: Session %s logged." % rel)
        _git_commit(vault, "brain: session %s" % rel, author)
        return rel


def new_rule(vault, text, rationale, author):
    """Enqueue a rule proposal under mcp_proposals/ (does NOT write rules/).
    Returns the proposal id; an admin must approve_proposal to apply it."""
    _require_author(author)
    with _writer_lock(vault):
        secret_gate(text + "\n" + rationale)
        pid = "proposal-" + hashlib.sha1(
            (text + "|" + rationale).encode("utf-8")).hexdigest()[:8]
        doc = ('---\n'
               'type: Reference\n'
               'description: "Queued rule proposal (%s)"\n'
               'tags: [proposal, rule]\n'
               'timestamp: %s\n'
               'status: pending\n'
               'author: %s\n'
               '---\n\n'
               '## Rule\n%s\n\n## Rationale\n%s\n'
               % (pid, _today(), author["name"], text.strip(), rationale.strip()))
        validate_frontmatter(doc)
        _write(os.path.join(vault, "mcp_proposals", pid + ".md"), doc)
        _triple_update(vault, None, None,
                       "* **Update**: Rule proposal %s enqueued (pending approval)." % pid)
        _git_commit(vault, "brain: enqueue rule proposal %s" % pid, author)
        return pid


def propose_concept_update(vault, concept_id, replacement, rationale, author):
    """Queue a full replacement for a protected Dashboard/PROTOCOL concept.

    The live target is never touched until an authenticated admin approves the
    proposal. Rule changes continue to use ``new_rule`` so their append-only
    semantics remain distinct from full-document replacement.
    """
    _require_author(author)
    cid = concept_id.replace("\\", "/").lstrip("/")
    if cid not in ("Dashboard.md", "PROTOCOL.md"):
        raise AuthzError("concept replacement proposals are limited to Dashboard.md and PROTOCOL.md")
    with _writer_lock(vault):
        target_path = _resolve(vault, cid)
        if not os.path.isfile(target_path):
            raise OKFValidationError("no such protected concept: %s" % cid)
        secret_gate(replacement + "\n" + rationale)
        if cid == "PROTOCOL.md":
            validate_frontmatter(replacement)
        pid = "proposal-" + hashlib.sha1(
            (cid + "|" + replacement + "|" + rationale).encode("utf-8")
        ).hexdigest()[:8]
        doc = ('---\n'
               'type: Reference\n'
               'description: "Queued protected concept proposal (%s)"\n'
               'tags: [proposal, protected-concept]\n'
               'timestamp: %s\n'
               'status: pending\n'
               'proposal_kind: concept_replace\n'
               'target: %s\n'
               'author: %s\n'
               '---\n\n'
               '## Rationale\n%s\n\n## Replacement\n%s\n'
               % (pid, _today(), cid, author["name"], rationale.strip(),
                  replacement.rstrip()))
        validate_frontmatter(doc)
        _write(os.path.join(vault, "mcp_proposals", pid + ".md"), doc)
        _triple_update(
            vault, None, None,
            "* **Update**: Protected concept proposal %s enqueued for %s (pending approval)."
            % (pid, cid),
        )
        _git_commit(vault, "brain: enqueue protected proposal %s" % pid, author)
        return pid


def _section(body, name):
    """Return the text under a `## name` heading in `body`, or ""."""
    m = re.search(r"(?ms)^##\s+%s\s*\n(.*?)(?=^##\s|\Z)" % re.escape(name), body)
    return m.group(1).strip() if m else ""


def approve_proposal(vault, proposal_id, is_admin, admin_author=None):
    """Apply a queued rule or protected-concept proposal. Admin only."""
    if not is_admin:
        raise AuthzError("admin privilege required to approve a rule proposal")
    with _writer_lock(vault):
        pid = proposal_id[:-3] if proposal_id.endswith(".md") else proposal_id
        if not re.match(r"^proposal-[a-f0-9]{8}$", pid):
            raise OKFValidationError("invalid proposal id")
        ppath = os.path.join(vault, "mcp_proposals", pid + ".md")
        if not os.path.isfile(ppath):
            raise OKFValidationError("no such proposal: %s" % pid)
        pdoc = _read(ppath)
        fm, body = _parse_frontmatter(pdoc)

        proposal_kind = fm.get("proposal_kind") or "rule"
        if proposal_kind == "concept_replace":
            target = (fm.get("target") or "").replace("\\", "/").lstrip("/")
            if target not in ("Dashboard.md", "PROTOCOL.md"):
                raise AuthzError("invalid protected proposal target")
            marker = "## Replacement\n"
            if marker not in body:
                raise OKFValidationError("protected proposal replacement is missing")
            replacement = body.split(marker, 1)[1].rstrip() + "\n"
            secret_gate(replacement)
            if target == "PROTOCOL.md":
                validate_frontmatter(replacement)
            _write(_resolve(vault, target), replacement)
            applied_target = target
            log_line = "* **Update**: Protected concept proposal %s approved and applied to %s." % (pid, target)
        elif proposal_kind == "rule":
            rules_file = os.path.join(vault, "rules", "working-rules.md")
            if not os.path.isfile(rules_file):
                raise OKFValidationError("rules/working-rules.md not found")
            addition = "\n## %s\n%s\n\n_Rationale:_ %s\n" % (
                pid, _section(body, "Rule"), _section(body, "Rationale"))
            _write(rules_file, _read(rules_file).rstrip("\n") + "\n" + addition)
            applied_target = "rules/working-rules.md"
            log_line = "* **Update**: Rule proposal %s approved and applied." % pid
        else:
            raise OKFValidationError("unknown proposal kind: %s" % proposal_kind)

        _write(ppath, re.sub(r"(?m)^status:\s*pending\s*$", "status: approved", pdoc))

        author = admin_author or {
            "name": fm.get("author") or "admin",
            "email": (fm.get("author") or "admin") + "@example.com",
        }
        _triple_update(vault, None, None, log_line)
        _git_commit(vault, "brain: approve proposal %s" % pid, author)
        return applied_target
