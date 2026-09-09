"""Identical bytes, reported with provenance — ticket 05's acceptance.

  - the identical-byte count is never emitted alone: every place it appears,
    the count of pairs carrying provenance evidence appears beside it
  - a pair where both files carry a generation header links to the producer
  - a pair with no provenance is reported as exactly that, with no inference
    about why
  - producer parsing does not capture trailing comment syntax
  - no forbidden vocabulary (in `test_vocabulary.py`, over the statistics and
    the evidence names)

The pairing is the point of the ticket. On one real repository the first pass
found 28 byte-identical pairs and zero producers: every pair was a workbench
file matching a published file, one pipeline run 28 times, and the provenance
that explained all 28 was invisible. So the count of matching pairs is tested
here for what it is *reported beside*, not only for being right.
"""

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

from . import support

from build_estate import build
from orbit_context import provenance, store, surfaces
from orbit_context.indexer import index


class EstateTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-provenance-"))
        cls.estate = build(cls.tmp / "estate")
        cls.db = cls.tmp / "graph.duckdb"
        cls.stats = index(cls.estate, db_path=cls.db, detailed=True)
        cls.alpha = next(
            entry for entry in cls.stats["repositories"]
            if entry["repository"] == "alpha"
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def query(self, sql, params=None):
        connection = store.connect(self.db, read_only=True)
        try:
            return connection.execute(sql, params or []).fetchall()
        finally:
            connection.close()

    def edges(self, relationship_kind):
        return self.query(
            "SELECT source_path, target_path, subtype, source_address, "
            "evidence_path, evidence_line, content_sha256 "
            "FROM gl_context_edge WHERE relationship_kind = ? "
            "ORDER BY source_path, target_path",
            [relationship_kind],
        )


class TestTheCountIsNeverEmittedAlone(EstateTestCase):
    """The acceptance the ticket puts first, tested as a property of the shape.

    Not "the number is right" but "the number cannot be read without the one
    that stops it over-reading". Both live in one dict, built in one function,
    so a caller cannot emit the first and forget the second.
    """

    def companions(self, node):
        """Every dict in the statistics that reports a pair count."""
        found = []
        if isinstance(node, dict):
            if "pairs" in node:
                found.append(node)
            for child in node.values():
                found.extend(self.companions(child))
        elif isinstance(node, list):
            for child in node:
                found.extend(self.companions(child))
        return found

    def test_every_pair_count_carries_its_provenance_counts(self):
        reported = self.companions(self.stats)
        self.assertGreater(len(reported), 0)
        for block in reported:
            self.assertIn("pairs_with_provenance", block)
            self.assertIn("pairs_without_provenance", block)
            self.assertIn("produces_edges", block)

    def test_the_estate_total_and_every_repository_report_it(self):
        self.assertIn("identical_bytes", self.stats["graph"])
        for entry in self.stats["repositories"]:
            self.assertIn("identical_bytes", entry["graph"])

    def test_the_two_counts_partition_the_pairs(self):
        for block in self.companions(self.stats):
            self.assertEqual(
                block["pairs"],
                block["pairs_with_provenance"] + block["pairs_without_provenance"],
            )

    def test_a_repository_with_no_pairs_still_reports_every_key(self):
        # Zero is a measurement. A rung that found nothing has to read as a
        # rung that found nothing, not as a rung that was not looked at.
        gamma = next(entry for entry in self.stats["repositories"]
                     if entry["repository"] == "gamma")
        block = gamma["graph"]["identical_bytes"]
        self.assertEqual(block["pairs"], 0)
        self.assertEqual(
            set(block["produces_by_evidence"]), set(provenance.EVIDENCE_LADDER)
        )

    def test_the_summary_is_the_only_source_of_both(self):
        empty = provenance.summary(provenance.Scan(), [], [])
        self.assertEqual(empty["pairs"], 0)
        self.assertEqual(empty["pairs_with_provenance"], 0)


class TestIdenticalBytes(EstateTestCase):
    def test_the_byte_identical_pair_is_an_edge(self):
        pairs = {(row[0], row[1]) for row in self.edges("IDENTICAL_BYTES")}
        self.assertIn(("AGENTS.md", "CLAUDE.md"), pairs)
        self.assertIn(("build/rules.md", "dist/rules.md"), pairs)

    def test_one_row_per_unordered_pair(self):
        pairs = [(row[0], row[1]) for row in self.edges("IDENTICAL_BYTES")]
        self.assertEqual(len(pairs), len(set(pairs)))
        for first, second in pairs:
            self.assertNotIn((second, first), pairs)
            # Lexicographic, so which way round a pair is written is not a
            # fact about the walk order.
            self.assertLess(first, second)

    def test_the_edge_carries_the_digest_both_files_hash_to(self):
        root = Path(self.alpha["path"])
        for source, target, _, _, _, _, sha256 in self.edges("IDENTICAL_BYTES"):
            first = hashlib.sha256((root / source).read_bytes()).hexdigest()
            second = hashlib.sha256((root / target).read_bytes()).hexdigest()
            self.assertEqual(sha256, first)
            self.assertEqual(sha256, second)

    def test_an_observation_carries_no_detector(self):
        # The evidence is the hash. There is no rule that could have been
        # wrong, so there is no detector to name.
        for row in self.edges("IDENTICAL_BYTES"):
            self.assertIsNone(row[2])

    def test_every_file_is_hashed_not_only_the_surfaces(self):
        block = self.alpha["graph"]["identical_bytes"]
        self.assertGreater(block["files_hashed"], self.alpha["graph"]["surfaces"])

    def test_a_pair_is_never_written_across_two_repositories(self):
        # alpha/docs/notes.md and beta/docs/notes.md are the same bytes. They
        # are two snapshots, each with its own branch and commit, so there is
        # no pair -- and each repository still hashed its own copy.
        pairs = [(row[0], row[1]) for row in self.edges("IDENTICAL_BYTES")]
        self.assertNotIn(("docs/notes.md", "docs/notes.md"), pairs)
        for entry in self.stats["repositories"]:
            if entry["repository"] == "beta":
                self.assertEqual(entry["graph"]["identical_bytes"]["pairs"], 0)

    def test_empty_files_are_counted_and_left_out_of_the_pairing(self):
        # An empty file matches every other empty file. Twenty of them would
        # report 190 pairs that say nothing about any of them, so they are
        # named and excluded rather than silently dropped.
        block = self.alpha["graph"]["identical_bytes"]
        self.assertEqual(block["zero_byte_files_not_paired"], 2)
        paired = {path for row in self.edges("IDENTICAL_BYTES") for path in row[:2]}
        self.assertNotIn("build/.gitkeep", paired)
        self.assertNotIn("dist/.gitkeep", paired)


class TestPairsWithProvenance(EstateTestCase):
    def test_a_pair_whose_files_carry_a_header_links_to_the_producer(self):
        produced = {
            (row[0], row[1]) for row in self.edges("PRODUCES")
        }
        self.assertIn(("scripts/build_rules.py", "build/rules.md"), produced)
        self.assertIn(("scripts/build_rules.py", "dist/rules.md"), produced)
        self.assertEqual(
            self.alpha["graph"]["identical_bytes"]["pairs_with_provenance"], 1
        )

    def test_the_producer_edge_carries_a_file_line_locator(self):
        for row in self.edges("PRODUCES"):
            self.assertTrue(row[4])
            self.assertGreaterEqual(row[5], 1)

    def test_the_strongest_rung_wins(self):
        # `build/rules.md` names its producer in its own header AND is written
        # by a literal path in that same script. One fact, evidenced twice; the
        # row stands on the stronger rung and is not written twice.
        rungs = [row[2] for row in self.edges("PRODUCES") if row[1] == "build/rules.md"]
        self.assertEqual(rungs, [provenance.ARTIFACT_HEADER])

    def test_each_rung_of_the_ladder_is_reachable(self):
        by_evidence = self.alpha["graph"]["identical_bytes"]["produces_by_evidence"]
        for rung in provenance.EVIDENCE_LADDER:
            self.assertGreater(by_evidence[rung], 0, rung)

    def test_a_manifest_declaration_names_both_ends(self):
        edges = [row for row in self.edges("PRODUCES")
                 if row[2] == provenance.MANIFEST_DECLARATION]
        self.assertEqual(len(edges), 1)
        source, target, _, address, evidence_path, _, _ = edges[0]
        self.assertEqual(source, "docs/notes.md")
        self.assertEqual(target, "build/notes.md")
        self.assertEqual(address, "docs/notes.md")
        # The evidence is in neither end of the edge. That is why it has a
        # locator of its own.
        self.assertEqual(evidence_path, "build/manifest.json")

    def test_a_literal_write_path_is_evidenced_in_the_script(self):
        edges = [row for row in self.edges("PRODUCES")
                 if row[2] == provenance.LITERAL_WRITE_PATH]
        self.assertEqual([(row[0], row[1]) for row in edges],
                         [("scripts/build_rules.py", "build/tally.txt")])
        self.assertEqual(edges[0][4], "scripts/build_rules.py")


class TestPairsWithoutProvenance(EstateTestCase):
    def test_a_pair_with_no_provenance_is_reported_as_exactly_that(self):
        # CLAUDE.md and AGENTS.md are the same bytes and nothing in the estate
        # says why. The finding is the pair and the absence of evidence; no
        # third fact is derived from them.
        produced = {row[1] for row in self.edges("PRODUCES")}
        self.assertNotIn("CLAUDE.md", produced)
        self.assertNotIn("AGENTS.md", produced)
        self.assertEqual(
            self.alpha["graph"]["identical_bytes"]["pairs_without_provenance"], 1
        )

    def test_the_pair_is_still_a_row(self):
        # Reported, not withheld for lack of an explanation.
        pairs = {(row[0], row[1]) for row in self.edges("IDENTICAL_BYTES")}
        self.assertIn(("AGENTS.md", "CLAUDE.md"), pairs)

    def test_a_producer_named_but_not_in_the_tree_writes_no_edge(self):
        # `build/summary.md` names scripts/absent-build.py. An edge needs both
        # ends, so there is none -- and the naming is counted, because a
        # producer named and not found is not a producer never named.
        produced = {row[1] for row in self.edges("PRODUCES")}
        self.assertNotIn("build/summary.md", produced)
        self.assertEqual(
            self.alpha["graph"]["identical_bytes"]
            ["producer_named_no_indexed_target_match"],
            1,
        )

    def test_generation_declared_without_a_producer_is_its_own_count(self):
        # `build/notes.md` says it was generated and does not say by what.
        # That is evidence of something, and it is not evidence of what, so it
        # is neither an edge nor nothing.
        self.assertEqual(
            self.alpha["graph"]["identical_bytes"]
            ["generation_declared_without_producer_named"],
            1,
        )
        # And the weaker rung that does name both ends still stands.
        produced = {row[1] for row in self.edges("PRODUCES")}
        self.assertIn("build/notes.md", produced)


class TestReindex(EstateTestCase):
    def test_reindexing_does_not_write_a_second_copy_of_a_pair(self):
        before = self.edges("IDENTICAL_BYTES")
        index(self.estate, db_path=self.db)
        self.assertEqual(self.edges("IDENTICAL_BYTES"), before)


class TestProducerParsing(unittest.TestCase):
    """Only the first token, and none of the comment around it."""

    def test_trailing_comment_syntax_is_not_captured(self):
        header = "<!-- Generated by scripts/build.py -- DO NOT EDIT -->\n"
        self.assertEqual(provenance.header_producer(header), ("scripts/build.py", 1))

    def test_a_closing_marker_with_no_space_before_it(self):
        self.assertEqual(provenance.producer_name("scripts/build.py-->"),
                         "scripts/build.py")

    def test_a_name_in_backticks(self):
        self.assertEqual(provenance.producer_name("`scripts/build.py`"),
                         "scripts/build.py")

    def test_a_name_ending_a_sentence(self):
        self.assertEqual(provenance.producer_name("scripts/build.py."),
                         "scripts/build.py")

    def test_a_block_comment_close(self):
        self.assertEqual(provenance.producer_name("scripts/build.py*/"),
                         "scripts/build.py")
        self.assertEqual(
            provenance.header_producer("/* Generated by scripts/build.py */\n"),
            ("scripts/build.py", 1),
        )

    def test_a_frontmatter_declaration(self):
        text = "---\ngenerated_by: scripts/build.py\n---\n\n# Rules\n"
        self.assertEqual(provenance.header_producer(text), ("scripts/build.py", 2))

    def test_a_header_naming_nothing_path_shaped_is_not_a_producer(self):
        header = "<!-- Generated by hand -->\n"
        self.assertIsNone(provenance.header_producer(header))
        self.assertTrue(provenance.declares_generation(header))


class TestProseIsNotAHeader(unittest.TestCase):
    """The tool must not report itself.

    This project has already paid for that failure once, at 1,349 phantom
    findings out of 1,373. The first run of this detector read the sentence in
    ticket 05 that warns about trailing comment syntax and reported the ticket
    as an artifact of the script that sentence names. The ticket's own text is
    the regression case, read from the file rather than copied, so rewording it
    cannot quietly retire the test.
    """

    def test_the_ticket_that_asks_for_this_detector_is_not_an_artifact(self):
        ticket = (support.REPO_ROOT / "orbit" / "tickets"
                  / "05-identical-bytes-with-provenance.md")
        text = ticket.read_text(encoding="utf-8")
        self.assertIn("Generated by scripts/build.py", text)
        self.assertIsNone(provenance.header_producer(text))

    def test_a_sentence_about_generation_is_not_a_declaration(self):
        self.assertFalse(provenance.declares_generation(
            "The header says DO NOT EDIT, which is how an artifact declares "
            "itself.\n"
        ))

    def test_a_path_in_a_script_is_only_a_target_where_the_line_writes(self):
        root = support.REPO_ROOT
        reading = 'text = Path("orbit/README.md").read_text()\n'
        writing = 'Path("orbit/README.md").write_text(text)\n'
        self.assertEqual(provenance.script_productions(root, "build.py", reading), [])
        self.assertEqual(
            [one.artifact_path
             for one in provenance.script_productions(root, "build.py", writing)],
            ["orbit/README.md"],
        )

    def test_an_arrow_is_not_a_redirect(self):
        root = support.REPO_ROOT
        line = 'const load = () => require("orbit/README.md");\n'
        self.assertEqual(provenance.script_productions(root, "load.js", line), [])


class TestThisRepository(unittest.TestCase):
    """The detectors, run over the repository the code is sitting in.

    The same discipline `test_pointers.py` applies to pointers: a detector that
    can only be checked against a fixture it was written for has not been
    checked. This is the repository the ticket's own measurement came from --
    28 byte-identical pairs, every one a workbench file matching a published
    file.
    """

    @classmethod
    def setUpClass(cls):
        cls.root = support.REPO_ROOT.resolve()
        cls.scan = provenance.read_tree(cls.root, surfaces.walk_files(cls.root))
        cls.pairs = provenance.pairs(cls.scan.contents, cls.scan.zero_byte)
        cls.productions = provenance.strongest(cls.scan.productions)
        cls.summary = provenance.summary(cls.scan, cls.pairs, cls.productions)

    def test_the_pairs_the_ticket_measured_are_still_there(self):
        # The measurement the ticket was written from. Stated as a floor rather
        # than an equality: the estate is allowed to grow.
        self.assertGreaterEqual(self.summary["pairs"], 28)

    def test_the_pairing_is_between_the_workbench_and_the_published_files(self):
        # What a bare count over-reads *as*. Named here so that if the shape of
        # the finding ever changes, the test says which shape it was.
        crossing = [
            pair for pair in self.pairs
            if pair.first_path.startswith("_rule-workbench/")
            != pair.second_path.startswith("_rule-workbench/")
        ]
        self.assertGreaterEqual(len(crossing), 28)

    def test_no_file_here_is_reported_as_an_artifact_of_a_producer(self):
        # Zero producers on a repository whose identity pairs all have one is
        # the ticket's own finding, and it is a true one: nothing in this tree
        # declares its provenance in a header, a manifest or a write path.
        # A number above zero here is a claim, and it has to be checked by hand
        # before it is believed.
        self.assertEqual(
            [(one.producer_path, one.artifact_path) for one in self.productions],
            [],
        )

    def test_every_pair_is_reported_with_its_provenance_count(self):
        self.assertEqual(
            self.summary["pairs"],
            self.summary["pairs_with_provenance"]
            + self.summary["pairs_without_provenance"],
        )

    def test_nothing_was_left_unread(self):
        self.assertEqual(self.summary["files_not_read"], 0)


if __name__ == "__main__":
    unittest.main()
