Continue development of `kadirtutenn/brain-os-starter`.

The architecture has now been narrowed to its primary purpose.

Brain OS is NOT an AI model runtime.

Brain OS must never require an internal LLM, embedding model, reranking model, summarization model, or external AI API.

The Brain must be able to run using ordinary deterministic software, preferably Python standard library + SQLite plus the MCP transport dependencies already required by the project.

The primary product objective is:

> Provide multiple external AI agents with a shared memory, documentation, lessons, skills, project knowledge and agent knowledge system while minimizing the amount of unnecessary context that each caller AI must consume.

Optimize the caller model's context cost.

Do not optimize primarily for smaller models.

---

# 1. Rename `vault-template`

Remove the conceptual name:

```
vault-template/

```

Adopt:

```
brain-store/

```

as the canonical durable shared memory structure.

The Brain Store is not the cognitive runtime.

It is the durable source of truth.

Obsidian may still open a Brain Store as a vault, but Obsidian terminology must not define the system architecture.

Introduce:

```
BRAIN_STORE_PATH

```

as the canonical path variable.

Support `BRAIN_VAULT_PATH` temporarily as a deprecated compatibility alias.

---

# 2. New Top-Level Architecture

Target approximately:

```
brain-os-starter/

├── brain-store/
│   ├── Projects/
│   ├── Agents/
│   ├── Knowledge/
│   ├── Lessons/
│   ├── Skills/
│   ├── Insights/
│   ├── Sessions/
│   ├── Tasks.md
│   ├── Dashboard.md
│   ├── PROTOCOL.md
│   ├── index.md
│   └── log.md
│
├── runtime/
│   ├── parser/
│   ├── chunking/
│   ├── retrieval/
│   ├── ranking/
│   ├── cache/
│   ├── learning/
│   ├── tasks/
│   └── state/
│
├── cognitive-spec/
│   ├── retrieval.md
│   ├── memory.md
│   ├── learning.md
│   ├── context.md
│   └── task-state.md
│
├── mcp/
├── hooks/
├── agents/
└── skills/

```

Executable cognition must not be hidden inside the Brain Store.

---

# 3. Hard Architectural Invariant

Brain OS Core:

```
MUST NOT invoke an LLM
MUST NOT invoke an embedding model
MUST NOT require an AI provider
MUST NOT hide AI calls inside MCP tools

```

External AI agents use the Brain.

The Brain itself provides deterministic memory infrastructure.

---

# 4. Preserve OKF as Durable Metadata

Do not replace OKF.

The Markdown files and OKF frontmatter remain the source of truth.

Runtime databases are rebuildable projections and caches.

Never create a competing durable metadata authority.

---

# 5. Build the Retrieval Core Before Expanding Other Subsystems

Current implementation relies heavily on lexical scanning of Markdown files.

Replace it with a local deterministic retrieval subsystem.

Canonical runtime database:

```
~/.brain-runtime/retrieval.sqlite

```

It must be disposable and rebuildable from `brain-store/`.

---

# 6. Structural OKF Parser

Implement a stdlib Python parser specifically optimized for Brain Store Markdown.

Recognize:

```
frontmatter
heading hierarchy
paragraphs
lists
tables
fenced code
wikilinks
markdown links
identifiers

```

Use a line-state parser.

Do not require a heavyweight Markdown AST library unless testing later proves necessary.

---

# 7. Technical Token Normalization

Generate searchable terms from natural language and technical identifiers.

Preserve the original token AND derived tokens.

Examples:

```
getUserById
→
getUserById
get
user
by
id
get_user_by_id

```

```
searchKeyword_id
→
searchKeyword_id
searchKeyword
search
keyword
id
search_keyword_id

```

Handle:

```
camelCase
PascalCase
snake_case
kebab-case
file paths
API routes
database identifiers
version strings
common technical punctuation

```

Do not stem aggressively.

Technical exactness is more important than linguistic normalization.

---

# 8. Structure-First Chunking

Do not use fixed-size RAG chunking as the primary method.

Use:

```
structure first
size second

```

Primary chunk boundaries:

```
concept
heading
subheading
decision
observation
outcome
lesson
procedure
code block
table
fingerprint

```

Token/size limits are fallback splitting constraints, not the semantic definition of a chunk.

---

# 9. Chunk Schema

Use stable chunk references.

Store approximately:

```
chunk_id:
concept_id:
parent_chunk_id:
heading_path:

kind:
ordinal:

content:
content_hash:
context_units:

metadata:
  type:
  tags:
  project:
  scope:
  status:
  confidence:

previous_chunk:
next_chunk:

links:

```

Prefer a stable ref similar to:

```
Knowledge/System/api.md#question-api@<content-hash>

```

