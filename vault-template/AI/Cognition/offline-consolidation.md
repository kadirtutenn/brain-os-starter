---
type: Knowledge
description: Offline consolidation — sleep loop, lesson/skill promotion thresholds, suppression, pruning, and hot-path myelination.
tags: [living-brain, cognition, consolidation, learning]
timestamp: 2026-01-01
status: active
version: 0.1
provenance:
  - living-brain-v0.1 spec
---

# Offline Consolidation

At session end, distills experience into durable, small, high-quality knowledge.
Success condition: as the runtime log grows, the Durable Brain stays smaller and
higher-quality.

## Sleep loop

```text
select_episodes (prediction_error≥0.25 | reward≥0.60 | harm≥0.30 | user corrections | conflicts)
→ replay
→ reconcile_world_model · update_self_model · update_synaptic_weights
→ extract_action_changing_rules (max 5 lesson candidates)
→ per candidate: update_existing_slug_or_create_section
→ suppress_failed_paths · prune_low_value_edges · compress_hot_paths
→ write_session_handoff · update_dashboard · update_sessions_index · append_log_line
```

## Consolidation thresholds

**Lesson candidate:** `action_change_score ≥ 0.60 AND generalizability ≥ 0.50 AND evidence_confidence ≥ 0.60`.

**Durable lesson:** one strong failure-preventing constraint OR the same pattern in
two independent tasks OR a multi-source-verified cause-effect.

**Skill promotion:**
```yaml
promotion:
  minimum_independent_successes: 2
  minimum_confidence: 0.75
  maximum_open_contradictions: 0
  minimum_reuse_probability: 0.50
```

**Suppression:** `failure_count ≥ 2 AND success_count == 0` OR `contradiction_confidence ≥ 0.80`.

**Pruning:** `weight < 0.10 AND last_use > 90 days AND success_count == 0 AND unique_information == false`.
Critical historical records are not deleted, they are **archived**.

## Hot-path / myelination

A path becomes a hot-path: `use_count ≥ 5 AND success_rate ≥ 0.80 AND high retrieval cost`.
Result: a short summary node is created, the relevant section is compiled into a
skill, index keywords improve, and the router calls the short node directly. A
frequent chain is packaged under a single Skill.

This loop is run by `brain-manager` (single writer). Weight-update mechanics →
[[synaptic-policy]]. Distillation policy → [[consolidation-policy]]. Constitution 13-15 apply.
