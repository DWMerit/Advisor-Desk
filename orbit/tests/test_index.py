"""Index the fixture estate and check what lands in the graph.

Acceptance covered here:
  - `orbit sql "SELECT path, surface_kind, size_bytes FROM gl_context_surface"`
    returns rows
  - re-running the index does not duplicate rows
  - statistics report a non-zero skipped or errored count on a fixture
    containing a binary file
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from . import support  # noqa: F401

from build_estate import build
from orbit_context import store
from orbit_context.indexer import index
from orbit_context.ontology import load_domain
from orbit_context.store import StoreError


class EstateTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-index-"))
        cls.estate = build(cls.tmp / "estate")
        cls.db = cls.tmp / "graph.duckdb"
        cls.stats = index(cls.estate, db_path=cls.db, detailed=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def query(self, sql, params=None):
        connection = store.connect(self.db, read_only=True)
        try:
            return connection.execute(sql, params or []).fetchall()
        finally:
            connection.close()


class TestRowsLand(EstateTestCase):
    def test_the_acceptance_query_returns_rows(self):
        rows = self.query(
            "SELECT path, surface_kind, size_bytes FROM gl_context_surface ORDER BY path"
        )
        self.assertGreater(len(rows), 0)

    def test_both_repositories_are_indexed(self):
        projects = self.query("SELECT DISTINCT project_id FROM gl_context_surface")
        self.assertEqual(len(projects), 2)
        self.assertEqual(self.stats["graph"]["repositories"], 2)

    def test_root_and_nested_surfaces(self):
        paths = {row[0] for row in self.query("SELECT path FROM gl_context_surface")}
        self.assertIn("CLAUDE.md", paths)
        self.assertIn("AGENTS.md", paths)
        self.assertIn("GEMINI.md", paths)
        self.assertIn(".github/copilot-instructions.md", paths)
        self.assertIn("packages/ui/CLAUDE.md", paths)

    def test_paths_are_repository_relative(self):
        # gl_file stores repository-relative paths. An absolute path here joins
        # to nothing.
        for (path,) in self.query("SELECT path FROM gl_context_surface"):
            self.assertFalse(path.startswith("/"), path)

    def test_traversal_path_matches_the_local_graph(self):
        values = {row[0] for row in self.query("SELECT DISTINCT traversal_path FROM gl_context_surface")}
        self.assertEqual(values, {""})

    def test_pruned_directories_are_not_indexed(self):
        paths = {row[0] for row in self.query("SELECT path FROM gl_context_surface")}
        self.assertNotIn("node_modules/pkg/CLAUDE.md", paths)

    def test_ordinary_documentation_is_not_a_surface(self):
        paths = {row[0] for row in self.query("SELECT path FROM gl_context_surface")}
        self.assertNotIn("docs/notes.md", paths)
        self.assertNotIn("src/takeoff.py", paths)

    def test_size_bytes_matches_the_file(self):
        for (path, size) in self.query(
            "SELECT path, size_bytes FROM gl_context_surface WHERE project_id = ?",
            [self.stats["repositories"][0]["project_id"]],
        ):
            on_disk = (Path(self.stats["repositories"][0]["path"]) / path).stat().st_size
            self.assertEqual(size, on_disk, path)

    def test_no_content_column(self):
        # The row carries a path; the caller reads the bytes.
        columns = store.existing_columns(
            store.connect(self.db, read_only=True), "gl_context_surface"
        )
        self.assertNotIn("content", columns)


class TestCoverageIsRecorded(EstateTestCase):
    def test_binary_surface_is_counted(self):
        processing = self.stats["processing"]
        self.assertGreater(processing["skipped_files"] + processing["errored_files"], 0)

    def test_binary_surface_carries_a_reason(self):
        reasons = {
            entry["path"]: entry["reason"]
            for entry in self.stats["detailed"]["skipped_files"]
        }
        self.assertEqual(reasons.get("config/.cursorrules"), "invalid_utf8")

    def test_a_skipped_surface_is_still_a_row(self):
        rows = self.query(
            "SELECT reason, size_bytes FROM gl_context_surface WHERE path = ?",
            ["config/.cursorrules"],
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "invalid_utf8")
        self.assertGreater(rows[0][1], 0)

    def test_indexed_surfaces_have_an_empty_reason(self):
        rows = self.query(
            "SELECT reason FROM gl_context_surface WHERE path = 'GEMINI.md'"
        )
        self.assertEqual(rows, [("",)])

    def test_a_surface_outside_any_repository_is_reported(self):
        reasons = {
            entry["path"]: entry["reason"]
            for entry in self.stats["detailed"]["skipped_files"]
        }
        self.assertEqual(reasons.get("loose/CLAUDE.md"), "outside_indexed_repository")


class TestReindex(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-reindex-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.estate = build(self.tmp / "estate")
        self.db = self.tmp / "graph.duckdb"

    def count(self):
        connection = store.connect(self.db, read_only=True)
        try:
            return connection.execute("SELECT count(*) FROM gl_context_surface").fetchone()[0]
        finally:
            connection.close()

    def test_reindexing_does_not_duplicate_rows(self):
        index(self.estate, db_path=self.db)
        first = self.count()
        self.assertGreater(first, 0)
        index(self.estate, db_path=self.db)
        self.assertEqual(self.count(), first)
        index(self.estate, db_path=self.db)
        self.assertEqual(self.count(), first)

    def test_ids_are_stable_across_reindex(self):
        index(self.estate, db_path=self.db)
        connection = store.connect(self.db, read_only=True)
        before = connection.execute(
            "SELECT id, path FROM gl_context_surface ORDER BY id"
        ).fetchall()
        connection.close()
        index(self.estate, db_path=self.db)
        connection = store.connect(self.db, read_only=True)
        after = connection.execute(
            "SELECT id, path FROM gl_context_surface ORDER BY id"
        ).fetchall()
        connection.close()
        self.assertEqual(before, after)

    def test_a_removed_surface_leaves_the_snapshot(self):
        index(self.estate, db_path=self.db)
        (self.estate / "beta" / "GEMINI.md").unlink()
        # Commit so the snapshot key moves with the tree.
        index(self.estate, db_path=self.db)
        connection = store.connect(self.db, read_only=True)
        rows = connection.execute(
            "SELECT count(*) FROM gl_context_surface WHERE path = 'GEMINI.md'"
        ).fetchone()[0]
        connection.close()
        self.assertEqual(rows, 0)


class TestNeverWritesOrbitsTables(unittest.TestCase):
    def test_a_non_context_table_is_refused(self):
        node = load_domain()["Surface"]
        forged = type(node)(
            node_type=node.node_type, domain=node.domain, table="gl_file",
            columns=node.columns, source_file=node.source_file,
        )
        with self.assertRaises(StoreError):
            store.assert_context_table(forged.table)


if __name__ == "__main__":
    unittest.main()
