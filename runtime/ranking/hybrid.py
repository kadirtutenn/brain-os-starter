"""Hybrid scoring components kept separate for inspection and calibration."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping

RANKER_VERSION = "1.0.0"

DEFAULT_WEIGHTS = {
    "lexical_score": 0.31,
    "sparse_vector_score": 0.24,
    "metadata_score": 0.13,
    "project_scope_score": 0.13,
    "graph_score": 0.06,
    "fingerprint_score": 0.07,
    "verified_usage_score": 0.06,
    "redundancy_penalty": 0.18,
    "scope_mismatch_penalty": 0.35,
}


@dataclass
class RankedCandidate:
    chunk_id: str
    concept_id: str
    content: str
    content_hash: str
    context_units: int
    heading_path: list[str]
    kind: str
    metadata: dict[str, Any]
    components: dict[str, float] = field(default_factory=dict)
    score: float = 0.0
    terms: set[str] = field(default_factory=set)


def sparse_cosine(left: Mapping[str, float], right: Mapping[str, float]) -> float:
    if not left or not right:
        return 0.0
    common = set(left).intersection(right)
    dot = sum(left[key] * right[key] for key in common)
    lnorm = math.sqrt(sum(value * value for value in left.values()))
    rnorm = math.sqrt(sum(value * value for value in right.values()))
    return dot / (lnorm * rnorm) if lnorm and rnorm else 0.0


def hybrid_score(components: Mapping[str, float], weights: Mapping[str, float] | None = None) -> float:
    configured = weights or DEFAULT_WEIGHTS
    positive = sum(
        configured.get(name, 0.0) * value
        for name, value in components.items()
        if not name.endswith("_penalty")
    )
    negative = sum(
        configured.get(name, 0.0) * value
        for name, value in components.items()
        if name.endswith("_penalty")
    )
    return positive - negative
