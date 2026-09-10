"""The ladder: rungs of one book, related by name, read back out of the graph.

Advisor-Desk implements progressive disclosure by hand, fourteen times -- one
book at three sizes, so a session loads the rung its workflow can afford. It is
the stated purpose of the whole project and it was invisible to the graph: three
files per book with no relation between them.

What is asserted here is that the relation is a first-class edge, that a ladder
comes back rung by rung in size order with its byte counts, and that the two
things this tool cannot see are named rather than counted as zero -- which rung
a session loaded, and a rung word whose base rung is not in the tree.

Counts are against ``build_lineage``, never against a live repository: a test
that reads real repository content fails whenever that content changes,
including from this work. The acceptance run is evidence, recorded in the
ticket.
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from . import support

from build_lineage import build
from orbit_context import ladders, repomap, surfaces
from orbit_context.indexer import index

from .test_vocabulary import offending_words


def _edges(db_path: Path, branch: str) -> list[tuple]:
    import duckdb

    connection = duckdb.connect(str(db_path), read_only=True)
    try:
        return connection.execute(
            "SELECT source_path, target_path, subtype, source_kind, target_kind "
            "FROM gl_context_edge "
            "WHERE relationship_kind = 'RUNG_OF' AND branch = ? "
            "ORDER BY source_path",
            [branch],
        ).fetchall()
    finally:
        connection.close()


class TestTheRelationIsWritten(unittest.TestCase):
    """Seam A: build the estate, index it, assert on the stats and the rows."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-ladders-"))
        cls.estate = build(cls.tmp / "estate")
        cls.db = cls.tmp / "graph.duckdb"
        cls.stats = index(cls.estate, db_path=cls.db)
        cls.by_repo = {entry["repository"]: entry for entry in cls.stats["repositories"]}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_edge_type_is_one_the_ontology_declares(self):
        from orbit_context.ontology import load

        edge = load().edges[ladders.RUNG_OF_EDGE]
        self.assertTrue(edge.allows("Surface", "Surface"))

    def test_every_ladder_in_the_repository_is_found(self):
        found = self.by_repo["ladder"]["graph"]["ladders"]
        self.assertEqual(found["found"], 2)
        self.assertEqual(found["rungs"], 5)

    def test_a_book_with_fewer_rungs_is_a_count_and_not_a_finding(self):
        # Two of three is an observation about that book. It is reported as the
        # height it has, beside the book that carries three.
        self.assertEqual(
            self.by_repo["ladder"]["graph"]["ladders"]["ladders_by_rung_count"],
            {"2": 1, "3": 1},
        )

    def test_a_rung_word_with_no_base_rung_is_counted_and_not_dropped(self):
        # `drafts/takeoff.mini.md` names a rung and nothing in its directory is
        # named by the stem alone. An edge needs both ends, so no edge is
        # written -- and the rung the estate wrote is reported rather than
        # disappearing into the difference between two numbers.
        self.assertEqual(
            self.by_repo["ladder"]["graph"]["ladders"]["rungs_with_no_base_rung"], 1
        )

    def test_the_edge_leaves_the_rung_and_enters_the_base_rung(self):
        self.assertEqual(
            [(source, target) for source, target, _, _, _ in _edges(self.db, "main")],
            [
                ("clean-code/clean-code.nano.md", "clean-code/clean-code.md"),
                ("refactoring/refactoring.mini.md", "refactoring/refactoring.md"),
                ("refactoring/refactoring.nano.md", "refactoring/refactoring.md"),
            ],
        )

    def test_the_edge_carries_the_rung_word_the_filename_gave_it(self):
        by_source = {
            source: subtype for source, _, subtype, _, _ in _edges(self.db, "main")
        }
        self.assertEqual(by_source["refactoring/refactoring.mini.md"], "mini")
        self.assertEqual(by_source["refactoring/refactoring.nano.md"], "nano")

    def test_both_ends_are_surfaces(self):
        # A rung is a whole file that this tool already recognised as
        # governance. A file that is not a surface is not a rung of anything
        # the graph can be asked about.
        for _, _, _, source_kind, target_kind in _edges(self.db, "main"):
            self.assertEqual((source_kind, target_kind), ("Surface", "Surface"))

    def test_the_second_naming_shape_in_this_estate_is_not_keyed_on(self):
        # The workbench names its rungs `mini.md` and `nano.md`, with no stem in
        # front. The rule keys on a stem, so those are not rungs here -- stated
        # and asserted, rather than left to be discovered on a repository
        # nobody has looked at.
        sources = {source for source, _, _, _, _ in _edges(self.db, "main")}
        self.assertEqual(
            [path for path in sources if path.startswith("_rule-workbench/")], []
        )

    def test_a_repository_naming_nothing_this_way_finds_no_ladders(self):
        found = self.by_repo["vendor"]["graph"]["ladders"]
        self.assertEqual(found["found"], 0)
        self.assertEqual(found["rungs"], 0)
        self.assertEqual(_edges(self.db, "trunk"), [])

    def test_the_estate_total_is_the_two_repositories(self):
        self.assertEqual(self.stats["graph"]["ladders"]["found"], 2)
        self.assertEqual(self.stats["graph"]["ladders"]["rungs"], 5)

    def test_the_rung_edges_are_counted_in_the_edge_total(self):
        # The edge total has to reconcile without a remainder, or a new edge
        # type is a count that appears from nowhere.
        self.assertEqual(len(_edges(self.db, "main")), 3)


