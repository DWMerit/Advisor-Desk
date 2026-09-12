"""Workbench to published: a direction where the evidence supports one.

Byte identity is symmetric. Two files hashing the same says nothing about which
one came first, and on the real estate all 28 pairs are a workbench file
matching a published file -- one pipeline run 28 times, with the direction
obvious to a human and invisible to the tool.

What is asserted here is that a pair is ordered **only** where a ``PRODUCES``
edge relates its two ends, that every pair the graph holds carries either that
direction with its evidence rung or an explicit UNKNOWN with a reason, and that
the two ways a pair can fail to be ordered stay apart: a pair with a producer
that does not order it is not counted as a pair with no producer at all.

The prose case is the point of the ticket and it is asserted against this
repository's own files, not against a fixture. ``traceability.md`` states the
relationship in a sentence a human reads in ten seconds. Spec 0001 §14 lists
prose provenance as a permanent UNKNOWN, so it stays UNKNOWN: a direction read
out of a sentence would be indistinguishable in the output from one something
observed, and that indistinguishability is the whole failure this project
exists to refuse.

Counts are against ``build_lineage`` and ``build_estate``, never against a live
repository -- except where the assertion *is* that nothing was promoted, which
can only be checked where the prose actually is.
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
from orbit_context import pairs as pairs_module
from orbit_context import provenance, repomap, store, surfaces
from orbit_context.retrieve import repository
from orbit_context.indexer import index

from .test_vocabulary import offending_words


def _pair(first: str, second: str) -> provenance.Pair:
    return provenance.Pair("0" * 64, first, second)


def _production(producer: str, artifact: str,
                evidence: str = provenance.MANIFEST_DECLARATION,
                ) -> provenance.Production:
    return provenance.Production(
        producer_address=producer,
        producer_path=producer,
        artifact_path=artifact,
        evidence=evidence,
        evidence_path="build/manifest.json",
        evidence_line=3,
    )


class TestTheDirectionAlgebra(unittest.TestCase):
    """The rule itself, at the one seam where every case can be put to it.

    A direction comes from a ``PRODUCES`` edge between the two ends of the pair
    and from nothing else. The estate fixtures reach three of these cases; the
    fourth -- a producer that sorts after its artifact -- is a property of the
    ordering rather than of any estate, so it is put here rather than bent into
    a fixture to make it appear.
    """

    def order(self, matched, productions):
        found = provenance.directions(matched, productions)
        self.assertEqual(len(found), len(matched))
        return found[0]

    def test_a_declaration_between_the_two_ends_orders_the_pair(self):
        one = self.order(
            [_pair("workbench/nano.md", "published/nano.md")],
            [_production("workbench/nano.md", "published/nano.md")],
        )
        self.assertEqual(one.direction, provenance.SOURCE_PRODUCES_TARGET)
        self.assertEqual(one.producer_path, "workbench/nano.md")
        self.assertEqual(one.artifact_path, "published/nano.md")
        self.assertEqual(one.evidence, provenance.MANIFEST_DECLARATION)
        self.assertIsNone(one.reason)

    def test_the_pair_is_ordered_the_way_the_evidence_reads_not_the_way_it_sorts(self):
        # The producer sorting after its artifact. Nothing in the estate makes
        # this happen and nothing stops it, and a rule that quietly assumed the
        # lexicographically first path is the producer would pass every other
        # test here.
        one = self.order(
            [_pair("build/rules.md", "workbench/rules.md")],
            [_production("workbench/rules.md", "build/rules.md")],
        )
        self.assertEqual(one.direction, provenance.TARGET_PRODUCES_SOURCE)
        self.assertEqual(one.producer_path, "workbench/rules.md")
        self.assertEqual(one.artifact_path, "build/rules.md")

    def test_a_producer_outside_the_pair_does_not_order_it(self):
        one = self.order(
            [_pair("build/rules.md", "dist/rules.md")],
            [_production("scripts/build.py", "build/rules.md")],
        )
        self.assertEqual(one.direction, provenance.DIRECTION_UNKNOWN)
        self.assertEqual(one.reason, provenance.PRODUCER_OUTSIDE_THE_PAIR)
        self.assertIsNone(one.producer_path)
        self.assertIsNone(one.evidence)

    def test_no_evidence_at_either_end_is_its_own_reason(self):
        one = self.order([_pair("a.md", "b.md")], [])
        self.assertEqual(one.direction, provenance.DIRECTION_UNKNOWN)
        self.assertEqual(one.reason, provenance.NO_PRODUCER_AT_EITHER_END)

    def test_each_end_naming_the_other_leaves_the_pair_unordered(self):
        # Two claims that contradict each other about which end came first.
        # Picking one would be this tool deciding, and it has no basis to.
        one = self.order(
            [_pair("a.md", "b.md")],
            [_production("a.md", "b.md"), _production("b.md", "a.md")],
        )
        self.assertEqual(one.direction, provenance.DIRECTION_UNKNOWN)
        self.assertEqual(one.reason, provenance.EACH_END_NAMES_THE_OTHER)

    def test_a_producer_the_tree_does_not_hold_orders_nothing(self):
        # An edge needs both ends. A producer named but unresolved is counted
        # elsewhere; it cannot order a pair, because there is nothing to order.
        unresolved = provenance.Production(
            producer_address="scripts/absent.py",
            producer_path=None,
            artifact_path="build/rules.md",
            evidence=provenance.ARTIFACT_HEADER,
            evidence_path="build/rules.md",
            evidence_line=1,
        )
        one = self.order([_pair("build/rules.md", "dist/rules.md")], [unresolved])
        self.assertEqual(one.reason, provenance.NO_PRODUCER_AT_EITHER_END)

    def test_every_pair_comes_back_with_one_or_the_other(self):
        found = provenance.directions(
            [_pair("a.md", "b.md"), _pair("c.md", "d.md")],
            [_production("c.md", "d.md")],
        )
        for one in found:
            with self.subTest(pair=(one.pair.first_path, one.pair.second_path)):
                if one.direction == provenance.DIRECTION_UNKNOWN:
                    self.assertIn(one.reason, provenance.DIRECTION_UNKNOWN_REASONS)
                    self.assertIsNone(one.evidence)
                else:
                    self.assertIsNone(one.reason)
                    self.assertIn(one.evidence, provenance.EVIDENCE_LADDER)


class LineageTestCase(unittest.TestCase):
    """Seam A: build the estate, index it, assert on the stats and the rows."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-directions-"))
        cls.estate = build(cls.tmp / "estate")
        cls.db = cls.tmp / "graph.duckdb"
        cls.stats = index(cls.estate, db_path=cls.db)
        cls.by_repo = {entry["repository"]: entry
                       for entry in cls.stats["repositories"]}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def rows(self):
        connection = store.connect(self.db, read_only=True)
        try:
            return connection.execute(
                "SELECT source_path, target_path, direction, direction_reason, "
                "subtype, evidence_path, evidence_line FROM gl_context_edge "
                "WHERE relationship_kind = 'IDENTICAL_BYTES' AND branch = 'main' "
                "ORDER BY source_path, target_path"
            ).fetchall()
        finally:
            connection.close()


