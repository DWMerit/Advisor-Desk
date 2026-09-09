"""Read a clause back out of the file it came from.

The graph stores no clause text. A clause row carries a path and a byte span,
and this is the path that turns them back into bytes: find the row by ``fqn``,
open the file, seek to ``start_byte``, read to ``end_byte``.

What comes back is a span of the file as it is on disk right now. If the file
has been edited since the index run, the span is whatever now sits at those
offsets -- re-index and the offsets move. That is the guarantee being made:
never that the text is current, only that it is the file's own bytes and not a
copy the graph kept.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb

from . import store
from .workspace import Repository, git_info


class RetrievalError(Exception):
    """A clause could not be read back from its file."""


@dataclass(frozen=True)
class Located:
    """One clause row, resolved against the repository it belongs to."""

    repo_root: Path
    surface_path: str
    fqn: str
    clause_type: str
    start_line: int
    end_line: int
    start_byte: int
    end_byte: int

    @property
    def absolute_path(self) -> Path:
        return self.repo_root / self.surface_path

    @property
    def locator(self) -> str:
        return (
            f"{self.surface_path}:{self.start_line}-{self.end_line} "
            f"bytes {self.start_byte}-{self.end_byte} {self.clause_type}"
        )

    def read(self) -> bytes:
        """The file's own bytes for this span. Never decoded, never reflowed."""
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
            "SELECT surface_path, fqn, clause_type, start_line, end_line, "
            "       start_byte, end_byte "
            "FROM gl_context_clause "
            "WHERE project_id = ? AND branch = ? AND commit_sha = ? AND fqn = ? "
            "ORDER BY surface_path, start_byte",
            [found.project_id, found.branch, found.commit_sha, fqn],
        ).fetchall()
    except duckdb.CatalogException:
        raise RetrievalError(
            f"{db_path} holds no gl_context_clause table; run `orbit-context index` first"
        ) from None
    finally:
        connection.close()
    return [Located(found.root, *row) for row in rows]