---

# 10. Chunk Size Policy

Initial calibration only:

```
soft target: 180–300 context tokens
soft maximum: ~450
small chunks may remain below target

```

Never split a coherent small section just to hit a numeric target.

Do not split code blocks or tables arbitrarily.

Large structural sections may be subdivided using child headings or paragraph boundaries.

---

# 11. Session-Specific Chunking

Sessions must not be indexed like generic documents.

Generate typed session chunks:

```
summary
goal
observation
hypothesis
decision
action
outcome
insight
handoff

```

Do not preserve raw conversation transcripts as the normal durable session representation.

The session format should already be compressed before indexing.

---

# 12. Session Knowledge Graph

Preserve relations such as:

```
goal
→ caused
→ decision

decision
→ predicted
→ outcome

outcome
→ generated
→ insight

insight
→ promoted_to
→ lesson

lesson
→ promoted_to
→ skill

```

Store relations separately from chunk content.

---

# 13. SQLite Retrieval Schema

Create tables approximately equivalent to:

```
concepts
chunks
chunk_metadata
chunk_links
chunk_usage
sparse_features
fingerprints
context_receipts
retrieval_runs

```

Use an FTS5 virtual table for text retrieval.

The exact schema must remain migration-friendly.

---

# 14. FTS5 Candidate Retrieval

Use SQLite FTS5 as the first candidate generator.

Index fields separately:

```
title
heading
tags
description
identifiers
body

```

Use field-specific weighting.

Use BM25 / FTS relevance rather than the current raw term-count implementation.

Candidate generation should normally return a relatively small set such as top 30–100 before more expensive ranking stages.

---

# 15. Brain Sparse Representation

Do not depend on neural embeddings.

Create a deterministic sparse representation called:

```
BrainVector

```

or another appropriate internal name.

Features may include:

```
normalized words
technical identifiers
subtokens
heading terms
tag terms
description terms
project
scope
type
important bigrams
link targets
path components

```

Weights:

```
feature_weight
× normalized_tf
× idf
× document_quality

```

Store sparse features rather than large dense float arrays.

---

# 16. Sparse Similarity

Generate the same representation for queries.

Calculate sparse cosine similarity only against candidates returned by the lexical/filter stage.

Do not scan every vector for every query.

---

# 17. Hybrid Retrieval

Initial scoring model:

```
HybridScore =
    lexical_score
  + sparse_vector_score
  + metadata_score
  + project_scope_score
  + graph_score
  + fingerprint_score
  + verified_usage_score
  - redundancy_penalty
  - scope_mismatch_penalty

```

Keep every component independently observable.

Do not hide scoring inside one opaque number.

Initial component weights are calibration parameters, not permanent rules.

---

# 18. Metadata Ranking

Exploit information unique to Brain OS:

```
OKF type
tags
description
project
scope
status
confidence
authority
heading hierarchy
explicit links
task relationships
session chronology

```

Metadata is not merely filter data.

It is a ranking signal.

---

# 19. Graph Ranking

Explicit Brain relationships may boost candidates.

Examples:

```
project → decision
task → lesson
skill → lesson
session → project
fingerprint → hot_ref
agent → skill

```

Graph relevance must not override explicit authority or project mismatch.

---

# 20. Fingerprint-First Retrieval

Large reusable concepts should have compact fingerprints.

Support at least:

```
project fingerprint
design fingerprint
agent fingerprint
skill fingerprint
knowledge-cluster fingerprint

```

Normal retrieval should prefer a valid fingerprint before expanding the underlying large concept.

---

# 21. Deterministic and Curated Fingerprints

Distinguish:

```
deterministic fingerprint
curated fingerprint

```

A deterministic fingerprint may contain:

```
metadata
important headings
top identifiers
important links
active constraints
hash/version

```

and may be generated without AI.

A curated fingerprint may be written by an external agent after a deep inspection.

Brain OS stores, versions, validates and retrieves curated fingerprints but does not generate their semantic content internally.

---

# 22. Fingerprint Versioning

Fingerprints require:

```
source hashes
fingerprint hash
created/updated timestamp
provenance

```

When underlying content changes, mark affected fingerprints stale.

Do not silently continue serving outdated fingerprints as authoritative.

---

# 23. Context Packing

Retrieval is incomplete until results are packed under a caller budget.

For candidate `i`, estimate:

```
MarginalContextValue(i)
=
HybridScore(i)
-
Redundancy(i, already_selected)

```

Then:

```
Density(i)
=
MarginalContextValue(i)
/ ContextCost(i)

```

Select high-density chunks until the response budget is reached.

Avoid parent/child duplication.

---

# 24. Context Cost Is Model-Independent

Brain OS must not require a provider tokenizer.

