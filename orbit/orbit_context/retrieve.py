"""Read a clause back out of the file it came from.

The graph stores no clause text. A clause row carries a path and a byte span,
and this is the path that turns them back into bytes: find the row by ``fqn``,
open the file, seek to ``start_byte``, read to ``end_byte``.

Three contracts hold here, and each exists because the alternative is silently
wrong rather than merely unhelpful.

**An address identifies one clause.** An ``fqn`` is built from the estate's own
headings, so two siblings carrying identical text under identical headings share
one. That is a fact about the file, not a collision to paper over, so the fqn is
a *lookup key* and the row ``id`` is the *address* -- the same split GitLab Orbit
makes between ``Definition.fqn`` and ``Definition.id``. Resolving a non-unique
fqn raises ``AmbiguousAddress`` listing candidate ids; it never picks one and
never returns several concatenated.

**Offsets are only valid against the file they were recorded from.** Retrieval
compares the file's current SHA-256 against the digest stored at index time and
refuses on a mismatch. Slicing a changed file at old offsets returns bytes that
look like a clause and are not one.

**A parent's span includes its descendants.** ``#Rules`` covers the bytes of
``#Rules#Estimating`` and everything under it, matching GitLab, whose class
definition spans its methods. ``read()`` therefore returns the whole subtree;
``read_own()`` returns the parent's own text with descendant spans removed, for
callers that want a bounded load rather than a section.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import duckdb

from . import store
from .workspace import Repository, git_info


class RetrievalError(Exception):
    """A clause could not be read back from its file."""


class StaleIndex(RetrievalError):
    """The file changed after indexing, so the recorded offsets mean nothing."""


class AmbiguousAddress(RetrievalError):
    """An fqn matched more than one clause. Carries the candidates."""

    def __init__(self, fqn: str, candidates: "list[Located]"):
        self.fqn = fqn
        self.candidates = candidates
        super().__init__(
            f"{fqn!r} matches {len(candidates)} clauses; address one by id"
        )


@dataclass(frozen=True)
class Located:
    """One clause row, resolved against the repository it belongs to."""

    repo_root: Path
    clause_id: int
    surface_path: str
    fqn: str
    clause_type: str
    start_line: int
    end_line: int
    start_byte: int
    end_byte: int
    indexed_sha256: str = ""

    @property
    def absolute_path(self) -> Path:
        return self.repo_root / self.surface_path

    @property
    def locator(self) -> str:
        return (
            f"{self.surface_path}:{self.start_line}-{self.end_line} "
            f"bytes {self.start_byte}-{self.end_byte} {self.clause_type} "
            f"id={self.clause_id}"
        )

    def assert_current(self) -> None:
        """Refuse to slice a file that is not the one the offsets came from."""
        path = self.absolute_path
        try:
            current = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as error:
            raise RetrievalError(f"{path}: {error}") from None
        if not self.indexed_sha256:
            raise StaleIndex(
                f"{self.surface_path} was indexed without a digest; re-index "
                f"before reading clauses from it"
            )
        if current != self.indexed_sha256:
            raise StaleIndex(
                f"{self.surface_path} has changed since it was indexed "
                f"({self.indexed_sha256[:12]} -> {current[:12]}); the recorded "
                f"offsets do not describe this file. Re-index to move them."
            )

    def read(self) -> bytes:
        """The file's own bytes for this span, descendants included.

        Refuses if the file changed after indexing.
        """
        self.assert_current()
        path = self.absolute_path
        try:
            with open(path, "rb") as handle:
                handle.seek(self.start_byte)
                found = handle.read(self.end_byte - self.start_byte)
        except OSError as error:
            raise RetrievalError(f"{path}: {error}") from None
        if len(found) < self.end_byte - self.start_byte:
            raise RetrievalError(
                f"{path} is now {path.stat().st_size} bytes, shorter than the "
                f"recorded span {self.start_byte}-{self.end_byte}; re-index to move "
                f"the offsets"
            )
        return found

    def read_own(self, descendants: "list[Located]") -> bytes:
        """This clause's own bytes, with descendant spans removed.

        The bounded-load form: a heading section without the sections nested
        under it. Gaps are joined as they fall, so what comes back is still the
        file's own bytes, just not contiguous ones.
        """
        whole = self.read()
        inner = sorted(
            (d for d in descendants
             if d.clause_id != self.clause_id
             and d.start_byte >= self.start_byte and d.end_byte <= self.end_byte),
            key=lambda d: d.start_byte,
        )
        out, cursor = bytearray(), self.start_byte
        for child in inner:
            if child.start_byte > cursor:
                out += whole[cursor - self.start_byte:child.start_byte - self.start_byte]
            cursor = max(cursor, child.end_byte)
        if cursor < self.end_byte:
            out += whole[cursor - self.start_byte:]
        return bytes(out)


def repository(repo: str | Path = ".") -> Repository:
    """The repository whose snapshot a retrieval reads.

    ``project_id`` is a hash of the canonical repository path and branch and
    commit come from git, so a path inside the repository is enough to pick one
    snapshot out of however many the graph holds.
    """
    root = Path(repo).resolve()
    while not (root / ".git").exists():
        if root.parent == root:
            raise RetrievalError(f"{Path(repo).resolve()} is not inside a git repository")
        root = root.parent
    return git_info(root)


def clauses(fqn: str, repo: str | Path = ".",
            db_path: str | Path = store.DEFAULT_DB_PATH) -> list[Located]:
    """Every clause at ``fqn`` in this repository's indexed snapshot, in file order.

    Every, not the first: an fqn is built from the estate's own headings, so two
    siblings that carry the same text share one address. Reporting both is the
    record being honest about the file.
    """
    found = repository(repo)
    if not Path(db_path).exists():
        raise RetrievalError(f"no context graph at {db_path}; run `orbit-context index` first")
    connection = store.connect(db_path, read_only=True)
    try:
        rows = connection.execute(
            "SELECT c.id, c.surface_path, c.fqn, c.clause_type, c.start_line, "
            "       c.end_line, c.start_byte, c.end_byte, "
            "       COALESCE(MAX(s.content_sha256), '') "
            "FROM gl_context_clause c "
            "LEFT JOIN gl_context_surface s "
            "  ON s.project_id = c.project_id AND s.branch = c.branch "
            " AND s.commit_sha = c.commit_sha AND s.path = c.surface_path "
            "WHERE c.project_id = ? AND c.branch = ? AND c.commit_sha = ? "
            "  AND (c.fqn = ? OR CAST(c.id AS VARCHAR) = ?) "
            "GROUP BY c.id, c.surface_path, c.fqn, c.clause_type, c.start_line, "
            "         c.end_line, c.start_byte, c.end_byte "
            "ORDER BY c.surface_path, c.start_byte",
            [found.project_id, found.branch, found.commit_sha, fqn, fqn],
        ).fetchall()
    except duckdb.CatalogException:
        raise RetrievalError(
            f"{db_path} holds no gl_context_clause table; run `orbit-context index` first"
        ) from None
    finally:
        connection.close()
    return [Located(found.root, *row) for row in rows]


def resolve(address: str, repo: str | Path = ".",
            db_path: str | Path = store.DEFAULT_DB_PATH) -> Located:
    """Exactly one clause, or an error naming the candidates.

    ``address`` is an fqn or a clause id. An fqn that matches more than one
    clause raises rather than choosing: once pointers resolve against addresses,
    a silently-picked match becomes a wrong edge in the graph.
    """
    found = clauses(address, repo=repo, db_path=db_path)
    if not found:
        raise RetrievalError(f"no clause at {address!r}")
    if len(found) > 1:
        raise AmbiguousAddress(address, found)
    return found[0]


def descendants(parent: Located, repo: str | Path = ".",
                db_path: str | Path = store.DEFAULT_DB_PATH) -> list[Located]:
    """Every clause nested inside ``parent``'s span, in the same surface."""
    found = repository(repo)
    connection = store.connect(db_path, read_only=True)
    try:
        rows = connection.execute(
            "SELECT c.id, c.surface_path, c.fqn, c.clause_type, c.start_line, "
            "       c.end_line, c.start_byte, c.end_byte, '' "
            "FROM gl_context_clause c "
            "WHERE c.project_id = ? AND c.branch = ? AND c.commit_sha = ? "
            "  AND c.surface_path = ? AND c.id <> ? "
            "  AND c.start_byte >= ? AND c.end_byte <= ? "
            "ORDER BY c.start_byte",
            [found.project_id, found.branch, found.commit_sha,
             parent.surface_path, parent.clause_id,
             parent.start_byte, parent.end_byte],
        ).fetchall()
    finally:
        connection.close()
    return [Located(found.root, *row) for row in rows]
