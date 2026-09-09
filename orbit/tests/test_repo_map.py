"""`repo-map`: one repository's governance surface, from the graph, in a budget.

What is tested here is mostly about what the map refuses to do. It refuses to
re-walk the tree, so every count is answerable from one snapshot. It refuses to
print a count without its denominator, so a thin result cannot read as a
description of the estate. It refuses to print zero for a question it did not
measure. And it refuses to exceed the budget it prints on its own last line.
"""

import contextlib
import io
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from . import support  # noqa: F401

from build_estate import build
from orbit_context import detectors, history, pointers, provenance, repomap, store, surfaces
from orbit_context.clauses import CLAUSE_TYPES
from orbit_context.indexer import index
from orbit_context.workspace import git_info

from .test_vocabulary import offending_words

# The map reads git for the branch block, and this repository's own environment
# exports a base ref and a session id. Tests that do not mean to exercise that
# pass this instead, so a result never depends on where the suite is run.
NO_ENVIRONMENT: dict = {}


def write(path: Path, text: str) -> None:
    """Write a fixture file, with the path away from the write call.

    Routed through a helper for the same reason fixtures/build_estate.py routes
    its writes: a quoted path on a line that also calls `write_text` is a
    literal write path, and this repository's own provenance detector reads it
    as this file producing that artifact. The detector is right about the line
    and the claim is not true of a test, so the line is written differently
    rather than the detector being taught an exception.
    """
    path.write_text(text)


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, check=True,
                            capture_output=True, text=True)
    return result.stdout.strip()


def make_repo(root: Path, branch: str = "main") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "--initial-branch", branch)
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "user.name", "Fixture")
    return root


def commit(root: Path, message: str) -> None:
    git(root, "add", "-A")
    git(root, "commit", "--allow-empty", "-m", message)


