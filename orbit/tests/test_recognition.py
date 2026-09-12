"""Recognition without a vendor name, at Seam A and at Seam B.

Phase 1 recognised governance by the name a vendor gave it. Run against a
repository whose whole content is governance and none of it vendor-named, it
found nothing. Ticket 10 adds two rules on top of that one, and what is asserted
here is that all three run together without interfering, and that the one rule
that infers is separable from the two that do not.

Counts are against ``build_lineage``, never against a live repository: a test
that reads real repository content fails whenever that content changes,
including from this work. The acceptance run is evidence, recorded in the
ticket.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from . import support

from build_lineage import build
from orbit_context import repomap, surfaces
from orbit_context.indexer import index


def _rows(db_path: Path, columns: str, where: str = "") -> list[tuple]:
    import duckdb

    connection = duckdb.connect(str(db_path), read_only=True)
    try:
        clause = f" WHERE {where}" if where else ""
        return connection.execute(
            f"SELECT {columns} FROM gl_context_surface{clause} ORDER BY path"
        ).fetchall()
    finally:
        connection.close()


class TestRecognition(unittest.TestCase):
    """Seam A: build the estate, index it, assert on the stats and the rows."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-recognition-"))
        cls.estate = build(cls.tmp / "estate")
        cls.db = cls.tmp / "graph.duckdb"
        cls.stats = index(cls.estate, db_path=cls.db)
        cls.by_repo = {entry["repository"]: entry for entry in cls.stats["repositories"]}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_a_repository_with_no_vendor_name_is_no_longer_empty(self):
        # The finding this ticket exists for: phase 1 returned 0 here.
        #
        # 16 when ticket 10 wrote this. Ticket 11 put three more declared files
        # in the fixture -- `clean-code/clean-code.md`,
        # `clean-code/clean-code.nano.md` and `drafts/takeoff.mini.md`, a book
        # at two rungs and a rung word with no base rung -- and the three are
        # what this number moved by. Reconciled against the named files rather
        # than re-baselined.
        self.assertEqual(self.by_repo["ladder"]["graph"]["surfaces"], 19)

    def test_the_ladder_is_recognised_rung_by_rung(self):
        found = {
            path for (path,) in _rows(
                self.db, "path", "branch = 'main' AND path LIKE 'refactoring/%'"
            )
        }
        self.assertEqual(found, {
            "refactoring/refactoring.md",
            "refactoring/refactoring.mini.md",
            "refactoring/refactoring.nano.md",
        })

    def test_recognition_is_recorded_per_surface(self):
        self.assertEqual(
            self.by_repo["ladder"]["graph"]["recognition"],
            {
                surfaces.RECOGNITION_VENDOR_NAME: 0,
                # 14 at ticket 10, plus the three files ticket 11 added. Each
                # opens with a directive heading, so all three arrive by
                # declaration and the inferred count is unmoved -- which is the
                # half of this split that matters.
                surfaces.RECOGNITION_DECLARED_MARKER: 17,
                surfaces.RECOGNITION_CORPUS_ADJACENT: 2,
            },
        )

    def test_what_was_inferred_is_named_and_separable(self):
        # The two files that carry no heading of their own. They are recognised
        # from the directory they sit in, and the row says exactly that.
        inferred = {
            path for (path,) in _rows(
                self.db, "path",
                f"branch = 'main' AND recognition = "
                f"'{surfaces.RECOGNITION_CORPUS_ADJACENT}'",
            )
        }
        self.assertEqual(inferred, {
            "_rule-workbench/PROCESS.md",
            "_rule-workbench/RELEASE.md",
        })

    def test_a_directory_under_the_share_recognises_only_what_declared_itself(self):
        # notes/ is two of three. The two say so themselves and are surfaces;
        # the third is not, and the directory does not carry it in.
        found = {
            path for (path,) in _rows(
                self.db, "path", "branch = 'main' AND path LIKE 'notes/%'"
            )
        }
        self.assertEqual(found, {"notes/one.md", "notes/two.md"})

    def test_documentation_about_the_rules_is_not_a_rule(self):
        self.assertEqual(
            _rows(self.db, "path", "branch = 'main' AND path LIKE 'docs/%'"), []
        )

    def test_the_repository_root_is_out_of_the_corpus_rule_s_reach(self):
        self.assertEqual(
            _rows(self.db, "path", "branch = 'main' AND path = 'README.md'"), []
        )

    def test_recognition_did_not_widen_to_every_file(self):
        # Spec 0002 s12: a detector that finds everything has learned nothing
        # that `find` did not already know.
        coverage = self.by_repo["ladder"]["coverage"]
        self.assertLess(coverage["files_with_surface_kind"], coverage["files_walked"])
        self.assertGreater(coverage["files_with_no_surface_kind"], 0)


