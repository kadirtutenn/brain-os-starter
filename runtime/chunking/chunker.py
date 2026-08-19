"""Structure-first, size-second Brain Store chunking."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from runtime.parser import Block, Document
from runtime.retrieval.tokenize import searchable_terms

CHUNKER_VERSION = "1.0.0"
SOFT_TARGET_UNITS = 240
SOFT_MAX_UNITS = 450

_TYPED = {
    "goal": "goal", "observation": "observation", "hypothesis": "hypothesis",
    "decision": "decision", "action": "action", "outcome": "outcome",
    "insight": "insight", "handoff": "handoff", "summary": "summary",
    "lesson": "lesson", "procedure": "procedure", "fingerprint": "fingerprint",
}


def context_units(text: str) -> int:
    """Conservative provider-independent estimate, not an exact token count."""
    return max(1, math.ceil(max(len(text) / 4, len(text.split()) * 1.25)))


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "root"


def _kind(document: Document, block: Block) -> str:
    if block.kind in {"code", "table"}:
        return block.kind
    heading = block.heading_path[-1].lower() if block.heading_path else ""
    for needle, kind in _TYPED.items():
        if needle in heading:
            return kind
    doc_type = str(document.frontmatter.get("type", "")).lower()
    if doc_type == "session" and heading:
        return next((kind for needle, kind in _TYPED.items() if needle in heading), "summary")
    return "concept" if not block.heading_path else "section"


@dataclass
class Chunk:
    chunk_id: str
    concept_id: str
    parent_chunk_id: str | None
    heading_path: tuple[str, ...]
    kind: str
    ordinal: int
    content: str
    content_hash: str
    context_units: int
    character_count: int
    word_count: int
    byte_count: int
    metadata: dict[str, Any]
    previous_chunk: str | None = None
    next_chunk: str | None = None
    links: list[dict[str, str]] = field(default_factory=list)
    identifiers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _split_paragraph(block: Block) -> list[Block]:
    if context_units(block.text) <= SOFT_MAX_UNITS or block.kind in {"code", "table"}:
        return [block]
    paragraphs = re.split(r"\n{2,}", block.text)
    if len(paragraphs) == 1:
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", block.text)
        paragraphs = sentences
    groups: list[str] = []
    active = ""
    for part in paragraphs:
        proposal = (active + "\n\n" + part).strip() if active else part
        if active and context_units(proposal) > SOFT_MAX_UNITS:
            groups.append(active)
            active = part
        else:
            active = proposal
    if active:
        groups.append(active)
    return [Block(block.kind, text, block.start_line, block.end_line,
                  block.heading_path, block.language, block.links, block.identifiers)
            for text in groups]


def chunk_document(document: Document) -> list[Chunk]:
    """Create stable-ref chunks on semantic block/heading boundaries."""
    concept_id = document.source_path
    blocks = [piece for block in document.blocks if block.kind != "heading"
              for piece in _split_paragraph(block)]
    if not blocks and document.body.strip():
        blocks = [Block("paragraph", document.body.strip(), 1, 1)]
    chunks: list[Chunk] = []
    for ordinal, block in enumerate(blocks):
        content = block.text.strip()
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        anchor = _slug(block.heading_path[-1] if block.heading_path else "root")
        chunk_id = f"{concept_id}#{anchor}@{digest[:16]}"
        metadata = {
            key: document.frontmatter.get(key)
            for key in ("type", "tags", "project", "scope", "status", "confidence", "authority", "description")
            if document.frontmatter.get(key) not in (None, "", [])
        }
        identifiers = list(dict.fromkeys(block.identifiers + searchable_terms(content)))
        chunks.append(Chunk(
            chunk_id=chunk_id,
            concept_id=concept_id,
            parent_chunk_id=None,
            heading_path=block.heading_path,
            kind=_kind(document, block),
            ordinal=ordinal,
            content=content,
            content_hash=digest,
            context_units=context_units(content),
            character_count=len(content),
            word_count=len(content.split()),
            byte_count=len(content.encode("utf-8")),
            metadata=metadata,
            links=block.links,
            identifiers=identifiers,
        ))
    heading_parents: dict[tuple[str, ...], str] = {}
    for chunk in chunks:
        parent_path = chunk.heading_path[:-1]
        chunk.parent_chunk_id = heading_parents.get(parent_path)
        heading_parents.setdefault(chunk.heading_path, chunk.chunk_id)
    for index, chunk in enumerate(chunks):
        chunk.previous_chunk = chunks[index - 1].chunk_id if index else None
        chunk.next_chunk = chunks[index + 1].chunk_id if index + 1 < len(chunks) else None
    return chunks