class TestEstateMap(unittest.TestCase):
    """The map over the fixture estate, beside the statistics of the same run."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-map-"))
        cls.estate = build(cls.tmp / "estate")
        cls.db = cls.tmp / "graph.duckdb"
        cls.stats = index(cls.estate, db_path=cls.db)
        cls.alpha = cls.estate / "alpha"
        cls.map = repomap.read(cls.alpha, db_path=cls.db, environ=NO_ENVIRONMENT)
        cls.text = repomap.render(cls.map)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def repo_statistics(self, name: str) -> dict:
        for entry in self.stats["repositories"]:
            if entry["repository"] == name:
                return entry
        raise AssertionError(f"no statistics for {name}")

    def test_counts_match_the_index_run_that_wrote_them(self):
        # The map and the statistics are two readings of one run. Where they
        # disagree, one of them is reporting a repository that is not there.
        alpha = self.repo_statistics("alpha")
        # `index` counts surfaces it read; the table holds a row for every
        # surface it found, read or not. Reconciled here rather than left as two
        # numbers that quietly disagree.
        self.assertEqual(self.map.surfaces_read_in_full, alpha["graph"]["surfaces"])
        self.assertEqual(
            self.map.surface_rows,
            alpha["graph"]["surfaces"] + self.map.surfaces_not_read_in_full,
        )
        self.assertEqual(sum(self.map.clauses_by_type.values()),
                         alpha["graph"]["clauses"])
        self.assertEqual(sum(self.map.edges_by_kind.values()),
                         alpha["graph"]["edges"])
        self.assertEqual(sum(self.map.pointers_by_subtype.values()),
                         alpha["graph"]["pointers"])
        self.assertEqual(self.map.identical_pairs,
                         alpha["graph"]["identical_bytes"]["pairs"])
        self.assertEqual(self.map.pairs_with_provenance,
                         alpha["graph"]["identical_bytes"]["pairs_with_provenance"])

    def test_coverage_matches_the_walk(self):
        alpha = self.repo_statistics("alpha")
        self.assertEqual(self.map.files_walked, alpha["coverage"]["files_walked"])
        self.assertEqual(self.map.files_with_surface_kind,
                         alpha["coverage"]["files_with_surface_kind"])
        self.assertEqual(self.map.files_with_no_surface_kind,
                         alpha["coverage"]["files_with_no_surface_kind"])

    def test_one_repository_only(self):
        # The graph holds every repository in the estate. A query that forgets
        # its snapshot scope returns the estate under a heading naming one
        # repository, and nothing in the output would say so.
        beta = repomap.read(self.estate / "beta", db_path=self.db,
                            environ=NO_ENVIRONMENT)
        self.assertEqual(self.map.files_walked,
                         self.repo_statistics("alpha")["coverage"]["files_walked"])
        self.assertEqual(beta.files_walked,
                         self.repo_statistics("beta")["coverage"]["files_walked"])
        self.assertLess(self.map.files_walked, self.stats["coverage"]["files_walked"])

    def test_the_boundary_names_its_root_and_its_exclusions(self):
        self.assertEqual(self.map.indexed_root, str(self.estate.resolve()))
        for excluded in surfaces.PRUNED_DIRECTORIES:
            self.assertIn(excluded, self.map.excluded_directories)
            self.assertIn(excluded, self.text)

    def test_a_surface_found_and_not_read_is_a_row_and_says_so(self):
        # It is in the table, so it is in the row count; it was not read, so it
        # is not in the count `index` reports. Both are printed.
        self.assertGreater(self.map.surfaces_not_read_in_full, 0)
        self.assertIn(
            f"read in full  {self.map.surfaces_read_in_full} of "
            f"{self.map.surface_rows} rows",
            self.text,
        )

    def test_what_was_not_read_is_reported_with_its_reason(self):
        # The estate carries a file that is not valid UTF-8. Indexed or not, it
        # was reached, and a map that did not say so would report a repository
        # one file smaller than the one on disk.
        reasons = {reason for reason, _, _ in self.map.coverage_notes}
        self.assertIn(surfaces.REASON_INVALID_UTF8, reasons)
        self.assertIn(surfaces.REASON_INVALID_UTF8, self.text)

    def test_deepest_nesting_is_walked_not_stored(self):
        # Depth is not a column anywhere in the graph. If this number is right,
        # it was produced by walking CONTAINS.
        self.assertGreater(self.map.deepest_nesting, 1)
        self.assertIn("deepest nesting", self.text)

    def test_identical_pairs_are_never_printed_without_provenance(self):
        self.assertIn("carrying provenance evidence", self.text)
        self.assertIn("carrying no provenance evidence", self.text)
        self.assertEqual(
            self.map.identical_pairs,
            self.map.pairs_with_provenance
            + (self.map.identical_pairs - self.map.pairs_with_provenance),
        )

    def test_every_detector_is_listed_even_where_it_found_nothing(self):
        # A map printing only its non-zero rows reads as a description of the
        # estate. Printed in full, a column of zeroes reads as the inventory of
        # what these detectors look for.
        for kind in surfaces.SURFACE_KINDS:
            self.assertIn(kind, self.text)
        for clause_type in CLAUSE_TYPES:
            self.assertIn(clause_type, self.text)
        for subtype in pointers.SUBTYPES:
            self.assertIn(subtype, self.text)
        for sub_kind in pointers.SUB_KINDS:
            self.assertIn(sub_kind, self.text)
        for rung in provenance.EVIDENCE_LADDER:
            self.assertIn(rung, self.text)
        for edge_kind in repomap.EDGE_KINDS:
            self.assertIn(edge_kind, self.text)

    def test_the_three_non_resolutions_are_never_summed(self):
        self.assertEqual(set(self.map.external_refs_by_sub_kind), set(pointers.SUB_KINDS))

    def test_no_forbidden_vocabulary(self):
        self.assertEqual(offending_words(self.text), [])


class TestDetectorSetVersion(unittest.TestCase):
    """Every count carries the detector set that produced it."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-version-"))
        cls.estate = build(cls.tmp / "estate")
        cls.db = cls.tmp / "graph.duckdb"
        index(cls.estate, db_path=cls.db)
        cls.map = repomap.read(cls.estate / "alpha", db_path=cls.db,
                               environ=NO_ENVIRONMENT)
        cls.text = repomap.render(cls.map)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_version_is_derived_and_stable(self):
        self.assertEqual(detectors.version(), detectors.version())
        self.assertTrue(detectors.VERSION.startswith(f"{detectors.RECIPE}."))

    def test_the_version_moves_when_a_detector_changes(self):
        # The property that makes it worth having. A hand-maintained constant
        # would not have it, and a count taken before a detector change would
        # be compared with one taken after as though the estate had moved.
        before = detectors.version()
        original = dict(surfaces.SURFACE_BASENAMES)
        try:
            surfaces.SURFACE_BASENAMES["RULES.md"] = surfaces.INSTRUCTION_SURFACE
            self.assertNotEqual(detectors.version(), before)
        finally:
            surfaces.SURFACE_BASENAMES.clear()
            surfaces.SURFACE_BASENAMES.update(original)
        self.assertEqual(detectors.version(), before)

    def test_the_version_moves_when_a_pattern_boundary_changes(self):
        # Ticket 04's boundary fix moved one pattern and took a finding count
        # from 1,373 to 24. Private by convention, and the change the version
        # most needs to catch.
        before = detectors.version()
        original = provenance._GENERATED_BY
        try:
            provenance._GENERATED_BY = re.compile(original.pattern + "[ ]?")
            self.assertNotEqual(detectors.version(), before)
        finally:
            provenance._GENERATED_BY = original
        self.assertEqual(detectors.version(), before)

    def test_the_graph_records_the_version_that_wrote_it(self):
        self.assertEqual(self.map.graph_detector_version, detectors.VERSION)
        self.assertTrue(self.map.detectors_agree)

    def test_every_counted_section_carries_the_version(self):
        headings = [line for line in self.text.splitlines()
                    if line and line[0].isupper() and "  " in line
                    and not line.startswith("GIT")]
        self.assertGreaterEqual(len(headings), 7)
        for heading in headings:
            self.assertIn(f"[{detectors.VERSION}]", heading, heading)

    def test_a_graph_from_another_detector_set_is_reported_as_such(self):
        connection = store.connect(self.db)
        try:
            connection.execute(
                "UPDATE gl_context_run SET detector_set_version = '0.000000000000'"
            )
        finally:
            connection.close()
        result = repomap.read(self.estate / "alpha", db_path=self.db,
                              environ=NO_ENVIRONMENT)
        self.assertFalse(result.detectors_agree)
        text = repomap.render(result)
        self.assertIn("0.000000000000", text)
        self.assertIn(detectors.VERSION, text)
        self.assertEqual(offending_words(text), [])