Store deterministic:

```
character_count
word_count
byte_count
context_units

```

Use a conservative token estimate only as an estimate.

Allow MCP callers to specify their preferred response budget.

Do not claim exact provider-token counts unless the caller supplies them.

---

# 25. MCP Context API

Make the primary MCP read primitive:

```
brain_context

```

Conceptual input:

```
query:
project:
agent:
mode:
max_context_units:
context_handle:
filters:

```

Conceptual output:

```
context_handle:

fingerprints:
context_chunks:

refs:
omitted_refs:

coverage:
retrieval_metrics:
cache_metrics:

```

The external AI should not normally need to orchestrate repeated low-level `search → get_concept → search → get_concept` cycles.

---

# 26. Progressive Expansion

Provide:

```
brain_expand(ref)

```

The caller may expand:

```
fingerprint
→ section
→ adjacent section
→ full concept

```

Full concepts are never the default response when a smaller representation is sufficient.

---

# 27. Context Receipts

Track which exact content versions a caller already received.

Context handles store:

```
chunk refs
content hashes
fingerprint hashes
Brain Store version

```

Subsequent retrieval should preferentially return deltas.

Do not resend unchanged large context unnecessarily.

---

# 28. Cache Layers

Implement separately:

```
Parse Cache
Retrieval Cache
Context Receipt Cache
Fingerprint Cache

```

Parse cache avoids repeated parsing.

Retrieval cache avoids repeated ranking work.

Context receipt cache avoids repeatedly sending identical information to caller models.

Fingerprint cache makes large durable concepts cheap to reuse.

Do not confuse filesystem caching with caller-token optimization.

---

# 29. Shared Agent Memory

Create an `Agents/` durable namespace.

Agent concepts may describe:

```
capabilities
constraints
tool conventions
verified workflows
known limitations
successful patterns
relevant skills
project-specific conventions

```

Do not store hidden model reasoning or chain-of-thought.

Store observable knowledge and verified operational insights.

---

# 30. Agent-Aware Retrieval

`brain_context` may receive:

```
agent=<agent-id>

```

Context ranking may combine:

```
global knowledge
project knowledge
agent documentation
shared lessons
shared skills

```

Agent-specific context must not unnecessarily duplicate global/project context.

---

# 31. Knowledge Scope

Support scope metadata such as:

```
global
project
agent
project+agent

```

Global reusable knowledge should naturally surface across agents.

Project-specific knowledge should receive strong project filtering.

---

# 32. No Internal Semantic Learning Model

Brain learning must be telemetry-driven and deterministic.

Brain may detect patterns such as:

```
a chunk repeatedly participates in verified successful tasks

a lesson is reused across multiple projects

a fingerprint significantly reduces deep reads

a retrieval path repeatedly succeeds

a candidate is repeatedly retrieved but never used

two concepts are repeatedly co-activated

```

These observations may generate structured Insight candidates.

---

# 33. Internal Insights

Insights must be evidence-backed structured observations, not hidden reasoning.

Example:

```
insight_type: retrieval_hot_path

task_signature: api-debug

refs:
  - request-contract
  - api-error-pattern

sample_count: 17
verified_successes: 15

confidence: 0.88

suggested_action:
  compile_hot_path

evidence_refs: []

```

---

# 34. Semantic Promotion Remains External

Brain may create:

```
candidate Insight
candidate hot path
candidate lesson promotion
candidate skill promotion

```

but semantic rewriting into a new Lesson or Skill may be performed by an external agent.

Brain validates, versions and stores the result.

This preserves the no-internal-AI invariant.

---

# 35. External Vector Compatibility

Design vector storage as optional.

Allow chunks to contain:

```
external_vector
vector_provider_id
vector_version

```

if a caller externally provides them.

Brain OS never creates them.

Search APIs may optionally accept:

```
query_vector

```

Future vector search can therefore be introduced without changing Brain Store formats.

---

# 36. Do Not Implement HNSW Yet

Do not build a custom approximate-nearest-neighbor engine during the first retrieval milestone.

First measure:

```
chunk count
FTS candidate count
rerank latency
retrieval recall
memory cost

```

Use FTS/filter candidate generation followed by sparse reranking.

Only introduce an ANN index if real measurements demonstrate the need.

---

# 37. Retrieval Evaluation Dataset

Build a small golden evaluation dataset.

Each case contains:

```
query:
project:
agent:
expected_refs:
forbidden_refs:
max_context_units:

```

Measure:

```
Recall@K
Precision@K
MRR
context returned
duplicate context
fingerprint hit rate
deep-read rate
latency

```

Do not optimize retrieval weights without regression tests.

---

# 38. Retrieval Telemetry

Record:

