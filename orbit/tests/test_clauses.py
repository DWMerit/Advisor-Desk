"""A single rule is addressable.

Acceptance covered here:
  - a rule buried three headings deep is retrievable by `fqn`
  - retrieved text is byte-identical to that span of the file on disk
  - editing the file and re-indexing moves the offsets
  - no clause text is stored in any column
  - nesting depth is queryable via `CONTAINS`
"""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from . import support

from build_estate import SHARED_INSTRUCTIONS, build
from orbit_context import clauses, retrieve, store
from orbit_context.indexer import index
from orbit_context.ontology import load
from orbit_context.workspace import project_id_from_path

# Three headings deep, and the second rule under the deepest of them.
DEEP_FQN = (
    "CLAUDE.md#Estimating rules#M6 anchors#Cast-in channel"
    "#Edge distance ≥ 75 mm from the nearest saw cut."
)
SECTION_FQN = "CLAUDE.md#Estimating rules#M6 anchors#Cast-in channel"


class EstateTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-clause-"))
        cls.estate = build(cls.tmp / "estate")
        cls.alpha = cls.estate / "alpha"
        cls.db = cls.tmp / "graph.duckdb"
        cls.stats = index(cls.estate, db_path=cls.db)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def query(self, sql, params=None):
        connection = store.connect(self.db, read_only=True)
        try:
            return connection.execute(sql, params or []).fetchall()
        finally:
            connection.close()


class TestSegmentation(unittest.TestCase):
    """Structure only: heading tree first, then list items beneath a heading."""

    def setUp(self):
        self.found = clauses.segment(SHARED_INSTRUCTIONS, "CLAUDE.md")
        self.by_fqn = {clause.fqn: clause for clause in self.found}

    def test_heading_tree_is_the_fqn(self):
        self.assertIn("CLAUDE.md#Estimating rules", self.by_fqn)
        self.assertIn("CLAUDE.md#Estimating rules#M6 anchors", self.by_fqn)
        self.assertIn(SECTION_FQN, self.by_fqn)

    def test_a_list_item_beneath_a_heading_is_a_clause(self):
        self.assertEqual(self.by_fqn[DEEP_FQN].clause_type, clauses.LIST_RULE)

    def test_the_nearest_heading_is_recorded(self):
        self.assertEqual(self.by_fqn[DEEP_FQN].heading, "Cast-in channel")

    def test_a_fenced_block_is_a_clause(self):
        block = self.by_fqn["CLAUDE.md#Estimating rules#Takeoff#sh"]
        self.assertEqual(block.clause_type, clauses.CODE_BLOCK)

    def test_a_heading_section_holds_everything_under_it(self):
        section = self.by_fqn[SECTION_FQN]
        rule = self.by_fqn[DEEP_FQN]
        self.assertLessEqual(section.start_byte, rule.start_byte)
        self.assertGreaterEqual(section.end_byte, rule.end_byte)

    def test_offsets_are_byte_offsets_not_character_offsets(self):
        """The whole point of the ticket's warning.

        Everything above this clause contains an em dash, two curly quotes and
        a >= sign. Each costs more bytes than characters, so a character offset
        lands short of the clause's own text -- and silently.
        """
        rule = self.by_fqn[DEEP_FQN]
        raw = SHARED_INSTRUCTIONS.encode("utf-8")
        character_offset = SHARED_INSTRUCTIONS.index("- Edge distance")
        self.assertGreater(rule.start_byte, character_offset)
        self.assertTrue(
            raw[rule.start_byte:rule.end_byte].decode("utf-8").startswith("- Edge distance")
        )
        # What a character offset would have produced instead.
        self.assertFalse(
            raw[character_offset:].decode("utf-8", "replace").startswith("- Edge distance")
        )

    def test_every_clause_type_is_declared(self):
        for clause in self.found:
            self.assertIn(clause.clause_type, clauses.CLAUSE_TYPES)

    def test_a_frontmatter_field_is_a_clause(self):
        text = "---\nname: anchor-schedule\ndescription: Read it off the drawing.\n---\n\n# Body\n"
        found = {clause.fqn: clause for clause in clauses.segment(text, "SKILL.md")}
        self.assertEqual(
            found["SKILL.md#description"].clause_type, clauses.FRONTMATTER_FIELD
        )
        self.assertEqual(found["SKILL.md#name"].parent, None)

    def test_structure_inside_a_fenced_block_is_not_segmented(self):
        text = "# Heading\n\n```md\n## Not a heading\n- Not a rule\n```\n"
        found = [clause.fqn for clause in clauses.segment(text, "CLAUDE.md")]
        self.assertEqual(found, ["CLAUDE.md#Heading", "CLAUDE.md#Heading#md"])

    def test_a_file_with_no_structure_produces_no_clauses(self):
        self.assertEqual(clauses.segment("Just a sentence.\n", "CLAUDE.md"), [])