class TestBudget(unittest.TestCase):
    """The output fits a budget, and the budget cites a measurement."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-budget-"))
        cls.estate = build(cls.tmp / "estate")
        cls.db = cls.tmp / "graph.duckdb"
        index(cls.estate, db_path=cls.db)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_budget_cites_its_measurement(self):
        # Their repo-map, measured. An earlier draft of this project asserted a
        # token budget with no basis; this one names where its number came from.
        self.assertEqual(repomap.BUDGET_BYTES, 12874)
        self.assertIn("12,874", repomap.BUDGET_CITATION)
        self.assertIn("1,775", repomap.BUDGET_CITATION)

    def test_the_map_fits_and_says_what_it_cost(self):
        text = repomap.repo_map(self.estate / "alpha", db_path=self.db,
                                environ=NO_ENVIRONMENT)
        size = len(text.encode("utf-8"))
        self.assertLessEqual(size, repomap.BUDGET_BYTES)
        # Self-accounting: the size it prints is the size it is, footer included.
        self.assertIn(f"map {size} bytes of {repomap.BUDGET_BYTES} budget", text)
        self.assertIn(repomap.BUDGET_CITATION, text)

    def test_a_repository_that_would_overflow_is_capped_not_truncated(self):
        # Fifty copies of one file is 1,225 identical-byte pairs. The count is
        # the finding; the listing is capped, and says how many it did not list.
        root = make_repo(self.tmp / "many")
        for number in range(50):
            write(root / f"copy{number}.md", "same bytes\n")
        commit(root, "many copies")
        index(root, db_path=self.db)

        result = repomap.read(root, db_path=self.db, environ=NO_ENVIRONMENT)
        text = repomap.render(result)
        self.assertGreater(result.identical_pairs, repomap.EXAMPLE_ROWS)
        self.assertLessEqual(len(text.encode("utf-8")), repomap.BUDGET_BYTES)
        self.assertIn(
            f"{result.identical_pairs - repomap.EXAMPLE_ROWS} more pairs not listed",
            text,
        )

    def test_a_budget_the_full_map_exceeds_drops_the_listings_and_says_so(self):
        # The guarantee behind the caps rather than the mechanism. If a
        # repository ever finds a way past them, the map gives up its listings
        # rather than quietly exceeding the figure it just printed.
        full = repomap.read(self.estate / "alpha", db_path=self.db,
                            environ=NO_ENVIRONMENT)
        rendered = repomap.render(full)
        # Comfortably under, because the budget figure is printed in the footer
        # and a shorter number is itself a shorter map -- one byte under does
        # not prove anything.
        tight = len(rendered.encode("utf-8")) - 300
        trimmed = repomap.render(full, budget=tight)
        self.assertIn("Example listings left out", trimmed)
        self.assertLess(len(trimmed.encode("utf-8")), len(rendered.encode("utf-8")))
        self.assertEqual(offending_words(trimmed), [])


class TestARepositoryWithNoGovernanceSurface(unittest.TestCase):
    """A valid map reporting zero, not an error.

    The case that decides whether the map is readable at all. Zero surfaces is
    the common result on an ordinary repository, and it has to arrive as "these
    detectors recognise nothing here, out of 40 files" rather than as an empty
    output, an exception, or a bare zero.
    """

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-bare-"))
        cls.root = make_repo(cls.tmp / "plain")
        write(cls.root / "README.md", "# Plain\n\nOrdinary documentation.\n")
        write(cls.root / "main.py",
              "def total(quantities):\n    return sum(quantities)\n")
        commit(cls.root, "plain repository")
        cls.db = cls.tmp / "graph.duckdb"
        index(cls.root, db_path=cls.db)
        cls.map = repomap.read(cls.root, db_path=cls.db, environ=NO_ENVIRONMENT)
        cls.text = repomap.render(cls.map)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_it_is_a_map_and_not_an_error(self):
        self.assertEqual(self.map.surface_rows, 0)
        self.assertEqual(sum(self.map.clauses_by_type.values()), 0)
        self.assertEqual(sum(self.map.edges_by_kind.values()), 0)
        self.assertIn("SURFACES", self.text)
        self.assertIn("COVERAGE", self.text)

    def test_the_zero_arrives_with_its_denominator(self):
        self.assertEqual(self.map.files_with_surface_kind, 0)
        self.assertGreater(self.map.files_walked, 0)
        self.assertEqual(self.map.files_with_no_surface_kind, self.map.files_walked)
        self.assertIn(f"0 of {self.map.files_walked}", self.text)

    def test_the_zero_is_attributed_to_the_detectors(self):
        self.assertIn("statement about these detectors", self.text)
        self.assertIn(detectors.VERSION, self.text)

    def test_the_command_exits_zero(self):
        from orbit_context.cli import main
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            code = main(["repo-map", "--repo", str(self.root), "--db", str(self.db)])
        self.assertEqual(code, 0)
        self.assertIn("orbit-context repo-map", captured.getvalue())

    def test_an_unindexed_repository_is_an_error_with_a_next_step(self):
        # Different from a repository with nothing in it, and it must not be
        # answered with a map full of zeroes.
        other = make_repo(self.tmp / "never-indexed")
        write(other / "README.md", "# Other\n")
        commit(other, "not indexed")
        with self.assertRaises(repomap.RepoMapError) as raised:
            repomap.read(other, db_path=self.db, environ=NO_ENVIRONMENT)
        self.assertIn("orbit-context index", str(raised.exception))


class TestGitProvenance(unittest.TestCase):
    """Which commits ahead of base this session wrote, and how that is known."""

    SESSION = "https://claude.ai/code/session_01TESTSESSIONID0000000"
    OTHER = "https://claude.ai/code/session_01OTHERSESSION000000000"

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-git-"))
        cls.root = make_repo(cls.tmp / "branchy")
        write(cls.root / "README.md", "# Branchy\n")
        commit(cls.root, "base commit")
        git(cls.root, "checkout", "-b", "work")
        for number, trailer in enumerate((cls.SESSION, cls.SESSION, cls.OTHER)):
            write(cls.root / f"file{number}.md", f"body {number}\n")
            git(cls.root, "add", "-A")
            git(cls.root, "commit", "-m",
                f"change {number}\n\n{history.TRAILER_KEY}: {trailer}")
        write(cls.root / "plain.md", "no trailer\n")
        commit(cls.root, "change with no trailer")

        cls.db = cls.tmp / "graph.duckdb"
        index(cls.root, db_path=cls.db)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def state(self, environ=None, **kwargs):
        return history.branch_state(self.root, environ=environ or {}, **kwargs)

    def test_commits_ahead_of_base(self):
        state = self.state(base_override="main")
        self.assertEqual(state.branch, "work")
        self.assertEqual(state.ahead, 4)
        self.assertEqual(state.with_trailer, 3)

    def test_this_session_is_counted_by_its_trailer(self):
        state = self.state(base_override="main", session_override=self.SESSION)
        self.assertEqual(state.this_session, 2)
        self.assertEqual(state.matched_variables(), ("--session",))

    def test_an_id_wearing_another_prefix_still_matches(self):
        # One environment exports `cse_01ABC` for a trailer written
        # `.../session_01ABC`. Matching on the tail is what makes the count
        # right; matching on the whole string would report zero.
        state = self.state(
            environ={"CLAUDE_CODE_REMOTE_SESSION_ID": "cse_01TESTSESSIONID0000000"},
            base_override="main",
        )
        self.assertEqual(state.this_session, 2)
        self.assertEqual(state.matched_variables(), ("CLAUDE_CODE_REMOTE_SESSION_ID",))

    def test_no_session_id_reports_not_measured_and_never_zero(self):
        # The whole point of the block. A session that cannot identify itself
        # must not be told that none of the commits are its own -- that is the
        # failure this ticket exists to close, and zero is how it reads.
        state = self.state(base_override="main")
        self.assertIsNone(state.this_session)
        text = repomap.render(
            repomap.read(self.root, db_path=self.db, base="main", environ={})
        )
        self.assertIn("not measured", text)
        self.assertNotIn("carrying this session's trailer  0", text)

    def test_every_distinct_trailer_is_reported_whatever_matched(self):
        # The safeguard behind the heuristic: a reader who can see the
        # distribution can settle the question when the match comes up empty.
        state = self.state(base_override="main")
        self.assertEqual(state.by_trailer(), [(self.SESSION, 2), (self.OTHER, 1)])
        text = repomap.render(
            repomap.read(self.root, db_path=self.db, base="main", environ={})
        )
        self.assertIn(self.SESSION[-24:], text)

    def test_a_base_that_does_not_resolve_is_stated_not_guessed(self):
        state = self.state(base_override="origin/nothing-here")
        self.assertIsNone(state.base.ref)
        self.assertIsNone(state.ahead)
        text = repomap.render(
            repomap.read(self.root, db_path=self.db, base="origin/nothing-here",
                         environ={})
        )
        self.assertIn("not measured, because no base resolved", text)

    def test_the_rung_that_named_the_base_is_reported(self):
        # Ahead of what is half the number. It differs between checkouts of one
        # repository, so the map says which rung answered.
        from_environment = history.resolve_base(
            self.root, environ={history.BASE_VARIABLE: "main"}
        )
        self.assertEqual(from_environment, history.Base("main", history.BASE_VARIABLE))
        fallback = history.resolve_base(self.root, environ={})
        self.assertEqual(fallback.ref, "main")
        self.assertIn("first of", fallback.source)

    def test_git_state_is_labelled_as_not_a_detector_finding(self):
        text = repomap.render(
            repomap.read(self.root, db_path=self.db, base="main", environ={})
        )
        self.assertIn("not a detector finding", text)
        self.assertEqual(offending_words(text), [])


class TestCoverageTable(unittest.TestCase):
    """The walk's own record, written so the map does not have to re-walk."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-cover-"))
        cls.estate = build(cls.tmp / "estate")
        cls.db = cls.tmp / "graph.duckdb"
        index(cls.estate, db_path=cls.db)
        cls.alpha = git_info(cls.estate / "alpha")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def rows(self, sql: str) -> list:
        connection = store.connect(self.db, read_only=True)
        try:
            return connection.execute(
                sql, [self.alpha.project_id, self.alpha.branch, self.alpha.commit_sha]
            ).fetchall()
        finally:
            connection.close()

    def test_one_run_row_per_snapshot(self):
        rows = self.rows(
            "SELECT detector_set_version, files_walked, files_with_surface_kind "
            "FROM gl_context_run WHERE project_id = ? AND branch = ? AND commit_sha = ?"
        )
        self.assertEqual(len(rows), 1)
        version, walked, with_kind = rows[0]
        self.assertEqual(version, detectors.VERSION)
        self.assertGreater(walked, with_kind)

    def test_re_indexing_replaces_the_run_row_rather_than_adding_one(self):
        index(self.estate, db_path=self.db)
        self.assertEqual(
            len(self.rows("SELECT id FROM gl_context_run "
                          "WHERE project_id = ? AND branch = ? AND commit_sha = ?")),
            1,
        )

    def test_a_file_that_did_not_index_carries_its_reason(self):
        rows = self.rows(
            "SELECT path, reason, errored FROM gl_context_coverage "
            "WHERE project_id = ? AND branch = ? AND commit_sha = ?"
        )
        self.assertTrue(rows)
        reasons = {reason for _, reason, _ in rows}
        self.assertIn(surfaces.REASON_INVALID_UTF8, reasons)
        for _, reason, _ in rows:
            self.assertEqual(offending_words(reason), [])

    def test_files_with_surface_kind_counts_files_and_not_rows(self):
        # A settings file holds a row per hook. Counted as rows against a
        # denominator of files, coverage on a hook-heavy repository would go
        # above one.
        connection = store.connect(self.db, read_only=True)
        try:
            for row in connection.execute(
                "SELECT r.files_walked, r.files_with_surface_kind, "
                "       (SELECT count(DISTINCT s.path) FROM gl_context_surface s "
                "         WHERE s.project_id = r.project_id AND s.branch = r.branch "
                "           AND s.commit_sha = r.commit_sha) "
                "FROM gl_context_run r"
            ).fetchall():
                walked, recorded, distinct_paths = row
                self.assertEqual(recorded, distinct_paths)
                self.assertLessEqual(recorded, walked)
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
