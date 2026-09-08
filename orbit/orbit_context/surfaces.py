"""Detect instruction surfaces by filename convention, and read them.

Phase 1 detects one surface kind. Later tickets add skill packages, agent
definitions, hooks and MCP configs; they extend the tables below, not this
module's shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

INSTRUCTION_SURFACE = "instruction-surface"

# Matched on the file's basename.
SURFACE_BASENAMES: dict[str, str] = {
    "CLAUDE.md": INSTRUCTION_SURFACE,
    "AGENTS.md": INSTRUCTION_SURFACE,
    "GEMINI.md": INSTRUCTION_SURFACE,
    ".cursorrules": INSTRUCTION_SURFACE,
}

# Matched on the repository-relative path.
SURFACE_RELATIVE_PATHS: dict[str, str] = {
    ".github/copilot-instructions.md": INSTRUCTION_SURFACE,
}

# Directories never walked. `.git` is Orbit's own convention; the rest hold
# vendored trees whose surfaces belong to another estate.
PRUNED_DIRECTORIES = frozenset(
    {".git", "node_modules", "target", "vendor", "__pycache__", ".venv", "venv"}
)

# A surface larger than this is recorded with a reason instead of read.
MAX_SURFACE_BYTES = 5 * 1024 * 1024

# Reasons written to the `reason` column and to the JSON statistics. Kept
# outside the constrained vocabulary (see orbit/tests/test_vocabulary.py).
REASON_INVALID_UTF8 = "invalid_utf8"
REASON_OVERSIZE = "oversize"
REASON_READ_ERROR = "read_error"
REASON_NOT_A_FILE = "not_a_file"
REASON_OUTSIDE_REPOSITORY = "outside_indexed_repository"

INDEXED = ""


def surface_kind(relative_path: str) -> str | None:
    """The surface kind for a repository-relative path, or None."""
    posix = PurePosixPath(relative_path)
    kind = SURFACE_RELATIVE_PATHS.get(posix.as_posix())
    if kind is not None:
        return kind
    return SURFACE_BASENAMES.get(posix.name)


@dataclass(frozen=True)
class Candidate:
    """A path whose name says it is a surface, before it has been read."""

    relative_path: str
    absolute_path: Path
    kind: str


def walk_repo(repo_root: Path, nested_repos: list[Path] | None = None) -> list[Candidate]:
    """Every surface candidate in one repository, in sorted path order.

    Files belonging to a nested repository are left to that repository.
    """
    nested = {p.resolve() for p in (nested_repos or [])}
    candidates: list[Candidate] = []
    stack = [repo_root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_symlink():
                continue
            if entry.is_dir():
                if entry.name in PRUNED_DIRECTORIES:
                    continue
                if entry.resolve() in nested:
                    continue
                stack.append(entry)
                continue
            relative = entry.relative_to(repo_root).as_posix()
            kind = surface_kind(relative)
            if kind is not None:
                candidates.append(Candidate(relative, entry, kind))
    return sorted(candidates, key=lambda c: c.relative_path)


@dataclass(frozen=True)
class Reading:
    """The outcome of reading one candidate."""

    size_bytes: int
    reason: str
    detail: str = ""
    errored: bool = False

    @property
    def indexed(self) -> bool:
        return self.reason == INDEXED


def read_candidate(candidate: Candidate) -> Reading:
    """Read a candidate, classifying anything that stops it being indexed.

    A candidate that cannot be read still becomes a row: coverage is a property
    of the record, not a footnote.
    """
    path = candidate.absolute_path
    try:
        stat = path.stat()
    except OSError as error:
        return Reading(0, REASON_READ_ERROR, str(error), errored=True)

    if not path.is_file():
        return Reading(0, REASON_NOT_A_FILE, "", errored=False)

    size = stat.st_size
    if size > MAX_SURFACE_BYTES:
        return Reading(size, REASON_OVERSIZE, f"{size} bytes", errored=False)

    try:
        raw = path.read_bytes()
    except OSError as error:
        return Reading(size, REASON_READ_ERROR, str(error), errored=True)

    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as error:
        return Reading(size, REASON_INVALID_UTF8, f"byte offset {error.start}", errored=False)

    return Reading(size, INDEXED)


def walk_outside_repos(root: Path, repo_roots: list[Path]) -> list[Candidate]:
    """Surface candidates under ``root`` that belong to no repository.

    They carry no branch or commit, so they cannot become rows. They are
    reported instead, because a surface that is present but unindexed must not
    read as a surface that is absent.
    """
    repos = {p.resolve() for p in repo_roots}
    candidates: list[Candidate] = []
    stack = [root]
    while stack:
        current = stack.pop()
        if current.resolve() in repos:
            continue
        try:
            entries = sorted(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_symlink():
                continue
            if entry.is_dir():
                if entry.name in PRUNED_DIRECTORIES:
                    continue
                stack.append(entry)
                continue
            relative = entry.relative_to(root).as_posix()
            kind = surface_kind(relative)
            if kind is not None:
                candidates.append(Candidate(relative, entry, kind))
    return sorted(candidates, key=lambda c: c.relative_path)
