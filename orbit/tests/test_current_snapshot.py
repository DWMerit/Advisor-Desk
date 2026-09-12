"""Spec 0005: a figure read out of the graph is a figure of something that exists.

The store keeps every run ever indexed, so `SELECT count(*) FROM
gl_context_surface` adds unrelated snapshots together and the error grows on its
own -- every session indexes, and nothing has to go wrong for the number to
drift. The fix is a view per table naming the current snapshot, so the short
query is the correct one and the aggregate across runs is the deliberate one.

Acceptance covered here:
  - the current snapshot is addressable by name, without the caller writing a join
  - two runs of one repository: the view returns the newer run, the base table
    returns the sum -- the defect reproduced and fixed in one test
  - the view's row count equals the surfaces at that commit, so it is correct
    and not merely smaller
  - two repositories: each gets its own current snapshot, not one global newest
  - an answer carries its snapshot key
  - a query against a view in a store this project did not build fails and names
    the missing table
  - the detector set version is unmoved across this work

Every figure here comes from a fixture estate built by the test. Spec 0002 §6
keeps this repository's own live counts in evidence records rather than in
tests, because a test that reads live content fails whenever the content moves.
"""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import duckdb

from . import support  # noqa: F401

from build_estate import build
from orbit_context import detectors, store
from orbit_context.indexer import index, migrate
from orbit_context.ontology import load


# The version every count in tickets 07 and 14 was taken under. Views decide
# which rows an answer covers; the five hashed detector modules decide what is
# recognised, and this work touches none of them. Asserted rather than stated in
# prose: a figure moving after this date is not attributable to this change.
DETECTOR_SET_VERSION = support.DETECTOR_SET_VERSION


class SnapshotTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-snapshot-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.db = self.tmp / "graph.duckdb"

    def sql(self, statement, params=None):
        connection = store.connect(self.db, read_only=True)
        try:
            return connection.execute(statement, params or []).fetchall()
        finally:
            connection.close()

    def count(self, table, where="", params=None):
        clause = f" WHERE {where}" if where else ""
        return self.sql(f"SELECT count(*) FROM {table}{clause}", params)[0][0]

    def head_of(self, repository: Path) -> str:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repository, check=True,
            capture_output=True, text=True,
        ).stdout.strip()

    def at_commit(self, table, project_id, commit_sha, column="path"):
        """One snapshot's rows, scoped by hand -- what the view has to equal.

        Measured against this rather than against the `surfaces` count the index
        run prints: a recognised surface whose bytes could not be read gets a row
        and no count, so those are two different questions and only this one is
        about rows in the store.
        """
        return self.sql(
            f"SELECT {column} FROM {table} "
            "WHERE project_id = ? AND commit_sha = ? ORDER BY 1",
            [project_id, commit_sha],
        )

    def commit_a_change(self, repository: Path, name: str, text: str) -> None:
        """Move a fixture repository to a new commit, so a re-index is a new run.

        Re-indexing the same commit replaces its rows. A second *run* of one
        repository -- the shape this spec is about -- needs a second commit.
        """
        (repository / name).write_text(text, encoding="utf-8")
        for args in (("add", "-A"), ("commit", "-m", "a second commit")):
            subprocess.run(["git", *args], cwd=repository, check=True,
                           capture_output=True)