class TestTheDirectionIsOnTheRow(LineageTestCase):
    """The pair the corpus declares, and the two it only describes."""

    def test_the_estate_holds_the_three_pairs_the_fixture_put_there(self):
        self.assertEqual(
            [(row[0], row[1]) for row in self.rows()],
            [
                ("_rule-workbench/clean-code/nano.md", "clean-code/clean-code.nano.md"),
                ("_rule-workbench/refactoring/mini.md",
                 "refactoring/refactoring.mini.md"),
                ("_rule-workbench/refactoring/nano.md",
                 "refactoring/refactoring.nano.md"),
            ],
        )

    def test_the_declared_rung_carries_a_direction_and_its_rung(self):
        by_source = {row[0]: row for row in self.rows()}
        row = by_source["_rule-workbench/clean-code/nano.md"]
        self.assertEqual(row[2], provenance.SOURCE_PRODUCES_TARGET)
        self.assertIsNone(row[3])
        self.assertEqual(row[4], provenance.MANIFEST_DECLARATION)

    def test_the_direction_carries_the_locator_it_was_read_from(self):
        # The claim has to be readable back out of the estate, or it is this
        # tool's word for it.
        by_source = {row[0]: row for row in self.rows()}
        row = by_source["_rule-workbench/clean-code/nano.md"]
        self.assertEqual(row[5], "_rule-workbench/manifest.json")
        self.assertGreater(row[6], 0)
        declaration = (self.estate / "ladder" / row[5]).read_text(encoding="utf-8")
        line = declaration.splitlines()[row[6] - 1]
        self.assertIn("input", line + declaration)
        self.assertTrue(line.strip())

    def test_the_rung_described_only_in_prose_stays_unknown(self):
        # `refactoring`'s traceability file states the relationship in a
        # sentence. It is the same relationship the manifest declares for
        # `clean-code`, in the same repository, and it orders nothing.
        by_source = {row[0]: row for row in self.rows()}
        for path in ("_rule-workbench/refactoring/mini.md",
                     "_rule-workbench/refactoring/nano.md"):
            with self.subTest(path=path):
                row = by_source[path]
                self.assertEqual(row[2], provenance.DIRECTION_UNKNOWN)
                self.assertEqual(row[3], provenance.NO_PRODUCER_AT_EITHER_END)
                self.assertIsNone(row[4])
                self.assertIsNone(row[5])

    def test_the_prose_sentence_writes_no_producer_edge(self):
        connection = store.connect(self.db, read_only=True)
        try:
            produced = connection.execute(
                "SELECT source_path, target_path, evidence_path "
                "FROM gl_context_edge WHERE relationship_kind = 'PRODUCES' "
                "AND branch = 'main' ORDER BY target_path"
            ).fetchall()
        finally:
            connection.close()
        self.assertEqual(produced, [(
            "_rule-workbench/clean-code/nano.md",
            "clean-code/clean-code.nano.md",
            "_rule-workbench/manifest.json",
        )])

    def test_the_sentence_the_test_above_is_about_is_really_in_the_estate(self):
        # Without this the assertion passes on an estate where nobody wrote the
        # prose, which is not the case it is guarding.
        text = (self.estate / "ladder" / "_rule-workbench" / "refactoring"
                / "traceability.md").read_text(encoding="utf-8")
        self.assertIn("../../refactoring/refactoring.md", text)

    def test_every_row_carries_one_or_the_other(self):
        for source, target, direction, reason, evidence, _, _ in self.rows():
            with self.subTest(pair=(source, target)):
                if direction == provenance.DIRECTION_UNKNOWN:
                    self.assertIn(reason, provenance.DIRECTION_UNKNOWN_REASONS)
                else:
                    self.assertIn(direction, provenance.DIRECTIONS)
                    self.assertIsNone(reason)
                    self.assertIn(evidence, provenance.EVIDENCE_LADDER)