```
query signature
filters
candidate count
selected chunks
expanded chunks
returned context units
cache hits
fingerprint hits
caller-reported useful refs when available
verification outcome when available

```

Telemetry remains runtime data.

Do not automatically inject it into future agent context.

---

# 39. Primary Implementation Order

Implement in this order:

```
brain-store rename + migration
→ structural parser
→ typed chunker
→ retrieval SQLite schema
→ FTS5/BM25
→ technical token normalization
→ BrainVector sparse representation
→ hybrid ranker
→ context packer
→ fingerprints
→ caches/context receipts
→ MCP brain_context / brain_expand
→ session-specific chunking
→ agent-shared memory
→ retrieval telemetry
→ deterministic learning signals

```

Do not prioritize Task Engine, complex cognition or model routing before the retrieval foundation is verified.

---

# 40. Primary Optimization Target

The system succeeds when:

```
a Brain Store grows
while
the average context required by an external agent does not grow proportionally.

```

The key metric is not stored knowledge volume.

The key metric is:

```
Verified Useful Context
/
Context Returned To Caller

```

The Brain should progressively become better at returning fewer, higher-value pieces of shared memory to every compatible external agent.
---

# 41. VPS Production Runtime Architecture

The production VPS deployment must preserve the same core architectural invariant:

> Brain OS is deterministic shared memory infrastructure. It does not run an internal AI model.

The VPS is responsible for:

```text
persistent Brain Store
MCP transport
authentication
deterministic parsing
structural chunking
retrieval indexing
hybrid ranking
fingerprint lookup
context packing
cache
context receipts
task/runtime projections
telemetry
backup and recovery
```

It must not require:

```text
LLM APIs
embedding APIs
local language models
model rerankers
model summarizers
```

The calling external agent remains the only AI participant.

---

# 42. Canonical VPS Filesystem Layout

Migrate the existing production layout toward:

```text
/srv/brain/

├── store/                         # durable Brain Store; source of truth; git repository
│   ├── Projects/
│   ├── Agents/
│   ├── Knowledge/
│   ├── Lessons/
│   ├── Skills/
│   ├── Insights/
│   ├── Sessions/
│   ├── Tasks.md
│   ├── Dashboard.md
│   ├── PROTOCOL.md
│   ├── index.md
│   └── log.md
│
├── runtime/                       # rebuildable operational state
│   ├── retrieval.sqlite
│   ├── state.sqlite
│   ├── events.jsonl
│   ├── index-state.json
│   └── locks/
│
├── cache/                         # disposable performance data
│   ├── parse-cache.sqlite
│   ├── retrieval-cache.sqlite
│   └── context-cache.sqlite
│
├── app/                           # Brain OS / MCP server application code
├── tokens                         # BearerGate caller identities
├── backups/
└── deploy-brain.sh
```

The existing:

```text
/srv/brain/vault
```

must be migrated to:

```text
/srv/brain/store
```

Use `BRAIN_STORE_PATH` as the canonical environment variable.

During migration, `BRAIN_VAULT_PATH` may remain supported as a deprecated compatibility alias.

A temporary filesystem symlink may be used if necessary:

```text
/srv/brain/vault -> /srv/brain/store
```

Do not maintain two independent durable copies.

---

# 43. Persistence Classes

Production data must be explicitly divided into three persistence classes.

## Durable / critical

```text
/srv/brain/store
/srv/brain/tokens
```

Properties:

```text
must survive container replacement
must survive application deployment
must be backed up
must never depend on container writable layers
```

## Rebuildable runtime

```text
/srv/brain/runtime
```

Contains operational state that is useful to persist but must remain reconstructable.

Examples:

```text
retrieval.sqlite
state.sqlite
index generation state
context receipt metadata
events.jsonl
```

## Disposable cache

```text
/srv/brain/cache
```

Deleting this directory may reduce performance temporarily but must never destroy durable knowledge.

---

# 44. Production Network Topology

Preserve the current security topology.

Brain MCP runs under Openship as a Docker service bound only to:

```text
127.0.0.1:8085
```

The service must not bind directly to a public interface.

External MCP traffic enters through:

```text
https://${BRAIN_PUBLIC_DOMAIN}/mcp
```

Flow:

```text
External Agent
      │
      │ HTTPS
      ▼
${BRAIN_PUBLIC_DOMAIN}
      │
      ▼
nginx
      │
      ▼
127.0.0.1:8085
      │
      ▼
BearerGate
      │
      ▼
Brain MCP
      │
      ▼
Deterministic Cognitive Gateway
      │
      ▼
Brain Store / Runtime Retrieval
```

Do not weaken or bypass nginx + loopback + BearerGate boundaries during deployment.

---