class TestClausesLand(EstateTestCase):
    def test_the_deep_rule_is_a_row(self):
        rows = self.query(
            "SELECT clause_type, heading FROM gl_context_clause WHERE fqn = ?", [DEEP_FQN]
        )
        # One per repository holding those bytes: alpha's CLAUDE.md, and
        # alpha's AGENTS.md is a different surface_path.
        self.assertGreaterEqual(len(rows), 1)
        self.assertEqual(rows[0], ("list-rule", "Cast-in channel"))

    def test_statistics_count_clauses_and_edges(self):
        # One CONTAINS edge per clause. The edge total is larger because
        # gl_context_edge also holds the REFERENCES edges of ticket 04.
        self.assertGreater(self.stats["graph"]["clauses"], 0)
        contains = self.query(
            "SELECT count(*) FROM gl_context_edge WHERE relationship_kind = 'CONTAINS'"
        )[0][0]
        self.assertEqual(contains, self.stats["graph"]["clauses"])
        self.assertGreaterEqual(self.stats["graph"]["edges"], contains)

    def test_only_whole_file_text_surfaces_are_segmented(self):
        paths = {row[0] for row in self.query("SELECT DISTINCT surface_path FROM gl_context_clause")}
        self.assertIn("CLAUDE.md", paths)
        self.assertNotIn(".claude/settings.json", paths)
        self.assertNotIn(".mcp.json", paths)

    def test_a_skill_frontmatter_field_is_addressable(self):
        rows = self.query(
            "SELECT fqn FROM gl_context_clause WHERE clause_type = 'frontmatter-field' "
            "ORDER BY fqn"
        )
        self.assertIn(
            (".claude/skills/anchor-schedule/SKILL.md#description",),
            rows,
        )

    def test_reindexing_does_not_duplicate_clauses(self):
        before = self.query("SELECT count(*) FROM gl_context_clause")[0][0]
        index(self.estate, db_path=self.db)
        self.assertEqual(self.query("SELECT count(*) FROM gl_context_clause")[0][0], before)

    def test_no_clause_text_is_stored_in_any_column(self):
        """The row carries a path and offsets; the caller reads the bytes."""
        connection = store.connect(self.db, read_only=True)
        try:
            self.assertNotIn(
                "content", store.existing_columns(connection, "gl_context_clause")
            )
        finally:
            connection.close()

        # Scoped to alpha: three repositories hold a `CLAUDE.md`, and slicing
        # one repository's bytes at another's offsets compares nothing.
        raw = (self.alpha / "CLAUDE.md").read_bytes()
        rows = self.query(
            "SELECT *, start_byte, end_byte FROM gl_context_clause "
            "WHERE surface_path = 'CLAUDE.md' AND project_id = ?",
            [project_id_from_path(str(self.alpha))],
        )
        self.assertGreater(len(rows), 0)
        for row in rows:
            span = raw[row[-2]:row[-1]].decode("utf-8")
            stored = "\x00".join(str(value) for value in row)
            self.assertNotIn(span, stored)
            # An fqn quotes the estate's own heading, which is the address. What
            # must not be there is the clause itself -- anything past its first
            # line.
            beyond_the_first_line = span.split("\n", 1)[1].strip()
            if beyond_the_first_line:
                self.assertNotIn(beyond_the_first_line, stored)


class TestContainsEdges(EstateTestCase):
    def depth_of(self, fqn):
        """How deep a clause sits, walked over CONTAINS rather than read off a column."""
        rows = self.query(
            """
            WITH RECURSIVE walk(id, depth) AS (
                SELECT target_id, 1 FROM gl_context_edge
                 WHERE relationship_kind = 'CONTAINS' AND source_kind = 'Surface'
                UNION ALL
                SELECT e.target_id, walk.depth + 1
                  FROM gl_context_edge e JOIN walk ON e.source_id = walk.id
                 WHERE e.relationship_kind = 'CONTAINS' AND e.source_kind = 'Clause'
            )
            SELECT max(walk.depth)
              FROM walk JOIN gl_context_clause c ON c.id = walk.id
             WHERE c.fqn = ?
            """,
            [fqn],
        )
        return rows[0][0]

    def test_a_surface_contains_its_top_level_clauses(self):
        rows = self.query(
            "SELECT count(*) FROM gl_context_edge e "
            "JOIN gl_context_surface s ON s.id = e.source_id "
            "WHERE e.source_kind = 'Surface' AND e.relationship_kind = 'CONTAINS' "
            "AND s.path = 'CLAUDE.md'"
        )
        self.assertGreater(rows[0][0], 0)

    def test_a_clause_contains_the_clause_nested_in_it(self):
        rows = self.query(
            "SELECT count(*) FROM gl_context_edge "
            "WHERE source_kind = 'Clause' AND target_kind = 'Clause' "
            "AND relationship_kind = 'CONTAINS'"
        )
        self.assertGreater(rows[0][0], 0)

    def test_nesting_depth_is_queryable(self):
        self.assertEqual(self.depth_of("CLAUDE.md#Estimating rules"), 1)
        self.assertEqual(self.depth_of("CLAUDE.md#Estimating rules#M6 anchors"), 2)
        self.assertEqual(self.depth_of(SECTION_FQN), 3)
        self.assertEqual(self.depth_of(DEEP_FQN), 4)

    def test_every_edge_carries_its_snapshot(self):
        rows = self.query(
            "SELECT count(*) FROM gl_context_edge "
            "WHERE traversal_path IS NULL OR branch = '' OR commit_sha = ''"
        )
        self.assertEqual(rows[0][0], 0)

    def test_every_contains_edge_target_is_a_clause_row(self):
        rows = self.query(
            "SELECT count(*) FROM gl_context_edge e "
            "LEFT JOIN gl_context_clause c ON c.id = e.target_id "
            "WHERE e.relationship_kind = 'CONTAINS' AND c.id IS NULL"
        )
        self.assertEqual(rows[0][0], 0)


