"""Two states of one repository, differenced. Seam A and Seam B.

Counts are against ``build_states``, never against a live repository: a test
that reads real repository content fails whenever that content changes,
including from this work. The acceptance run over Advisor-Desk's own history is
evidence, recorded in the ticket and the README.

What the fixture pins, and why each row is here:

``c0 -> c1``
    A tool was added and no governance was. The file count moves by eight, the
    Markdown count by four -- two different numbers, so neither can stand in for
    the other -- every directory but the one that was added moves by zero, and
    **the governance count does not move at all**. That zero is the row the
    whole comparison turns on.

``c1 -> c2``
    Governance was added, and the count moves. The zero above has to be shown
    not to be structural: a comparison reporting no governance added whatever
    was added is measuring nothing.

``two names for one file``
    Counted once, labelled by the target, in every state -- and the number
    folded reported per state rather than absorbed into the total. Fourteen such
    links sit in both states of the real repository, and counted as governance
    in one state and not the other they would move the zero on their own.
"""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from . import support
from .test_vocabulary import offending_words

from build_states import BOOKS, GOVERNANCE, GOVERNANCE_LINK, STATES, TOOL, build
from orbit_context import compare


# What `c1` added, counted from the fixture's own tables rather than written
# down twice: a test whose expected number is a literal stops checking the
# fixture the moment the fixture changes.
TOOL_FILES = len(TOOL)
TOOL_MARKDOWN = len([name for name in TOOL if name.endswith(".md")])
# What `c2` added that is governance: three declared rule files and one agent
# definition. The vendor-named link it also added is a second name for a file
# that is already a surface, and adds nothing.
GOVERNANCE_ADDED = len(GOVERNANCE) + 1


def _compare(repo: Path, before: str, after: str, db: Path) -> compare.Comparison:
    return compare.compare(repo, before, after, db_path=db)