class TestTwoRunsOfOneRepository(SnapshotTestCase):
    """The defect, reproduced and then fixed, in one test.

    The store holds two commits of `beta`. An unscoped count adds them together;
    the current view answers for the commit that exists now.
    """

    def setUp(self):
        super().setUp()
        self.estate = build(self.tmp / "estate")
        self.beta = self.estate / "beta"
        first = index(self.estate, db_path=self.db)
        self.first_beta = self.surfaces_of(first, self.beta)
        self.first_commit = self.head_of(self.beta)
        self.commit_a_change(self.beta, "CLAUDE.md",
                             "# Beta\nA surface this commit added.\n")
        second = index(self.estate, db_path=self.db)
        self.second_beta = self.surfaces_of(second, self.beta)
        self.project_id = self.project_of(second, self.beta)
        self.second_commit = self.head_of(self.beta)
        self.rows_then = self.at_commit(
            "gl_context_surface", self.project_id, self.first_commit
        )
        self.rows_now = self.at_commit(
            "gl_context_surface", self.project_id, self.second_commit
        )

    @staticmethod
    def entry_for(statistics, repository: Path):
        for entry in statistics["repositories"]:
            if Path(entry["path"]) == repository:
                return entry
        raise AssertionError(f"{repository} was not indexed")

    def surfaces_of(self, statistics, repository: Path) -> int:
        return self.entry_for(statistics, repository)["graph"]["surfaces"]

    def project_of(self, statistics, repository: Path) -> int:
        return self.entry_for(statistics, repository)["project_id"]

    def test_the_two_runs_are_both_in_the_store(self):
        runs = self.count("gl_context_run", "project_id = ?", [self.project_id])
        self.assertEqual(runs, 2)

    def test_the_commit_moved_so_the_second_run_found_one_more_surface(self):
        # The guard on the fixture itself. If the two runs held the same rows
        # the rest of this class would pass without measuring anything.
        self.assertEqual(self.second_beta, self.first_beta + 1)

    def test_the_two_runs_are_ordered_against_each_other(self):
        # Both index runs land in the same second here, which is also what a
        # script indexing twice in a row does. `current_run` orders on
        # `indexed_at`, so the two have to be distinguishable at that column or
        # the view answers for whichever the tiebreak reaches.
        times = self.sql(
            "SELECT DISTINCT indexed_at FROM gl_context_run WHERE project_id = ?",
            [self.project_id],
        )
        self.assertEqual(len(times), 2)

    def test_the_base_table_answers_for_every_run(self):
        # The defect. Nothing is wrong with the store; the question is.
        unscoped = self.count("gl_context_surface", "project_id = ?", [self.project_id])
        self.assertEqual(unscoped, len(self.rows_then) + len(self.rows_now))

    def test_the_view_answers_for_the_current_run_alone(self):
        scoped = self.count("current_surface", "project_id = ?", [self.project_id])
        self.assertEqual(scoped, len(self.rows_now))
        self.assertLess(scoped, len(self.rows_then) + len(self.rows_now))

    def test_the_view_is_correct_and_not_merely_smaller(self):
        # Smaller than the unscoped figure is not the property being asserted.
        # These are the rows themselves, against the six-line join the view
        # replaces, so a view that dropped rows at random fails here rather than
        # reading as a fix.
        scoped = self.sql(
            "SELECT path FROM current_surface WHERE project_id = ? ORDER BY 1",
            [self.project_id],
        )
        self.assertEqual(scoped, self.rows_now)
        self.assertNotEqual(self.rows_now, self.rows_then)

    def test_the_view_holds_one_commit(self):
        commits = self.sql(
            "SELECT DISTINCT commit_sha FROM current_surface WHERE project_id = ?",
            [self.project_id],
        )
        self.assertEqual(len(commits), 1)

    def test_it_is_the_commit_the_working_tree_is_at(self):
        commit = self.sql(
            "SELECT DISTINCT commit_sha FROM current_surface WHERE project_id = ?",
            [self.project_id],
        )[0][0]
        self.assertEqual(commit, self.second_commit)

    def test_the_current_snapshot_is_addressable_without_a_join(self):
        # User story 6: no three-column join reconstructed from memory. The
        # whole query is the one below.
        rows = self.sql("SELECT count(*) FROM current_surface")
        self.assertGreater(rows[0][0], 0)

    def test_the_store_says_how_many_runs_are_behind_the_answer(self):
        # User story 7: whether an unscoped figure would have been misleading is
        # readable beside the answer rather than by counting run rows by hand.
        # Two figures, because they answer about different things: what an
        # unscoped count of this repository's rows would have summed, and what
        # the file holds altogether.
        held = self.sql(
            "SELECT runs_of_this_repository, runs_in_store FROM current_run "
            "WHERE project_id = ?",
            [self.project_id],
        )
        self.assertEqual(held, [(2, self.count("gl_context_run"))])

    def test_the_two_run_counts_are_different_questions(self):
        # Three repositories, one of them indexed twice: four run rows, and the
        # repository that moved has two of them. A single figure could not say
        # both, and the one a reader needs is the first.
        rows = self.sql(
            "SELECT project_id, runs_of_this_repository, runs_in_store "
            "FROM current_run ORDER BY runs_of_this_repository DESC"
        )
        self.assertEqual([row[1] for row in rows], [2, 1, 1])
        self.assertEqual({row[2] for row in rows}, {4})

    def test_every_table_scopes_the_same_way(self):
        for shape in load().tables:
            if shape.table == store.RUN_TABLE:
                continue
            view = shape.current_view
            with self.subTest(view=view):
                self.assertLessEqual(self.count(view), self.count(shape.table))
                commits = self.sql(
                    f"SELECT DISTINCT project_id, commit_sha FROM {view}"
                )
                self.assertEqual(len(commits), len(set(pid for pid, _ in commits)))


