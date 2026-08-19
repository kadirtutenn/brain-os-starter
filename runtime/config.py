"""Canonical Brain Store/runtime/cache path resolution."""

from __future__ import annotations

import os
import warnings
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BrainPaths:
    store: Path
    runtime: Path
    cache: Path

    @property
    def retrieval_db(self) -> Path:
        return self.runtime / "retrieval.sqlite"


def resolve_store_path(explicit: str | os.PathLike[str] | None = None) -> Path:
    """Resolve the canonical Brain Store path.

    ``BRAIN_VAULT_PATH`` remains a temporary, warning-emitting compatibility
    alias. An explicit value always wins, followed by ``BRAIN_STORE_PATH``.
    """
    if explicit:
        return Path(explicit).expanduser().resolve()
    canonical = os.environ.get("BRAIN_STORE_PATH")
    if canonical:
        return Path(canonical).expanduser().resolve()
    legacy = os.environ.get("BRAIN_VAULT_PATH")
    if legacy:
        warnings.warn(
            "BRAIN_VAULT_PATH is deprecated; use BRAIN_STORE_PATH",
            DeprecationWarning,
            stacklevel=2,
        )
        return Path(legacy).expanduser().resolve()
    return Path.home().joinpath("Brain").resolve()


def resolve_paths(
    store: str | os.PathLike[str] | None = None,
    runtime: str | os.PathLike[str] | None = None,
    cache: str | os.PathLike[str] | None = None,
) -> BrainPaths:
    runtime_path = Path(
        runtime or os.environ.get("BRAIN_RUNTIME_PATH") or "~/.brain-runtime"
    ).expanduser().resolve()
    cache_path = Path(
        cache or os.environ.get("BRAIN_CACHE_PATH") or runtime_path / "cache"
    ).expanduser().resolve()
    return BrainPaths(resolve_store_path(store), runtime_path, cache_path)