# 45. BearerGate Authentication

Every MCP request, including reads, must continue to pass through BearerGate.

Authentication source:

```text
/srv/brain/tokens
```

The token file must remain dynamically reloadable.

Adding or revoking a caller should not require a Brain MCP restart.

Bearer identity should also become Brain provenance.

Where possible associate an authenticated request with:

```yaml
caller_id:
agent_id:
author:
permissions:
```

Use this identity for:

```text
writes
task creation
task completion
session ownership
fingerprint authorship
lesson authorship
context receipt ownership
audit logs
```

Do not expose raw bearer tokens to Brain Store Markdown or telemetry.

---

# 46. Shared Runtime vs Caller-Scoped Runtime

The VPS serves multiple external agents.

The following may be globally shared:

```text
OKF parser cache
chunk index
FTS5 index
BrainVector sparse features
fingerprints
graph relations
document hashes
retrieval statistics
```

The following must remain caller or session scoped:

```text
context handles
known chunk hashes
known fingerprint hashes
active session state
active task state
caller retrieval receipts
```

A chunk sent to one caller must not be considered already known by another caller.

---

# 47. Container Mounts

The Brain MCP container should receive explicit host mounts equivalent to:

```yaml
volumes:
  - /srv/brain/store:/brain/store
  - /srv/brain/runtime:/brain/runtime
  - /srv/brain/cache:/brain/cache
  - /srv/brain/tokens:/brain/tokens:ro
```

Application configuration should point to:

```text
BRAIN_STORE_PATH=/brain/store
BRAIN_RUNTIME_PATH=/brain/runtime
BRAIN_CACHE_PATH=/brain/cache
BRAIN_TOKEN_FILE=/brain/tokens
```

Do not store durable Brain data in the image or container writable layer.

---

# 48. Openship Deployment Contract

Brain OS is deployed through the existing Openship installation.

Production deployment must preserve these Openship deployment values:

```yaml
deployTarget: local
buildStrategy: local
runtimeMode: docker
publicEndpoints: []
serviceDeploymentMode: services
```

These values are intentional.

`publicEndpoints` must remain empty because external access is handled by nginx and the existing public Brain endpoint.

Do not allow Openship to derive or provision a managed public project domain for Brain MCP.

Service `ports` and `volumes` must be passed using Docker Compose-compatible definitions.

---

# 49. Docker Compose Requirement

The VPS environment must use:

```text
docker compose
```

with the Docker Compose v2 plugin.

Do not use legacy:

```text
docker-compose
```

v1.

Production automation must fail clearly if only an incompatible Compose v1 installation is detected.

---

# 50. Openship Redis Isolation

Brain OS must not depend on, stop, restart, mutate, flush, reuse, or reconfigure the dedicated:

```text
openship-redis
```

container.

Openship uses this Redis instance for its own API functions such as caching and rate limiting.

Brain retrieval/cache/state must use its own filesystem/SQLite storage unless a future architecture explicitly introduces an isolated Brain-owned service.

The availability of Brain memory must not depend on the Openship Redis data plane.

---

# 51. Openship Administrative Security Boundary

Preserve Openship's current authenticated administration configuration.

Do not restore or introduce an unauthenticated admin mode.

Public signup or administrative registration endpoints must remain restricted according to the existing nginx/local-only policy.

Brain deployment automation must not modify Openship authentication policy as a side effect.

---

# 52. Brain MCP Caller Endpoint

The production Brain endpoint remains:

```text
https://${BRAIN_PUBLIC_DOMAIN}/mcp
```

External clients such as OpenCode connect using their own bearer token.

A client should normally interact through high-level Brain tools:

```text
brain_context
brain_expand
brain_continue
brain_start_project
brain_status
brain_write
```

Low-level tools such as:

```text
search
get_concept
get_dashboard
find_lesson
find_skill
```

may remain available for debugging, compatibility, and explicit low-level access.

---

# 53. Server-Side Retrieval Principle

The external agent must not receive a large candidate set and be expected to perform retrieval itself.

Correct flow:

```text
query
→ server-side project/scope filter
→ FTS5 candidate retrieval
→ BrainVector sparse reranking
→ OKF metadata score
→ graph/fingerprint score
→ redundancy removal
→ context receipt comparison
→ context packing
→ compact MCP response
```

All of these operations are deterministic Brain-side computation.

They do not consume AI model tokens.

The caller model only pays context cost for the compact final response.

---

# 54. VPS Retrieval Database

Canonical production retrieval database:

```text
/srv/brain/runtime/retrieval.sqlite
```

Properties:

```text
not git tracked
not a durable source of truth
rebuildable from /srv/brain/store
persistent across normal container restarts
schema-versioned
```

