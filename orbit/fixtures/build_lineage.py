#!/usr/bin/env python3
"""Build a throwaway two-repository estate that carries both recognition paths.

Separate from ``build_estate`` on purpose. That fixture carries 305 tests, many
of them asserting absolute counts, and re-baselining them to make room for a new
shape risks switching off a test that was catching something. Spec 0002 s7 calls
this out as a blast-radius decision rather than a seam decision: same seam,
second builder.

Two repositories, side by side, because the two recognition paths have to be
shown not to interfere:

``ladder``
    The clone-lineage shape. A book directory of three rungs, a second book at
    two, a rung word with no base rung beside it, a rule workbench, a
    documentation tree, and a directory that declares itself only in part.
    No vendor-named file anywhere in it -- phase 1 finds nothing here at all.

    The workbench names its rungs ``mini.md`` and ``nano.md``, with no stem in
    front of them. That is the second naming shape this one repository uses,
    and the ladder rule does not key on it -- which is here to be asserted
    rather than to be discovered later on a repository nobody has looked at.
``vendor``
    The shape phase 1 was built for: ``CLAUDE.md``, ``AGENTS.md``, an agent
    definition. Its ``CLAUDE.md`` also opens with a directive heading, which is
    the case where the two paths meet on one file.

    python3 orbit/fixtures/build_lineage.py            # into a temp dir
    python3 orbit/fixtures/build_lineage.py /some/dir  # into a named dir

Prints the estate root.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


def _rules(title: str, body: str) -> str:
    """A rule file, opening the way the corpus opens every one of them."""
    return f"# OBEY {title}\n\n## Decision rules\n\n{body}\n"


def _prose(title: str, body: str) -> str:
    """A Markdown file that declares nothing about itself."""
    return f"# {title}\n\n{body}\n"


# The three rungs of one ladder, distinct bytes at each rung so byte identity
# has nothing to find that this fixture did not put there.
LADDER = {
    "refactoring/refactoring.md": _rules(
        "Refactoring",
        "- Preserve observable behaviour while the structure moves.\n"
        "- Work in steps small enough to build, test and review.\n"
        "- Establish a safety net before a risky move.",
    ),
    "refactoring/refactoring.mini.md": _rules(
        "Refactoring",
        "- Preserve observable behaviour while the structure moves.\n"
        "- Work in steps small enough to build, test and review.",
    ),
    "refactoring/refactoring.nano.md": _rules(
        "Refactoring", "- Preserve observable behaviour; move in small steps."
    ),
}

# A second book, at two rungs rather than three. Not a defect and not a gap:
# how many rungs a book carries is an observation, and a ladder of two is
# reported as two. It is here so the count is exercised at a height other than
# the one every book in this estate happens to share.
SHORT_LADDER = {
    "clean-code/clean-code.md": _rules(
        "Clean Code",
        "- A function does one thing, at one level of abstraction.\n"
        "- A name that needs a comment is a name that has not been chosen.\n"
        "- Leave the code cleaner than the state it was found in.",
    ),
    "clean-code/clean-code.nano.md": _rules(
        "Clean Code", "- One thing per function; name it so no comment is needed."
    ),
}

# A rung word with no base rung beside it. The name says `mini`, and nothing in
# the directory is named by the stem alone, so there is no second end for an
# edge and no ladder to walk. Counted and named rather than dropped: a rung the
# estate wrote and this tool could not attach is not the same as no rung.
UNATTACHED_RUNG = {
    "drafts/takeoff.mini.md": _rules(
        "Takeoff", "- Count from the marked-up set, never from the schedule alone."
    ),
}

# The workbench. Nine files declare themselves; two do not, and are governance
# all the same -- they are the instructions for producing the other nine.
WORKBENCH_BOOKS = ("refactoring", "clean-code", "release-it")

WORKBENCH_PROSE = {
    "_rule-workbench/PROCESS.md": _prose(
        "Rule Compression Process",
        "Compressed rule sets are decision-equivalent to the full source,\n"
        "not sentence-equivalent.",
    ),
    "_rule-workbench/RELEASE.md": _prose(
        "Release Process",
        "Rebuild every rung, then check the ladder against its traceability.",
    ),
}

# A documentation tree. Prose about the rules, and not a rule.
DOCS = {
    "docs/USAGE.md": _prose(
        "Usage", "Three versions of every rule set ship: full, mini and nano."
    ),
    "docs/compatibility/one.md": _prose("Refactoring vs Clean Code", "Complementary."),
    "docs/compatibility/two.md": _prose("Refactoring vs Release It", "Complementary."),
    "docs/compatibility/three.md": _prose("Clean Code vs Release It", "Complementary."),
}

# Two of three declare themselves: under the share a directory needs to become a
# corpus. The two are still recognised, because each says so itself. The third
# is not, and that is the whole point of it.
PART_DECLARED = {
    "notes/one.md": _rules("Estimating", "- Dimensions are millimetres."),
    "notes/two.md": _rules("Takeoff", "- Quantities come from the marked-up set."),
    "notes/three.md": _prose("Scratch", "Half a thought, kept for later."),
}

# The vendor repository. Its CLAUDE.md carries a directive heading as well as a
# vendor name, which is the one file in the estate both paths reach.
VENDOR_CLAUDE = _rules(
    "Estimating rules", "- Anchor spacing is stated on the drawing, never assumed."
)

SKILL_DEFINITION = (
    "---\n"
    "name: {name}\n"
    "description: Reads the {name} schedule off the section.\n"
    "---\n"
    "\n"
    "# {title}\n"
    "\n"
    "Quantities come from the marked-up set.\n"
)

AGENT_DEFINITION = (
    "---\n"
    "name: takeoff-reviewer\n"
    "description: Checks a takeoff against the marked-up set.\n"
    "---\n"
    "\n"
    "# Takeoff reviewer\n"
    "\n"
    "Read the section, not the elevation.\n"
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _init_repo(root: Path, branch: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "--initial-branch", branch)
    _git(root, "config", "user.email", "fixture@example.invalid")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "fixture lineage")


def build(destination: str | Path | None = None) -> Path:
    """Create the estate and return its root."""
    root = (
        Path(destination)
        if destination
        else Path(tempfile.mkdtemp(prefix="orbit-context-lineage-"))
    )
    root.mkdir(parents=True, exist_ok=True)

    _build_ladder(root / "ladder")
    _build_vendor(root / "vendor")
    return root


def _build_ladder(root: Path) -> None:
    """A repository whose governance carries no vendor name anywhere."""
    for relative, text in {**LADDER, **SHORT_LADDER, **UNATTACHED_RUNG}.items():
        _write(root / relative, text)

    for book in WORKBENCH_BOOKS:
        _write(root / "_rule-workbench" / book / "mini.md",
               _rules(book, f"- The mini rung of {book}, kept decision-equivalent."))
        _write(root / "_rule-workbench" / book / "nano.md",
               _rules(book, f"- The nano rung of {book}, always-on reminders."))
        _write(root / "_rule-workbench" / book / "traceability.md",
               _rules(book, f"- Every rung of {book} traces back to the full source."))

    for relative, text in {**WORKBENCH_PROSE, **DOCS, **PART_DECLARED}.items():
        _write(root / relative, text)

    # Not Markdown, and in a directory that is otherwise entirely rules: what
    # the corpus rule counts is Markdown, so this stays a file.
    _write(root / "notes" / "tally.txt", "anchors: 412\n")
    # A root file that declares nothing. The repository root is out of the
    # corpus rule's reach whatever its share, and this is what would come in.
    _write(root / "README.md", _prose("AI agent rules", "Fourteen books, three rungs."))
    _init_repo(root, "main")


def _build_vendor(root: Path) -> None:
    """The shape phase 1 was built for, with a corpus beside it."""
    _write(root / "CLAUDE.md", VENDOR_CLAUDE)
    _write(root / "AGENTS.md", _prose("Agents", "One surface at the root."))
    _write(root / ".claude" / "agents" / "takeoff-reviewer.md", AGENT_DEFINITION)
    _write(root / "docs" / "notes.md", _prose("Notes", "Ordinary documentation."))
    for name in ("alpha", "beta", "gamma"):
        _write(root / "rules" / f"{name}.md",
               _rules(name.title(), f"- The {name} rule, declared in its own heading."))

    # Three vendor-named surfaces and a fourth file that declared nothing. A
    # vendor name is a statement about one file, not about its neighbours, so
    # this directory is not a corpus and the README is not carried in with them.
    for name in ("anchors", "channels", "fixings"):
        _write(root / "skills" / name / "SKILL.md",
               SKILL_DEFINITION.format(name=name, title=name.title()))
    _write(root / "skills" / "README.md",
           _prose("Skills", "What each skill in this directory is for."))
    _init_repo(root, "trunk")


if __name__ == "__main__":
    print(build(sys.argv[1] if len(sys.argv) > 1 else None))