class TestEachRepositoryHasItsOwnCurrentSnapshot(SnapshotTestCase):
    """Current is per repository, not one global newest.

    A store holds several repositories -- that is the design, not a fault. A
    view taking the newest run in the whole store would answer for one
    repository and return nothing at all for the others.
    """

    def setUp(self):
        super().setUp()
        self.estate = build(self.tmp / "estate")
        self.beta = self.estate / "beta"
        self.first = index(self.estate, db_path=self.db)
        self.commit_a_change(self.beta, "CLAUDE.md", "# Beta\nA later commit.\n")
        self.second = index(self.estate, db_path=self.db)

    def test_every_repository_appears_in_the_current_view(self):
        listed = {row[0] for row in self.sql("SELECT DISTINCT project_id FROM current_run")}
        indexed = {entry["project_id"] for entry in self.second["repositories"]}
        self.assertEqual(len(indexed), 3)
        self.assertEqual(listed, indexed)

    def test_one_row_per_repository(self):
        rows = self.sql("SELECT project_id, count(*) FROM current_run GROUP BY 1")
        for project_id, count in rows:
            self.assertEqual(count, 1, project_id)

    def test_each_repository_carries_its_own_rows_at_its_own_commit(self):
        for entry in self.second["repositories"]:
            scoped = self.sql(
                "SELECT path FROM current_surface WHERE project_id = ? ORDER BY 1",
                [entry["project_id"]],
            )
            self.assertEqual(
                scoped,
                self.at_commit("gl_context_surface", entry["project_id"],
                               self.head_of(Path(entry["path"]))),
                entry["path"],
            )

    def test_a_repository_that_did_not_move_keeps_its_own_commit(self):
        # Two of the three repositories are at the same commit in both runs, and
        # the third moved. A global newest would answer for the third alone.
        moved = {entry["project_id"]: entry["commit_sha"]
                 for entry in self.second["repositories"]}
        current = dict(self.sql("SELECT project_id, commit_sha FROM current_run"))
        self.assertEqual(current, moved)

    def test_the_whole_store_total_is_the_sum_of_the_current_snapshots(self):
        total = self.count("current_surface")
        per_repository = sum(
            len(self.at_commit("gl_context_surface", entry["project_id"],
                               self.head_of(Path(entry["path"]))))
            for entry in self.second["repositories"]
        )
        self.assertEqual(total, per_repository)
        self.assertLess(total, self.count("gl_context_surface"))


class TestAnAnswerCarriesItsSnapshotKey(SnapshotTestCase):
    """Spec 0002 §9: a number that cannot be tied back to named files is not a
    result. The key travels with the rows rather than being a second query."""

    def setUp(self):
        super().setUp()
        self.estate = build(self.tmp / "estate")
        index(self.estate, db_path=self.db)

    def test_every_view_carries_the_whole_snapshot_key(self):
        connection = store.connect(self.db, read_only=True)
        try:
            for shape in load().tables:
                columns = store.existing_columns(connection, shape.current_view)
                with self.subTest(view=shape.current_view):
                    for column in store.SNAPSHOT_KEY:
                        self.assertIn(column, columns)
        finally:
            connection.close()

    def test_a_count_can_be_quoted_with_its_provenance(self):
        rows = self.sql(
            "SELECT branch, commit_sha, count(*) FROM current_surface "
            "GROUP BY 1, 2 ORDER BY 3 DESC"
        )
        self.assertEqual(len(rows), 3)
        for branch, commit_sha, count in rows:
            self.assertTrue(branch)
            self.assertEqual(len(commit_sha), 40)
            self.assertGreater(count, 0)

    def test_the_view_carries_every_column_the_table_carries(self):
        connection = store.connect(self.db, read_only=True)
        try:
            for shape in load().tables:
                if shape.table == store.RUN_TABLE:
                    continue
                with self.subTest(view=shape.current_view):
                    self.assertEqual(
                        store.existing_columns(connection, shape.current_view),
                        store.existing_columns(connection, shape.table),
                    )
        finally:
            connection.close()

    def test_the_snapshot_view_says_which_detector_set_read_it(self):
        versions = self.sql("SELECT DISTINCT detector_set_version FROM current_run")
        self.assertEqual(versions, [(detectors.VERSION,)])


