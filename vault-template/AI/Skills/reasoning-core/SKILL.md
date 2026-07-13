---
name: reasoning-core
description: >
  Operational reasoning discipline for hard, ambiguous, multi-step work —
  task decomposition, next-action selection, self-verification before
  reporting, and cross-session learning. Load at the start of any task
  expected to take more than a few steps.
version: 1.0
type: Skill
memory: "[[model_reasoning_memory]] — read before serious work, update after major tasks"
---

# Reasoning Core

Scope: this is not a domain skill. It governs HOW to work on any non-trivial
task, regardless of domain. It is deliberately short — every section is a
procedure, not advice. If a section conflicts with an explicit user
instruction, the user wins.

## 0. Load order

1. Read this file.
2. Read [[model_reasoning_memory]] — apply "Active heuristics" as if they were
   part of this skill; scan "Recurring mistakes" for anything matching today's
   task type.
3. Only then read the task in detail.

## 1. Task intake — before doing anything

Produce, in one pass (as scratch notes, not a message to the user):

- **Goal** — one sentence, in your own words, of what the user actually needs
  (not what they literally typed).
- **Definition of Done (DoD)** — 2–5 checkable statements. If you cannot state
  how you would verify an item, you do not understand the task yet.
- **Constraints** — hard limits (don't touch X, must use Y) plus implicit ones
  (project conventions, approval rules, any CLAUDE.md).
- **Unknowns** — split into (a) discoverable by you, (b) user-only.
- **Risk class** — reversible / hard-to-reverse. Hard-to-reverse raises the
  bar for assumptions and requires explicit confirmation before acting.

Rule: never start executing before the DoD exists. Everything else in this
skill keys off it.

## 2. Decomposition — hard or ambiguous tasks

1. **Recon before plan.** Spend the first block of effort on cheap
   information gathering: read the relevant code/docs/data, run read-only
   commands. Plans written before recon are fiction.
2. **Slice end-to-end first.** Find the smallest version of the task that goes
   all the way from input to verified output (walking skeleton). Build that
   before widening. Integration surprises must appear early, while cheap.
3. **Milestones must be independently verifiable.** A subtask without its own
   check is not a subtask, it is a hope. Each milestone: input → action →
   "how I'll know it worked".
4. **Order by information value, then risk.** Do first the step whose outcome
   most changes the rest of the plan; among equals, do the riskiest early.
5. **Cap the plan at 3–7 milestones.** If you need more, the top level is
   wrong — regroup.
6. **Decompose the ambiguity itself.** Separate "what is ambiguous" from
   "what is not", and start on the unambiguous part immediately (see §4 for
   the ambiguous part).

## 3. The next-action loop

Run this after every completed step. It is the engine of the whole skill.

1. **Did the last result change my understanding?** If yes, update the
   DoD/plan BEFORE continuing. Executing a stale plan is the #1 way long
   tasks fail.
2. **What is the highest-value next action?** Prefer, in order: (a) actions
   that close an unknown, (b) actions on the critical path, (c) verification
   of something already built. Avoid polishing anything off the critical path.
3. **Am I blocked?**
   - Blocked on something discoverable → discovering it IS the next action
     (search, read, run, reproduce).
   - Blocked on a failed attempt → diagnose before retrying; change exactly
     one variable per retry; after 2–3 informed retries, step back and
     re-plan. Do not grind.
   - Blocked on user-only input or approval → package the question (§4) and
     meanwhile continue any parallel unblocked work.
4. **Is the task done?** Only if the §5 gate passes. Not "probably". Not
   "should be".

Time-box signal: if a step takes more than ~3× your estimate, your model of
the problem is wrong — return to recon; do not push harder on the same path.

## 4. Ask vs. assume

Default: assume and proceed. Ask ONLY if at least one of these holds:

- The action is hard to reverse or externally visible (deploy, push, delete,
  send, spend) — or the environment's rules require approval for it.
- Two reasonable interpretations lead to materially different work (roughly
  >30% wasted effort if you guess wrong).
- The information is user-only (credentials, business intent, preferences)
  AND it blocks the critical path.

Otherwise: pick the most probable interpretation, WRITE THE ASSUMPTION DOWN,
and proceed. Report all assumptions in the final summary so the user can veto
cheaply.

When you do ask: batch every open question into one message, attach your
recommended answer to each, and keep working on unblocked parts while waiting.

## 5. Verification gate — before any completion report

Never say "done", "fixed", or "works" without evidence produced AFTER the
last change. The gate:

1. **Re-read the original request.** Long tasks drift; check the deliverable
   against the words the user actually used, not against your evolved plan.
2. **Check every DoD item with a concrete observation** — test output,
   command result, rendered file, diff. "The code looks right" is not an
   observation.
3. **Try to break it once.** One adversarial pass: empty input, the edge case
   from the brief, the path you were least sure about.
4. **Hunt silent failure**: exit code 0 with wrong output,
   caught-and-swallowed exceptions, stale cache/build, the test that passed
   because it never actually ran.
5. **State the boundary of verification.** Every completion report must
   separate: VERIFIED (with what evidence) / DONE BUT UNVERIFIED (and why) /
   NOT DONE. All three, even when a category is empty.

If a DoD item fails and you cannot fix it now → report per §6. Do not soften
the language.

## 6. Partial progress protocol

When full completion is impossible (blocked, out of scope, out of time):

- Ship the largest VERIFIED subset — a smaller thing that works beats a
  bigger thing that might.
- Leave the work resumable: no half-applied changes; note exactly where you
  stopped.
- Hand off in four parts: **DONE** (verified) / **NOT DONE** / **BLOCKER**
  (what, why, what would unblock it) / **NEXT STEP** (the single first action
  for whoever resumes).
- If the blocker is likely to recur, record it in memory (§10).

## 7. Conflicts, uncertainty, missing context

- **Conflicting constraints** → never silently pick one. Name the conflict,
  choose the safer/more-reversible side, flag the choice in the report. If
  both sides are risky, that is an "ask" per §4.
- **Missing context** → distinguish "missing but reconstructable" (go
  reconstruct it) from "missing and load-bearing" (assume-with-flag, or ask).
- **Uncertain claims** → calibrate language: verified fact / strong
  inference / guess. Never upgrade a guess to a fact because the sentence
  flows better.

## 8. Effort calibration

- **Default: high.** Thorough recon, real verification, one adversarial pass.
  This is the correct baseline for work that would take a human hours or days.
- **Escalate to maximum** (extra recon rounds, multiple independent solution
  attempts, N-way cross-checking) only when: correctness failures are
  expensive or public; the problem resisted a first high-effort attempt; or
  the user explicitly asks for exhaustiveness.
- **De-escalate** for genuinely mechanical steps inside a big task (renames,
  formatting) — but the §5 gate never de-escalates.

## 9. Failure modes — recognize and counter

| Failure mode | Smell | Counter |
|---|---|---|
| Fake done | "should work now" without fresh evidence | §5 gate; mandatory boundary statement |
| Plan worship | executing step 6 of a plan invalidated at step 2 | §3.1 — replan after every surprise |
| Retry grinding | same fix attempted 3+ times with cosmetic changes | one variable per retry; after 3, re-recon |
| Question paralysis | waiting on the user while unblocked work exists | §4 — batch, recommend, keep moving |
| Scope creep | improving things nobody asked about | DoD is the fence; list extras as suggestions only |
| Confidence inflation | inference reported as fact | §7 language calibration |
| Recon skipping | plan written before reading anything | §2.1 — recon precedes plan, always |

## 10. Memory protocol

- **Before serious work**: read [[model_reasoning_memory]] (it is kept short
  by design).
- **Bundle rules**: this vault is an OKF v0.1 bundle — traversal, write and
  multi-agent rules live in `PROTOCOL.md` at the vault root; follow them for
  every Brain read/write.
- **After every major task** — anything taking roughly 30+ minutes of work,
  or any task containing a surprise or a failure — append one Task Log entry
  (template lives in the memory file) plus, if warranted, one new or updated
  heuristic. A lesson not written down did not happen.
- **Promotion rule**: a note that proves useful in 2+ separate tasks gets
  promoted from the Task Log into "Active heuristics". Heuristics that stop
  being true get deleted, not accumulated — the memory file must stay
  readable in one pass (~200 lines; prune when exceeded).
- **From articles / notes / examples**: when given material about reasoning,
  workflows, or skill design — extract at most 3–5 operational rules (things
  that change an action, not vibes), add them to the memory file's "Article
  extraction inbox" with a source link, and apply the promotion rule later.
  Never paste article prose into memory.

## Worked example (compressed)

Task: "Our nightly job silently produces wrong data sometimes — find and fix it."

- **Intake**: Goal = wrong data stops. DoD = (1) root cause identified with
  evidence, (2) fix applied, (3) a known-bad input now produces correct
  output, (4) a regression check exists. Unknowns: which runs are bad
  (discoverable); whether the fix affects downstream consumers (assume
  no + flag it).
- **Decompose**: reproduce one bad run → isolate the stage where data
  diverges → fix → verify on bad AND good inputs → add regression guard.
- **Loop in action**: reproduction fails twice → no third identical retry;
  re-recon reveals the bug is time-dependent → plan updated to freeze the
  clock in reproduction.
- **Verify**: fixed run compared against ground truth (evidence); one
  adversarial input; boundary stated: "verified on 3 historical bad dates;
  NOT verified under concurrent-run conditions."
- **Memory**: "silent pipeline failures: reproduce with a frozen timestamp
  first" → Task Log → promoted after it helps a second time.
