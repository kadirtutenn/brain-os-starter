---
type: Template
description: "Session handoff template — copy, fill in; leave '—' in empty sections"
tags: [meta]
timestamp: 2026-01-01
---

# Template — copy the block below into a new file

File name: `YYYY-MM-DD-topic.md` (second topic same day: `YYYY-MM-DD-2-topic.md`).
On exit, do the triple update: a [Sessions/index](index.md) line + Dashboard
"Active State" + a [log](../log.md) line. Detail → [PROTOCOL §2, §11](../PROTOCOL.md).

A session is not a raw transcript: don't copy full prompts/tool output, don't
write internal monologue. Compression limits: summary ≤5 lines, critical
observations ≤7, hypotheses ≤5, decision episodes ≤5, ledger ≤15, lesson
candidates ≤5, risks ≤7, handoff ≤6. Open a new session when the main goal/project
changes or context reaches ~80%.

```markdown
---
type: Session
description: <one-sentence purpose and outcome of the session>
tags: [session, <project>, <domain>]
timestamp: YYYY-MM-DD
status: active
project: <project-id>
session_id: <uuid-or-stable-slug>
---

# <YYYY-MM-DD — Session title>

## 1. Session summary
- **Purpose:**
- **Starting state:**
- **Ending state:**
- **The one definite next action:**
- **Overall result:** success | partial | blocked | failed

## 2. Active goals
| Goal | Level | Source | Start gap | End gap | Status |
|---|---|---|---:|---:|---|
|  | L2/L3/L4 | user/project/inferred |  |  | active/achieved/blocked |

## 3. Critical observations
Only directly observed events.
### observation-<slug>
- **Epistemic status:** observed
- **Source:** tool/user/file/test
- **Observation:**
- **Confidence:**
- **Artifact/ref:**

## 4. Inferences and hypotheses
### hypothesis-<slug>
- **Epistemic status:** inferred | predicted
- **Claim:**
- **Confidence start → end:**
- **Supporting / refuting evidence:**
- **Status:** proposed | testing | confirmed | refuted

## 5. Decision episodes
### decision-<slug>
- **Problem:**
- **Active goal:**
- **Options:** 1. — 2. — 3.
- **Chosen + why:**
- **Expected outcome / success probability / confidence:**
- **Risks + verification plan:**
- **Observed outcome:**
- **Prediction error / decision quality:**
- **Memory refs:**

## 6. Action & outcome ledger
| # | Action | Expected | Observed | Status | Evidence |
|---:|---|---|---|---|---|
| 1 |  |  |  | pass/fail/partial |  |

## 7. Runtime memory summary
- **Active assemblies:**
- **Suppressed strategies:**
- **Open conflicts:**
- **Context pressure:**
- **Critical memory refs used:**

## 8. Learning and consolidation
### Lesson candidates
- `<target file>#<slug>` — one action-changing sentence. Evidence: — · Independent verification: — · Action: update | create-section | no-write
### Synaptic / world / self change candidates
| Source | Relation | Target | Old w | Δw | New w | Why |
|---|---|---|---:|---:|---:|---|
|  |  |  |  |  |  |  |

## 9. Open risks and unknowns
| Risk / unknown | Impact | Likelihood | Mitigation | Owner |
|---|---:|---:|---|---|
|  |  |  |  |  |

## 10. Handoff
- **File/branch to continue:**
- **First concept to open + first command/action:**
- **Success condition:**
- **What NOT to do:**
- **Required artifact refs:**

## 11. Brain changes
- Updated concept / index / Lessons/INDEX line / Dashboard / log line:
```
