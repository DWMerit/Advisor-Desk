"""Ticket 09: the store holds only what this run put there.

Two conditions, both at the seams the rest of the suite already uses -- the
statistics `index` returns, the CLI's exit code and stderr, and the DuckDB file
read back by SQL.

Acceptance covered here:
  - a column the ontology does not declare fails the run, naming the remedy
  - `migrate` removes such a column, and refuses one that holds values
  - no count moves across the migration
  - index output lists every repository in the store -- branch, commit, index
    time, detector version -- not only the one indexed
  - re-indexing one repository leaves the others' rows, and the output says
    which rows it replaced
  - rows written under another detector set are distinguishable
"""

import contextlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path

from . import support  # noqa: F401

from build_estate import build
from orbit_context import cli, detectors, store
from orbit_context.indexer import index, migrate
from orbit_context.ontology import load


COUNTED_TABLES = (
    "gl_context_surface",
    "gl_context_clause",
    "gl_context_edge",
    "gl_context_external_ref",
    "gl_context_run",
    "gl_context_coverage",
)


class StoreTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-store-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.db = self.tmp / "graph.duckdb"

    def sql(self, statement, params=None, read_only=True):
        connection = store.connect(self.db, read_only=read_only)
        try:
            return connection.execute(statement, params or []).fetchall()
        finally:
            connection.close()

    def execute(self, statement, params=None):
        connection = store.connect(self.db)
        try:
            connection.execute(statement, params or [])
        finally:
            connection.close()

    def counts(self):
        """Every table's row count, in one dict. The guard the ticket asks for.

        Removing a column is the cheapest place to move a number without
        noticing, so the counts are taken whole rather than one table at a time.
        """
        return {table: self.sql(f"SELECT count(*) FROM {table}")[0][0]
                for table in COUNTED_TABLES}


