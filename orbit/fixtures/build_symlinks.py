#!/usr/bin/env python3
"""Build a throwaway repository whose governance is exposed through symlinks.

A third builder rather than a change to ``build_estate`` or ``build_lineage``.
Both carry tests asserting absolute counts, and ticket 15 moves the walk itself:
folding symlinks into either fixture would re-baseline counts that ticket 10, 11
and 12 reconciled by hand. Spec 0002 s7's rule, applied a second time -- same
seam, third builder.

One repository, holding every shape ticket 15 has a rule for:

``full.md``
    Four books, each exposing its canonical source under a working name, the
    way ``_rule-workbench/<book>/full.md`` does on the real estate. Each is a
    link the walk lists and never reads, and each is named by a pointer written
    in the ``traceability.md`` beside it.

the corpus trap
    ``_rule-workbench`` holds 12 declared Markdown files of 15 that were read --
    80%, over the 75% share -- and the four links would take it to 12 of 19,
    under it. The three files recognised only by that share are exactly the
    three that would be lost, which is what makes the trap measurable rather
    than argued.

``CLAUDE.md``
    A vendor-named link to ``AGENTS.md``. A name is readable without opening the
    file, so this is a candidate; it becomes a row carrying the reason it was
    not read, the way an oversize surface does.

``clean-code/clean-code.mini.md``
    A rung word carried by a link, pointing at the base rung in its own
    directory. Followed, it would be a second rung of that ladder *and* a
    byte-identical pair with its own target. Listed, it is neither.

``.claude/agents/reviewer.mini.md``
    A vendor name and a rung word on the same link, beside the agent definition
    it names. This is the route by which a link could still reach a ladder: a
    vendor name makes it a row whatever it is, and the rung rule reads two
    filenames. Both ends of a ladder have to be files that were read.

``.claude/commands/audit.md``
    The other way round: a real rung word beside a **base rung** that is a
    link. The estate did write that rung and this tool cannot attach it, which
    is a different fact from the case above and is counted as one.

``mirror``
    A link to a directory. Listed once, never descended into: descending would
    walk one tree twice and count one file as two.

``node_modules``
    A link wearing a pruned name. Those names are refused by name, before
    anything asks what the entry is: a link named `node_modules` names a tree
    whose surfaces belong to another estate whether or not it is a directory,
    and telling which would mean following it.

``docs/missing.md``
    A link whose target is not there. Nothing about listing a link needs its
    target, so it is a row of the walk like any other and no error.

    python3 orbit/fixtures/build_symlinks.py            # into a temp dir
    python3 orbit/fixtures/build_symlinks.py /some/dir  # into a named dir

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


# The four books, and the rungs each one publishes. `refactoring` is a whole
# ladder; `clean-code` publishes its mini rung as a link rather than a file;
# the other two publish their full rung alone.
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
    "release-it/release-it.md": _rules(
        "Release It", "- Every remote call carries a timeout and a bulkhead."
    ),
    "code-complete/code-complete.md": _rules(
        "Code Complete", "- Build the routine's contract before its body."
    ),
}

BOOKS = ("refactoring", "clean-code", "release-it", "code-complete")

# The one link the walk refuses, and it refuses it by its name.
PRUNED_LINK = "node_modules"

# Links, as `link path -> target`, the target written the way the estate writes
# it: relative to the directory the link sits in.
LINKS = {
    **{f"_rule-workbench/{book}/full.md": f"../../{book}/{book}.md"
       for book in BOOKS},
    # A vendor name on a link. Recognised by that name, never opened.
    "CLAUDE.md": "AGENTS.md",
    # A rung word on a link, naming the base rung in its own directory.
    "clean-code/clean-code.mini.md": "clean-code.md",
    # A rung word on a link that a vendor name reaches, so it is a row -- and
    # still not a rung, because a rung is one of two files holding one book.
    ".claude/agents/reviewer.mini.md": "reviewer.md",
    # And the base rung of a real rung word, as a link. `audit.mini.md` is a
    # rung the estate wrote; its base is a node nothing read.
    ".claude/commands/audit.md": "../../docs/USAGE.md",
    # A link to a directory, and a link to nothing.
    "mirror": "refactoring",
    # A link wearing a pruned name. Refused by the name, not by what it is.
    PRUNED_LINK: "refactoring",
    "docs/missing.md": "../nowhere.md",
}

# The three files in the workbench that declare nothing of their own. They are
# the instructions for producing the rest of it, and the share is the only thing
# that recognises them -- so they are what the trap costs if a file the walk
# never read is allowed to count against the files it did.
WORKBENCH_PROSE = {
    "_rule-workbench/PROCESS.md": _prose(
        "Rule Compression Process",
        "Compressed rule sets are decision-equivalent to the full source.",
    ),
    "_rule-workbench/RELEASE.md": _prose(
        "Release Process",
        "Rebuild every rung, then check the ladder against its traceability.",
    ),
    "_rule-workbench/CHECK_COMPATIBILITY.md": _prose(
        "Compatibility Check",
        "Read both books' decision rules before writing a pair note.",
    ),
}

# The pointer at the link. Written the way the estate writes it -- a bare
# filename in backticks, resolved against the directory the file sits in -- so
# the edge it produces lands on the link's own path.
TRACEABILITY = """# OBEY {book}

