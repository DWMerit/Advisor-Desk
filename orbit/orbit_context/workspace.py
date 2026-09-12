"""Repository discovery and git state, matching orbit-local's conventions.

Two conventions here are load-bearing. Get either wrong and joins to Orbit's
own tables return zero rows silently rather than erroring:

``traversal_path``
    The empty string in the local graph. Orbit's local linker pushes ``""`` for
    every row (crates/code-graph/src/v2/linker/graph.rs); repositories are told
    apart by ``project_id``, not by traversal path.

``project_id``
    Rust's ``DefaultHasher`` (SipHash-1-3, zero keys) over the canonical
    repository path, sign bit cleared
    (crates/orbit-local/src/workspace.rs::project_id_from_path). Reproduced
    below so a repository Orbit has not indexed still gets the id Orbit would
    give it. Pinned by test vectors in orbit/tests/test_workspace.py.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

# Orbit's local graph writes the empty string for every traversal_path.
LOCAL_TRAVERSAL_PATH = ""

_MASK64 = (1 << 64) - 1


def _rotl(value: int, bits: int) -> int:
    return ((value << bits) | (value >> (64 - bits))) & _MASK64


def _siphash_1_3(data: bytes) -> int:
    """SipHash-1-3 with zero keys — Rust's std ``DefaultHasher``."""
    v0 = 0x736F6D6570736575
    v1 = 0x646F72616E646F6D
    v2 = 0x6C7967656E657261
    v3 = 0x7465646279746573

    def round_() -> None:
        nonlocal v0, v1, v2, v3
        v0 = (v0 + v1) & _MASK64
        v1 = _rotl(v1, 13) ^ v0
        v0 = _rotl(v0, 32)
        v2 = (v2 + v3) & _MASK64
        v3 = _rotl(v3, 16) ^ v2
        v0 = (v0 + v3) & _MASK64
        v3 = _rotl(v3, 21) ^ v0
        v2 = (v2 + v1) & _MASK64
        v1 = _rotl(v1, 17) ^ v2
        v2 = _rotl(v2, 32)

    length = len(data)
    offset = 0
    while length - offset >= 8:
        block = int.from_bytes(data[offset : offset + 8], "little")
        v3 ^= block
        round_()
        v0 ^= block
        offset += 8

    tail = data[offset:]
    block = ((length & 0xFF) << 56) | int.from_bytes(tail + b"\x00" * (8 - len(tail)), "little")
    v3 ^= block
    round_()
    v0 ^= block

    v2 ^= 0xFF
    for _ in range(3):
        round_()

    return (v0 ^ v1 ^ v2 ^ v3) & _MASK64


def project_id_from_path(path: str) -> int:
    """The project id orbit-local derives for a canonical repository path.

    Rust hashes a ``str`` as its UTF-8 bytes followed by a ``0xff`` terminator.
    """
    return _siphash_1_3(path.encode("utf-8") + b"\xff") & 0x7FFF_FFFF_FFFF_FFFF


def stable_id(*parts: object) -> int:
    """A deterministic positive id for a row, so re-indexing reproduces it."""
    joined = "\x00".join(str(part) for part in parts)
    return _siphash_1_3(joined.encode("utf-8") + b"\xff") & 0x7FFF_FFFF_FFFF_FFFF


class GitError(Exception):
    """git could not answer for a repository."""


@dataclass(frozen=True)
class Repository:
    root: Path
    project_id: int
    branch: str
    commit_sha: str

    @property
    def name(self) -> str:
        return self.root.name


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed in {root}: {result.stderr.strip()}")
    return result.stdout.strip()


def git_info(root: str | Path) -> Repository:
    """Read branch and commit for one repository."""
    canonical = Path(root).resolve()
    branch = _git(canonical, "rev-parse", "--abbrev-ref", "HEAD")
    commit_sha = _git(canonical, "rev-parse", "HEAD")
    return Repository(
        root=canonical,
        project_id=project_id_from_path(str(canonical)),
        branch=branch,
        commit_sha=commit_sha,
    )


def is_git_repo(path: Path) -> bool:
    git = path / ".git"
    return git.is_dir() or git.is_file()


def discover_repos(root: str | Path) -> list[Path]:
    """Every git repository at or under ``root``, outermost first.

    Nested repositories are returned too; ``walk_repo`` keeps their files out of
    the enclosing repository's rows.
    """
    start = Path(root).resolve()
    found: list[Path] = []
    if is_git_repo(start):
        found.append(start)
    stack = [start]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(p for p in current.iterdir() if p.is_dir() and not p.is_symlink())
        except OSError:
            continue
        for entry in entries:
            if entry.name == ".git":
                continue
            if is_git_repo(entry):
                found.append(entry)
            stack.append(entry)
    return sorted(set(found), key=lambda p: (len(p.parts), p))