class TestTheCountsAreNeverReportedApart(LineageTestCase):
    """Ticket 05's rule, still binding, extended to the direction counts."""

    def blocks(self, node):
        found = []
        if isinstance(node, dict):
            if "pairs" in node:
                found.append(node)
            for child in node.values():
                found.extend(self.blocks(child))
        elif isinstance(node, list):
            for child in node:
                found.extend(self.blocks(child))
        return found

    def test_a_pair_count_never_appears_without_its_provenance_count(self):
        reported = self.blocks(self.stats)
        self.assertGreater(len(reported), 0)
        for block in reported:
            self.assertIn("pairs_with_provenance", block)
            self.assertIn("pairs_with_a_direction", block)
            self.assertIn("pairs_with_no_direction", block)

    def test_the_direction_counts_partition_the_pairs(self):
        for block in self.blocks(self.stats):
            self.assertEqual(
                block["pairs"],
                block["pairs_with_a_direction"]
                + sum(block["pairs_with_no_direction"].values()),
            )

    def test_every_reason_is_present_even_at_zero(self):
        # Zero is a measurement. A reason that found nothing must read as a
        # reason that found nothing, not as a reason nobody looked for.
        for block in self.blocks(self.stats):
            self.assertEqual(
                set(block["pairs_with_no_direction"]),
                set(provenance.DIRECTION_UNKNOWN_REASONS),
            )
            self.assertEqual(
                set(block["pairs_by_direction_evidence"]),
                set(provenance.EVIDENCE_LADDER),
            )

    def test_the_ladder_repository_reports_what_the_fixture_holds(self):
        block = self.by_repo["ladder"]["graph"]["identical_bytes"]
        self.assertEqual(block["pairs"], 3)
        self.assertEqual(block["pairs_with_a_direction"], 1)
        self.assertEqual(
            block["pairs_by_direction_evidence"][provenance.MANIFEST_DECLARATION], 1
        )
        self.assertEqual(
            block["pairs_with_no_direction"][provenance.NO_PRODUCER_AT_EITHER_END], 2
        )

    def test_a_pair_with_no_producer_is_apart_from_one_that_is_merely_unordered(self):
        # The acceptance this ticket turns on. Both are UNKNOWN and they are
        # different statements about the estate, so one is never read as the
        # other.
        block = self.by_repo["ladder"]["graph"]["identical_bytes"]
        self.assertEqual(
            block["pairs_with_no_direction"][provenance.PRODUCER_OUTSIDE_THE_PAIR], 0
        )
        self.assertNotEqual(
            block["pairs_with_no_direction"][provenance.NO_PRODUCER_AT_EITHER_END],
            block["pairs_with_no_direction"][provenance.PRODUCER_OUTSIDE_THE_PAIR],
        )

    def test_the_pairs_carrying_provenance_are_the_ones_a_producer_reaches(self):
        # `pairs_with_provenance` is ticket 05's count and it does not move:
        # what the direction adds is which of those pairs it also orders.
        for block in self.blocks(self.stats):
            self.assertEqual(
                block["pairs_with_provenance"],
                block["pairs"]
                - block["pairs_with_no_direction"][
                    provenance.NO_PRODUCER_AT_EITHER_END],
            )


