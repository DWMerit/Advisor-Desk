#!/usr/bin/env python3
"""Build one throwaway repository committed in three states, for the comparison.

A fourth builder rather than a change to ``build_estate``, ``build_lineage`` or
``build_symlinks``. All three carry tests asserting absolute counts, and what is
new here is not a shape but a *history*: the same repository at three commits, so
one state can be differenced against another. Spec 0002 s7's rule, applied a
fourth time -- same seam, another builder.

The three states mirror the three the comparison is aimed at, and each is a git
tag so a test names a state the way the command line does:

``c0``
    The corpus, untouched. Three books published at their rungs, a rule
    workbench beside them, and a `full.md` symlink per book exposing the
    published book under a working name. Two names for one file, in the state
    that has no tool in it yet, so the fold is exercised at both ends of the
    comparison rather than only at the end that grew.

``c1``
    ``c0`` plus a tool directory -- Python, a README, tickets and a spec -- and
    one edited line in a file that already existed. **It adds no governance.**
    Nothing under ``tool/`` declares itself a rule file and nothing there is
    vendor-named, so the governance count must not move between ``c0`` and
    ``c1``. That zero is the row the whole comparison turns on, and a fixture
    that could not produce it could not falsify anything.

``c2``
    ``c1`` plus governance: an agent definition, three declared rule files, and
    a vendor-named symlink to a file that is already a surface. The zero above
    has to be shown not to be structural -- a comparison that reports no
    governance added *whatever* was added is not measuring governance -- and
    that link is the case where a state grows a second name for one file rather
    than a second file.

    python3 orbit/fixtures/build_states.py            # into a temp dir
    python3 orbit/fixtures/build_states.py /some/dir  # into a named dir

Prints the repository root.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

# The tags the three states are committed under, in order. Named for the states
# in spec 0002 s3 rather than for what the fixture does, because what a test
# reads them against is that table.
STATES = ("c0", "c1", "c2")


def _rules(title: str, body: str) -> str:
    """A rule file, opening the way the corpus opens every one of them."""
    return f"# OBEY {title}\n\n## Decision rules\n\n{body}\n"


def _prose(title: str, body: str) -> str:
    """A Markdown file that declares nothing about itself."""
    return f"# {title}\n\n{body}\n"


# The published books, each at the rungs it carries. Every one of them declares
# itself, so none of them needs the corpus rule to be recognised.
PUBLISHED = {
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
    "clean-code/clean-code.md": _rules(
        "Clean Code",
        "- A function does one thing, at one level of abstraction.\n"
        "- Leave the code cleaner than the state it was found in.",
    ),
    "clean-code/clean-code.nano.md": _rules(
        "Clean Code", "- One thing per function; name it so no comment is needed."
    ),
    "release-it/release-it.md": _rules(
        "Release It", "- Every remote call carries a timeout and a bulkhead."
    ),
}

BOOKS = ("refactoring", "clean-code", "release-it")

# One link per book, exposing the published book under a working name -- the
# shape `_rule-workbench/<book>/full.md` carries on the real estate. Present in
# every state: two names for one file is a property of the corpus here, not
# something a session added, so a comparison that folded only the state that
# grew would report the fold itself as a change.
WORKBENCH_LINKS = {
    f"_rule-workbench/{book}/full.md": f"../../{book}/{book}.md" for book in BOOKS
}

# The two workbench files that declare nothing of their own. They are what the
# corpus rule is for, and they are here so the corpus path is exercised beside
# the declared one.
WORKBENCH_PROSE = {
    "_rule-workbench/PROCESS.md": _prose(
        "Rule Compression Process",
        "Compressed rule sets are decision-equivalent to the full source.",
    ),
    "_rule-workbench/RELEASE.md": _prose(
        "Release Process",
        "Rebuild every rung, then check the ladder against its traceability.",
    ),
}

TRACEABILITY = """# OBEY {book}

## Compression decisions

- `full.md` is the canonical source exposure; the canonical full source was
  not edited.
