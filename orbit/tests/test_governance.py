"""Every governance object is a surface — ticket 02's acceptance.

  - all six surface_kind values appear from a fixture containing one of each
  - frontmatter bytes and body bytes are separately queryable for a skill
  - a hook definition row carries its matcher quoted verbatim with a
    `file:line` locator
  - a hook whose command resolves to a script in the tree is linked to it
  - a hook whose command is a PATH lookup is recorded as unresolvable, not as
    missing from the tree
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from . import support  # noqa: F401

from build_estate import build
from orbit_context import settings, store, surfaces
from orbit_context.indexer import index

# The six the ticket names. `hook-target` is additive on top of them.
TICKET_KINDS = {
    surfaces.INSTRUCTION_SURFACE,
    surfaces.SKILL_PACKAGE,
    surfaces.AGENT_DEFINITION,
    surfaces.COMMAND_DEFINITION,
    surfaces.HOOK_DEFINITION,
    surfaces.MCP_CONFIG,
}


class GovernanceTestCase(unittest.TestCase):
    """The fixture's `gamma` repository holds one of every governance object."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-governance-"))
        cls.estate = build(cls.tmp / "estate")
        cls.db = cls.tmp / "graph.duckdb"
        cls.stats = index(cls.estate, db_path=cls.db, detailed=True)
        cls.gamma = next(
            entry for entry in cls.stats["repositories"] if entry["repository"] == "gamma"
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


class TestSixKinds(GovernanceTestCase):
    def test_the_demo_query_lists_every_kind_with_its_size(self):
        rows = self.query(
            "SELECT surface_kind, name, size_bytes FROM gl_context_surface "
            "WHERE project_id = ? ORDER BY surface_kind, name",
            [self.gamma["project_id"]],
        )
        kinds = {row[0] for row in rows}
        self.assertTrue(TICKET_KINDS <= kinds, sorted(TICKET_KINDS - kinds))
        for kind, _, size in rows:
            self.assertGreater(size, 0, kind)

    def test_a_skill_package_is_named_from_its_frontmatter(self):
        rows = self.query(
            "SELECT path, name FROM gl_context_surface "
            "WHERE surface_kind = ? AND project_id = ?",
            [surfaces.SKILL_PACKAGE, self.gamma["project_id"]],
        )
        self.assertEqual(
            rows, [(".claude/skills/anchor-schedule/SKILL.md", "anchor-schedule")]
        )

    def test_an_agent_definition_is_named_from_its_frontmatter(self):
        rows = self.query(
            "SELECT path, name FROM gl_context_surface "
            "WHERE surface_kind = ? AND project_id = ?",
            [surfaces.AGENT_DEFINITION, self.gamma["project_id"]],
        )
        self.assertEqual(rows, [(".claude/agents/takeoff-reviewer.md", "takeoff-reviewer")])

    def test_a_command_is_named_by_its_path_under_commands(self):
        rows = dict(self.query(
            "SELECT path, name FROM gl_context_surface "
            "WHERE surface_kind = ? AND project_id = ?",
            [surfaces.COMMAND_DEFINITION, self.gamma["project_id"]],
        ))
        self.assertEqual(rows[".claude/commands/price-check.md"], "price-check")
        self.assertEqual(rows[".claude/commands/takeoff/count.md"], "takeoff/count")

    def test_mcp_servers_are_named_wherever_they_are_declared(self):
        rows = self.query(
            "SELECT path, name FROM gl_context_surface "
            "WHERE surface_kind = ? AND project_id = ? ORDER BY path",
            [surfaces.MCP_CONFIG, self.gamma["project_id"]],
        )
        self.assertEqual(
            rows,
            [(".claude/settings.json", "estimating-notes"),
             (".mcp.json", "drawing-index")],
        )

    def test_a_declaration_that_is_absent_is_reported_not_dropped(self):
        reasons = {
            entry["path"]: entry["reason"]
            for entry in self.stats["detailed"]["skipped_files"]
        }
        for path in (".claude/skills/undeclared/SKILL.md", ".claude/agents/scratch.md"):
            self.assertEqual(reasons.get(path), "frontmatter_declaration_absent", path)

    def test_a_file_without_a_declaration_is_not_a_row(self):
        rows = self.query(
            "SELECT count(*) FROM gl_context_surface WHERE path IN (?, ?)",
            [".claude/skills/undeclared/SKILL.md", ".claude/agents/scratch.md"],
        )
        self.assertEqual(rows, [(0,)])


class TestFrontmatterIsMeasuredApartFromTheBody(GovernanceTestCase):
    """The description loads at boot for every session; the body does not."""

    def test_a_skills_frontmatter_and_body_are_separately_queryable(self):
        rows = self.query(
            "SELECT frontmatter_bytes, body_bytes, size_bytes "
            "FROM gl_context_surface WHERE surface_kind = ? AND project_id = ?",
            [surfaces.SKILL_PACKAGE, self.gamma["project_id"]],
        )
        self.assertEqual(len(rows), 1)
        frontmatter, body, size = rows[0]
        self.assertGreater(frontmatter, 0)
        self.assertGreater(body, 0)
        self.assertEqual(frontmatter + body, size)

    def test_boot_cost_is_a_fraction_of_the_file(self):
        # The point of the split: a client-blind sum reports the whole file as
        # the boot cost.
        (frontmatter, size), = self.query(
            "SELECT frontmatter_bytes, size_bytes FROM gl_context_surface "
            "WHERE surface_kind = ? AND project_id = ?",
            [surfaces.SKILL_PACKAGE, self.gamma["project_id"]],
        )
        self.assertLess(frontmatter, size)

    def test_a_surface_without_frontmatter_reports_zero_not_null(self):
        (frontmatter, body, size), = self.query(
            "SELECT frontmatter_bytes, body_bytes, size_bytes "
            "FROM gl_context_surface WHERE path = 'CLAUDE.md' AND project_id = ?",
            [self.gamma["project_id"]],
        )
        self.assertEqual(frontmatter, 0)
        self.assertEqual(body, size)

    def test_a_surface_that_was_not_read_reports_null_not_zero(self):
        (frontmatter, body), = self.query(
            "SELECT frontmatter_bytes, body_bytes FROM gl_context_surface "
            "WHERE path = 'config/.cursorrules'"
        )
        self.assertIsNone(frontmatter)
        self.assertIsNone(body)


class TestHookDefinitions(GovernanceTestCase):
    def hooks(self):
        return self.query(
            "SELECT path, name, matcher, start_line, end_line, target_path, "
            "target_resolution, size_bytes FROM gl_context_surface "
            "WHERE surface_kind = ? AND project_id = ? ORDER BY start_line",
            [surfaces.HOOK_DEFINITION, self.gamma["project_id"]],
        )

    def test_every_hook_command_becomes_a_row(self):
        self.assertEqual(len(self.hooks()), 4)

    def test_a_hook_carries_its_matcher_verbatim_with_a_file_line_locator(self):
        settings_path = self.estate / "gamma" / ".claude" / "settings.json"
        lines = settings_path.read_text(encoding="utf-8").splitlines()
        for path, _, matcher, start_line, end_line, _, _, _ in self.hooks():
            self.assertEqual(path, ".claude/settings.json")
            self.assertIsNotNone(start_line)
            self.assertGreaterEqual(end_line, start_line)
            # The locator points at the entry it describes.
            self.assertIn('"command"', lines[start_line - 1])
            if matcher is not None:
                # Verbatim: the matcher is in the file exactly as recorded.
                self.assertIn(f'"matcher": "{matcher}"', settings_path.read_text())

    def test_matchers_are_quoted_not_normalised(self):
        matchers = {row[2] for row in self.hooks()}
        self.assertIn("Bash", matchers)
        self.assertIn("Edit|Write", matchers)

    def test_a_group_with_no_matcher_key_records_null_not_empty(self):
        by_event = {row[1]: row[2] for row in self.hooks()}
        self.assertIsNone(by_event["SessionStart"])

    def test_a_hooks_size_is_its_entry_not_its_file(self):
        file_size = (self.estate / "gamma" / ".claude" / "settings.json").stat().st_size
        for row in self.hooks():
            self.assertGreater(row[7], 0)
            self.assertLess(row[7], file_size)


class TestHookCommandResolution(GovernanceTestCase):
    def resolutions(self):
        return self.query(
            "SELECT target_resolution, target_path FROM gl_context_surface "
            "WHERE surface_kind = ? AND project_id = ?",
            [surfaces.HOOK_DEFINITION, self.gamma["project_id"]],
        )

    def test_a_command_in_the_tree_is_linked_to_that_file(self):
        linked = [
            path for resolution, path in self.resolutions()
            if resolution == settings.RESOLUTION_IN_TREE
        ]
        self.assertEqual(linked, [".claude/hooks/check-anchors.sh"] * 2)

    def test_the_linked_file_is_marked_as_a_hook_target(self):
        rows = self.query(
            "SELECT path, size_bytes FROM gl_context_surface "
            "WHERE surface_kind = ? AND project_id = ?",
            [surfaces.HOOK_TARGET, self.gamma["project_id"]],
        )
        self.assertEqual(len(rows), 1, "two hooks, one script, one hook-target row")
        path, size = rows[0]
        self.assertEqual(path, ".claude/hooks/check-anchors.sh")
        self.assertEqual(
            size, (self.estate / "gamma" / path).stat().st_size
        )

    def test_a_path_lookup_is_recorded_as_a_path_lookup(self):
        resolutions = {row[0] for row in self.resolutions()}
        self.assertIn(settings.RESOLUTION_PATH_LOOKUP, resolutions)

    def test_a_path_lookup_is_not_recorded_as_a_target_that_is_not_there(self):
        # The two are different findings about the estate and stay different.
        for resolution, path in self.resolutions():
            if resolution == settings.RESOLUTION_PATH_LOOKUP:
                self.assertEqual(path, "")
        self.assertIn(
            settings.RESOLUTION_NO_INDEXED_TARGET_MATCH,
            {row[0] for row in self.resolutions()},
        )

    def test_a_project_dir_variable_is_expanded(self):
        # `$CLAUDE_PROJECT_DIR/.claude/hooks/check-anchors.sh` is the same file
        # as `.claude/hooks/check-anchors.sh`.
        in_tree = [
            row for row in self.resolutions()
            if row[0] == settings.RESOLUTION_IN_TREE
        ]
        self.assertEqual(len(in_tree), 2)

    def test_non_hook_rows_carry_no_resolution(self):
        rows = self.query(
            "SELECT count(*) FROM gl_context_surface "
            "WHERE surface_kind <> ? AND target_resolution IS NOT NULL",
            [surfaces.HOOK_DEFINITION],
        )
        self.assertEqual(rows, [(0,)])


class TestCommandResolutionRules(unittest.TestCase):
    """The resolution rules on their own, without an estate around them."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-resolve-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        script = self.tmp / "hooks" / "run.sh"
        script.parent.mkdir(parents=True)
        script.write_text("#!/bin/sh\n", encoding="utf-8")

    def resolve(self, command):
        return settings.resolve_command(command, self.tmp)

    def test_a_relative_script_in_the_tree(self):
        self.assertEqual(self.resolve("hooks/run.sh"), ("hooks/run.sh", "in-tree"))

    def test_an_interpreter_in_front_of_a_script_in_the_tree(self):
        self.assertEqual(
            self.resolve("sh hooks/run.sh --check"), ("hooks/run.sh", "in-tree")
        )

    def test_an_absolute_path_inside_the_tree(self):
        self.assertEqual(
            self.resolve(f"{self.tmp}/hooks/run.sh"), ("hooks/run.sh", "in-tree")
        )

    def test_a_bare_program_name(self):
        self.assertEqual(self.resolve("jq -r '.tool_input'"), (None, "path-lookup"))

    def test_a_path_that_is_not_in_the_tree(self):
        self.assertEqual(
            self.resolve("python3 hooks/absent.py"), (None, "no-indexed-target-match")
        )

    def test_a_variable_that_cannot_be_expanded(self):
        self.assertEqual(
            self.resolve("$SOME_OTHER_ROOT/run.sh"), (None, "unexpanded-variable")
        )

    def test_a_command_that_cannot_be_split(self):
        self.assertEqual(self.resolve("echo 'unbalanced"), (None, "unparsable-command"))

    def test_a_path_outside_the_tree_is_not_linked(self):
        self.assertEqual(self.resolve("/usr/local/bin/run.sh")[0], None)


class TestEntriesOnOneLine(unittest.TestCase):
    """A settings file written on one line still gets one row per hook.

    The row id is derived from the entry's offset, not from its line, or a
    minified file would collapse every hook into a single row.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-oneline-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.estate = build(self.tmp / "estate")
        (self.estate / "gamma" / ".claude" / "settings.json").write_text(
            '{"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":'
            '[{"type":"command","command":"a.sh"},'
            '{"type":"command","command":"b.sh"}]}]}}',
            encoding="utf-8",
        )
        self.db = self.tmp / "graph.duckdb"
        index(self.estate, db_path=self.db)

    def test_both_entries_survive(self):
        connection = store.connect(self.db, read_only=True)
        try:
            rows = connection.execute(
                "SELECT start_line, size_bytes FROM gl_context_surface "
                "WHERE surface_kind = ?", [surfaces.HOOK_DEFINITION]
            ).fetchall()
        finally:
            connection.close()
        self.assertEqual(len(rows), 2)
        self.assertEqual({row[0] for row in rows}, {1})


class TestContainersThatCannotBeRead(unittest.TestCase):
    """A settings file that will not parse yields notes, never guessed rows."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-badjson-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.estate = build(self.tmp / "estate")
        (self.estate / "gamma" / ".claude" / "settings.json").write_text(
            '{"hooks": {', encoding="utf-8"
        )
        self.db = self.tmp / "graph.duckdb"
        self.stats = index(self.estate, db_path=self.db, detailed=True)

    def test_it_is_reported_with_a_reason(self):
        reasons = {
            entry["path"]: entry["reason"]
            for entry in self.stats["detailed"]["skipped_files"]
        }
        self.assertEqual(reasons.get(".claude/settings.json"), "invalid_json")

    def test_it_produces_no_rows(self):
        connection = store.connect(self.db, read_only=True)
        try:
            rows = connection.execute(
                "SELECT count(*) FROM gl_context_surface WHERE path = '.claude/settings.json'"
            ).fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(rows, 0)


if __name__ == "__main__":
    unittest.main()
