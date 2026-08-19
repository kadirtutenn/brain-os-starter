"""Deterministic Brain OS runtime.

This package deliberately has no model, provider, or network dependency.
Markdown in the Brain Store is authoritative; runtime state is rebuildable.
"""

from .config import BrainPaths, resolve_paths

__all__ = ["BrainPaths", "resolve_paths"]