Do not rebuild the entire database on every Brain MCP restart.

---

# 55. Incremental Indexing

Indexing must be incremental.

Store at minimum:

```text
last_indexed_git_commit
schema_version
parser_version
chunker_version
brainvector_version
ranker_version
```

Preferred change detection:

```text
last indexed commit
→ current Brain Store commit
→ git diff --name-only
→ reparse only changed files
```

Fallback:

```text
path
→ mtime
→ content hash
→ reparse only if content changed
```

Deleted or renamed concepts must remove or update their runtime chunks.

---

# 56. Algorithm Generation Tracking

A source Markdown file may remain unchanged while its indexed representation becomes stale.

Every indexed representation must record versions such as:

```yaml
schema_version:
parser_version:
chunker_version:
brainvector_version:
ranker_version:
```

If `chunker_version` changes, affected chunks must be regenerated even when their Markdown source hash is unchanged.

Support controlled migrations rather than silently mixing incompatible retrieval generations.

---

# 57. Index CLI

Provide deterministic maintenance commands equivalent to:

```text
brain index status
brain index refresh
brain index rebuild
brain index migrate
brain index verify
```

Expected behavior:

### `status`

Report:

```text
Brain Store commit
last indexed commit
schema versions
stale file count
chunk count
FTS status
fingerprint stale count
```

### `refresh`

Incrementally process changed files.

### `rebuild`

Recreate the runtime retrieval projection from Brain Store.

### `migrate`

Upgrade runtime representations to current parser/chunker/index generations.

### `verify`

Check index integrity against Brain Store source hashes.

---

# 58. Deployment Lifecycle

`/srv/brain/deploy-brain.sh` must evolve into a deterministic production deployment pipeline.

Target sequence:

```text
preflight
→ upload/sync application
→ security/config validation
→ ensure directories
→ ensure permissions
→ backup critical state
→ build image
→ Openship deployment
→ container health check
→ Brain Store migration check
→ runtime schema migration
→ incremental retrieval refresh
→ index integrity check
→ MCP readiness check
→ authenticated MCP smoke test
→ deployment success
```

Do not report deployment success before the authenticated MCP endpoint and retrieval layer are ready.

---

# 59. Deployment Preflight

Before deploying validate:

```text
docker available
docker compose v2 available
/srv/brain/store accessible
/srv/brain/tokens readable
/srv/brain/runtime writable
/srv/brain/cache writable
Brain Store git repository healthy
required nginx route already present or intentionally managed
Openship API accessible
Openship Redis untouched
required environment variables present
```

Abort safely on failed critical checks.

---

# 60. Directory Bootstrap

Deployment must idempotently ensure:

```text
/srv/brain/store
/srv/brain/runtime
/srv/brain/runtime/locks
/srv/brain/cache
/srv/brain/backups
```

Do not overwrite an existing Brain Store during directory initialization.

Permissions must allow the Brain container to access its mounted runtime/store paths without making the durable store broadly writable to unrelated services.

---

# 61. Migration From `/vault` to `/store`

Production migration must be explicit and reversible.

Recommended sequence:

```text
verify /srv/brain/vault
→ create backup
→ stop Brain MCP writes
→ move vault to /srv/brain/store
→ create temporary compatibility symlink if required
→ update environment/config
→ start new Brain MCP
→ verify store git state
→ verify MCP reads
→ verify gated write
→ remove compatibility path only after all clients are migrated
```

Never copy two live writable Brain Stores and let them diverge.

---

# 62. Deployment Backups

Before a deployment that changes Brain Store structure or runtime schema, create a timestamped backup of critical state.

At minimum protect:

```text
/srv/brain/store
/srv/brain/tokens
```

Runtime SQLite backup may be retained for rollback convenience but must never be required for durable recovery.

Cache backups are unnecessary.

---

# 63. Health Endpoints

Expose separate:

```text
/health/live
/health/ready
```

## `/health/live`

Only verifies that the Brain MCP application process is alive.

Example:

```json
{
  "status": "ok"
}
```

## `/health/ready`

Must verify operational dependencies.

Example shape:

```yaml
status: ready

store:
  accessible: true
  git_repository: true

auth:
  token_file_readable: true

retrieval:
  database_open: true
  fts_available: true
  schema_current: true

index:
  ready: true
  stale_files: 0

cache:
  writable: true
```

Do not expose secrets, tokens, filesystem-sensitive content, or private Brain content through health responses.

---

# 64. Deployment Readiness Gate

Deployment is successful only when all required conditions pass:

```text
container running
/health/live passes
/health/ready passes
Brain Store mounted
BearerGate active
retrieval database valid
index refresh completed
authenticated brain_context smoke test passes
```

