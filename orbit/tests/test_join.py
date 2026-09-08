"""The join to Orbit's own gl_file.

Acceptance: "`orbit sql` joining `gl_context_surface` to `gl_file` on `path`
returns rows for a repo indexed by both tools."

Getting traversal_path or project_id wrong makes this join return zero rows
silently rather than erroring, so it is asserted rather than eyeballed. The
gl_file DDL below is copied from a graph.duckdb written by orbit 0.118.1.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from . import support  # noqa: F401

from build_estate import build
from orbit_context import store
from orbit_context.indexer import index
from orbit_context.workspace import project_id_from_path, stable_id

GL_FILE_DDL = """
CREATE TABLE gl_file(
    id BIGINT NOT NULL,
    traversal_path VARCHAR NOT NULL,
    project_id BIGINT NOT NULL,
    branch VARCHAR NOT NULL,
    commit_sha VARCHAR DEFAULT('') NOT NULL,
    path VARCHAR NOT NULL,
    "name" VARCHAR NOT NULL,
    "extension" VARCHAR NOT NULL,
    "language" VARCHAR NOT NULL,
    size_bytes BIGINT DEFAULT(0) NOT NULL,
    reason VARCHAR DEFAULT('') NOT NULL
)
"""


class TestJoinToGlFile(unittest.TestCase):
    """Stand in for `orbit local index`, then join what both tools wrote."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-join-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.estate = build(self.tmp / "estate")
        self.db = self.tmp / "graph.duckdb"
        self.stats = index(self.estate, db_path=self.db)
        self.alpha = next(
            entry for entry in self.stats["repositories"] if entry["repository"] == "alpha"
        )
        self._write_gl_file_rows()

    def _write_gl_file_rows(self):
        """Write gl_file rows the way orbit local index would."""
        root = Path(self.alpha["path"])
        connection = store.connect(self.db)
        connection.execute(GL_FILE_DDL)
        rows = []
        for path in sorted(root.rglob("*")):
            if not path.is_file() or ".git" in path.parts:
                continue
            relative = path.relative_to(root).as_posix()
            rows.append([
                stable_id("gl_file", relative),
                "",                                   # traversal_path
                project_id_from_path(str(root)),
                self.alpha["branch"],
                self.alpha["commit_sha"],
                relative,
                path.name,
                path.suffix.lstrip("."),
                "unknown",
                path.stat().st_size,
                "",
            ])
        connection.executemany(
            "INSERT INTO gl_file VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows
        )
        connection.close()

    def query(self, sql):
        connection = store.connect(self.db, read_only=True)
        try:
            return connection.execute(sql).fetchall()
        finally:
            connection.close()

    def test_join_on_path_returns_rows(self):
        rows = self.query(
            "SELECT c.path, c.surface_kind, f.language "
            "FROM gl_context_surface c JOIN gl_file f ON f.path = c.path "
            "ORDER BY c.path"
        )
        self.assertGreater(len(rows), 0)

    def test_join_scoped_by_project_id_returns_rows(self):
        # The scoped join is the correct one across an estate: every local row
        # carries the same empty traversal_path, and paths are
        # repository-relative, so path alone matches across repositories.
        rows = self.query(
            "SELECT c.path, c.size_bytes, f.size_bytes "
            "FROM gl_context_surface c "
            "JOIN gl_file f ON f.path = c.path AND f.project_id = c.project_id "
            "ORDER BY c.path"
        )
        self.assertGreater(len(rows), 0)
        for _, context_size, file_size in rows:
            self.assertEqual(context_size, file_size)

    def test_surfaces_are_a_subset_of_files(self):
        unmatched = self.query(
            "SELECT c.path FROM gl_context_surface c "
            "LEFT JOIN gl_file f ON f.path = c.path AND f.project_id = c.project_id "
            "WHERE f.path IS NULL AND c.project_id = %d" % self.alpha["project_id"]
        )
        self.assertEqual(unmatched, [])


if __name__ == "__main__":
    unittest.main()
