---
type: Reference
description: "Open Knowledge Format (OKF) v0.1 spec summary — the format rules this Brain bundle follows"
tags: [meta, okf]
---

# OKF v0.1 — Spec Summary

The Brain is an OKF v0.1 bundle. If the full OKF text is unavailable, this
summary is binding.

## Core rules

- **Bundle** = a directory tree of markdown files; the unit of distribution. A
  git repo is recommended.
- **Concept** = one `.md` file. Concept ID = the path without `.md`
  (`tables/users.md` → `tables/users`).
- Every concept: YAML frontmatter (delimited by `---`) + markdown body.
- Frontmatter — REQUIRED: `type` (short, descriptive; no central registry).
  Recommended, in order: `title`, `description` (one sentence), `resource` (the
  canonical URI of the thing; omit for abstract concepts), `tags` (list),
  `timestamp` (ISO 8601). Producers may add keys; consumers must not reject
  unknown keys or types.
- Body: structural markdown preferred. Conventional headings: `# Schema`,
  `# Examples`, `# Citations`.

## Reserved files

- `index.md` — directory listing (progressive disclosure). NO frontmatter (one
  exception: at the bundle root, an `okf_version: "0.1"` declaration). Format:
  `# Section` headings with `* [Title](url) - description` lines under them.
- `log.md` — chronological change log, newest on top, `## YYYY-MM-DD` headings,
  `* **Label**: prose` lines.

## Links

- Bundle-relative (`/tables/x.md`, recommended) or relative (`./x.md`). A link
  is an undirected, untyped relationship claim; the surrounding text names the
  relationship type.
- A consumer does not treat a broken link as an error (it may point at
  not-yet-written knowledge).

## Conformance (v0.1)

1. Every non-reserved `.md` has parseable frontmatter.
2. Every frontmatter has a non-empty `type`.
3. Reserved files, if present, follow the structure above.
A consumer must NOT reject a bundle for: a missing optional field, an unknown
type/key, a broken link, or a missing index.md.

## Local deviations of this bundle

→ see `PROTOCOL.md` §5: wikilink usage in bodies, the frontmatter-less
Dashboard, and `Lessons/INDEX.md` acting as that directory's index.
