"""Golden retrieval evaluation without provider tokenizers or AI models."""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from typing import Any

from runtime.retrieval.index import RetrievalIndex


def _matches(ref: str, expected: str) -> bool:
    return ref == expected or ref.startswith(expected) or expected in ref


def evaluate(index: RetrievalIndex, dataset: str | Path) -> dict[str, Any]:
    cases = json.loads(Path(dataset).read_text(encoding="utf-8"))
    results = []
    for case in cases:
        started = time.perf_counter()
        response = index.context(
            case["query"], project=case.get("project", ""),
            agent=case.get("agent", "eval"), mode=case.get("mode", "compact"),
            max_context_units=case.get("max_context_units", 800),
            caller_id="evaluation:" + case.get("id", "case"),
        )
        refs = response["refs"]
        expected = case.get("expected_refs", [])
        forbidden = case.get("forbidden_refs", [])
        hit_positions = [
            position for position, ref in enumerate(refs, 1)
            if any(_matches(ref, target) for target in expected)
        ]
        expected_hits = sum(
            1 for target in expected if any(_matches(ref, target) for ref in refs)
        )
        relevant_refs = sum(1 for ref in refs if any(_matches(ref, target) for target in expected))
        forbidden_hits = sum(1 for ref in refs if any(_matches(ref, target) for target in forbidden))
        hashes = [item["content_hash"] for item in response["fingerprints"] + response["context_chunks"]]
        results.append({
            "id": case.get("id", ""),
            "recall_at_k": expected_hits / max(1, len(expected)),
            "precision_at_k": max(0, relevant_refs - forbidden_hits) / max(1, len(refs)),
            "mrr": 1 / min(hit_positions) if hit_positions else 0,
            "context_returned": response["coverage"]["returned_context_units"],
            "duplicate_context": len(hashes) - len(set(hashes)),
            "fingerprint_hit_rate": len(response["fingerprints"]) / max(1, len(refs)),
            "deep_read_rate": 1.0 if case.get("mode") == "deep" else 0.0,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "refs": refs,
        })
    metric_names = (
        "recall_at_k", "precision_at_k", "mrr", "context_returned",
        "duplicate_context", "fingerprint_hit_rate", "deep_read_rate", "latency_ms",
    )
    aggregate = {
        name: round(statistics.fmean(result[name] for result in results), 4)
        for name in metric_names
    } if results else {}
    return {"case_count": len(results), "aggregate": aggregate, "cases": results}
