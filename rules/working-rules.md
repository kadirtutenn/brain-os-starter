---
type: Reference
description: "Team-wide agent working rules — injected into every session by the rules.py hook (bypass: BRAIN_RULES_BYPASS=1)"
tags: [rules, meta]
---

# Working Rules v1.0

Scope: every AI agent, session, and sub-agent working in this environment.
Edit this file to fit your team; the structure below is a starting point.

## Safety & Approval
1. Deletion, irreversible actions, deploys, `git push`/`commit`, config and
   dependency changes require the owner's EXPLICIT approval. Vague answers
   ("maybe", "probably") are not approval. If a repo has a `CLAUDE.md`, it
   overrides these rules on conflict.
2. Secrets are never written to code, logs, repos, or chat. If an embedded
   secret is found, report it immediately WITHOUT quoting the value and
   recommend rotation.
3. Anything that can affect production is tested in order: mockup → local →
   isolated-live. Local success does not guarantee production.
4. Before renaming a file or changing its format, find and read the automation
   that consumes it (hook, cron, script, CI).

## Working Discipline
5. "Done" = evidence. Every completion report has three parts: VERIFIED (with
   evidence) / UNVERIFIED (with reason) / NOT DONE. "It should work" without
   evidence is banned.
6. Write a Definition of Done before starting (2–5 checkable items); at the end
   verify against the DoD, not against the plan.
7. Measure a baseline before optimizing (benchmark-first); measure again after,
   report the gain as a number.
8. No monolithic changes — small, single-purpose, independently reversible steps.
9. If the same fix fails twice, the third attempt changes the diagnosis, not the patch.

## Token Economy
10. CLI over MCP. Read filtered (grep/head), don't open the same file twice in a
    session, run independent reads in parallel.
11. Information lookup order: Brain Dashboard (from the hook) → root index →
    frontmatter (`head -8`) → body. Full directory scans are a last resort.

## Memory & Learning
12. Durable knowledge is written to the Brain (OKF v0.1; write rules live in the
    vault root `PROTOCOL.md`). End of session: handoff + triple update
    (Sessions/index + Dashboard + log).
13. Distillation pipeline: Session → Lesson → (useful in 2+ tasks) promote to
    heuristic/Skill. Invalidated records are deleted; pruning is maintenance, not loss.
14. Sub-agents are read-only to the Brain. Only the main session writes to it;
    parallel agents never write the same file.

## Communication
15. Prose-first, minimal formatting, at most one question per reply.

## Bypass
These rules are injected once per session by `hooks/rules.py`. In an
experimental/emergency case, `BRAIN_RULES_BYPASS=1` disables the injection.
Bypass only mutes the REMINDER — the rules themselves and any `CLAUDE.md`
approval requirements remain in force in all cases.
