---
type: Reference
description: "Brain working protocol — read/write/learning loop and multi-agent rules (OKF v0.1)"
tags: [meta, protocol]
---

# Brain Protocol

This bundle follows [OKF v0.1](Knowledge/okf-spec-v0.1.md): every concept `.md`
begins with `type` + `description` + `tags` + `timestamp` frontmatter; each
directory's `index.md` provides progressive disclosure; the root `log.md` is the
change log. This file is the read/write contract for every session, agent, and
sub-agent that touches the Brain.

## 1. Read protocol (token-optimized)

1. The Dashboard is already injected into context by the hook — do NOT read it again.
2. Structure question → the [root index](index.md) or the relevant directory's
   `index.md`. Don't scan directories to list files.
3. To understand what a concept is, read its frontmatter first (`head -8`); open
   the body only if you truly need it.
4. Topic search: try a frontmatter scan before a full grep —
   `grep -r "^description:\|^tags:" --include="*.md" . | grep -i "keyword"` — then
   read only the matching section of the file.
5. Never open the same file twice in one session; the content is already in context.
6. To see what changed, look at the last ~10 lines of [log](log.md); don't open files one by one.

## 2. Write protocol

1. Every content change is a triple update: the file's `timestamp` + the relevant
   `index.md` line + one line in [log](log.md) (`* **Update**: ...`).
2. A new concept file cannot be created without frontmatter. Minimum: `type`,
   `description`, `tags`, `timestamp`.
3. **A new lesson does NOT open a new file.** Add a `## slug` section to the
   relevant `Lessons/<area>/problems.md` or `patterns.md`, then update that file's
   keyword line in [Lessons/INDEX](Lessons/INDEX.md). The INDEX line format is
   parsed by the hook — don't break it: `- [[target]] — kw1, kw2, kw3`.
4. End of session: a handoff file per [session-template](Sessions/session-template.md)
   + Dashboard "Active State" + a `Sessions/index.md` line + a log line.
5. Do not DELETE files in the Brain, and do not RENAME `Dashboard.md` /
   `Lessons/INDEX.md` (hook dependency) — these require owner approval.

## 3. Learning loop (self-improvement)

Knowledge is distilled in one direction; each level feeds the next:

```
Session (raw event) → Lesson (## slug: one rule) → useful in 2+ tasks
  → promote: a heuristic in reasoning-core memory OR a section in the relevant Skill/Knowledge file
  → an invalidated lesson/heuristic is SUPPRESSED/ARCHIVED, not deleted (pruning = maintenance, not loss)
```

- After each major task, a retrospective: a Task Log entry in
  [model_reasoning_memory](AI/Memory/model_reasoning_memory.md) (template lives in the file).
- Hypotheses live in [Hypotheses/hypotheses](Hypotheses/hypotheses.md): Proposed →
  Testing → Confirmed/Refuted. A confirmed hypothesis becomes a Lesson.
- Importing an article/note: at most 3–5 action-changing rules, with a source
  link, into the memory file's "Article extraction inbox" — never paste the
  article text (reasoning-core §10).

## 4. Multi-agent rules

1. **Single-writer principle:** the main session writes to the Brain. Sub-agents
   (search, analysts, parallel workers) are READ-ONLY to the Brain — they return
   findings, the main session does the writing. Exception: when `brain-manager` /
   `context-builder` is spawned explicitly to write, the main flow doesn't touch
   the same file meanwhile.
2. When spawning an agent, don't copy Brain content into the prompt; give only
   the relevant concept **paths** ("first read the frontmatter of: ...") + a
   "Brain is read-only" reminder.
3. Parallel agents never write the same file; work is split by file.
4. Session start order: Dashboard (from the hook) → last lines of [log](log.md) if
   needed → concepts matching the task. For a model using reasoning-core:
   [SKILL](AI/Skills/reasoning-core/SKILL.md) + [memory](AI/Memory/model_reasoning_memory.md) come first.

## 5. OKF conformance notes and local deviations

- **Links:** bodies use Obsidian wikilinks (`[[...]]`) for the graph view. If an
  OKF export is needed, a script converts wikilinks → markdown links. New index
  files prefer markdown relative links (with multiple `index.md` files, `[[index]]`
  is ambiguous — always give the path).
- **Dashboard.md** carries no frontmatter: it is injected into every prompt, so
  every line is a token cost.
- **Lessons/INDEX.md** is that directory's index file and the hook's keyword source.
- **type vocabulary** (use one of these before inventing a new type): `Session,
  Lesson, Skill, Catalog, Knowledge, Performance Report, Action Plan, Runbook,
  Research Note, Agent, Project, Hub, Reference, Template, Task Board, Hypothesis
  Board, Memory, Dashboard`.

## 6. Maintenance

- `index.md` files and `Lessons/INDEX.md` get a monthly stale check (in the index
  but not on disk / on disk but not in the index).
- `model_reasoning_memory.md` is pruned past ~200 lines; `Tasks.md` past inactive lines.
- Consolidation candidates are noted in the log.

## 7. Epistemic status protocol

Every important record is marked `observed`, `inferred`, `predicted`, `imagined`,
`desired`, `counterfactual`, or `unknown`. Predictions and simulations cannot be
stored as observations. Detail → [AI/Cognition/perception-policy](AI/Cognition/perception-policy.md).

## 8. Runtime vs Durable Brain

Transient activations, working memory, candidate options, simulation branches, and
eligibility traces are NOT written to Brain markdown. They live in the
`~/.brain-runtime/` store ([AI/Runtime/runtime-contract](AI/Runtime/runtime-contract.md)).
Only knowledge that passes the consolidation gate is written to the Durable Brain.

## 9. Token economy

A big memory is not a big context. Retrieval goes index → frontmatter → heading →
full concept, in that order. The same content is not re-read in one session. Agent
communication is path/ref-based. Future simulation branches with a limit and stops
once the decision ordering is fixed. Threshold mechanics → [AI/Cognition/metacognition](AI/Cognition/metacognition.md).

## 10. Goal and decision protocol

Explicit user goals outrank inferred goals. Important decisions are kept as
decision episodes with options, prediction, risk, verification plan, and observed
outcome ([AI/Runtime/decision-episode-schema](AI/Runtime/decision-episode-schema.md)).
A decision whose outcome was not observed is not complete. Policy →
[AI/Cognition/goal-system](AI/Cognition/goal-system.md), [decision-policy](AI/Cognition/decision-policy.md).

## 11. Session and consolidation protocol

A session is not a raw transcript. It keeps critical observations, inferences,
decisions, action-outcomes, prediction errors, lesson candidates, and handoff. At
each session end, `brain-manager` runs consolidation →
[AI/Cognition/offline-consolidation](AI/Cognition/offline-consolidation.md),
[AI/Memory/consolidation-policy](AI/Memory/consolidation-policy.md).

## 12. Contradiction and reconsolidation

When new evidence conflicts with old knowledge, the new "truth" is not simply
added. Scope, date, environment, and evidence are compared; the old knowledge is
narrowed, made `suppressed`/`deprecated`, or made conditional →
[AI/Cognition/world-model](AI/Cognition/world-model.md).

## 13. Runtime safety

The system cannot change its own constitutional rules. Model-generated goals
cannot outrank user goals. Irreversible actions require human approval per the
risk mode (any `CLAUDE.md` approval rules fall under `policy_violation` and always win).