## Compression decisions

- `full.md` is the canonical source exposure; the canonical full source was
  not edited.
- Every rung of {book} traces back to that full source.
"""

ROOT_INSTRUCTIONS = _prose(
    "Agents", "One instruction surface at the root, and a link beside it."
)

DOCS = _prose("Usage", "Four books, published at the rungs each one carries.")

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


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _link(path: Path, target: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.symlink_to(target)


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _init_repo(root: Path, branch: str) -> None:
    _git(root, "init", "--initial-branch", branch)
    _git(root, "config", "user.email", "fixture@example.invalid")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "fixture symlinks")


def _workbench_rung(book: str, rung: str) -> str:
    """The workbench copy of one rung: the published bytes where there are any.

    `clean-code` publishes its mini rung as a *link* to its full rung, so the
    bytes that copy matches are the full rung's. The pair is real -- two files
    on disk holding the same bytes -- and the link between them is not a third
    end of it.
    """
    published = PUBLISHED.get(f"{book}/{book}.{rung}.md")
    if published is not None:
        return published
    if f"{book}/{book}.{rung}.md" in LINKS:
        return PUBLISHED[f"{book}/{book}.md"]
    return _rules(book, f"- The {rung} rung of {book}, kept decision-equivalent.")


def build(destination: str | Path | None = None) -> Path:
    """Create the estate and return its root."""
    root = (
        Path(destination)
        if destination
        else Path(tempfile.mkdtemp(prefix="orbit-context-symlinks-"))
    )
    workbench = root / "workbench"
    workbench.mkdir(parents=True, exist_ok=True)

    for relative, text in PUBLISHED.items():
        _write(workbench / relative, text)
    for relative, text in WORKBENCH_PROSE.items():
        _write(workbench / relative, text)
    for book in BOOKS:
        _write(workbench / "_rule-workbench" / book / "mini.md",
               _workbench_rung(book, "mini"))
        _write(workbench / "_rule-workbench" / book / "nano.md",
               _workbench_rung(book, "nano"))
        _write(workbench / "_rule-workbench" / book / "traceability.md",
               TRACEABILITY.format(book=book))
    _write(workbench / "AGENTS.md", ROOT_INSTRUCTIONS)
    _write(workbench / "docs" / "USAGE.md", DOCS)
    _write(workbench / ".claude" / "agents" / "reviewer.md", AGENT_DEFINITION)
    _write(workbench / ".claude" / "commands" / "audit.mini.md",
           _prose("Audit", "Read the rung the workflow can afford."))

    for relative, target in LINKS.items():
        _link(workbench / relative, target)

    _init_repo(workbench, "main")
    return root


if __name__ == "__main__":
    print(build(sys.argv[1] if len(sys.argv) > 1 else None))
