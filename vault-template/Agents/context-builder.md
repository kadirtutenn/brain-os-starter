---
type: Agent
description: "Records new system/table/business-rule discoveries into the Brain"
resource: ~/.claude/agents/context-builder.md
tags: [brain, meta]
timestamp: 2026-01-01
---
# Agent: context-builder

**Kind:** Brain Management · **Operational definition:** `~/.claude/agents/context-builder.md`

---

## What it does

Records learned system, database, and domain knowledge into the Brain:
- Writes a new discovered table/schema into Knowledge.
- Documents an understood system architecture or workflow.
- Adds an important business rule/constraint under Knowledge/System.

## When to call it

- A new table is discovered.
- A system architecture is understood.
- An important business rule is learned.

## Tools

`Read`, `Write`, `Edit`, `Bash`

## Links

→ [[../Knowledge/index|Knowledge Index]]