class TestAQueryAgainstTheWrongStoreFails(SnapshotTestCase):
    """The second defect, and the whole of its mitigation.

    `orbit local sql` without `--db` reads GitLab Orbit's own graph, which holds
    a table of the same name with three rows left over from before the gates. A
    query written against `gl_context_surface` answers 3 without failing. A
    query written against a current view cannot: no such view exists there.
    """

    def setUp(self):
        super().setUp()
        self.other = self.tmp / "someone-elses.duckdb"
        connection = duckdb.connect(str(self.other))
        try:
            connection.execute(
                "CREATE TABLE gl_context_surface ("
                "  id BIGINT, traversal_path VARCHAR, project_id BIGINT,"
                "  branch VARCHAR, commit_sha VARCHAR, path VARCHAR)"
            )
            connection.executemany(
                "INSERT INTO gl_context_surface VALUES (?, '', 1, 'main', '', ?)",
                [[n, f"CLAUDE.md-{n}"] for n in range(3)],
            )
        finally:
            connection.close()

    def read(self, statement):
        connection = duckdb.connect(str(self.other), read_only=True)
        try:
            return connection.execute(statement).fetchall()
        finally:
            connection.close()

    def test_the_base_table_answers_a_plausible_number(self):
        # The reason this matters: nothing about 3 looks wrong.
        self.assertEqual(self.read("SELECT count(*) FROM gl_context_surface"), [(3,)])

    def test_the_view_fails_instead_of_answering(self):
        with self.assertRaises(duckdb.CatalogException):
            self.read("SELECT count(*) FROM current_surface")

    def test_the_failure_names_the_table_it_could_not_find(self):
        with self.assertRaises(duckdb.CatalogException) as raised:
            self.read("SELECT count(*) FROM current_surface")
        self.assertIn("current_surface", str(raised.exception))

    def test_the_view_exists_in_a_store_this_project_built(self):
        index(build(self.tmp / "estate"), db_path=self.db)
        self.assertGreater(self.count("current_surface"), 0)

    def test_no_view_carries_a_name_another_graph_could_hold(self):
        # The mitigation is the name. A view prefixed like one of Orbit's own
        # tables could exist in their graph too, and the wrong-store query would
        # be back to answering rather than failing.
        for shape in load().tables:
            for prefix in store.ORBIT_OWNED_PREFIXES:
                self.assertFalse(shape.current_view.startswith(prefix),
                                 shape.current_view)


class TestTheViewsAreDeclaredByEveryPathIntoTheStore(SnapshotTestCase):
    def setUp(self):
        super().setUp()
        self.estate = build(self.tmp / "estate")
        index(self.estate, db_path=self.db)

    def views(self):
        # `internal` excludes DuckDB's own catalog views, which are in the same
        # listing and are not this store's.
        return {row[0] for row in
                self.sql("SELECT view_name FROM duckdb_views() WHERE NOT internal")}

    def test_indexing_declares_one_view_per_table(self):
        self.assertEqual(
            self.views(), {shape.current_view for shape in load().tables}
        )

    def test_migrating_declares_them_too(self):
        # A store brought to the ontology by `migrate` is one a reader queries
        # next, and a view left behind at the old shape is the failure mode the
        # migration exists to remove.
        connection = store.connect(self.db)
        try:
            connection.execute("DROP VIEW current_surface")
        finally:
            connection.close()
        migrate(self.db)
        self.assertIn("current_surface", self.views())

    def test_a_column_added_to_a_table_appears_in_its_view(self):
        # The declaration sits with the table, so there is no second place to
        # forget a column. Simulated with a column the ontology does not
        # declare, which is the only column this test can add.
        connection = store.connect(self.db)
        try:
            connection.execute("ALTER TABLE gl_context_surface ADD COLUMN activation VARCHAR")
            store.declare_views(connection, load().tables)
            self.assertIn("activation", store.existing_columns(connection, "current_surface"))
        finally:
            connection.close()

    def test_re_indexing_leaves_the_views_readable(self):
        before = self.count("current_surface")
        index(self.estate, db_path=self.db)
        self.assertEqual(self.count("current_surface"), before)


