"""Migration-friendly SQLite retrieval projection schema."""

SCHEMA_VERSION = 1

SCHEMA_SQL = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS index_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS concepts (
    concept_id TEXT PRIMARY KEY,
    source_path TEXT NOT NULL UNIQUE,
    source_hash TEXT NOT NULL,
    mtime_ns INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    parser_version TEXT NOT NULL,
    chunker_version TEXT NOT NULL,
    brainvector_version TEXT NOT NULL,
    indexed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    concept_id TEXT NOT NULL REFERENCES concepts(concept_id) ON DELETE CASCADE,
    parent_chunk_id TEXT,
    heading_path TEXT NOT NULL,
    kind TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    context_units INTEGER NOT NULL,
    character_count INTEGER NOT NULL,
    word_count INTEGER NOT NULL,
    byte_count INTEGER NOT NULL,
    previous_chunk TEXT,
    next_chunk TEXT
);
CREATE INDEX IF NOT EXISTS idx_chunks_concept ON chunks(concept_id, ordinal);
CREATE TABLE IF NOT EXISTS chunk_metadata (
    chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY(chunk_id, key, value)
);
CREATE INDEX IF NOT EXISTS idx_metadata_lookup ON chunk_metadata(key, value);
CREATE TABLE IF NOT EXISTS chunk_links (
    chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    link_kind TEXT NOT NULL,
    target TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT '',
    relation TEXT NOT NULL DEFAULT 'links_to'
);
CREATE INDEX IF NOT EXISTS idx_links_target ON chunk_links(target);
CREATE TABLE IF NOT EXISTS chunk_usage (
    chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    caller_id TEXT NOT NULL,
    retrieved_count INTEGER NOT NULL DEFAULT 0,
    useful_count INTEGER NOT NULL DEFAULT 0,
    verified_success_count INTEGER NOT NULL DEFAULT 0,
    last_used_at TEXT,
    PRIMARY KEY(chunk_id, caller_id)
);
CREATE TABLE IF NOT EXISTS sparse_features (
    chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    feature TEXT NOT NULL,
    weight REAL NOT NULL,
    PRIMARY KEY(chunk_id, feature)
);
CREATE INDEX IF NOT EXISTS idx_sparse_feature ON sparse_features(feature);
CREATE TABLE IF NOT EXISTS fingerprints (
    fingerprint_id TEXT PRIMARY KEY,
    concept_id TEXT NOT NULL REFERENCES concepts(concept_id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    source_hashes TEXT NOT NULL,
    fingerprint_hash TEXT NOT NULL,
    provenance TEXT NOT NULL,
    stale INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS external_vectors (
    chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    vector_provider_id TEXT NOT NULL,
    vector_version TEXT NOT NULL,
    vector_json TEXT NOT NULL,
    supplied_at TEXT NOT NULL,
    PRIMARY KEY(chunk_id, vector_provider_id, vector_version)
);
CREATE TABLE IF NOT EXISTS context_receipts (
    context_handle TEXT PRIMARY KEY,
    caller_id TEXT NOT NULL,
    agent_id TEXT NOT NULL DEFAULT '',
    store_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS context_receipt_items (
    context_handle TEXT NOT NULL REFERENCES context_receipts(context_handle) ON DELETE CASCADE,
    ref TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    item_kind TEXT NOT NULL,
    PRIMARY KEY(context_handle, ref, content_hash)
);
CREATE TABLE IF NOT EXISTS retrieval_runs (
    run_id TEXT PRIMARY KEY,
    query_signature TEXT NOT NULL,
    caller_id TEXT NOT NULL,
    agent_id TEXT NOT NULL DEFAULT '',
    filters_json TEXT NOT NULL,
    candidate_count INTEGER NOT NULL,
    selected_refs_json TEXT NOT NULL,
    returned_context_units INTEGER NOT NULL,
    avoided_context_units INTEGER NOT NULL,
    cache_hit INTEGER NOT NULL,
    fingerprint_hits INTEGER NOT NULL,
    fts_ms REAL NOT NULL,
    rerank_ms REAL NOT NULL,
    total_ms REAL NOT NULL,
    created_at TEXT NOT NULL,
    verification_outcome TEXT,
    useful_refs_json TEXT
);
CREATE TABLE IF NOT EXISTS insights (
    insight_id TEXT PRIMARY KEY,
    insight_type TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    sample_count INTEGER NOT NULL,
    confidence REAL NOT NULL,
    suggested_action TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5(
    chunk_id UNINDEXED,
    title,
    heading,
    tags,
    description,
    identifiers,
    body,
    tokenize='unicode61 remove_diacritics 2'
);
"""