class TestAProducerOutsideThePairIsReached(unittest.TestCase):
    """The other reason, on the phase 1 estate, which already holds the shape.

    ``build_estate`` is untouched and used read-only, per spec 0002 §7. Its
    ``build/rules.md`` and ``dist/rules.md`` are the same bytes and each names
    the same script in its own header -- a producer at both ends of the pair and
    outside it, which orders nothing.
    """

    @classmethod
    def setUpClass(cls):
        from build_estate import build as build_phase_one

        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-outside-"))
        cls.estate = build_phase_one(cls.tmp / "estate")
        cls.db = cls.tmp / "graph.duckdb"
        cls.stats = index(cls.estate, db_path=cls.db)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def row(self, source, target):
        connection = store.connect(self.db, read_only=True)
        try:
            return connection.execute(
                "SELECT direction, direction_reason FROM gl_context_edge "
                "WHERE relationship_kind = 'IDENTICAL_BYTES' "
                "AND source_path = ? AND target_path = ?",
                [source, target],
            ).fetchall()
        finally:
            connection.close()

    def test_a_pair_a_third_file_produced_is_unordered_for_that_reason(self):
        self.assertEqual(
            self.row("build/rules.md", "dist/rules.md"),
            [(provenance.DIRECTION_UNKNOWN, provenance.PRODUCER_OUTSIDE_THE_PAIR)],
        )

    def test_a_pair_nothing_produced_is_unordered_for_the_other_reason(self):
        self.assertEqual(
            self.row("AGENTS.md", "CLAUDE.md"),
            [(provenance.DIRECTION_UNKNOWN, provenance.NO_PRODUCER_AT_EITHER_END)],
        )

    def test_both_reasons_are_counted_in_one_estate(self):
        block = self.stats["graph"]["identical_bytes"]
        self.assertGreater(
            block["pairs_with_no_direction"][provenance.PRODUCER_OUTSIDE_THE_PAIR], 0
        )
        self.assertGreater(
            block["pairs_with_no_direction"][provenance.NO_PRODUCER_AT_EITHER_END], 0
        )


class TestThePairsAreQueryable(LineageTestCase):
    """The demo: every pair the snapshot holds, each with a direction or why not."""

    def reading(self):
        return pairs_module.read(self.estate / "ladder", db_path=self.db)

    def test_every_pair_comes_back_from_the_graph(self):
        found = self.reading()
        self.assertEqual(len(found.pairs), 3)
        self.assertEqual(found.counts.total, 3)
        self.assertEqual(found.counts.with_a_direction, 1)

    def test_the_listing_names_the_direction_and_the_rung(self):
        text = pairs_module.render(self.reading())
        self.assertIn(provenance.MANIFEST_DECLARATION, text)
        self.assertIn("clean-code/clean-code.nano.md", text)

    def test_the_listing_names_the_reason_where_there_is_no_direction(self):
        text = pairs_module.render(self.reading())
        self.assertIn(provenance.DIRECTION_UNKNOWN, text)
        self.assertIn(provenance.NO_PRODUCER_AT_EITHER_END, text)

    def test_the_counts_are_in_the_same_block_as_the_listing(self):
        text = pairs_module.render(self.reading())
        heading = next(line for line in text.splitlines()
                       if line.startswith("IDENTICAL BYTES"))
        self.assertIn("3 pairs", heading)

    def test_a_snapshot_with_no_index_run_says_so(self):
        with self.assertRaises(pairs_module.PairsError):
            pairs_module.read(self.estate / "ladder",
                              db_path=self.tmp / "nothing.duckdb")

    def test_the_output_carries_no_forbidden_word(self):
        self.assertEqual(offending_words(pairs_module.render(self.reading())), [])