class TestRetrieval(EstateTestCase):
    def read_span(self, fqn):
        found = retrieve.clauses(fqn, repo=self.alpha, db_path=self.db)
        self.assertEqual(len(found), 1, fqn)
        return found[0]

    def test_a_rule_three_headings_deep_is_retrievable_by_fqn(self):
        located = self.read_span(DEEP_FQN)
        self.assertEqual(located.surface_path, "CLAUDE.md")
        self.assertTrue(
            located.read().decode("utf-8").startswith("- Edge distance")
        )

    def test_retrieved_text_is_byte_identical_to_the_file(self):
        located = self.read_span(SECTION_FQN)
        on_disk = (self.alpha / "CLAUDE.md").read_bytes()
        self.assertEqual(
            located.read(), on_disk[located.start_byte:located.end_byte]
        )

    def test_an_fqn_with_no_clause_returns_nothing(self):
        self.assertEqual(
            retrieve.clauses("CLAUDE.md#Absent", repo=self.alpha, db_path=self.db), []
        )

    def test_the_command_prints_only_the_bytes(self):
        """`show` writes the span to stdout and its locator to stderr."""
        result = subprocess.run(
            [sys.executable, str(support.ORBIT_ROOT / "bin" / "orbit-context"),
             "show", DEEP_FQN, "--repo", str(self.alpha), "--db", str(self.db)],
            capture_output=True, check=True,
        )
        on_disk = (self.alpha / "CLAUDE.md").read_bytes()
        located = self.read_span(DEEP_FQN)
        self.assertEqual(result.stdout, on_disk[located.start_byte:located.end_byte])
        self.assertIn(b"CLAUDE.md:", result.stderr)

    def test_the_command_reports_an_fqn_it_cannot_find(self):
        result = subprocess.run(
            [sys.executable, str(support.ORBIT_ROOT / "bin" / "orbit-context"),
             "show", "CLAUDE.md#Absent", "--repo", str(self.alpha), "--db", str(self.db)],
            capture_output=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, b"")


class TestEditingMovesTheOffsets(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-offsets-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.estate = build(self.tmp / "estate")
        self.alpha = self.estate / "alpha"
        self.db = self.tmp / "graph.duckdb"

    def test_editing_the_file_and_reindexing_moves_the_offsets(self):
        index(self.estate, db_path=self.db)
        before = retrieve.clauses(DEEP_FQN, repo=self.alpha, db_path=self.db)[0]
        original = before.read()

        surface = self.alpha / "CLAUDE.md"
        surface.write_text(
            "# Preamble\n\nInserted above everything — in bytes, not characters.\n\n"
            + surface.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        index(self.estate, db_path=self.db)

        after = retrieve.clauses(DEEP_FQN, repo=self.alpha, db_path=self.db)[0]
        self.assertGreater(after.start_byte, before.start_byte)
        self.assertGreater(after.start_line, before.start_line)
        self.assertEqual(after.read(), original)


class TestOntology(unittest.TestCase):
    def setUp(self):
        self.ontology = load()

    def test_clause_is_declared_before_it_is_written(self):
        node = self.ontology.nodes["Clause"]
        self.assertEqual(node.table, "gl_context_clause")
        for column in ("fqn", "clause_type", "start_line", "end_line",
                       "start_byte", "end_byte"):
            self.assertIn(column, node.column_names)

    def test_clause_content_is_virtual(self):
        self.assertNotIn("content", self.ontology.nodes["Clause"].column_names)

    def test_no_prose_columns_and_no_depth_column(self):
        node = self.ontology.nodes["Clause"]
        for banned in ("summary", "purpose", "depth", "text", "body"):
            self.assertNotIn(banned, node.column_names)

    def test_contains_declares_both_variants(self):
        edge = self.ontology.edges["CONTAINS"]
        self.assertEqual(edge.table, "gl_context_edge")
        self.assertTrue(edge.allows("Surface", "Clause"))
        self.assertTrue(edge.allows("Clause", "Clause"))
        self.assertFalse(edge.allows("Clause", "Surface"))

    def test_the_edge_table_uses_their_column_shape(self):
        edge = self.ontology.edges["CONTAINS"]
        for column in ("source_id", "source_kind", "relationship_kind",
                       "target_id", "target_kind", "traversal_path"):
            self.assertIn(column, edge.column_names)


if __name__ == "__main__":
    unittest.main()
