"""Line-state parser for OKF-flavoured Brain Store Markdown.

It recognizes the structural forms the retrieval system needs without trying
to be a complete CommonMark renderer. The parser is intentionally stdlib-only.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PARSER_VERSION = "1.0.0"

_FM_LINE = re.compile(r"^([A-Za-z_][\w-]*):\s*(.*)$")
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_FENCE = re.compile(r"^\s*(```+|~~~+)(.*)$")
_LIST = re.compile(r"^\s*(?:[-+*]|\d+[.)])\s+")
_TABLE_DIVIDER = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")
_WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")
_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_IDENTIFIER = re.compile(
    r"(?<![\w])(?:/[A-Za-z0-9._~!$&'()*+,;=:@%/-]+|"
    r"[A-Za-z_][A-Za-z0-9_.:/@-]*[A-Z0-9_./:@-][A-Za-z0-9_.:/@-]*|"
    r"v?\d+(?:\.\d+){1,3}(?:[-+][A-Za-z0-9.-]+)?)(?![\w])"
)


@dataclass(frozen=True)
class Heading:
    level: int
    text: str
    line: int


@dataclass
class Block:
    kind: str
    text: str
    start_line: int
    end_line: int
    heading_path: tuple[str, ...] = ()
    language: str = ""
    links: list[dict[str, str]] = field(default_factory=list)
    identifiers: list[str] = field(default_factory=list)


@dataclass
class Document:
    source_path: str
    source_hash: str
    frontmatter: dict[str, Any]
    headings: list[Heading]
    blocks: list[Block]
    links: list[dict[str, str]]
    identifiers: list[str]
    body: str
    parser_version: str = PARSER_VERSION


def _scalar(value: str) -> Any:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        return [
            part.strip().strip("\"'")
            for part in value[1:-1].split(",")
            if part.strip()
        ]
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    return value.strip("\"'")


def _frontmatter(lines: list[str]) -> tuple[dict[str, Any], int]:
    if not lines or lines[0].strip() != "---":
        return {}, 0
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return {}, 0
    result: dict[str, Any] = {}
    active_list: str | None = None
    for line in lines[1:end]:
        match = _FM_LINE.match(line)
        if match:
            key, value = match.groups()
            if value:
                result[key] = _scalar(value)
                active_list = None
            else:
                result[key] = []
                active_list = key
        elif active_list and re.match(r"^\s*-\s+", line):
            result[active_list].append(re.sub(r"^\s*-\s+", "", line).strip("\"'"))
    return result, end + 1


def _annotations(text: str) -> tuple[list[dict[str, str]], list[str]]:
    links: list[dict[str, str]] = []
    for match in _WIKILINK.finditer(text):
        target, _, label = match.group(1).partition("|")
        links.append({"kind": "wikilink", "target": target.strip(), "label": label.strip()})
    for match in _MD_LINK.finditer(text):
        links.append({"kind": "markdown", "target": match.group(2), "label": match.group(1)})
    identifiers = list(dict.fromkeys(m.group(0) for m in _IDENTIFIER.finditer(text)))
    return links, identifiers


def parse_markdown(text: str, source_path: str = "") -> Document:
    """Parse Markdown into structural blocks using a deterministic line state."""
    lines = text.splitlines()
    fm, cursor = _frontmatter(lines)
    headings: list[Heading] = []
    blocks: list[Block] = []
    hierarchy: list[str] = []
    buffer: list[str] = []
    buffer_kind = "paragraph"
    buffer_start = cursor + 1

    def flush(end_line: int) -> None:
        nonlocal buffer, buffer_start
        content = "\n".join(buffer).strip("\n")
        if content.strip():
            links, identifiers = _annotations(content)
            blocks.append(Block(buffer_kind, content, buffer_start, end_line,
                                tuple(hierarchy), links=links, identifiers=identifiers))
        buffer = []

    i = cursor
    while i < len(lines):
        line = lines[i]
        heading = _HEADING.match(line)
        fence = _FENCE.match(line)
        if heading:
            flush(i)
            level, title = len(heading.group(1)), heading.group(2).strip()
            hierarchy[:] = hierarchy[: level - 1]
            hierarchy.append(title)
            headings.append(Heading(level, title, i + 1))
            links, identifiers = _annotations(title)
            blocks.append(Block("heading", line, i + 1, i + 1,
                                tuple(hierarchy), links=links, identifiers=identifiers))
            i += 1
            buffer_start = i + 1
            continue
        if fence:
            flush(i)
            marker, language = fence.groups()
            start = i
            code = [line]
            i += 1
            while i < len(lines):
                code.append(lines[i])
                if lines[i].lstrip().startswith(marker[:3]):
                    i += 1
                    break
                i += 1
            content = "\n".join(code)
            links, identifiers = _annotations(content)
            blocks.append(Block("code", content, start + 1, i, tuple(hierarchy),
                                language=language.strip(), links=links,
                                identifiers=identifiers))
            buffer_start = i + 1
            continue
        is_table = i + 1 < len(lines) and "|" in line and _TABLE_DIVIDER.match(lines[i + 1])
        if is_table:
            flush(i)
            start = i
            table = [line, lines[i + 1]]
            i += 2
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                table.append(lines[i])
                i += 1
            content = "\n".join(table)
            links, identifiers = _annotations(content)
            blocks.append(Block("table", content, start + 1, i, tuple(hierarchy),
                                links=links, identifiers=identifiers))
            buffer_start = i + 1
            continue
        kind = "list" if _LIST.match(line) else "paragraph"
        if line.strip() == "":
            flush(i)
            i += 1
            buffer_start = i + 1
            buffer_kind = "paragraph"
            continue
        if buffer and kind != buffer_kind:
            flush(i)
            buffer_start = i + 1
        buffer_kind = kind
        buffer.append(line)
        i += 1
    flush(len(lines))

    all_links = [link for block in blocks for link in block.links]
    all_identifiers = list(dict.fromkeys(i for block in blocks for i in block.identifiers))
    body = "\n".join(lines[cursor:])
    return Document(
        source_path=source_path.replace("\\", "/"),
        source_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        frontmatter=fm,
        headings=headings,
        blocks=blocks,
        links=all_links,
        identifiers=all_identifiers,
        body=body,
    )


def parse_path(path: str | Path, root: str | Path | None = None) -> Document:
    file_path = Path(path)
    source = file_path.relative_to(root).as_posix() if root else file_path.as_posix()
    return parse_markdown(file_path.read_text(encoding="utf-8"), source)
