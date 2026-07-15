"""Contract tests for mcp/core.py.

These exercise core.py purely through the public API declared in the shared
contract (import from ``core``). They never touch the real vault: the ``vault``
fixture (see conftest.py) hands over an isolated, git-init-ed copy.
"""
import os
import subprocess

import pytest

import core
from conftest import FIXTURE_VAULT, count_files


# --------------------------------------------------------------------------- #
# read side
# --------------------------------------------------------------------------- #
def test_get_dashboard_verbatim(vault):
    got = core.get_dashboard(vault)
    with open(os.path.join(vault, "Dashboard.md"), encoding="utf-8") as f:
        expected = f.read()
    assert got == expected


def test_get_index_lists_dirs(vault):
    out = core.get_index(vault)
    assert isinstance(out, str)
    assert "Lessons" in out
    assert "Skills" in out


def test_find_concept_ranks_frontmatter_match_above_body_match(vault):
    # "sprocket" is in example-skill.md's frontmatter (description + tags) but
    # only in sample.md's body, so the skill must outrank the note.
    results = core.find_concept(vault, "sprocket")
    assert results, "expected at least the two seeded matches"

    ids = [r["id"] for r in results]
    skill = next(i for i in ids if i.endswith("example-skill.md"))
    note = next(i for i in ids if i.endswith("sample.md"))
    assert ids.index(skill) < ids.index(note)

    # results are ranked most-relevant first (the internal score is not
    # exposed by contract), so the frontmatter match must be at the top.
    assert results[0]["id"].endswith("example-skill.md")


def test_get_concept_parses_frontmatter_and_body(vault):
    c = core.get_concept(vault, "Skills/example-skill.md")
    assert c["id"] == "Skills/example-skill.md"
    assert c["type"] == "Skill"
    assert c["description"] == "How to assemble a sprocket workflow from generic parts"
    assert isinstance(c["tags"], list)
    assert "sprocket" in c["tags"]
    assert "Assemble a Workflow" in c["body"]
    # the frontmatter delimiters must not leak into the parsed body
    assert not c["body"].lstrip().startswith("---")


# --------------------------------------------------------------------------- #
# new_lesson: append-only, never creates a file
# --------------------------------------------------------------------------- #
def test_new_lesson_appends_and_does_not_create_file(vault, author):
    problems = os.path.join(vault, "Lessons", "demo", "problems.md")
    before_count = count_files(vault)

    core.new_lesson(
        vault,
        area="demo",
        slug="flaky-widget",
        content="Widgets intermittently fail to initialize under load.",
        keywords=["widget", "flaky", "init"],
        author=author,
    )

    # No new file anywhere in the vault (append + triple update only).
    assert count_files(vault) == before_count

    with open(problems, encoding="utf-8") as f:
        body = f.read()
    assert "## existing" in body           # pre-existing heading preserved
    assert "## flaky-widget" in body        # new heading appended
    assert "Widgets intermittently fail" in body

    with open(os.path.join(vault, "Lessons", "INDEX.md"), encoding="utf-8") as f:
        index = f.read()
    assert "widget" in index.lower()        # keyword line added to INDEX


def test_new_lesson_unknown_area_raises(vault, author):
    with pytest.raises(core.OKFValidationError):
        core.new_lesson(
            vault,
            area="does-not-exist",
            slug="whatever",
            content="Body text.",
            keywords=["x"],
            author=author,
        )


# --------------------------------------------------------------------------- #
# gates
# --------------------------------------------------------------------------- #
def test_secret_gate_flags_password():
    with pytest.raises(core.SecretDetected):
        core.secret_gate("password: hunter2")


def test_secret_gate_allows_clean_text():
    # a benign frontmatter+body block must pass untouched
    core.secret_gate("type: Skill\ndescription: \"safe\"\n\nnothing secret here")


# --------------------------------------------------------------------------- #
# rules: proposal queue + admin-only approval
# --------------------------------------------------------------------------- #
def test_new_rule_enqueues_proposal_without_touching_rules(vault, author):
    proposal_id = core.new_rule(
        vault,
        text="Always verify output before shipping.",
        rationale="Reduces avoidable regressions.",
        author=author,
    )
    assert proposal_id

    proposals_dir = os.path.join(vault, "mcp_proposals")
    assert os.path.isdir(proposals_dir)
    assert os.listdir(proposals_dir), "expected a queued proposal file"

    # the live rules surface must be untouched by a mere proposal
    assert not os.path.isdir(os.path.join(vault, "rules"))


def test_approve_proposal_requires_admin(vault, author):
    proposal_id = core.new_rule(
        vault,
        text="A proposed rule.",
        rationale="Because.",
        author=author,
    )
    with pytest.raises(core.AuthzError):
        core.approve_proposal(vault, proposal_id, is_admin=False)


# --------------------------------------------------------------------------- #
# write pipeline -> git commit authored by the caller
# --------------------------------------------------------------------------- #
def test_write_creates_commit_with_caller_author(vault, author):
    before = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=vault, check=True, capture_output=True, text=True,
    ).stdout.strip()

    core.new_lesson(
        vault,
        area="demo",
        slug="committed-lesson",
        content="A lesson that should land as a git commit.",
        keywords=["commit", "author"],
        author=author,
    )

    after = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=vault, check=True, capture_output=True, text=True,
    ).stdout.strip()
    assert int(after) == int(before) + 1

    name, email = subprocess.run(
        ["git", "log", "-1", "--format=%an%n%ae"],
        cwd=vault, check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    assert name == author["name"]
    assert email == author["email"]