class TestTheTwoPathsDoNotInterfere(unittest.TestCase):
    """The vendor repository, indexed in the same estate as the corpus one."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-both-paths-"))
        cls.estate = build(cls.tmp / "estate")
        cls.db = cls.tmp / "graph.duckdb"
        cls.stats = index(cls.estate, db_path=cls.db)
        cls.by_repo = {entry["repository"]: entry for entry in cls.stats["repositories"]}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_vendor_names_are_still_recognised(self):
        found = dict(_rows(self.db, "path, recognition", "branch = 'trunk'"))
        self.assertEqual(found[".claude/agents/takeoff-reviewer.md"],
                         surfaces.RECOGNITION_VENDOR_NAME)
        self.assertEqual(found["AGENTS.md"], surfaces.RECOGNITION_VENDOR_NAME)

    def test_a_vendor_name_outranks_a_heading_on_the_same_file(self):
        # vendor/CLAUDE.md carries both. A vendor filename is the older and
        # narrower statement, so it is the one recorded.
        found = dict(_rows(self.db, "path, recognition", "branch = 'trunk'"))
        self.assertEqual(found["CLAUDE.md"], surfaces.RECOGNITION_VENDOR_NAME)

    def test_both_paths_run_in_one_repository(self):
        self.assertEqual(
            self.by_repo["vendor"]["graph"]["recognition"],
            {
                surfaces.RECOGNITION_VENDOR_NAME: 6,
                surfaces.RECOGNITION_DECLARED_MARKER: 3,
                surfaces.RECOGNITION_CORPUS_ADJACENT: 0,
            },
        )

    def test_a_vendor_name_does_not_make_its_directory_a_corpus(self):
        # skills/ holds three vendor-named surfaces and a README that declared
        # nothing. A vendor name is a statement about one file; the directory
        # share counts only what declared itself, so the README stays out.
        found = {
            path for (path,) in _rows(
                self.db, "path", "branch = 'trunk' AND path LIKE 'skills/%'"
            )
        }
        self.assertEqual(found, {
            "skills/anchors/SKILL.md",
            "skills/channels/SKILL.md",
            "skills/fixings/SKILL.md",
        })

    def test_the_estate_total_is_the_two_repositories(self):
        # 25 and 17 at ticket 10; the three files ticket 11 added to the ladder
        # repository are the whole difference, and the vendor repository is
        # untouched at 6 and 3.
        self.assertEqual(self.stats["graph"]["surfaces"], 28)
        self.assertEqual(
            self.stats["graph"]["recognition"],
            {
                surfaces.RECOGNITION_VENDOR_NAME: 6,
                surfaces.RECOGNITION_DECLARED_MARKER: 20,
                surfaces.RECOGNITION_CORPUS_ADJACENT: 2,
            },
        )

    def test_every_recognition_value_is_one_the_ontology_names(self):
        values = {value for (value,) in _rows(self.db, "DISTINCT recognition")}
        self.assertTrue(values)
        self.assertTrue(values <= set(surfaces.RECOGNITION_KINDS), values)


class TestTheSplitAddsUpToTheCount(unittest.TestCase):
    """Against the phase 1 estate, which holds a surface that cannot be read.

    ``build_estate`` is untouched and is used here read-only. A candidate that
    fails to read still becomes a row carrying its reason, and it is not counted
    as a surface -- so a split taken over every row would not sum to the total it
    is printed beside.
    """

    @classmethod
    def setUpClass(cls):
        from build_estate import build as build_phase_one

        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-split-"))
        cls.estate = build_phase_one(cls.tmp / "estate")
        cls.stats = index(cls.estate, db_path=cls.tmp / "graph.duckdb")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_estate_split_sums_to_the_estate_count(self):
        self.assertEqual(
            sum(self.stats["graph"]["recognition"].values()),
            self.stats["graph"]["surfaces"],
        )

    def test_every_repository_s_split_sums_to_its_own_count(self):
        for entry in self.stats["repositories"]:
            with self.subTest(repository=entry["repository"]):
                self.assertEqual(
                    sum(entry["graph"]["recognition"].values()),
                    entry["graph"]["surfaces"],
                )

    def test_the_estate_really_does_hold_a_surface_that_was_not_read(self):
        # Without this the two sums above would pass on an estate where every
        # candidate read cleanly, which is not the case they are guarding.
        detailed = index(self.estate, db_path=self.tmp / "detailed.duckdb",
                         detailed=True)
        reasons = {
            entry["reason"] for entry in detailed["detailed"]["skipped_files"]
        }
        self.assertIn(surfaces.REASON_INVALID_UTF8, reasons)


class TestSeamB(unittest.TestCase):
    """The command line, tested the way the comparison is run."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-recognition-cli-"))
        cls.estate = build(cls.tmp / "estate")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_index_reports_the_recognition_split_beside_the_count(self):
        completed = subprocess.run(
            [sys.executable, "-m", "orbit_context.cli", "index", str(self.estate),
             "--db", str(self.tmp / "cli.duckdb")],
            cwd=str(support.ORBIT_ROOT), capture_output=True, text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        statistics = json.loads(completed.stdout)
        self.assertEqual(statistics["graph"]["surfaces"], 28)
        self.assertEqual(
            statistics["graph"]["recognition"][surfaces.RECOGNITION_CORPUS_ADJACENT], 2
        )
        # The version every count above was produced by. Two counts either side
        # of this ticket are not comparable, and the output has to say so.
        self.assertIn("detector_set_version", statistics)

    def test_a_row_written_before_the_column_existed_is_named_not_dropped(self):
        # A snapshot indexed before `recognition` was declared carries the
        # column's default. Dropped, its repository would print an all-zero
        # split beside a surface count that is not zero -- which reads as an
        # estate the rules found nothing in, rather than as rows that predate
        # the rules.
        import duckdb

        db = self.tmp / "older.duckdb"
        indexed = subprocess.run(
            [sys.executable, "-m", "orbit_context.cli", "index", str(self.estate),
             "--db", str(db)],
            cwd=str(support.ORBIT_ROOT), capture_output=True, text=True,
        )
        self.assertEqual(indexed.returncode, 0, indexed.stderr)
        connection = duckdb.connect(str(db))
        try:
            connection.execute(
                "UPDATE gl_context_surface SET recognition = '' "
                "WHERE branch = 'trunk'"
            )
        finally:
            connection.close()

        mapped = subprocess.run(
            [sys.executable, "-m", "orbit_context.cli", "repo-map",
             "--repo", str(self.estate / "vendor"), "--db", str(db)],
            cwd=str(support.ORBIT_ROOT), capture_output=True, text=True,
        )
        self.assertEqual(mapped.returncode, 0, mapped.stderr)
        # Named, with the whole snapshot's nine files behind it, rather than a
        # split of three zeroes sitting under a count of nine.
        self.assertRegex(
            mapped.stdout, rf"{repomap.RECOGNITION_NOT_RECORDED}\s+9\b"
        )

    def test_the_orientation_command_says_what_it_read_rather_than_was_told(self):
        db = self.tmp / "map.duckdb"
        indexed = subprocess.run(
            [sys.executable, "-m", "orbit_context.cli", "index", str(self.estate),
             "--db", str(db)],
            cwd=str(support.ORBIT_ROOT), capture_output=True, text=True,
        )
        self.assertEqual(indexed.returncode, 0, indexed.stderr)
        mapped = subprocess.run(
            [sys.executable, "-m", "orbit_context.cli", "repo-map",
             "--repo", str(self.estate / "ladder"), "--db", str(db)],
            cwd=str(support.ORBIT_ROOT), capture_output=True, text=True,
        )
        self.assertEqual(mapped.returncode, 0, mapped.stderr)
        self.assertIn("recognised by", mapped.stdout)
        self.assertIn(surfaces.RECOGNITION_CORPUS_ADJACENT, mapped.stdout)
        # Not just present in the tally -- called out for what it is.
        self.assertIn("read off a directory rather than stated by the estate: 2",
                      mapped.stdout)


if __name__ == "__main__":
    unittest.main()
