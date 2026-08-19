---
type: Reference
description: "Brain Store read, write, learning, session, and multi-agent protocol"
tags: [meta, protocol, deterministic-retrieval]
timestamp: 2026-08-19
---

# Brain Store Protocol

## 1. Durable authority

OKF Markdown is the durable source of truth. Runtime SQLite indexes, sparse
features, caches, receipts, telemetry, and task state are rebuildable projections
and must not become a competing metadata authority.

Brain OS itself does not invoke an LLM, embedding model, model reranker,
summarizer, or AI provider. External agents perform semantic work.

## 2. Read protocol

1. Start with `brain_context(query, project, agent, max_context_units)`.
2. Use returned fingerprints and compact chunks before requesting more content.
3. Expand only a returned stable ref with `brain_expand`: section, adjacent, then
   full concept only when justified.
4. Continue the same task with its context handle so unchanged hashes are not
   resent.
5. Use low-level indexes/search only for debugging or explicit manual traversal.

## 3. Write protocol

1. Every new concept has `type`, `description`, `tags`, and `timestamp`.
2. A new lesson is a `## slug` section in the appropriate
   `Lessons/<area>/problems.md` or `patterns.md`, plus its `Lessons/INDEX.md` line.
3. Durable writes pass the single-writer lock, OKF validation, secret gate,
   protected-target authorization, provenance, triple update, and authored git
   commit pipeline.
4. `Dashboard.md`, `PROTOCOL.md`, and rules are proposal/admin protected.
5. No remote delete tool exists. Suppress/deprecate invalidated knowledge and let
   a human perform maintenance.

## 4. Sessions and relations

A durable Session is compressed before indexing. Use typed sections: summary,
goal, observation, hypothesis, decision, action, outcome, insight, and handoff.
Do not store raw transcripts or hidden chain-of-thought.

Record observable relationships such as:

```text
goal -> caused -> decision
decision -> predicted -> outcome
outcome -> generated -> insight
insight -> promoted_to -> lesson
lesson -> promoted_to -> skill
```

## 5. Learning boundary

Runtime telemetry may generate evidence-backed Insight candidates with counts,
confidence, suggested action, and evidence refs. Semantic promotion or rewriting
into a Lesson/Skill is performed by an external agent or human through the gated
write path.

Important claims use an epistemic status such as `observed`, `inferred`,
`predicted`, `desired`, `counterfactual`, or `unknown`. A prediction is never
stored as an observation.

## 6. Multi-agent behavior

All compatible external agents share the same Store format. Parser/index/cache
state may be global; context handles, known hashes, active sessions/tasks, and
receipts are caller/session scoped. Content sent to one caller is never assumed
known by another.

Write ownership remains serialized. Parallel agents must not write the same
concept concurrently, and raw bearer tokens must never enter Markdown,
fingerprints, logs, or telemetry.

## 7. Completion evidence

Static artifacts or passing unit tests do not prove a live deployment. Production
completion requires a mounted durable Store, valid/rebuildable index, zero stale
files, both health probes, BearerGate, loopback/nginx topology, and authenticated
`brain_context` smoke evidence through the public route.