class TestTheLadderIsQueryable(unittest.TestCase):
    """The demo: ask for one book's ladder, get its rungs in size order."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-ladder-query-"))
        cls.estate = build(cls.tmp / "estate")
        cls.db = cls.tmp / "graph.duckdb"
        index(cls.estate, db_path=cls.db)
        cls.reading = ladders.read(cls.estate / "ladder", db_path=cls.db)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_ladder_comes_back_rung_by_rung(self):
        one, = ladders.find(self.reading, "refactoring")
        self.assertEqual(
            [rung.path for rung in one.rungs],
            [
                "refactoring/refactoring.md",
                "refactoring/refactoring.mini.md",
                "refactoring/refactoring.nano.md",
            ],
        )

    def test_the_rungs_come_back_in_size_order_with_byte_counts(self):
        one, = ladders.find(self.reading, "refactoring")
        sizes = [rung.size_bytes for rung in one.rungs]
        self.assertEqual(sizes, sorted(sizes, reverse=True))
        self.assertTrue(all(size > 0 for size in sizes))

    def test_the_byte_count_is_the_file_s_own(self):
        one, = ladders.find(self.reading, "refactoring")
        for rung in one.rungs:
            with self.subTest(path=rung.path):
                self.assertEqual(
                    rung.size_bytes,
                    (self.estate / "ladder" / rung.path).stat().st_size,
                )

    def test_a_book_at_two_rungs_answers_with_two(self):
        one, = ladders.find(self.reading, "clean-code")
        self.assertEqual(len(one.rungs), 2)

    def test_a_name_that_matches_nothing_matches_nothing(self):
        self.assertEqual(ladders.find(self.reading, "the-pragmatic-programmer"), [])

    def test_which_rung_a_session_loaded_is_unknown_with_the_reason_named(self):
        text = ladders.render(self.reading, ladders.find(self.reading, "refactoring"))
        self.assertIn("UNKNOWN", text)
        self.assertIn(ladders.RUNG_LOADED_UNKNOWN, text)
        # Never a zero. An unobservable quantity must not improve a number by
        # being unobservable.
        self.assertNotRegex(text, r"rung this session loaded\s+0\b")

    def test_the_rule_the_ladders_were_keyed_on_is_stated(self):
        text = ladders.render(self.reading, self.reading.ladders)
        self.assertIn(ladders.LADDER_RULE, text)
        for word in surfaces.RUNG_WORDS:
            self.assertIn(word, text)

    def test_a_rung_with_no_base_rung_is_named_in_the_output(self):
        text = ladders.render(self.reading, self.reading.ladders)
        self.assertIn("drafts/takeoff.mini.md", text)

    def test_a_repository_with_none_says_found_rather_than_none(self):
        reading = ladders.read(self.estate / "vendor", db_path=self.db)
        self.assertEqual(reading.ladders, [])
        text = ladders.render(reading, reading.ladders)
        self.assertIn(ladders.LADDER_RULE, text)
        self.assertIn("found", text)

    def test_no_forbidden_vocabulary(self):
        for repository in ("ladder", "vendor"):
            with self.subTest(repository=repository):
                reading = ladders.read(self.estate / repository, db_path=self.db)
                text = ladders.render(reading, reading.ladders)
                self.assertEqual(offending_words(text), [])


class TestTheMapPrintsLaddersInsideItsBudget(unittest.TestCase):
    """`repo-map` carries the same block, under the rules the map holds to.

    The map answers "what governance does this repository carry" in one screen,
    and progressive disclosure is what this estate's governance mostly is. So
    the block is here too -- and it obeys the budget the same way every other
    listing in the map does.
    """

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-ladder-map-"))
        cls.estate = build(cls.tmp / "estate")
        cls.db = cls.tmp / "graph.duckdb"
        index(cls.estate, db_path=cls.db)
        cls.map = repomap.read(cls.estate / "ladder", db_path=cls.db, environ={})
        cls.text = repomap.render(cls.map)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_map_and_the_command_answer_the_same_question_once(self):
        reading = ladders.read(self.estate / "ladder", db_path=self.db)
        self.assertEqual(
            [one.base_path for one in self.map.ladders],
            [one.base_path for one in reading.ladders],
        )
        self.assertEqual(
            self.map.rungs_with_no_base_rung, reading.rungs_with_no_base_rung
        )

    def test_the_new_edge_kind_is_in_the_inventory_the_map_prints(self):
        self.assertIn(ladders.RUNG_OF_EDGE, repomap.EDGE_KINDS)
        self.assertIn(ladders.RUNG_OF_EDGE, self.text)

    def test_the_map_names_the_rung_with_no_base_rung(self):
        self.assertIn("drafts/takeoff.mini.md", self.text)

    def test_a_budget_the_map_exceeds_drops_the_ladder_listing_too(self):
        # A map that says it left its listings out and then prints one is a map
        # whose budget is held by luck rather than by construction.
        tight = len(self.text.encode("utf-8")) - 300
        trimmed = repomap.render(self.map, budget=tight)
        self.assertIn("Example listings left out", trimmed)
        self.assertNotIn("drafts/takeoff.mini.md", trimmed)
        # The count stays. What was dropped is the listing, and the map says how
        # much of it.
        self.assertIn("rung words with no base rung beside them  1", trimmed)
        self.assertIn("1 more not listed", trimmed)

    def test_a_long_path_cannot_push_the_map_past_its_budget(self):
        # Every other listing in the map cuts a path to a printable width. One
        # unbounded line is all it takes to exceed a figure the map printed on
        # its own last line.
        long_path = "a-very-long-directory-name/" * 8 + "book.mini.md"
        lines = ladders.summary_lines(
            [], [long_path], self.map.graph_detector_version,
            limit=repomap.EXAMPLE_ROWS, shorten=repomap._short,
        )
        listed, = [line for line in lines if line.startswith("    a-very-long")]
        self.assertLessEqual(len(listed.strip()), repomap.MAX_TEXT_WIDTH)

    def test_no_forbidden_vocabulary(self):
        self.assertEqual(offending_words(self.text), [])


class TestSeamB(unittest.TestCase):
    """The command line, tested the way the demo is run."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-ladder-cli-"))
        cls.estate = build(cls.tmp / "estate")
        cls.db = cls.tmp / "graph.duckdb"
        indexed = subprocess.run(
            [sys.executable, "-m", "orbit_context.cli", "index", str(cls.estate),
             "--db", str(cls.db)],
            cwd=str(support.ORBIT_ROOT), capture_output=True, text=True,
        )
        assert indexed.returncode == 0, indexed.stderr
        cls.statistics = json.loads(indexed.stdout)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_ladder(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "orbit_context.cli", "ladder", *args,
             "--repo", str(self.estate / "ladder"), "--db", str(self.db)],
            cwd=str(support.ORBIT_ROOT), capture_output=True, text=True,
        )

    def test_index_reports_the_ladders_beside_the_other_counts(self):
        self.assertEqual(self.statistics["graph"]["ladders"]["found"], 2)

    def test_asking_for_one_book_prints_its_rungs_in_size_order(self):
        completed = self.run_ladder("refactoring")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        # The rung lines: a byte count, then the path. The ladder's own heading
        # names the base rung too, so the rows are picked out by their shape
        # rather than by the path appearing anywhere on the line.
        printed = [
            line for line in completed.stdout.splitlines()
            if re.match(r"^\s+\d+\s+refactoring/", line)
        ]
        self.assertEqual(len(printed), 3)
        self.assertIn("refactoring/refactoring.md", printed[0])
        self.assertIn("refactoring/refactoring.nano.md", printed[-1])
        sizes = [int(line.split()[0]) for line in printed]
        self.assertEqual(sizes, sorted(sizes, reverse=True))

    def test_asking_for_nothing_in_particular_lists_every_ladder(self):
        completed = self.run_ladder()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("refactoring/refactoring.md", completed.stdout)
        self.assertIn("clean-code/clean-code.md", completed.stdout)

    def test_a_name_that_matches_no_ladder_says_what_the_rule_keys_on(self):
        completed = self.run_ladder("code-complete")
        self.assertEqual(completed.returncode, 1)
        self.assertIn(ladders.LADDER_RULE, completed.stderr)

    def test_the_output_carries_the_detector_set_that_produced_it(self):
        completed = self.run_ladder("refactoring")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn(self.statistics["detector_set_version"], completed.stdout)

    def test_no_forbidden_vocabulary_on_the_command_line(self):
        for args in ((), ("refactoring",)):
            with self.subTest(args=args):
                completed = self.run_ladder(*args)
                self.assertEqual(offending_words(completed.stdout), [])


if __name__ == "__main__":
    unittest.main()