class StatesTestCase(unittest.TestCase):
    """Seam A: build the repository at three commits and difference them."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-compare-"))
        cls.repo = build(cls.tmp / "states")
        cls.db = cls.tmp / "graph.duckdb"
        cls.tool = _compare(cls.repo, STATES[0], STATES[1], cls.db)
        cls.governance = _compare(cls.repo, STATES[1], STATES[2], cls.db)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


class TestASessionThatAddedATool(StatesTestCase):
    def test_the_files_it_added_are_counted(self):
        self.assertEqual(
            self.tool.after.files_walked - self.tool.before.files_walked,
            TOOL_FILES,
        )

    def test_markdown_and_files_are_different_numbers(self):
        # A comparison reporting one number for both would say neither: this
        # session added eight files, four of them Markdown, and the second
        # figure is the one that reads as governance if nothing separates them.
        markdown = self.tool.suffixes()[".md"]
        self.assertEqual(markdown.delta, TOOL_MARKDOWN)
        self.assertNotEqual(markdown.delta, TOOL_FILES)

    def test_nothing_outside_the_directory_it_added_moved(self):
        for name, row in self.tool.directories().items():
            expected = TOOL_FILES if name == "tool" else 0
            self.assertEqual(row.delta, expected, name)

    def test_the_files_outside_what_moved_are_totalled(self):
        # The row the ticket asks for as "non-orbit files: 201, 201, 0". Every
        # directory but the one that grew is at delta 0, so the total is the
        # whole of the first state -- and it is totalled over every directory,
        # listed or not, so the listing's cap cannot hide a file from it.
        outside = self.tool.before.files_walked
        self.assertRegex(
            compare.render(self.tool),
            rf"every directory that did not move\s+{outside}\s+{outside}\s+0",
        )

    def test_it_added_no_governance(self):
        # The row this ticket turns on. The session built a tool and left the
        # rule corpus alone; a comparison reporting governance here is reporting
        # rules the session did not write.
        self.assertEqual(self.tool.surfaces().delta, 0)
        self.assertEqual(
            self.tool.before.surface_rows, self.tool.after.surface_rows
        )

    def test_both_absolute_figures_sit_beside_every_delta(self):
        # A delta alone cannot tell "the second state added forty" from "the
        # first state was miscounted by forty", and the second is the failure
        # mode this project has already had twice.
        for row in self.tool.rows():
            self.assertEqual(row.delta, row.after - row.before, row.name)
            self.assertIn(str(row.before), compare.render(self.tool))
            self.assertIn(str(row.after), compare.render(self.tool))


class TestASessionThatGrewGovernance(StatesTestCase):
    def test_governance_added_is_reported_where_it_was_added(self):
        # The zero above is a measurement, not a property of the comparison.
        self.assertEqual(self.governance.surfaces().delta, GOVERNANCE_ADDED)

    def test_a_second_name_for_one_file_adds_no_surface(self):
        link, target = GOVERNANCE_LINK
        labels = self.governance.after.surface_labels
        self.assertIn(target, labels)
        self.assertNotIn(link, labels)


class TestTwoNamesForOneFile(StatesTestCase):
    def test_a_link_is_folded_into_the_file_it_names(self):
        for book in BOOKS:
            self.assertNotIn(
                f"_rule-workbench/{book}/full.md", self.tool.before.surface_labels
            )
            self.assertIn(
                f"{book}/{book}.md", self.tool.before.surface_labels
            )

    def test_the_number_folded_is_reported_per_state(self):
        # Never a total. A fold in one state and not the other is exactly what
        # moves a zero, and one summed figure would hide which state it was.
        self.assertEqual(self.tool.before.surfaces_folded, len(BOOKS))
        self.assertEqual(self.tool.after.surfaces_folded, len(BOOKS))
        self.assertEqual(self.governance.after.surfaces_folded, len(BOOKS) + 1)

    def test_the_fold_is_reported_beside_the_count_and_not_inside_it(self):
        text = compare.render(self.governance)
        self.assertIn("two names for one file", text)
        self.assertIn(GOVERNANCE_LINK[1], text)


class TestTheStatesAreComparable(StatesTestCase):
    def test_both_states_carry_the_same_detector_set(self):
        self.assertEqual(
            self.tool.before.detector_set_version,
            self.tool.after.detector_set_version,
        )
        self.assertTrue(self.tool.comparable)

    def test_the_output_states_the_detector_set(self):
        self.assertIn(self.tool.before.detector_set_version,
                      compare.render(self.tool))

    def test_states_read_by_different_detector_sets_are_not_comparable(self):
        moved = compare.Comparison(
            before=self.tool.before,
            after=self.tool.after.with_detector_set_version("1.000000000000"),
            database_path=str(self.db),
        )
        self.assertFalse(moved.comparable)
        # Said, not implied: the deltas are still printed, and what the reader
        # has to know about them is that two detector sets produced them.
        self.assertIn(compare.NOT_COMPARABLE, compare.render(moved))


class TestTheComparisonLeavesTheRepositoryAlone(StatesTestCase):
    def test_the_working_tree_is_not_checked_out_over(self):
        state = subprocess.run(
            ["git", "status", "--porcelain"], cwd=self.repo,
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(state.stdout, "")
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.repo,
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(head.stdout.strip(), self.governance.after.commit_sha)

    def test_no_worktree_is_left_behind(self):
        listed = subprocess.run(
            ["git", "worktree", "list"], cwd=self.repo,
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(len(listed.stdout.strip().splitlines()), 1,
                         listed.stdout)


class TestTheOutput(StatesTestCase):
    def test_it_carries_no_word_from_the_constrained_vocabulary(self):
        for comparison in (self.tool, self.governance):
            self.assertEqual(offending_words(compare.render(comparison)), [])

    def test_it_says_what_was_indexed_for_each_state(self):
        text = compare.render(self.tool)
        self.assertIn(self.tool.before.commit_sha[:12], text)
        self.assertIn(self.tool.after.commit_sha[:12], text)


class TestTheCommandLine(unittest.TestCase):
    """Seam B: the shape of the arguments, the output and the exit code."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-compare-cli-"))
        cls.repo = build(cls.tmp / "states")
        cls.db = cls.tmp / "graph.duckdb"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_compare(self, *arguments):
        return subprocess.run(
            [sys.executable, "-m", "orbit_context.cli", "compare", *arguments,
             "--repo", str(self.repo), "--db", str(self.db)],
            cwd=str(support.ORBIT_ROOT), capture_output=True, text=True,
        )

    def test_one_command_prints_the_table(self):
        result = self.run_compare(STATES[0], STATES[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("files walked", result.stdout)
        self.assertIn("governance surfaces", result.stdout)
        self.assertIn(".md", result.stdout)

    def test_the_exit_code_says_when_a_state_could_not_be_read(self):
        result = self.run_compare(STATES[0], "no-such-commit")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("no-such-commit", result.stderr)


if __name__ == "__main__":
    unittest.main()