class TestAnOlderSnapshotDoesNotReadAsAMeasurement(LineageTestCase):
    """A row written before the direction existed carries NULL, not UNKNOWN.

    A store holds many snapshots and many detector sets -- that is the design --
    so this build reads rows an older one wrote. UNKNOWN is a measurement: a run
    looked and found nothing that ordered the pair. NULL is the absence of one.
    Reading the first as the second lets an older snapshot report an order
    nobody looked for, and reading it as "carrying provenance" -- which negative
    logic does, because NULL is not the no-producer reason -- says something
    about the estate that no row supports.
    """

    def setUp(self):
        self.older = self.tmp / "older.duckdb"
        shutil.copy(self.db, self.older)
        connection = store.connect(self.older)
        try:
            connection.execute(
                "UPDATE gl_context_edge SET direction = NULL, "
                "direction_reason = NULL, subtype = NULL "
                "WHERE relationship_kind = 'IDENTICAL_BYTES'"
            )
        finally:
            connection.close()

    def reading(self):
        return pairs_module.read(self.estate / "ladder", db_path=self.older)

    def test_the_rows_are_counted_apart_from_both_provenance_counts(self):
        counts = self.reading().counts
        self.assertEqual(counts.total, 3)
        self.assertEqual(counts.not_measured, 3)
        self.assertEqual(counts.with_provenance, 0)
        self.assertEqual(counts.without_provenance, 0)
        self.assertEqual(counts.with_a_direction, 0)

    def test_the_map_does_not_report_them_as_carrying_provenance(self):
        result = repomap.read(self.estate / "ladder", db_path=self.older,
                              environ={})
        self.assertEqual(result.identical_pairs, 3)
        self.assertEqual(result.pairs_with_provenance, 0)

    def test_the_block_names_them_and_says_what_resolves_it(self):
        text = pairs_module.render(self.reading())
        self.assertIn("no direction recorded", text)
        self.assertIn(pairs_module.NOT_MEASURED_REMEDY, text)
        self.assertIn(pairs_module.NOT_MEASURED, text)

    def test_the_condition_is_reported_in_the_constrained_vocabulary(self):
        # This block only prints on a store in this state, so the lint over
        # `repo-map`'s output never reaches it. Linted here instead.
        self.assertEqual(offending_words(pairs_module.render(self.reading())), [])
        self.assertEqual(offending_words(pairs_module.NOT_MEASURED), [])
        self.assertEqual(offending_words(pairs_module.NOT_MEASURED_REMEDY), [])

    def test_a_snapshot_that_did_measure_prints_no_such_line(self):
        # The line is a condition, not an inventory row. Where every pair was
        # measured there is nothing to say, and saying it anyway would read as
        # a defect on every healthy store.
        self.assertNotIn(
            "no direction recorded",
            pairs_module.render(pairs_module.read(self.estate / "ladder",
                                                  db_path=self.db)),
        )


class TestAStoreThatPredatesTheColumns(LineageTestCase):
    """The read seam says which command resolves it, rather than a traceback.

    `index` already stops on a store whose columns and the ontology's disagree,
    and names `migrate`. The read commands reach the same store and, until this
    was fixed, answered with a raw DuckDB binder error.
    """

    def setUp(self):
        self.older = self.tmp / "no-column.duckdb"
        shutil.copy(self.db, self.older)
        connection = store.connect(self.older)
        try:
            connection.execute(
                "ALTER TABLE gl_context_edge DROP COLUMN direction"
            )
        finally:
            connection.close()

    def test_the_pairs_command_names_the_remedy(self):
        with self.assertRaises(pairs_module.PairsError) as raised:
            pairs_module.read(self.estate / "ladder", db_path=self.older)
        self.assertIn("orbit-context migrate", str(raised.exception))
        self.assertIn(str(self.older), str(raised.exception))

    def test_the_map_raises_its_own_error_rather_than_a_duckdb_one(self):
        with self.assertRaises(repomap.RepoMapError) as raised:
            repomap.read(self.estate / "ladder", db_path=self.older, environ={})
        self.assertIn("orbit-context migrate", str(raised.exception))

    def test_the_command_line_prints_it_and_exits_one(self):
        for argv in (["pairs"], ["repo-map"]):
            with self.subTest(argv=argv):
                completed = subprocess.run(
                    [sys.executable, "-m", "orbit_context.cli", *argv,
                     "--repo", str(self.estate / "ladder"),
                     "--db", str(self.older)],
                    capture_output=True, text=True, cwd=str(support.ORBIT_ROOT),
                )
                self.assertEqual(completed.returncode, 1)
                self.assertIn("orbit-context migrate", completed.stderr)
                self.assertNotIn("Traceback", completed.stderr)


