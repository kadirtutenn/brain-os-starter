import json
import shutil
from pathlib import Path

import pytest

from runtime.chunking import chunk_document
from runtime.parser import parse_markdown
from runtime.retrieval import RetrievalIndex
from runtime.retrieval.tokenize import normalize_token


SAMPLE = """---
type: Knowledge
description: API lookup contract
tags: [api, user]
project: atlas
scope: project
timestamp: 2026-08-19
---

# User API

Use `getUserById` at [/api/users/:id](https://example.invalid/api).

## Decision

Keep searchKeyword_id exact and use [[Lessons/api-patterns]].

| field | value |
| --- | --- |
| user_id | v1.2.3 |

```python
def get_user(user_id):
    return user_id
```
"""


def make_store(tmp_path: Path) -> Path:
    store = tmp_path / "store"
    (store / "Knowledge").mkdir(parents=True)
    (store / "Lessons").mkdir()
    (store / "Knowledge" / "api.md").write_text(SAMPLE, encoding="utf-8")
    (store / "Lessons" / "other.md").write_text(
        """---
type: Lesson
description: CSS color note
tags: [css]
project: other
scope: project
timestamp: 2026-08-19
---
# Styling
Use a blue background.
""", encoding="utf-8")
    return store


def index_for(tmp_path: Path) -> RetrievalIndex:
    store = make_store(tmp_path)
    return RetrievalIndex(store, tmp_path / "runtime" / "retrieval.sqlite", tmp_path / "cache")


def test_parser_recognizes_required_structures():
    document = parse_markdown(SAMPLE, "Knowledge/api.md")
    assert document.frontmatter["project"] == "atlas"
    assert [block.kind for block in document.blocks].count("table") == 1
    assert [block.kind for block in document.blocks].count("code") == 1
    assert document.headings[-1].text == "Decision"
    assert any(link["kind"] == "wikilink" for link in document.links)
    assert any(link["kind"] == "markdown" for link in document.links)
    assert "getUserById" in document.identifiers


def test_technical_normalization_preserves_exact_and_derived_terms():
    assert normalize_token("getUserById") == [
        "getUserById", "get", "user", "by", "id", "get_user_by_id"
    ]
    values = normalize_token("searchKeyword_id")
    assert "searchKeyword_id" in values
    assert "searchKeyword" in values
    assert "search" in values and "keyword" in values and "id" in values
    assert "search_keyword_id" in values


def test_chunker_is_structure_first_and_keeps_code_table_whole():
    chunks = chunk_document(parse_markdown(SAMPLE, "Knowledge/api.md"))
    assert any(chunk.kind == "decision" for chunk in chunks)
    assert any(chunk.kind == "table" and "user_id" in chunk.content for chunk in chunks)
    assert any(chunk.kind == "code" and chunk.content.endswith("```") for chunk in chunks)
    assert all(chunk.chunk_id.startswith("Knowledge/api.md#") for chunk in chunks)
    assert all(chunk.content_hash in chunk.chunk_id or chunk.content_hash[:16] in chunk.chunk_id for chunk in chunks)


def test_chunker_disambiguates_identical_chunks_in_one_concept():
    document = parse_markdown(
        "# Repeated\n\nSame text.\n\n# Repeated\n\nSame text.\n",
        "Knowledge/repeated.md",
    )
    chunks = chunk_document(document)
    assert len(chunks) == 2
    assert len({chunk.chunk_id for chunk in chunks}) == 2
    assert chunks[1].chunk_id == f"{chunks[0].chunk_id}~2"


def test_rebuild_refresh_verify_and_generation_status(tmp_path):
    index = index_for(tmp_path)
    rebuilt = index.rebuild()
    assert rebuilt["files_reparsed"] == 2
    assert rebuilt["chunks_rebuilt"] > 2
    assert index.verify()["ok"] is True
    unchanged = index.refresh()
    assert unchanged["files_reparsed"] == 0
    status = index.status()
    assert status["stale_file_count"] == 0
    assert status["fts_available"] is True
    assert status["parser_version"] and status["chunker_version"]


def test_incremental_refresh_replaces_changed_and_deleted_documents(tmp_path):
    index = index_for(tmp_path)
    index.rebuild()
    api = index.store / "Knowledge" / "api.md"
    api.write_text(SAMPLE.replace("lookup contract", "lookup contract changed"), encoding="utf-8")
    (index.store / "Lessons" / "other.md").unlink()
    refreshed = index.refresh()
    assert refreshed["files_reparsed"] == 1
    assert refreshed["files_deleted"] == 1
    assert index.status()["concept_count"] == 1
    assert index.verify()["ok"] is True


def test_hybrid_context_is_budgeted_observable_and_project_aware(tmp_path):
    index = index_for(tmp_path)
    index.rebuild()
    result = index.context(
        "getUserById user lookup API", project="atlas", agent="codex",
        max_context_units=260, caller_id="alice",
    )
    assert result["refs"]
    assert result["coverage"]["returned_context_units"] <= 260
    assert result["retrieval_metrics"]["candidate_chunks"] >= 1
    assert result["fingerprints"]
    assert all("score_components" in chunk for chunk in result["context_chunks"])
    assert result["context_chunks"][0]["concept_id"] == "Knowledge/api.md"


def test_context_receipts_are_caller_scoped_and_return_deltas(tmp_path):
    index = index_for(tmp_path)
    index.rebuild()
    first = index.context("getUserById API", caller_id="alice", max_context_units=300)
    second = index.context(
        "getUserById API", caller_id="alice",
        context_handle=first["context_handle"], max_context_units=300,
    )
    assert set(first["refs"]).isdisjoint(second["refs"])
    with pytest.raises(PermissionError):
        index.context(
            "getUserById API", caller_id="bob",
            context_handle=first["context_handle"], max_context_units=300,
        )


def test_expand_progresses_from_fingerprint_without_resending_receipt(tmp_path):
    index = index_for(tmp_path)
    index.rebuild()
    first = index.context("getUserById", caller_id="alice", mode="fingerprints")
    expanded = index.expand(
        first["fingerprints"][0]["ref"], level="adjacent",
        context_handle=first["context_handle"], caller_id="alice",
    )
    assert expanded["concept_id"] == "Knowledge/api.md"
    assert expanded["chunks"]
    assert expanded["context_units"] <= 2400


def test_separate_cache_files_and_no_model_dependencies(tmp_path):
    index = index_for(tmp_path)
    index.rebuild()
    assert (tmp_path / "cache" / "parse-cache.sqlite").exists()
    assert (tmp_path / "cache" / "retrieval-cache.sqlite").exists()
    assert (tmp_path / "cache" / "context-cache.sqlite").exists()
    assert (tmp_path / "cache" / "fingerprint-cache.sqlite").exists()
    source = Path("runtime").read_text if False else ""  # keep test stdlib-only
    requirements = Path("mcp/requirements.txt").read_text(encoding="utf-8").lower()
    for forbidden in ("openai", "anthropic", "sentence-transformers", "torch"):
        assert forbidden not in requirements