A container being in a running state is not sufficient evidence of a successful deployment.

---

# 65. Authenticated MCP Smoke Test

After deployment execute a minimal authenticated test through the same nginx/public route used by real agents.

Test at least:

```text
authentication succeeds
brain_status or equivalent succeeds
brain_context returns bounded context
retrieval metrics are present
unauthenticated request is rejected
```

Avoid performing a durable write in every deployment unless running against a dedicated test concept or explicitly configured smoke-test area.

---

# 66. Rollback Strategy

Application deployment must be rollback-capable.

Rollback must distinguish:

```text
application rollback
runtime schema rollback
Brain Store content rollback
```

Application code rollback must not automatically roll back Brain Store knowledge.

If a runtime index migration fails:

```text
preserve Brain Store
discard/rebuild runtime retrieval state
restore previous application if required
```

Because retrieval state is reconstructable, runtime corruption must never require restoring old Brain knowledge.

---

# 67. Git Responsibilities

`/srv/brain/store` remains a git repository.

Git represents durable Brain knowledge history.

Application code and Brain Store data should remain conceptually separate.

Application deployments should not create unrelated commits inside Brain Store.

Brain writes may continue using authored commits through the existing gated write pipeline.

Runtime/cache changes must never appear in Brain Store git history.

---

# 68. Backup and Recovery Classes

## Critical backup

```text
/srv/brain/store
/srv/brain/tokens
```

## Valuable operational history

```text
/srv/brain/runtime/events.jsonl
```

may be backed up if it contains useful non-durable telemetry or task lineage.

## Rebuildable

```text
/srv/brain/runtime/retrieval.sqlite
/srv/brain/cache/*
```

must not be treated as irreplaceable backup data.

---

# 69. Recovery Procedure

A clean recovery onto a fresh Brain MCP instance should be possible using:

```text
Brain Store backup/git clone
+ tokens
+ current Brain OS application
```

Then:

```text
create runtime/cache directories
→ rebuild retrieval.sqlite
→ verify fingerprints
→ verify FTS
→ start MCP
→ run readiness checks
```

This procedure must not require any AI model or external embedding service.

---

# 70. Cache Persistence on VPS

Keep caches outside the container so normal deployment/restart does not erase warm state.

However every cache entry must have deterministic invalidation data.

Use:

```text
content hash
source version
parser version
chunker version
Brain Store commit where relevant
```

Never serve cached content solely because a TTL has not expired if the underlying Brain source changed.

---

# 71. Context Receipt Persistence

Context receipts may persist under:

```text
/srv/brain/runtime
```

or the dedicated context cache database.

Receipts must be:

```text
caller scoped
agent scoped where known
session/context-handle scoped
version aware
expirable
```

A context receipt is an optimization hint, not durable knowledge.

Losing receipts may increase caller context cost temporarily but must not cause knowledge loss.

---

# 72. Fingerprint Persistence

Curated fingerprints belong in:

```text
/srv/brain/store
```

because they are reusable durable agent knowledge.

Generated runtime fingerprint projections/cache belong in:

```text
/srv/brain/runtime
```

or:

```text
/srv/brain/cache
```

A deterministic runtime fingerprint must never silently replace an authored curated fingerprint.

---

# 73. Shared Multi-Agent VPS Behavior

The VPS must support agents such as:

```text
OpenCode
Claude Code
Codex
Kimi
Agent SDK clients
future MCP-compatible agents
```

without changing the Brain Store format.

Each agent may contribute:

```text
session memory
project fingerprints
lessons
skills
agent documentation
tasks
verified operational knowledge
```

All agents consume the same shared Brain Store through the same retrieval system.

This is a central Brain OS property:

> One durable shared memory substrate, many independent external agents.

---

# 74. Deployment Metrics

Record deployment/runtime metrics without injecting them into normal AI context.

At minimum:

```text
deployment duration
index refresh duration
files reparsed
chunks rebuilt
retrieval database size
cache warm/cold state
health-check latency
MCP smoke-test latency
current store commit
current app version
parser/chunker/ranker versions
```

These metrics exist for operations and optimization, not as default Brain context.

---

# 75. Retrieval Production Metrics

On the VPS track:

```text
candidate chunks
selected chunks
returned context units
avoided context units
fingerprint hit rate
context receipt hit rate
retrieval cache hit rate
full-concept expansion rate
FTS latency
rerank latency
total brain_context latency
```

This data is required to validate that deterministic VPS computation is actually reducing caller AI context.

---

# 76. Production Optimization Rule

Prefer additional deterministic VPS computation when it materially reduces unnecessary caller-model context.

Conceptually:

```text
small CPU / SQLite cost
→ large context reduction
→ desirable
```