class TestTheBlockStaysReadableWhenNothingIsListed(unittest.TestCase):
    """The counts are never capped; the listing is, and it says so where it can.

    `repo-map` drops every listing once it has exceeded its budget. The line
    saying how many pairs went unlisted is indented like the reason rows above
    it, so without its own heading a reader scanning down reads it as a fourth
    reason -- the exact misreading the heading exists to prevent.
    """

    def counts(self, total=3):
        counts = pairs_module.PairCounts()
        for _ in range(total):
            counts.add(provenance.DIRECTION_UNKNOWN,
                       provenance.NO_PRODUCER_AT_EITHER_END, None)
        return counts

    def test_the_dropped_line_sits_under_the_listing_heading(self):
        lines = pairs_module.summary_lines(self.counts(), [], "1.000000000000")
        index = lines.index("    3 pairs not listed")
        self.assertEqual(lines[index - 1], "  pair by pair")

    def test_a_partial_listing_says_how_many_more(self):
        one = pairs_module.Pairing(
            "a.md", "b.md", "0" * 64, provenance.DIRECTION_UNKNOWN,
            reason=provenance.NO_PRODUCER_AT_EITHER_END,
        )
        lines = pairs_module.summary_lines(self.counts(), [one], "1.000000000000")
        self.assertIn("    2 more pairs not listed", lines)

    def test_a_snapshot_with_no_pairs_prints_no_listing_heading(self):
        lines = pairs_module.summary_lines(
            pairs_module.PairCounts(), [], "1.000000000000"
        )
        self.assertNotIn("  pair by pair", lines)
        self.assertIn("\nIDENTICAL BYTES  0 pairs  [1.000000000000]", lines)


class TestAVocabularyThisBuildHasNotSeen(unittest.TestCase):
    """A value read off a row is data, and this build may not know it.

    These counts are pre-seeded with the reasons and rungs this build declares,
    and they are filled from rows another detector set may have written. An
    unknown value is a finding -- it is what a version mismatch looks like in
    the numbers -- so it is added to the tally rather than dropped, and never
    raised from a property.
    """

    def test_an_unknown_reason_is_counted_beside_the_known_ones(self):
        counts = pairs_module.PairCounts()
        counts.add(provenance.DIRECTION_UNKNOWN, "a-reason-from-another-set", None)
        self.assertEqual(counts.by_reason["a-reason-from-another-set"], 1)
        self.assertEqual(counts.total, 1)
        for reason in provenance.DIRECTION_UNKNOWN_REASONS:
            self.assertIn(reason, counts.by_reason)

    def test_an_unknown_rung_is_counted_beside_the_known_ones(self):
        counts = pairs_module.PairCounts()
        counts.add(provenance.SOURCE_PRODUCES_TARGET, None, "a-rung-from-another-set")
        self.assertEqual(counts.by_direction_evidence["a-rung-from-another-set"], 1)
        self.assertEqual(counts.with_a_direction, 1)

    def test_an_unknown_direction_falls_back_to_what_the_row_says_about_it(self):
        counts = pairs_module.PairCounts()
        counts.add("a-direction-from-another-set", "a-reason-from-another-set", None)
        self.assertEqual(counts.with_a_direction, 0)
        self.assertEqual(counts.by_reason["a-reason-from-another-set"], 1)

    def test_neither_count_raises_on_any_of_them(self):
        counts = pairs_module.PairCounts()
        counts.add("elsewhere", "elsewhere", "elsewhere")
        counts.add(None, None, None)
        self.assertEqual(counts.total, 2)
        self.assertEqual(counts.not_measured, 1)
        self.assertEqual(counts.with_provenance, 1)


class TestTheMapCountsWithoutFetchingEveryPair(LineageTestCase):
    """A map that prints five pairs must not read every pair to count them.

    Pairing is quadratic inside a hash group: five hundred identical files are a
    hundred and twenty-four thousand pairs, and the map still prints five. The
    counts come from a GROUP BY and the listing from a LIMIT, both owned by
    `pairs`, so bounding the fetch does not cost the map its arithmetic.
    """

    def test_the_two_statements_agree_and_only_one_fetches_rows(self):
        connection = store.connect(self.db, read_only=True)
        try:
            found = repository(self.estate / "ladder")
            snapshot = [found.project_id, found.branch, found.commit_sha]
            counts = pairs_module.counts_from_graph(connection, snapshot)
            listed = pairs_module.from_graph(connection, snapshot, limit=1)
        finally:
            connection.close()
        self.assertEqual(counts.total, 3)
        self.assertEqual(len(listed), 1)
        self.assertEqual(counts, pairs_module.PairCounts.of(
            pairs_module.read(self.estate / "ladder", db_path=self.db).pairs
        ))

    def test_the_map_lists_no_more_than_its_cap(self):
        result = repomap.read(self.estate / "ladder", db_path=self.db, environ={})
        self.assertLessEqual(len(result.pairings), repomap.EXAMPLE_ROWS)
        self.assertEqual(result.identical_pairs, 3)


