"""SQLite/FTS5 deterministic retrieval projection for a Brain Store."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import re
import sqlite3
import subprocess
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from runtime.cache import SQLiteCache
from runtime.chunking import Chunk, chunk_document
from runtime.chunking.chunker import CHUNKER_VERSION
from runtime.config import BrainPaths, resolve_paths
from runtime.parser import parse_path
from runtime.parser.okf_parser import PARSER_VERSION
from runtime.ranking import RankedCandidate, hybrid_score, sparse_cosine
from runtime.ranking.hybrid import RANKER_VERSION
from runtime.retrieval.schema import SCHEMA_SQL, SCHEMA_VERSION
from runtime.retrieval.tokenize import TOKENIZER_VERSION, normalized_words, searchable_terms

BRAINVECTOR_VERSION = "1.0.0"
RECEIPT_TTL_DAYS = 14
DEFAULT_CANDIDATES = 60


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _meta_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _title(document: Any) -> str:
    return document.headings[0].text if document.headings else Path(document.source_path).stem


def _git_commit(store: Path) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(store), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True, timeout=3,
        ).stdout.strip()
    except Exception:
        return "nogit:" + _hash(str(store))[:16]


def _fts_query(query: str) -> str:
    terms = [term for term in normalized_words(query) if len(term) > 1]
    safe = []
    for term in dict.fromkeys(terms):
        cleaned = re.sub(r'[^\w./:@-]', '', term, flags=re.UNICODE)
        if cleaned:
            safe.append('"%s"' % cleaned.replace('"', '""'))
    return " OR ".join(safe[:32])


class RetrievalIndex:
    """Build, verify, and query a rebuildable retrieval projection."""

    def __init__(
        self,
        store_path: str | os.PathLike[str] | None = None,
        db_path: str | os.PathLike[str] | None = None,
        cache_path: str | os.PathLike[str] | None = None,
    ):
        paths = resolve_paths(store=store_path, cache=cache_path)
        if db_path:
            paths = BrainPaths(paths.store, Path(db_path).expanduser().resolve().parent, paths.cache)
            self.db_path = Path(db_path).expanduser().resolve()
        else:
            self.db_path = paths.retrieval_db
        self.paths = paths
        self.store = paths.store
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.paths.cache.mkdir(parents=True, exist_ok=True)
        self.parse_cache = SQLiteCache(self.paths.cache / "parse-cache.sqlite", "parse")
        self.retrieval_cache = SQLiteCache(self.paths.cache / "retrieval-cache.sqlite", "retrieval")
        self.context_cache = SQLiteCache(self.paths.cache / "context-cache.sqlite", "context")
        self.fingerprint_cache = SQLiteCache(self.paths.cache / "fingerprint-cache.sqlite", "fingerprint")
        self._migrate()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def _migrate(self) -> None:
        with self._connect() as db:
            db.executescript(SCHEMA_SQL)
            state = {
                "schema_version": str(SCHEMA_VERSION),
                "parser_version": PARSER_VERSION,
                "chunker_version": CHUNKER_VERSION,
                "brainvector_version": BRAINVECTOR_VERSION,
                "ranker_version": RANKER_VERSION,
                "tokenizer_version": TOKENIZER_VERSION,
            }
            db.executemany(
                "INSERT OR REPLACE INTO index_state(key,value) VALUES (?,?)",
                state.items(),
            )

    def _markdown_files(self) -> list[Path]:
        if not self.store.is_dir():
            raise FileNotFoundError(f"Brain Store not found: {self.store}")
        return sorted(
            path for path in self.store.rglob("*.md")
            if ".git" not in path.parts and not any(part.startswith(".") for part in path.relative_to(self.store).parts)
        )

    def _file_state(self, path: Path) -> tuple[str, int]:
        raw = path.read_bytes()
        return hashlib.sha256(raw).hexdigest(), path.stat().st_mtime_ns

    def _delete_concept(self, db: sqlite3.Connection, concept_id: str) -> None:
        ids = [row[0] for row in db.execute(
            "SELECT chunk_id FROM chunks WHERE concept_id=?", (concept_id,)
        )]
        for chunk_id in ids:
            db.execute("DELETE FROM chunk_fts WHERE chunk_id=?", (chunk_id,))
        db.execute("DELETE FROM concepts WHERE concept_id=?", (concept_id,))

    def _index_document(self, db: sqlite3.Connection, path: Path, source_hash: str, mtime_ns: int) -> int:
        document = parse_path(path, self.store)
        concept_id = document.source_path
        self._delete_concept(db, concept_id)
        title = _title(document)
        description = str(document.frontmatter.get("description", ""))
        db.execute(
            """INSERT INTO concepts
               (concept_id,source_path,source_hash,mtime_ns,title,description,metadata_json,
                parser_version,chunker_version,brainvector_version,indexed_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (concept_id, concept_id, source_hash, mtime_ns, title, description,
             _json(document.frontmatter), PARSER_VERSION, CHUNKER_VERSION,
             BRAINVECTOR_VERSION, _now()),
        )
        chunks = chunk_document(document)
        tags = " ".join(_meta_values(document.frontmatter.get("tags")))
        for chunk in chunks:
            self._insert_chunk(db, chunk, title, description, tags)
        self._upsert_fingerprint(db, document, chunks, title, description)
        return len(chunks)

    def _insert_chunk(
        self, db: sqlite3.Connection, chunk: Chunk, title: str, description: str, tags: str
    ) -> None:
        db.execute(
            """INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (chunk.chunk_id, chunk.concept_id, chunk.parent_chunk_id,
             _json(chunk.heading_path), chunk.kind, chunk.ordinal, chunk.content,
             chunk.content_hash, chunk.context_units, chunk.character_count,
             chunk.word_count, chunk.byte_count, chunk.previous_chunk,
             chunk.next_chunk),
        )
        for key, value in chunk.metadata.items():
            for item in _meta_values(value):
                db.execute("INSERT INTO chunk_metadata VALUES (?,?,?)",
                           (chunk.chunk_id, key, item))
        for link in chunk.links:
            db.execute("INSERT INTO chunk_links VALUES (?,?,?,?,?)",
                       (chunk.chunk_id, link.get("kind", "link"),
                        link.get("target", ""), link.get("label", ""), "links_to"))
        for match in re.finditer(
            r"(?m)^\s*([^\n→-]+?)\s*(?:→|->)\s*([a-z_]+)\s*(?:→|->)\s*([^\n]+?)\s*$",
            chunk.content,
        ):
            source, relation, target = (part.strip() for part in match.groups())
            db.execute("INSERT INTO chunk_links VALUES (?,?,?,?,?)",
                       (chunk.chunk_id, "relation", target, source, relation))
        db.execute(
            "INSERT INTO chunk_fts(chunk_id,title,heading,tags,description,identifiers,body) "
            "VALUES (?,?,?,?,?,?,?)",
            (chunk.chunk_id, title, " ".join(chunk.heading_path), tags, description,
             " ".join(chunk.identifiers), chunk.content),
        )

    def _upsert_fingerprint(
        self, db: sqlite3.Connection, document: Any, chunks: list[Chunk], title: str, description: str
    ) -> None:
        metadata = document.frontmatter
        doc_type = str(metadata.get("type", "")).lower()
        headings = [heading.text for heading in document.headings[:8]]
        identifiers = document.identifiers[:16]
        links = [link.get("target", "") for link in document.links[:12]]
        lines = [f"# {title}"]
        if description:
            lines.append(description)
        for key in ("project", "scope", "status", "authority"):
            if metadata.get(key):
                lines.append(f"{key}: {metadata[key]}")
        if headings:
            lines.append("headings: " + "; ".join(headings))
        if identifiers:
            lines.append("identifiers: " + ", ".join(identifiers))
        if links:
            lines.append("links: " + ", ".join(links))
        content = "\n".join(lines)
        kind = next((kind for kind in ("project", "design", "agent", "skill") if kind in doc_type), "knowledge-cluster")
        provenance = "curated" if doc_type == "fingerprint" else "deterministic"
        fingerprint_id = f"fingerprint:{document.source_path}"
        now = _now()
        digest = _hash(content)
        db.execute(
            """INSERT INTO fingerprints
               (fingerprint_id,concept_id,kind,content,source_hashes,fingerprint_hash,
                provenance,stale,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(fingerprint_id) DO UPDATE SET
                 kind=excluded.kind, content=excluded.content,
                 source_hashes=excluded.source_hashes,
                 fingerprint_hash=excluded.fingerprint_hash,
                 provenance=excluded.provenance, stale=0, updated_at=excluded.updated_at""",
            (fingerprint_id, document.source_path, kind, content,
             _json([document.source_hash]), digest, provenance, 0, now, now),
        )

    def _rebuild_sparse_features(self, db: sqlite3.Connection) -> None:
        db.execute("DELETE FROM sparse_features")
        rows = db.execute(
            """SELECT c.chunk_id,c.content,c.heading_path,k.title,k.description,k.metadata_json
               FROM chunks c JOIN concepts k ON k.concept_id=c.concept_id"""
        ).fetchall()
        raw_vectors: dict[str, Counter[str]] = {}
        document_frequency: Counter[str] = Counter()
        for row in rows:
            metadata = json.loads(row[5])
            weighted = Counter(normalized_words(row[1]))
            weighted.update({term: count * 2.0 for term, count in Counter(
                normalized_words(" ".join(json.loads(row[2])))
            ).items()})
            weighted.update({term: count * 2.5 for term, count in Counter(
                normalized_words(" ".join(_meta_values(metadata.get("tags"))))
            ).items()})
            weighted.update({term: count * 2.0 for term, count in Counter(
                normalized_words(row[3] + " " + row[4])
            ).items()})
            for key in ("project", "scope", "type"):
                weighted.update({term: 2.5 for term in normalized_words(str(metadata.get(key, "")))})
            raw_vectors[row[0]] = weighted
            document_frequency.update(weighted.keys())
        total = max(1, len(rows))
        inserts: list[tuple[str, str, float]] = []
        for chunk_id, counts in raw_vectors.items():
            max_tf = max(counts.values(), default=1.0)
            for feature, count in counts.items():
                idf = math.log((total + 1) / (document_frequency[feature] + 1)) + 1.0
                inserts.append((chunk_id, feature, float(count / max_tf * idf)))
        db.executemany("INSERT INTO sparse_features VALUES (?,?,?)", inserts)

    def refresh(self) -> dict[str, Any]:
        """Incrementally reparse changed files and delete stale projections."""
        started = time.perf_counter()
        files = self._markdown_files()
        current = {path.relative_to(self.store).as_posix(): path for path in files}
        files_reparsed = chunks_rebuilt = deleted = 0
        with self._connect() as db:
            existing = {row["concept_id"]: row for row in db.execute(
                "SELECT concept_id,source_hash,mtime_ns,parser_version,chunker_version,brainvector_version FROM concepts"
            )}
            for concept_id in sorted(set(existing) - set(current)):
                self._delete_concept(db, concept_id)
                deleted += 1
            for concept_id, path in current.items():
                source_hash, mtime_ns = self._file_state(path)
                old = existing.get(concept_id)
                stale_generation = old and (
                    old["parser_version"] != PARSER_VERSION
                    or old["chunker_version"] != CHUNKER_VERSION
                    or old["brainvector_version"] != BRAINVECTOR_VERSION
                )
                if old and old["source_hash"] == source_hash and not stale_generation:
                    continue
                chunks_rebuilt += self._index_document(db, path, source_hash, mtime_ns)
                files_reparsed += 1
            if files_reparsed or deleted:
                self._rebuild_sparse_features(db)
                self.retrieval_cache.clear()
                self.fingerprint_cache.clear()
            commit = _git_commit(self.store)
            state = {
                "last_indexed_git_commit": commit,
                "last_refresh_at": _now(),
                "store_version": self._store_version(db),
            }
            db.executemany("INSERT OR REPLACE INTO index_state VALUES (?,?)", state.items())
        return {
            "files_seen": len(files), "files_reparsed": files_reparsed,
            "files_deleted": deleted, "chunks_rebuilt": chunks_rebuilt,
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            "store_commit": _git_commit(self.store),
        }

    def rebuild(self) -> dict[str, Any]:
        with self._connect() as db:
            db.execute("DELETE FROM context_receipt_items")
            db.execute("DELETE FROM context_receipts")
            db.execute("DELETE FROM retrieval_runs")
            db.execute("DELETE FROM chunk_fts")
            db.execute("DELETE FROM concepts")
        self.parse_cache.clear()
        self.retrieval_cache.clear()
        self.context_cache.clear()
        self.fingerprint_cache.clear()
        result = self.refresh()
        result["mode"] = "rebuild"
        return result

    def migrate(self) -> dict[str, Any]:
        self._migrate()
        result = self.refresh()
        result["schema_version"] = SCHEMA_VERSION
        return result

    def _store_version(self, db: sqlite3.Connection) -> str:
        rows = db.execute("SELECT concept_id,source_hash FROM concepts ORDER BY concept_id").fetchall()
        return _hash("\n".join(f"{row[0]}:{row[1]}" for row in rows))

    def _stale_files(self, db: sqlite3.Connection) -> list[str]:
        existing = {row["concept_id"]: row for row in db.execute(
            "SELECT concept_id,source_hash,parser_version,chunker_version,brainvector_version FROM concepts"
        )}
        current_paths = {p.relative_to(self.store).as_posix(): p for p in self._markdown_files()}
        stale = list(set(existing) - set(current_paths)) + list(set(current_paths) - set(existing))
        for concept_id in set(existing).intersection(current_paths):
            row = existing[concept_id]
            digest, _ = self._file_state(current_paths[concept_id])
            if (digest != row["source_hash"] or row["parser_version"] != PARSER_VERSION
                    or row["chunker_version"] != CHUNKER_VERSION
                    or row["brainvector_version"] != BRAINVECTOR_VERSION):
                stale.append(concept_id)
        return sorted(set(stale))

    def status(self) -> dict[str, Any]:
        with self._connect() as db:
            state = dict(db.execute("SELECT key,value FROM index_state"))
            stale = self._stale_files(db)
            fts_ok = bool(db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='chunk_fts'"
            ).fetchone())
            return {
                "store_path": str(self.store),
                "database_path": str(self.db_path),
                "store_commit": _git_commit(self.store),
                "last_indexed_commit": state.get("last_indexed_git_commit", ""),
                "schema_version": int(state.get("schema_version", 0)),
                "parser_version": state.get("parser_version"),
                "chunker_version": state.get("chunker_version"),
                "brainvector_version": state.get("brainvector_version"),
                "ranker_version": state.get("ranker_version"),
                "stale_file_count": len(stale),
                "stale_files": stale,
                "concept_count": db.execute("SELECT count(*) FROM concepts").fetchone()[0],
                "chunk_count": db.execute("SELECT count(*) FROM chunks").fetchone()[0],
                "fts_available": fts_ok,
                "fingerprint_stale_count": db.execute(
                    "SELECT count(*) FROM fingerprints WHERE stale=1"
                ).fetchone()[0],
                "database_bytes": self.db_path.stat().st_size if self.db_path.exists() else 0,
            }

    def verify(self) -> dict[str, Any]:
        with self._connect() as db:
            integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
            stale = self._stale_files(db)
            orphan_chunks = db.execute(
                "SELECT count(*) FROM chunks c LEFT JOIN concepts k ON k.concept_id=c.concept_id WHERE k.concept_id IS NULL"
            ).fetchone()[0]
            fts_chunks = db.execute("SELECT count(*) FROM chunk_fts").fetchone()[0]
            chunks = db.execute("SELECT count(*) FROM chunks").fetchone()[0]
        return {
            "ok": integrity == "ok" and not stale and not orphan_chunks and fts_chunks == chunks,
            "integrity": integrity, "stale_files": stale,
            "orphan_chunks": orphan_chunks, "chunk_count": chunks,
            "fts_chunk_count": fts_chunks,
        }

    def _query_vector(self, db: sqlite3.Connection, query: str) -> dict[str, float]:
        counts = Counter(normalized_words(query))
        total_chunks = db.execute("SELECT max(1,count(*)) FROM chunks").fetchone()[0]
        vector: dict[str, float] = {}
        max_tf = max(counts.values(), default=1)
        for feature, count in counts.items():
            df = db.execute("SELECT count(*) FROM sparse_features WHERE feature=?", (feature,)).fetchone()[0]
            vector[feature] = count / max_tf * (math.log((total_chunks + 1) / (df + 1)) + 1)
        return vector

    def _chunk_vector(self, db: sqlite3.Connection, chunk_id: str) -> dict[str, float]:
        return {row[0]: row[1] for row in db.execute(
            "SELECT feature,weight FROM sparse_features WHERE chunk_id=?", (chunk_id,)
        )}

    def _metadata(self, db: sqlite3.Connection, chunk_id: str) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in db.execute("SELECT key,value FROM chunk_metadata WHERE chunk_id=?", (chunk_id,)):
            if key in output:
                output[key] = output[key] if isinstance(output[key], list) else [output[key]]
                output[key].append(value)
            else:
                output[key] = value
        return output

    def candidates(
        self, query: str, project: str = "", agent: str = "",
        filters: dict[str, Any] | None = None, limit: int = DEFAULT_CANDIDATES,
    ) -> tuple[list[RankedCandidate], dict[str, float]]:
        started = time.perf_counter()
        match = _fts_query(query)
        if not match:
            return [], {"fts_ms": 0.0, "rerank_ms": 0.0}
        filters = filters or {}
        with self._connect() as db:
            rows = db.execute(
                """SELECT f.chunk_id, bm25(chunk_fts,0.0,8.0,6.0,5.0,4.0,2.5,1.0) AS rank,
                          c.concept_id,c.content,c.content_hash,c.context_units,c.heading_path,c.kind
                   FROM chunk_fts f JOIN chunks c ON c.chunk_id=f.chunk_id
                   WHERE chunk_fts MATCH ? ORDER BY rank LIMIT ?""",
                (match, max(1, min(int(limit), 100))),
            ).fetchall()
            fts_ms = (time.perf_counter() - started) * 1000
            query_vector = self._query_vector(db, query)
            query_terms = set(normalized_words(query))
            ranked: list[RankedCandidate] = []
            for position, row in enumerate(rows):
                metadata = self._metadata(db, row[0])
                if any(str(metadata.get(key, "")).lower() != str(value).lower()
                       for key, value in filters.items() if value not in (None, "")):
                    continue
                chunk_vector = self._chunk_vector(db, row[0])
                metadata_terms = set(normalized_words(" ".join(
                    str(metadata.get(key, "")) for key in ("type", "tags", "description", "project", "scope")
                )))
                metadata_score = len(query_terms & metadata_terms) / max(1, len(query_terms))
                candidate_project = str(metadata.get("project", ""))
                scope = str(metadata.get("scope", ""))
                project_score = 1.0 if project and candidate_project.lower() == project.lower() else 0.0
                if agent and agent.lower() in metadata_terms:
                    project_score = max(project_score, 0.75)
                mismatch = 1.0 if project and candidate_project and candidate_project.lower() != project.lower() else 0.0
                graph_hits = db.execute(
                    "SELECT count(*) FROM chunk_links WHERE chunk_id=? AND lower(target) LIKE ?",
                    (row[0], "%" + (project or agent or query.split()[0]).lower() + "%"),
                ).fetchone()[0]
                usage = db.execute(
                    "SELECT coalesce(sum(verified_success_count),0),coalesce(sum(useful_count),0),coalesce(sum(retrieved_count),0) "
                    "FROM chunk_usage WHERE chunk_id=?", (row[0],)
                ).fetchone()
                verified = min(1.0, (usage[0] * 2 + usage[1]) / max(1, usage[2]))
                fp = db.execute(
                    "SELECT content FROM fingerprints WHERE concept_id=? AND stale=0",
                    (row["concept_id"],),
                ).fetchone()
                fp_terms = set(normalized_words(fp[0])) if fp else set()
                components = {
                    "lexical_score": (len(rows) - position) / max(1, len(rows)),
                    "sparse_vector_score": sparse_cosine(query_vector, chunk_vector),
                    "metadata_score": metadata_score,
                    "project_scope_score": project_score,
                    "graph_score": min(1.0, graph_hits / 2),
                    "fingerprint_score": len(query_terms & fp_terms) / max(1, len(query_terms)),
                    "verified_usage_score": verified,
                    "redundancy_penalty": 0.0,
                    "scope_mismatch_penalty": mismatch,
                }
                candidate = RankedCandidate(
                    chunk_id=row["chunk_id"], concept_id=row["concept_id"], content=row["content"],
                    content_hash=row["content_hash"], context_units=row["context_units"],
                    heading_path=json.loads(row["heading_path"]), kind=row["kind"], metadata=metadata,
                    components=components, terms=set(chunk_vector),
                )
                candidate.score = hybrid_score(components)
                ranked.append(candidate)
            ranked.sort(key=lambda item: (-item.score, item.context_units, item.chunk_id))
            rerank_ms = (time.perf_counter() - started) * 1000 - fts_ms
        return ranked, {"fts_ms": round(fts_ms, 3), "rerank_ms": round(rerank_ms, 3)}

    def _known_hashes(self, db: sqlite3.Connection, handle: str, caller_id: str) -> set[str]:
        owner = db.execute("SELECT caller_id FROM context_receipts WHERE context_handle=?", (handle,)).fetchone()
        if not owner:
            return set()
        if owner[0] != caller_id:
            raise PermissionError("context handle belongs to another caller")
        return {row[0] for row in db.execute(
            "SELECT content_hash FROM context_receipt_items WHERE context_handle=?", (handle,)
        )}

    def _fingerprint(self, db: sqlite3.Connection, concept_id: str) -> sqlite3.Row | None:
        return db.execute(
            "SELECT fingerprint_id,content,fingerprint_hash,kind,provenance FROM fingerprints "
            "WHERE concept_id=? AND stale=0 ORDER BY provenance='curated' DESC LIMIT 1",
            (concept_id,),
        ).fetchone()

    def context(
        self,
        query: str,
        project: str = "",
        agent: str = "",
        mode: str = "compact",
        max_context_units: int = 1200,
        context_handle: str = "",
        filters: dict[str, Any] | None = None,
        caller_id: str = "local",
    ) -> dict[str, Any]:
        """Return fingerprint-first, budgeted context with observable scoring."""
        total_started = time.perf_counter()
        if not query.strip():
            raise ValueError("query is required")
        budget = max(32, min(int(max_context_units), 20000))
        candidates, timing = self.candidates(query, project, agent, filters)
        selected: list[RankedCandidate] = []
        omitted: list[str] = []
        fingerprints: list[dict[str, Any]] = []
        remaining = budget
        with self._connect() as db:
            store_version = self._store_version(db)
            handle = context_handle or uuid.uuid4().hex
            known = self._known_hashes(db, handle, caller_id) if context_handle else set()
            selected_terms: set[str] = set()
            selected_hashes: set[str] = set()
            selected_headings: set[tuple[str, tuple[str, ...]]] = set()
            concept_chunk_counts: Counter[str] = Counter()
            fingerprinted: set[str] = set()
            ordered = sorted(
                candidates,
                key=lambda item: item.score / max(1, item.context_units),
                reverse=True,
            )
            for candidate in ordered:
                heading_key = (candidate.concept_id, tuple(candidate.heading_path))
                if candidate.content_hash in known or candidate.content_hash in selected_hashes:
                    omitted.append(candidate.chunk_id)
                    continue
                if heading_key in selected_headings:
                    omitted.append(candidate.chunk_id)
                    continue
                overlap = len(candidate.terms & selected_terms) / max(1, len(candidate.terms))
                candidate.components["redundancy_penalty"] = overlap
                candidate.score = hybrid_score(candidate.components)
                if overlap > 0.82:
                    omitted.append(candidate.chunk_id)
                    continue
                fp = self._fingerprint(db, candidate.concept_id)
                if (mode != "deep" and fp and candidate.concept_id not in fingerprinted
                        and fp[2] not in known and len(fingerprints) < 5):
                    fp_units = max(1, math.ceil(len(fp[1]) / 4))
                    if fp_units <= remaining:
                        fingerprints.append({
                            "ref": fp[0], "concept_id": candidate.concept_id,
                            "kind": fp[3], "content": fp[1], "content_hash": fp[2],
                            "provenance": fp[4], "context_units": fp_units,
                        })
                        fingerprinted.add(candidate.concept_id)
                        remaining -= fp_units
                if mode == "fingerprints" and candidate.concept_id in fingerprinted:
                    omitted.append(candidate.chunk_id)
                    continue
                if (mode == "compact" and candidate.concept_id in fingerprinted
                        and concept_chunk_counts[candidate.concept_id] >= 1):
                    omitted.append(candidate.chunk_id)
                    continue
                marginal = candidate.score - overlap * 0.18
                density = marginal / max(1, candidate.context_units)
                candidate.components["marginal_context_value"] = marginal
                candidate.components["density"] = density
                if candidate.context_units <= remaining:
                    selected.append(candidate)
                    selected_terms.update(candidate.terms)
                    selected_hashes.add(candidate.content_hash)
                    selected_headings.add(heading_key)
                    concept_chunk_counts[candidate.concept_id] += 1
                    remaining -= candidate.context_units
                else:
                    omitted.append(candidate.chunk_id)
            expires = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=RECEIPT_TTL_DAYS)).isoformat()
            db.execute(
                """INSERT INTO context_receipts VALUES (?,?,?,?,?,?)
                   ON CONFLICT(context_handle) DO UPDATE SET
                   store_version=excluded.store_version, expires_at=excluded.expires_at""",
                (handle, caller_id, agent, store_version, _now(), expires),
            )
            receipt_items = [
                (handle, item["ref"], item["content_hash"], "fingerprint") for item in fingerprints
            ] + [
                (handle, item.chunk_id, item.content_hash, "chunk") for item in selected
            ]
            db.executemany("INSERT OR IGNORE INTO context_receipt_items VALUES (?,?,?,?)", receipt_items)
            for item in selected:
                db.execute(
                    """INSERT INTO chunk_usage(chunk_id,caller_id,retrieved_count,last_used_at)
                       VALUES (?,?,1,?) ON CONFLICT(chunk_id,caller_id) DO UPDATE SET
                       retrieved_count=retrieved_count+1,last_used_at=excluded.last_used_at""",
                    (item.chunk_id, caller_id, _now()),
                )
            returned_units = budget - remaining
            avoided = sum(item.context_units for item in candidates) - sum(item.context_units for item in selected)
            run_id = uuid.uuid4().hex
            total_ms = (time.perf_counter() - total_started) * 1000
            db.execute(
                "INSERT INTO retrieval_runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (run_id, _hash(query.lower().strip()), caller_id, agent, _json(filters or {}),
                 len(candidates), _json([i.chunk_id for i in selected]), returned_units,
                 max(0, avoided), 0, len(fingerprints), timing["fts_ms"],
                 timing["rerank_ms"], round(total_ms, 3), _now(), None, None),
            )
        context_chunks = [{
            "ref": item.chunk_id, "concept_id": item.concept_id,
            "heading_path": item.heading_path, "kind": item.kind,
            "content": item.content, "content_hash": item.content_hash,
            "context_units": item.context_units, "metadata": item.metadata,
            "score": round(item.score, 6),
            "score_components": {k: round(v, 6) for k, v in item.components.items()},
        } for item in selected]
        refs = [item["ref"] for item in fingerprints] + [item["ref"] for item in context_chunks]
        return {
            "context_handle": handle,
            "fingerprints": fingerprints,
            "context_chunks": context_chunks,
            "refs": refs,
            "omitted_refs": omitted,
            "coverage": {
                "candidate_count": len(candidates), "selected_count": len(refs),
                "returned_context_units": budget - remaining,
                "max_context_units": budget, "delta_omissions": len(known),
            },
            "retrieval_metrics": {
                **timing, "total_ms": round((time.perf_counter() - total_started) * 1000, 3),
                "candidate_chunks": len(candidates), "selected_chunks": len(selected),
                "fingerprint_hits": len(fingerprints), "avoided_context_units": max(0, avoided),
            },
            "cache_metrics": {"retrieval_cache_hit": False, "context_receipt_hit": bool(known)},
        }

    def expand(
        self, ref: str, level: str = "section", context_handle: str = "",
        caller_id: str = "local", max_context_units: int = 2400,
    ) -> dict[str, Any]:
        """Expand fingerprint -> section -> adjacent -> full concept."""
        with self._connect() as db:
            if ref.startswith("fingerprint:"):
                fp = db.execute("SELECT concept_id FROM fingerprints WHERE fingerprint_id=?", (ref,)).fetchone()
                if not fp:
                    raise KeyError(f"unknown ref: {ref}")
                concept_id = fp[0]
                anchor_ordinal = 0
            else:
                row = db.execute("SELECT concept_id,ordinal FROM chunks WHERE chunk_id=?", (ref,)).fetchone()
                if not row:
                    raise KeyError(f"unknown ref: {ref}")
                concept_id, anchor_ordinal = row[0], row[1]
            if context_handle:
                known = self._known_hashes(db, context_handle, caller_id)
            else:
                known = set()
            if level == "full_concept":
                rows = db.execute("SELECT * FROM chunks WHERE concept_id=? ORDER BY ordinal", (concept_id,)).fetchall()
            elif level == "adjacent":
                rows = db.execute(
                    "SELECT * FROM chunks WHERE concept_id=? AND ordinal BETWEEN ? AND ? ORDER BY ordinal",
                    (concept_id, max(0, anchor_ordinal - 1), anchor_ordinal + 1),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT * FROM chunks WHERE concept_id=? AND ordinal=?", (concept_id, anchor_ordinal)
                ).fetchall()
            items, units = [], 0
            for row in rows:
                if row["content_hash"] in known or units + row["context_units"] > max_context_units:
                    continue
                items.append({
                    "ref": row["chunk_id"], "concept_id": row["concept_id"],
                    "heading_path": json.loads(row["heading_path"]), "kind": row["kind"],
                    "content": row["content"], "content_hash": row["content_hash"],
                    "context_units": row["context_units"],
                })
                units += row["context_units"]
            if context_handle:
                db.executemany(
                    "INSERT OR IGNORE INTO context_receipt_items VALUES (?,?,?,?)",
                    [(context_handle, item["ref"], item["content_hash"], "chunk") for item in items],
                )
            return {"source_ref": ref, "level": level, "concept_id": concept_id,
                    "chunks": items, "context_units": units}

    def report_usage(
        self, caller_id: str, useful_refs: Iterable[str], verified: bool = False,
        retrieval_run_id: str = "",
    ) -> dict[str, Any]:
        refs = list(dict.fromkeys(useful_refs))
        with self._connect() as db:
            for ref in refs:
                db.execute(
                    """INSERT INTO chunk_usage
                       (chunk_id,caller_id,retrieved_count,useful_count,verified_success_count,last_used_at)
                       VALUES (?,?,0,1,?,?) ON CONFLICT(chunk_id,caller_id) DO UPDATE SET
                       useful_count=useful_count+1,
                       verified_success_count=verified_success_count+excluded.verified_success_count,
                       last_used_at=excluded.last_used_at""",
                    (ref, caller_id, 1 if verified else 0, _now()),
                )
            if retrieval_run_id:
                db.execute(
                    "UPDATE retrieval_runs SET verification_outcome=?,useful_refs_json=? WHERE run_id=? AND caller_id=?",
                    ("verified_success" if verified else "reported_useful", _json(refs), retrieval_run_id, caller_id),
                )
        return {"updated_refs": refs, "verified": verified}

    def derive_insights(self, minimum_samples: int = 3) -> list[dict[str, Any]]:
        """Generate evidence-backed operational candidates; never rewrites knowledge."""
        output = []
        with self._connect() as db:
            rows = db.execute(
                """SELECT chunk_id,sum(retrieved_count) r,sum(useful_count) u,
                          sum(verified_success_count) v FROM chunk_usage
                   GROUP BY chunk_id HAVING r>=?""", (minimum_samples,)
            ).fetchall()
            for row in rows:
                confidence = (row[2] + row[3]) / max(1, row[1] + row[3])
                if confidence < 0.5:
                    continue
                insight_id = "insight:" + _hash(f"hot:{row[0]}:{row[1]}:{row[2]}:{row[3]}")[:16]
                evidence = {"refs": [row[0]], "retrievals": row[1],
                            "useful": row[2], "verified_successes": row[3]}
                db.execute(
                    "INSERT OR REPLACE INTO insights VALUES (?,?,?,?,?,?,?)",
                    (insight_id, "retrieval_hot_path", _json(evidence), row[1],
                     confidence, "consider_curated_fingerprint", _now()),
                )
                output.append({"insight_id": insight_id, "insight_type": "retrieval_hot_path",
                               "evidence": evidence, "sample_count": row[1],
                               "confidence": round(confidence, 4),
                               "suggested_action": "consider_curated_fingerprint"})
        return output
