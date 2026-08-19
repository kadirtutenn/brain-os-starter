# Deterministic Retrieval Contract

Brain OS retrieves context with ordinary software only. Markdown plus OKF
frontmatter in `brain-store/` is authoritative; SQLite is a disposable,
schema-versioned projection.

The retrieval path is:

1. project/scope filters;
2. FTS5/BM25 candidate generation;
3. technical-token BrainVector sparse cosine;
4. observable metadata, graph, fingerprint, usage, and mismatch components;
5. redundancy-aware context packing;
6. caller-scoped context receipt comparison.

No stage may call an LLM, embedding service, reranking model, summarizer, or AI
provider. Full concepts are an explicit expansion, not the normal response.
