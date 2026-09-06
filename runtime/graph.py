"""Deterministic Markdown wikilink graph inspection."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from runtime.parser import parse_path

RESERVED = {"index.md", "INDEX.md", "log.md"}


def _target_path(store: Path, source: Path, target: str) -> Path | None:
    target = target.split("|", 1)[0].split("#", 1)[0].strip()
    if not target:
        return None
    clean = target.lstrip("/")
    candidates = [store / clean, source.parent / clean]
    if not clean.endswith(".md"):
        candidates.extend([store / f"{clean}.md", source.parent / f"{clean}.md"])
    for candidate in candidates:
        resolved = candidate.resolve()
        try:
            resolved.relative_to(store.resolve())
        except ValueError:
            continue
        if resolved.is_file() and resolved.suffix == ".md":
            return resolved
    # Obsidian resolves a bare wikilink by note name, regardless of folder.
    if "/" not in clean:
        matches = sorted(store.rglob(f"{clean}.md"))
        if len(matches) == 1:
            return matches[0].resolve()
    return None


def inspect(store_path: str | os.PathLike[str]) -> dict[str, Any]:
    store = Path(store_path).expanduser().resolve()
    files = sorted(p for p in store.rglob("*.md") if "." not in p.parts and p.name not in RESERVED)
    nodes = {p.relative_to(store).as_posix() for p in files}
    edges: list[dict[str, str]] = []
    broken: list[dict[str, str]] = []
    inbound: dict[str, int] = {node: 0 for node in nodes}
    for source in files:
        document = parse_path(source, store)
        source_id = source.relative_to(store).as_posix()
        for link in document.links:
            if link.get("kind") != "wikilink":
                continue
            target = link.get("target", "")
            resolved = _target_path(store, source, target)
            if resolved is None:
                broken.append({"source": source_id, "target": target})
                continue
            target_id = resolved.relative_to(store).as_posix()
            edges.append({"source": source_id, "target": target_id})
            inbound[target_id] = inbound.get(target_id, 0) + 1
    orphaned = sorted(node for node, count in inbound.items() if count == 0)
    return {
        "store_path": str(store),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "broken_wikilinks": broken,
        "orphaned_nodes": orphaned,
        "ok": not broken,
    }
