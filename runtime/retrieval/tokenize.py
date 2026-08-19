"""Technical token normalization that preserves exact identifiers."""

from __future__ import annotations

import re

TOKENIZER_VERSION = "1.0.0"

_RAW = re.compile(r"[A-Za-z0-9]+(?:[._:/@-][A-Za-z0-9]+)*|/[A-Za-z0-9._~!$&'()*+,;=:@%/-]+")
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def _parts(token: str) -> tuple[list[str], list[str]]:
    trimmed = token.strip(".,;:()[]{}<>`'\"")
    segments = [s for s in re.split(r"[._:/@-]+", trimmed) if s]
    subtokens: list[str] = []
    for segment in segments:
        subtokens.extend(part for part in _CAMEL.split(segment) if part)
    return segments, subtokens


def normalize_token(token: str) -> list[str]:
    """Return exact, component, lowercase, and snake_case search forms."""
    token = token.strip()
    if not token:
        return []
    segments, subtokens = _parts(token)
    lowered = [p.lower() for p in subtokens if p]
    values = [token]
    values.extend(segments)
    values.extend(lowered)
    if len(lowered) > 1:
        values.append("_".join(lowered))
    return list(dict.fromkeys(v for v in values if v))


def searchable_terms(text: str) -> list[str]:
    terms: list[str] = []
    for match in _RAW.finditer(text or ""):
        terms.extend(normalize_token(match.group(0)))
    return list(dict.fromkeys(terms))


def normalized_words(text: str) -> list[str]:
    return [term.lower() for term in searchable_terms(text) if term]