class TestDriftFailsTheRun(StoreTestCase):
    """The decision recorded in the ticket: a mismatch is a failed run.

    Dropping a column cannot be undone, and a run that prints a surface count
    while having removed one is a run whose numbers cannot be read afterwards.
    So the run refuses, and names the command that resolves it.
    """

    def setUp(self):
        super().setUp()
        self.estate = build(self.tmp / "estate")
        index(self.estate, db_path=self.db)
        self.execute("ALTER TABLE gl_context_surface ADD COLUMN client VARCHAR")

    def test_the_run_fails(self):
        with self.assertRaises(store.SchemaDrift):
            index(self.estate, db_path=self.db)

    def test_the_failure_names_the_table_and_the_column(self):
        with self.assertRaises(store.SchemaDrift) as raised:
            index(self.estate, db_path=self.db)
        self.assertIn("gl_context_surface", str(raised.exception))
        self.assertIn("client", str(raised.exception))

    def test_the_failure_names_the_remedy(self):
        with self.assertRaises(store.SchemaDrift) as raised:
            index(self.estate, db_path=self.db)
        message = str(raised.exception)
        self.assertIn("orbit-context migrate", message)
        self.assertIn(str(self.db), message)

    def test_no_rows_are_written_by_a_run_that_refuses(self):
        before = self.counts()
        with self.assertRaises(store.SchemaDrift):
            index(self.estate, db_path=self.db)
        self.assertEqual(self.counts(), before)

    def test_the_cli_exits_non_zero_and_says_so(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = cli.main(["index", str(self.estate), "--db", str(self.db)])
        self.assertEqual(code, 1)
        self.assertIn("client", stderr.getvalue())
        self.assertIn("orbit-context migrate", stderr.getvalue())


class TestMigrateRemovesWhatTheOntologyDoesNotDeclare(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.estate = build(self.tmp / "estate")
        index(self.estate, db_path=self.db)

    def test_an_undeclared_column_is_removed(self):
        self.execute("ALTER TABLE gl_context_surface ADD COLUMN client VARCHAR")
        report = migrate(self.db)
        removed = {entry["table"]: entry["columns_removed"] for entry in report["tables"]}
        self.assertEqual(removed["gl_context_surface"], ["client"])
        self.assertNotIn(
            "client",
            store.existing_columns(store.connect(self.db, read_only=True),
                                   "gl_context_surface"),
        )

    def test_the_four_pre_gate_columns_are_removed_together(self):
        for column in ("client", "activation", "evidence_class", "detector"):
            self.execute(f"ALTER TABLE gl_context_surface ADD COLUMN {column} VARCHAR")
        migrate(self.db)
        columns = store.existing_columns(
            store.connect(self.db, read_only=True), "gl_context_surface"
        )
        for column in ("client", "activation", "evidence_class", "detector"):
            self.assertNotIn(column, columns)

    def test_no_count_moves_across_the_migration(self):
        # The ticket's own guard. Those columns carry no count; if a number
        # moves, something else changed at the same time.
        self.execute("ALTER TABLE gl_context_surface ADD COLUMN client VARCHAR")
        before = self.counts()
        migrate(self.db)
        self.assertEqual(self.counts(), before)

    def test_the_report_carries_the_counts_either_side(self):
        self.execute("ALTER TABLE gl_context_surface ADD COLUMN client VARCHAR")
        report = migrate(self.db)
        for entry in report["tables"]:
            self.assertEqual(entry["rows_before"], entry["rows_after"], entry["table"])

    def test_indexing_runs_again_once_migrated(self):
        self.execute("ALTER TABLE gl_context_surface ADD COLUMN client VARCHAR")
        migrate(self.db)
        statistics = index(self.estate, db_path=self.db)
        self.assertGreater(statistics["graph"]["surfaces"], 0)

    def test_a_column_named_like_a_keyword_is_still_removable(self):
        # The name came from something other than this tool, so it is not known
        # to be a bare word. Unquoted, `order` is a parse error rather than a
        # column, and the store would be at a dead end: the run refusing, and
        # the command it names failing.
        self.execute('ALTER TABLE gl_context_surface ADD COLUMN "order" VARCHAR')
        migrate(self.db)
        self.assertNotIn(
            "order",
            store.existing_columns(store.connect(self.db, read_only=True),
                                   "gl_context_surface"),
        )

    def test_a_declared_column_the_store_lacks_is_added_and_reported(self):
        self.execute("ALTER TABLE gl_context_run DROP COLUMN indexed_at")
        report = migrate(self.db)
        added = {entry["table"]: entry["columns_added"] for entry in report["tables"]}
        self.assertEqual(added["gl_context_run"], ["indexed_at"])
        self.assertIn(
            "indexed_at",
            store.existing_columns(store.connect(self.db, read_only=True),
                                   "gl_context_run"),
        )

    def test_migrating_a_store_that_matches_removes_nothing(self):
        before = self.counts()
        report = migrate(self.db)
        for entry in report["tables"]:
            self.assertEqual(entry["columns_removed"], [], entry["table"])
        self.assertEqual(self.counts(), before)

    def test_the_cli_migrates(self):
        self.execute("ALTER TABLE gl_context_surface ADD COLUMN client VARCHAR")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = cli.main(["migrate", "--db", str(self.db)])
        self.assertEqual(code, 0)
        self.assertIn("client", stdout.getvalue())


class TestMigrateRefusesAColumnHoldingValues(StoreTestCase):
    """A column with values in it is data, not a leftover.

    The tool cannot tell which it is, and removing it would be the one thing a
    migration must never do quietly. So it is named and nothing is removed --
    including the columns that would otherwise have gone, because a partial
    migration is a third state nobody asked for.
    """

    def setUp(self):
        super().setUp()
        self.estate = build(self.tmp / "estate")
        index(self.estate, db_path=self.db)
        self.execute("ALTER TABLE gl_context_surface ADD COLUMN client VARCHAR")
        self.execute("ALTER TABLE gl_context_surface ADD COLUMN activation VARCHAR")
        self.execute("UPDATE gl_context_surface SET client = 'a-session' "
                     "WHERE path = 'CLAUDE.md'")

    def test_the_migration_is_refused(self):
        with self.assertRaises(store.MigrationRefused):
            migrate(self.db)

    def test_nothing_is_altered_by_a_refusal(self):
        # Not even the declared columns: a refusal that had already changed the
        # schema is not the refusal its own message says it is. Checked against
        # a store missing a column the ontology declares, which a migration
        # that reached its work would have added.
        self.execute("ALTER TABLE gl_context_run DROP COLUMN indexed_at")
        with self.assertRaises(store.MigrationRefused):
            migrate(self.db)
        self.assertNotIn(
            "indexed_at",
            store.existing_columns(store.connect(self.db, read_only=True),
                                   "gl_context_run"),
        )

    def test_remove_values_is_the_decision_taken_by_hand(self):
        rows = self.sql("SELECT count(*) FROM gl_context_surface")[0][0]
        report = migrate(self.db, remove_values=True)
        removed = {entry["table"]: entry for entry in report["tables"]}
        surface = removed["gl_context_surface"]
        self.assertEqual(sorted(surface["columns_removed"]), ["activation", "client"])
        self.assertGreater(surface["values_removed"]["client"], 0)
        self.assertNotIn("activation", surface["values_removed"])
        # The rows themselves stay. It is the column that goes.
        self.assertEqual(self.sql("SELECT count(*) FROM gl_context_surface")[0][0], rows)

    def test_the_cli_takes_the_decision(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = cli.main(["migrate", "--db", str(self.db), "--remove-values"])
        self.assertEqual(code, 0)
        self.assertNotIn(
            "client",
            store.existing_columns(store.connect(self.db, read_only=True),
                                   "gl_context_surface"),
        )

    def test_the_refusal_names_the_column_and_how_many_rows_hold_it(self):
        with self.assertRaises(store.MigrationRefused) as raised:
            migrate(self.db)
        message = str(raised.exception)
        self.assertIn("gl_context_surface.client", message)
        held = self.sql("SELECT count(*) FROM gl_context_surface "
                        "WHERE client IS NOT NULL")[0][0]
        self.assertGreater(held, 0)
        self.assertIn(str(held), message)

    def test_nothing_is_removed_when_one_column_is_refused(self):
        with self.assertRaises(store.MigrationRefused):
            migrate(self.db)
        columns = store.existing_columns(
            store.connect(self.db, read_only=True), "gl_context_surface"
        )
        self.assertIn("client", columns)
        self.assertIn("activation", columns)


class TestTheStoreContentsAreVisible(StoreTestCase):
    """Index one estate into a store that already holds another."""

    def setUp(self):
        super().setUp()
        self.first = build(self.tmp / "first")
        self.second = build(self.tmp / "second")
        index(self.first, db_path=self.db)
        self.statistics = index(self.second, db_path=self.db)

    def listed(self):
        return self.statistics["store"]["repositories"]

    def test_every_repository_in_the_store_is_listed(self):
        listed = {entry["path"] for entry in self.listed()}
        indexed_now = {entry["path"] for entry in self.statistics["repositories"]}
        self.assertEqual(len(indexed_now), 3)
        self.assertEqual(len(listed), 6)
        self.assertTrue(indexed_now < listed)

    def test_the_repositories_this_run_did_not_touch_are_marked(self):
        touched = {entry["path"] for entry in self.listed()
                   if entry["indexed_by_this_run"]}
        self.assertEqual(
            touched, {entry["path"] for entry in self.statistics["repositories"]}
        )

    def test_each_carries_branch_commit_index_time_and_detector_version(self):
        for entry in self.listed():
            self.assertTrue(entry["branch"], entry["path"])
            self.assertEqual(len(entry["commit_sha"]), 40, entry["path"])
            self.assertTrue(entry["indexed_at"], entry["path"])
            self.assertEqual(entry["detector_set_version"], detectors.VERSION)
            self.assertTrue(entry["detector_set_is_current"])

    def test_each_carries_the_rows_it_holds(self):
        for entry in self.listed():
            self.assertGreater(entry["rows"]["gl_context_surface"], 0, entry["path"])
            self.assertEqual(entry["rows"]["gl_context_run"], 1, entry["path"])
        total = sum(entry["rows"]["gl_context_surface"] for entry in self.listed())
        self.assertEqual(
            total, self.sql("SELECT count(*) FROM gl_context_surface")[0][0]
        )

    def test_a_first_index_into_an_empty_store_lists_only_its_own(self):
        other = self.tmp / "solo.duckdb"
        statistics = index(self.first, db_path=other)
        self.assertEqual(len(statistics["store"]["repositories"]), 3)


class TestReindexingLeavesTheOthersAlone(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.first = build(self.tmp / "first")
        self.second = build(self.tmp / "second")
        index(self.first, db_path=self.db)
        self.before = self.rows_by_project()

    def rows_by_project(self):
        return dict(self.sql(
            "SELECT project_id, count(*) FROM gl_context_surface GROUP BY 1"
        ))

    def test_indexing_a_second_estate_leaves_the_first(self):
        index(self.second, db_path=self.db)
        after = self.rows_by_project()
        for project_id, count in self.before.items():
            self.assertEqual(after[project_id], count)

    def test_re_indexing_the_first_leaves_the_second(self):
        index(self.second, db_path=self.db)
        second = {project_id: count for project_id, count in self.rows_by_project().items()
                  if project_id not in self.before}
        self.assertTrue(second)
        index(self.first, db_path=self.db)
        after = self.rows_by_project()
        for project_id, count in second.items():
            self.assertEqual(after[project_id], count)

    def test_a_first_index_replaced_nothing(self):
        statistics = index(self.second, db_path=self.db)
        self.assertEqual(statistics["replaced"]["gl_context_surface"], 0)

    def test_re_indexing_says_which_rows_it_replaced(self):
        statistics = index(self.first, db_path=self.db)
        self.assertEqual(
            statistics["replaced"]["gl_context_surface"],
            sum(self.before.values()),
        )

    def test_each_repository_says_which_of_its_own_rows_it_replaced(self):
        statistics = index(self.first, db_path=self.db)
        for entry in statistics["repositories"]:
            self.assertEqual(
                entry["replaced"]["gl_context_surface"],
                self.before[entry["project_id"]],
                entry["path"],
            )


class TestAnotherDetectorSetIsDistinguishable(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.first = build(self.tmp / "first")
        self.second = build(self.tmp / "second")
        index(self.first, db_path=self.db)
        self.execute(
            "UPDATE gl_context_run SET detector_set_version = '0.000000000000'"
        )
        self.statistics = index(self.second, db_path=self.db)

    def test_the_older_rows_are_marked(self):
        older = [entry for entry in self.statistics["store"]["repositories"]
                 if not entry["detector_set_is_current"]]
        self.assertEqual(len(older), 3)
        for entry in older:
            self.assertEqual(entry["detector_set_version"], "0.000000000000")
            self.assertFalse(entry["indexed_by_this_run"])

    def test_the_count_is_reported_beside_the_current_version(self):
        block = self.statistics["store"]
        self.assertEqual(block["detector_set_version"], detectors.VERSION)
        self.assertEqual(block["repositories_from_other_detector_sets"], 3)

    def test_every_row_is_attributable_to_a_detector_set(self):
        # The join that makes it so: every context row carries the snapshot key
        # its run row carries, so no row is left without a version.
        orphaned = self.sql(
            "SELECT count(*) FROM gl_context_surface s "
            "WHERE NOT EXISTS (SELECT 1 FROM gl_context_run r "
            "  WHERE r.traversal_path = s.traversal_path "
            "    AND r.project_id = s.project_id AND r.branch = s.branch "
            "    AND r.commit_sha = s.commit_sha)"
        )[0][0]
        self.assertEqual(orphaned, 0)


class TestTheRunRowRecordsWhenItRan(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.estate = build(self.tmp / "estate")
        index(self.estate, db_path=self.db)

    def test_indexed_at_is_declared_by_the_ontology(self):
        self.assertIn("indexed_at", load().nodes["IndexRun"].column_names)

    def test_every_run_row_carries_a_time(self):
        rows = self.sql("SELECT count(*) FROM gl_context_run WHERE indexed_at IS NULL")
        self.assertEqual(rows[0][0], 0)

    def test_re_indexing_the_same_snapshot_moves_the_time_forward(self):
        before = self.sql("SELECT id, indexed_at FROM gl_context_run ORDER BY id")
        index(self.estate, db_path=self.db)
        after = self.sql("SELECT id, indexed_at FROM gl_context_run ORDER BY id")
        self.assertEqual([row[0] for row in before], [row[0] for row in after])
        for (_, first), (_, second) in zip(before, after):
            self.assertGreaterEqual(second, first)


if __name__ == "__main__":
    unittest.main()