class TestSeamB(unittest.TestCase):
    """The command line, tested the way the comparison is run."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-directions-cli-"))
        cls.estate = build(cls.tmp / "estate")
        cls.db = cls.tmp / "graph.duckdb"
        cls.orbit(["index", str(cls.estate)])

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    @classmethod
    def orbit(cls, argv):
        return subprocess.run(
            [sys.executable, "-m", "orbit_context.cli", *argv,
             "--db", str(cls.db)],
            capture_output=True, text=True, cwd=str(support.ORBIT_ROOT),
        )

    def test_the_command_prints_every_pair_with_a_direction_or_a_reason(self):
        completed = self.orbit(["pairs", "--repo", str(self.estate / "ladder")])
        self.assertEqual(completed.returncode, 0, completed.stderr)
        listed = [line for line in completed.stdout.splitlines() if " = " in line]
        self.assertEqual(len(listed), 3)
        for line in listed:
            self.assertTrue(
                provenance.DIRECTION_UNKNOWN in line
                or any(rung in line for rung in provenance.EVIDENCE_LADDER),
                line,
            )

    def test_the_counts_travel_with_the_listing(self):
        completed = self.orbit(["pairs", "--repo", str(self.estate / "ladder")])
        self.assertIn("carrying provenance evidence", completed.stdout)
        self.assertIn("carrying a direction", completed.stdout)

    def test_a_repository_with_no_pairs_reports_that_rather_than_failing(self):
        completed = self.orbit(["pairs", "--repo", str(self.estate / "vendor")])
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("0 pairs", completed.stdout)

    def test_the_repository_map_reports_the_direction_beside_the_pair_count(self):
        completed = self.orbit(["repo-map", "--repo", str(self.estate / "ladder")])
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("carrying a direction", completed.stdout)

    def test_the_index_statistics_carry_it_too(self):
        completed = self.orbit(["index", str(self.estate)])
        self.assertEqual(completed.returncode, 0, completed.stderr)
        block = json.loads(completed.stdout)["graph"]["identical_bytes"]
        self.assertEqual(block["pairs_with_a_direction"], 1)

    def test_neither_command_prints_a_forbidden_word(self):
        for argv in (["pairs", "--repo", str(self.estate / "ladder")],
                     ["repo-map", "--repo", str(self.estate / "ladder")]):
            with self.subTest(argv=argv):
                completed = self.orbit(argv)
                self.assertEqual(offending_words(completed.stdout), [])


class TestThisRepository(unittest.TestCase):
    """The prose case, read out of the estate that wrote it.

    ``_rule-workbench/refactoring/traceability.md`` says ``full.md`` *"should
    resolve to ``../../refactoring/refactoring.md``"*. That is a producer
    relationship stated in a sentence, and it is the one this ticket refuses to
    promote. Asserted here against the real file rather than a copy, so that
    rewording the sentence cannot quietly retire the test -- the same discipline
    the ticket 05 regression case already uses.
    """

    @classmethod
    def setUpClass(cls):
        cls.root = support.REPO_ROOT.resolve()
        cls.scan = provenance.read_tree(cls.root, surfaces.walk_files(cls.root))
        cls.pairs = provenance.pairs(cls.scan.contents, cls.scan.zero_byte)
        cls.productions = provenance.strongest(cls.scan.productions)
        cls.directions = provenance.directions(cls.pairs, cls.productions)
        cls.summary = provenance.summary(cls.scan, cls.pairs, cls.productions)

    def test_the_sentence_that_states_the_relationship_is_still_there(self):
        text = (self.root / "_rule-workbench" / "refactoring"
                / "traceability.md").read_text(encoding="utf-8")
        self.assertIn("../../refactoring/refactoring.md", text)
        self.assertIn("full.md", text)

    def test_reading_it_produced_no_producer(self):
        self.assertEqual(
            [one.artifact_path for one in self.productions
             if one.evidence_path.startswith("_rule-workbench/")],
            [],
        )

    def test_every_pair_here_is_unknown_for_the_reason_that_there_is_no_producer(self):
        # 28 pairs, every one of them a workbench file matching a published
        # file, and every one of them UNKNOWN. The discomfort is the mechanism:
        # nothing in this corpus declares the relationship anywhere a tool can
        # read it, so the tool does not have it.
        self.assertGreaterEqual(len(self.directions), 28)
        self.assertEqual(
            {one.reason for one in self.directions},
            {provenance.NO_PRODUCER_AT_EITHER_END},
        )

    def test_the_two_counts_are_reported_together(self):
        self.assertEqual(self.summary["pairs_with_a_direction"], 0)
        self.assertEqual(
            self.summary["pairs"],
            self.summary["pairs_with_no_direction"][
                provenance.NO_PRODUCER_AT_EITHER_END],
        )




class TestTwoDistinctPathsNeverPrintAsOne(unittest.TestCase):
    """A pair of two different files must not print as one file beside itself.

    Found by ticket 07's audit, in `repo-map` over Estimating-Lab. The pair

        work/sparx-academy-new-ken.transcript/2026-08-20-8bbf42cf/images/4856501b5adc.webp
        work/sparx-academy-new-ken.transcript/2026-08-20-ea6aa9c3/images/4856501b5adc.webp

    shares a long prefix *and* a long suffix and differs only in the middle,
    which is exactly the region a middle elision removes. Both ends printed as
    `work/sparx-academy-ne…ages/4856501b5adc.webp`, so a true finding -- two
    distinct files hold identical bytes -- reached the page reading as a file
    identical to itself. Spec 0002 section 9 makes one false assertion a stop,
    and a reader cannot tell this line from a genuine one.

    The guarantee asserted here is the whole fix: distinct inputs, distinct
    output, whatever the width and wherever the two diverge.
    """

    SOURCE = ("work/sparx-academy-new-ken.transcript/2026-08-20-8bbf42cf"
              "/images/4856501b5adc.webp")
    TARGET = ("work/sparx-academy-new-ken.transcript/2026-08-20-ea6aa9c3"
              "/images/4856501b5adc.webp")

    def pairing(self, source, target):
        return pairs_module.Pairing(
            source, target, "0" * 64, provenance.DIRECTION_UNKNOWN,
            reason=provenance.NO_PRODUCER_AT_EITHER_END,
        )

    def rendered(self, source, target, width=44):
        line = pairs_module._line(
            self.pairing(source, target), lambda path: repomap._short(path, width)
        )
        left, _, right = line.partition(" = ")
        return left.strip(), right.split("  ")[0].strip()

    def test_the_pair_the_audit_found_prints_two_different_strings(self):
        left, right = self.rendered(self.SOURCE, self.TARGET)
        self.assertNotEqual(left, right)

    def test_what_differs_survives_the_cut(self):
        left, right = self.rendered(self.SOURCE, self.TARGET)
        self.assertIn("8bbf42cf", left)
        self.assertIn("ea6aa9c3", right)

    def test_a_pair_that_already_printed_distinctly_is_left_alone(self):
        left, right = self.rendered("a/one.md", "a/two.md")
        self.assertEqual((left, right), ("a/one.md", "a/two.md"))

    def test_two_paths_diverging_late_inside_one_long_segment(self):
        stem = "w/" + "x" * 200
        left, right = self.rendered(stem + "a.md", stem + "b.md")
        self.assertNotEqual(left, right)

    def test_five_is_the_width_the_guarantee_starts_at(self):
        # `tell_apart` derives the bound: what differs sits one character past
        # the marker, a middle cut keeps (width - 1) // 2 leading characters,
        # so it survives once that head is two. Pinned here so a caller cut
        # narrower than the guarantee cannot arrive unnoticed -- every caller
        # in this codebase cuts at 40 or more.
        for width in range(5, 12):
            with self.subTest(width=width):
                left, right = self.rendered(self.SOURCE, self.TARGET, width)
                self.assertNotEqual(left, right)

    def test_the_guarantee_holds_across_widths_and_divergence_points(self):
        for width in (12, 20, 44, 64):
            for cut in (4, 37, 48, 60):
                source = self.SOURCE[:cut] + "Q" + self.SOURCE[cut + 1:]
                with self.subTest(width=width, cut=cut):
                    left, right = self.rendered(source, self.TARGET, width)
                    self.assertNotEqual(left, right)


if __name__ == "__main__":
    unittest.main()
