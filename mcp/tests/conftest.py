"""Shared pytest fixtures for the mcp/core.py test suite.

Every write-path test runs against a throwaway copy of ``fixture_vault`` that is
``git init``-ed inside pytest's tmp dir, so commits made by core.py never touch
the real repository.
"""
import os
import shutil
import subprocess
import sys

import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
MCP_DIR = os.path.dirname(TESTS_DIR)
FIXTURE_VAULT = os.path.join(TESTS_DIR, "fixture_vault")

# Make ``import core`` resolve to mcp/core.py regardless of the invocation cwd.
if MCP_DIR not in sys.path:
    sys.path.insert(0, MCP_DIR)


def _git(cwd, *args):
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


@pytest.fixture
def vault(tmp_path):
    """Copy the fixture vault into an isolated tmp dir and git-init it.

    Yields the vault root as a ``str`` (the address type core.py expects).
    """
    dst = tmp_path / "vault"
    shutil.copytree(FIXTURE_VAULT, dst)

    _git(dst, "init", "-q")
    # A committer identity so core.py's ``git commit`` never fails; this is the
    # committer, distinct from the per-call --author the write functions set.
    _git(dst, "config", "user.name", "Test Committer")
    _git(dst, "config", "user.email", "committer@example.com")
    _git(dst, "config", "commit.gpgsign", "false")
    _git(dst, "add", "-A")
    _git(dst, "commit", "-q", "-m", "seed fixture vault")

    yield str(dst)


@pytest.fixture
def author():
    """A generic authenticated caller identity."""
    return {"name": "Alice Example", "email": "alice@example.com"}


def count_files(root):
    """Count regular files under ``root``, ignoring the .git directory."""
    total = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        total += len(filenames)
    return total