- Every rung of {book} traces back to that full source.
"""

ROOT_INSTRUCTIONS = _prose(
    "Agents",
    "Read the rung the workflow can afford before opening the full book.",
)

# Files that are not governance and are not meant to become it. A comparison
# whose file count and whose governance count moved together would be measuring
# one thing twice.
NOT_GOVERNANCE = {
    "README.md": _prose("AI agent rules", "Three books, published at their rungs."),
    "docs/USAGE.md": _prose("Usage", "How to load a rung."),
    "docs/NOTES.md": _prose("Notes", "Ordinary documentation."),
    "LICENSE": "MIT\n",
    ".gitignore": "*.pyc\n",
}

BINARY = "assets/logo.png"

# --- c1: a tool, and no governance ----------------------------------------
#
# Eight files, every one of them under `tool/`. Four are Markdown, so the
# markdown delta and the file delta are different numbers and neither can stand
# in for the other. None of them declares itself a rule file, and `tool/` holds
# no vendor name, so the governance count must not move.
TOOL = {
    "tool/indexer.py": "def index(path):\n    return sorted(path.iterdir())\n",
    "tool/store.py": "def connect(path):\n    return path\n",
    "tool/cli.py": "def main(argv):\n    return 0\n",
    "tool/tests/test_indexer.py": "def test_index():\n    assert True\n",
    "tool/README.md": _prose("The tool", "What it indexes and what it does not."),
    "tool/tickets/01-first.md": _prose(
        "01 - The first ticket", "Index the corpus and count what was found."
    ),
    "tool/tickets/02-second.md": _prose(
        "02 - The second ticket", "Difference two states of one repository."
    ),
    "tool/specs/0001-observation.md": _prose(
        "Spec 0001", "Observation, and what stays an UNKNOWN."
    ),
}

# The line `c1` edits in a file that already existed. Outside `tool/` and it
# changes no count: the real C1 edited two lines of `.gitignore` and nothing
# else outside the directory it added, and a comparison that reported that as a
# change outside the tool would be reporting an edit as an addition.
EDITED = (".gitignore", "*.pyc\n__pycache__/\n")

# --- c2: governance grows --------------------------------------------------
GOVERNANCE = {
    "governance/house.md": _rules(
        "House rules", "- Every change carries the ticket it came from."
    ),
    "governance/review.md": _rules(
        "Review", "- Read the diff against the ticket before the code."
    ),
    "governance/release.md": _rules(
        "Release", "- A release names the states it was measured against."
    ),
}

AGENT_DEFINITION = (
    "---\n"
    "name: reviewer\n"
    "description: Checks a rung against the book it was compressed from.\n"
    "---\n"
    "\n"
    "# Reviewer\n"
    "\n"
    "Read the full rung before the mini one.\n"
)

# A second name for a file that is already a surface, and a vendor name on it so
# it is recognised without being read. Counted once, labelled by the target.
GOVERNANCE_LINK = ("GEMINI.md", "CLAUDE.md")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _link(path: Path, target: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.symlink_to(target)


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _commit(root: Path, message: str, tag: str) -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-m", message)
    _git(root, "tag", tag)


def _build_c0(root: Path) -> None:
    """The corpus, untouched."""
    for relative, text in {**PUBLISHED, **NOT_GOVERNANCE}.items():
        _write(root / relative, text)
    for book in BOOKS:
        _write(root / "_rule-workbench" / book / "mini.md",
               _workbench_rung(book, "mini"))
        _write(root / "_rule-workbench" / book / "nano.md",
               _workbench_rung(book, "nano"))
        _write(root / "_rule-workbench" / book / "traceability.md",
               TRACEABILITY.format(book=book))
    for relative, text in WORKBENCH_PROSE.items():
        _write(root / relative, text)
    for relative, target in WORKBENCH_LINKS.items():
        _link(root / relative, target)
    _write(root / "CLAUDE.md", ROOT_INSTRUCTIONS)
    (root / Path(BINARY).parent).mkdir(parents=True, exist_ok=True)
    (root / BINARY).write_bytes(b"\x89PNG\r\n\x1a\n" + bytes(range(64)))


def _build_c1(root: Path) -> None:
    """A tool, and no governance."""
    for relative, text in TOOL.items():
        _write(root / relative, text)
    _write(root / EDITED[0], EDITED[1])


def _build_c2(root: Path) -> None:
    """Governance grows, including a second name for one file."""
    for relative, text in GOVERNANCE.items():
        _write(root / relative, text)
    _write(root / ".claude" / "agents" / "reviewer.md", AGENT_DEFINITION)
    _link(root / GOVERNANCE_LINK[0], GOVERNANCE_LINK[1])


def _workbench_rung(book: str, rung: str) -> str:
    """The workbench copy of one rung: the published bytes where there are any.

    That is the workbench-to-published pairing ticket 12 measures. Where a book
    publishes no such rung the workbench copy is the only copy of itself and
    pairs with nothing, so byte identity has something to find and something to
    leave alone.
    """
    published = PUBLISHED.get(f"{book}/{book}.{rung}.md")
    if published is not None:
        return published
    return _rules(book, f"- The {rung} rung of {book}, kept decision-equivalent.")


def build(destination: str | Path | None = None) -> Path:
    """Create the repository at all three states and return its root."""
    root = (
        Path(destination)
        if destination
        else Path(tempfile.mkdtemp(prefix="orbit-context-states-"))
    )
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "--initial-branch", "main")
    _git(root, "config", "user.email", "fixture@example.invalid")
    _git(root, "config", "user.name", "Fixture")

    _build_c0(root)
    _commit(root, "the corpus", STATES[0])
    _build_c1(root)
    _commit(root, "a tool, and no governance", STATES[1])
    _build_c2(root)
    _commit(root, "governance grows", STATES[2])
    return root


if __name__ == "__main__":
    print(build(sys.argv[1] if len(sys.argv) > 1 else None))