Do not optimize server compute in isolation if doing so causes the external model to receive significantly more irrelevant context.

The primary production efficiency objective remains:

```text
Verified Useful Context
/
Context Returned To Caller
```

---

# 77. Production Completion Criteria

The VPS migration/deployment work is complete only when:

```text
Brain Store is outside the container
Brain Store uses canonical /srv/brain/store
old vault path has a controlled migration path
BearerGate still protects every MCP request
MCP remains loopback-only behind nginx
Openship deployment remains local/docker/services
Openship Redis is untouched
runtime/cache paths are persistent host mounts
retrieval index survives normal restarts
retrieval index can be rebuilt from Brain Store
incremental indexing works
schema/parser/chunker generations are tracked
health/live and health/ready exist
authenticated MCP smoke tests pass
deployment supports rollback
no internal AI/model dependency exists
```

The deployed architecture must remain recoverable from durable Brain Store data without any AI service.

---

# 78. Verified Production Evidence — 2026-08-21

Status: **COMPLETE for the production criteria in Section 77**, with the
installation-local Openship hardening patch retained as an explicit operational
caveat.

## 78.1 Live route and deployment

```text
public MCP route: https://${BRAIN_PUBLIC_DOMAIN}/mcp
public readiness: HTTP 200
unauthenticated MCP request: HTTP 401
active Openship deployment: dep_QEEmMtYzZQpzBKR_
active container image: sha256:a95f7ca3032589e4fa75abf17f59ae52faea79b65217153ed5b3b165a1af2118
container state: running / healthy
```

The production service binds only to `127.0.0.1:8085`; nginx owns the TLS
route. The container runs as `10001:10001`, with a read-only root filesystem,
`cap_drop: ALL`, `no-new-privileges`, bounded `/tmp`, and read-only token
mounting. No Brain Store directory is embedded in the active image.

## 78.2 Durable Store and retrieval projection

```text
canonical Store: /srv/brain/store
Store commit: c3ed656174af6a727bd0bfd775768747159b6a81
Store worktree: clean
files seen: 66
retrieval chunks: 1229
FTS chunks: 1229
integrity: ok
stale files: 0
orphan chunks: 0
```

The retrieval index was refreshed and verified after the final gated content
writes. It survived both a full VPS reboot and a controlled Docker restart.
Redis remained a separate persistent Openship dependency and returned `PONG`
after restart.

## 78.3 Authenticated MCP evidence

The public-route smoke test verified:

```text
unauthenticated brain_status rejected: true
authenticated brain_status received: true
authenticated brain_context received: true
returned context bounded to max_context_units: true
retrieval metrics present: true
```

Codex also successfully called the configured Brain MCP tools after bearer
rotation and application restart. The VPS persists only a SHA-256 verifier;
the raw caller credential is held in macOS Keychain and supplied to Codex
through `BRAIN_MCP_TOKEN`.

## 78.4 Gated knowledge maintenance

Protected full-document changes now use a two-step path:

```text
propose_concept_update
→ pending proposal artifact
→ approve_proposal (admin only)
→ protected target replacement + authored Git commit
```

Dashboard reconciliation was applied through proposal
`proposal-4a306355`. The production Session handoff is:

```text
Sessions/2026-08-21-brain-os-production-deployment-security-hardening-and-reboot.md
```

`recent_changes` now reads newest-first activity, and the update log creates a
new date block when the day changes.

## 78.5 VPS security and operating system

```text
kernel: 5.15.0-190-generic
reboot required: no
UFW inbound allowlist: 22/tcp, 80/tcp, 443/tcp
SSH password authentication: disabled
SSH root access: key-only
fail2ban sshd jail: active
nginx config test: successful
certbot timer: active
backup file mode: 0600
```

All 17 initially pending standard packages and the three phased
netplan/snapd packages were upgraded. Docker was restarted after the `runc`
upgrade; Brain, Bugünlük, Redis, and Openship recovered through their restart
policies and passed their relevant health checks.

## 78.6 Recovery evidence

A clean authenticated image is retained as:

```text
brain-os:rollback-clean-20260821
sha256:53a71033183e6d0c4a19c3237caf082b4e74d7e30357a5d28379b1a8cbe4996c
```

Critical Store/token-verifier backups are stored under `/srv/brain/backups`
with mode `0600`. Runtime SQLite remains rebuildable and is not required for
durable recovery.

## 78.7 Operational caveat

Openship `0.1.11` required an installation-local runtime patch so advanced
Docker hardening fields are honored. An Openship update may overwrite that
patch. After every Openship upgrade, reapply the repository patch helper and
revalidate container user, read-only rootfs, capabilities, security options,
mount modes, loopback binding, authenticated MCP smoke, and Redis continuity.
