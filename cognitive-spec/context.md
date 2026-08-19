# Context Contract

Context cost is provider-independent. Every chunk records character, word, byte,
and conservative `context_units` counts. These units are estimates, never claims
about an exact provider tokenizer.

`brain_context` accepts a budget and returns fingerprints, chunks, stable refs,
omissions, coverage, and independently observable retrieval metrics. Selection
maximizes marginal score per context unit while penalizing parent/child and
near-duplicate content.

Context handles are caller-scoped, agent-aware, version-aware, and expirable.
They suppress unchanged content only for the caller who received it.
