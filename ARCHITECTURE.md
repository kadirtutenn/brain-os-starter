# Brain OS Architecture

## Invariant

Brain OS is deterministic shared-memory infrastructure. It must not invoke an
LLM, embedding model, model reranker, model summarizer, or AI provider—directly
or behind MCP. Many independent external agents can use the same Brain Store;
the Store format does not depend on the calling model.

## Authority and projections

```text
brain-store/ OKF Markdown (durable authority)
        |
        v
line-state parser -> typed structural chunks -> SQLite FTS5 + sparse features
        |                                      (rebuildable projection)
        v
filter -> BM25 candidates -> hybrid rerank -> redundancy-aware packing
        |                                      (deterministic computation)
        v
fingerprints + compact chunks + refs + receipt delta -> external agent
```

Runtime databases never become a competing metadata authority. Every indexed
row carries source hashes and parser/chunker/BrainVector generations. Deleting
the runtime and cache directories may affect latency but cannot destroy durable
knowledge.

## Retrieval pipeline

The parser recognizes OKF frontmatter, headings, paragraphs, lists, tables,
fenced code, wiki/Markdown links, and technical identifiers. Chunk boundaries
follow structure first and use size only as a fallback; code blocks and tables
remain intact.

FTS5/BM25 produces a bounded candidate set. BrainVector uses normalized words,
exact technical identifiers, camel/snake/kebab/path/API/version subtokens,
metadata, and path/heading signals. Sparse cosine runs only over FTS candidates.

Hybrid scoring exposes each component:

- lexical relevance;
- sparse similarity;
- OKF metadata;
- project/scope and agent fit;
- explicit graph relations;
- valid fingerprint fit;
- verified usage;
- redundancy and scope-mismatch penalties.

Context packing selects marginal value per `context_units`. These units are
provider-independent estimates backed by character, word, and byte counts—not
claims about exact provider tokens.

## Fingerprints and receipts

Deterministic fingerprints summarize metadata, headings, identifiers, links,
constraints, and source hashes. Curated fingerprints are authored durable
knowledge and take precedence; the runtime never silently overwrites them.

Context receipts record exact chunk/fingerprint hashes per caller, agent, and
handle. A receipt from one caller is never used to suppress context for another.
`brain_continue` returns content-version deltas, while `brain_expand` moves from
fingerprint to section, adjacent sections, or an explicitly requested full
concept.

## Learning boundary

The runtime may derive structured Insights from observable telemetry—retrievals,
explicit useful refs, verified outcomes, or repeated hot paths. It does not
perform semantic rewriting. An external agent or human promotes an Insight to a
Lesson or Skill through the normal approval/write pipeline. Hidden reasoning or
chain-of-thought is never stored.

## Runtime isolation

Globally shared state includes parser/index caches, chunks, sparse features,
fingerprints, source hashes, and aggregate retrieval statistics. Caller/session
state includes handles, known hashes, active sessions/tasks, and receipts.

Production maps these classes to `/srv/brain/store`, `/srv/brain/runtime`, and
`/srv/brain/cache`. The MCP container is loopback-only behind nginx and
BearerGate. Openship deploys the Compose service with no managed public endpoint;
its Redis and admin-auth configuration are outside Brain OS authority.

## Legacy cognitive material

The earlier Living Brain prose and deterministic state engine were moved out of
the Store to `cognitive-spec/legacy/` and `runtime/state/living-brain/`. They are
not prerequisites for retrieval and cannot introduce model/provider calls. New
work prioritizes verified retrieval quality and context reduction.