class TestTheDocumentedQueriesRun(SnapshotTestCase):
    """`orbit/README.md`'s queries, executed rather than read.

    Following the documentation is its own failure mode when the documentation
    names a table the store does not offer, and a reader has no way to tell the
    two apart from the error. So every documented query is run here against a
    fixture store.

    This class reads live repository content, which the rest of the file does
    not. The rule it is read against -- spec 0005's *"a test that reads live
    content fails whenever the content changes"* -- is about live *figures*, and
    keeps them in evidence records. There is no way to check that the documented
    queries run without reading the document, the acceptance asks for exactly
    that check, and `orbit/tests/test_pointers.py` already measures this
    repository's prose the same way. Every figure asserted here still comes from
    the fixture estate.
    """

    # A documented query that means to span runs says so in its own first line.
    # The marker is in the SQL rather than in this file so that the reason is
    # beside the query, where someone copying it will read it.
    ACROSS_RUNS = "-- across runs, deliberately"

    # The one name in the documented queries that is not this store's. It is
    # GitLab Orbit's own file table, reached through their CLI by ATTACH, and
    # `orbit/tests/test_join.py` is where that join is measured.
    ANOTHER_GRAPHS_TABLE = "gl_file"

    # Anchored at the start of a line so it matches the commands in the fenced
    # blocks and not the prose that names the same command mid-sentence.
    _QUERY = re.compile(
        r'^orbit local sql --db [^\n"]*(?:\\\n *)?"(.*?)"', re.DOTALL | re.MULTILINE
    )

    def setUp(self):
        super().setUp()
        index(build(self.tmp / "estate"), db_path=self.db)

    def documented(self):
        text = (support.ORBIT_ROOT / "README.md").read_text(encoding="utf-8")
        found = self._QUERY.findall(text)
        self.assertGreater(
            len(found), 10,
            "the pattern matched almost nothing, so this class is passing "
            "without reading the documented queries at all",
        )
        return found

    def test_every_documented_query_runs(self):
        skipped = set()
        for statement in self.documented():
            if self.ANOTHER_GRAPHS_TABLE in statement:
                skipped.add(self.ANOTHER_GRAPHS_TABLE)
                continue
            with self.subTest(query=statement[:60]):
                self.sql(statement)
        # Named rather than left as a silent exemption: a second table
        # appearing here is a documented query this store cannot answer.
        self.assertEqual(skipped, {self.ANOTHER_GRAPHS_TABLE})

    def test_the_documented_table_of_views_lists_what_the_store_declares(self):
        """The README pairs each view with its table by hand. Checked, not read.

        `declare_views` derives that pairing; the table restates it. A table
        added to the ontology gets a view without anyone editing the README, and
        the row that is then missing is the documentation failing quietly.
        """
        text = (support.ORBIT_ROOT / "README.md").read_text(encoding="utf-8")
        rows = re.findall(r"^\| `(current_[a-z_]+)` \| `(gl_context_[a-z_]+)`",
                          text, re.MULTILINE)
        self.assertEqual(
            {view: table for view, table in rows},
            {shape.current_view: shape.table for shape in load().tables},
        )

    def test_the_documented_queries_read_the_current_snapshot(self):
        """A documented example is the query a reader copies, so it is scoped.

        What this holds is that the example nobody reads twice before pasting
        answers for one commit. The base tables are still the way to ask across
        runs, and an example that means to is exempt -- by saying so in its own
        first line, which is the marker above rather than a list kept here.
        """
        for statement in self.documented():
            if self.ACROSS_RUNS in statement:
                continue
            with self.subTest(query=statement[:60]):
                for shape in load().tables:
                    self.assertNotIn(
                        shape.table, statement,
                        f"a documented query reads {shape.table} rather than "
                        f"{shape.current_view}. If it means to span runs, say so "
                        f"in its first line: {self.ACROSS_RUNS!r}",
                    )

    def test_asking_across_runs_is_documented_too(self):
        # Spec 0005 keeps the aggregate possible and makes it the deliberate
        # query. Deliberate is not the same as undocumented: an example exists,
        # it runs, and it says in its own first line what it is.
        across = [statement for statement in self.documented()
                  if self.ACROSS_RUNS in statement]
        self.assertEqual(len(across), 1)
        rows = self.sql(across[0])
        self.assertEqual(len(rows), 3)


class TestTheDetectorSetIsUnmoved(unittest.TestCase):
    """Views decide which rows an answer covers. Detectors decide what is
    recognised, and this work edits none of the five hashed modules."""

    def test_the_version_is_the_one_every_earlier_figure_was_taken_under(self):
        self.assertEqual(detectors.VERSION, DETECTOR_SET_VERSION)


if __name__ == "__main__":
    unittest.main()
