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

import contextlib
import dataclasses
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from . import support
from .test_vocabulary import offending_words

from build_states import (
    BOOKS, GOVERNANCE, GOVERNANCE_LINK, SETTINGS_PATH, SETTINGS_ROWS, STATES,
    TOOL, build,
)
from orbit_context import compare
from orbit_context.cli import main


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


class TestRowsStandingAtOnePath(StatesTestCase):
    """Only a link folds. Several rows legitimately stand at one path."""

    def test_a_settings_file_keeps_a_row_per_entry(self):
        # Two hooks and an MCP server in one file. A fold keyed on the path
        # would take these three down to one and report a file folded into
        # itself -- the dedupe quietly changing a count, which is the failure
        # mode this whole batch exists to catch.
        state = self.tool.before
        self.assertEqual(state.surface_rows - state.surface_files,
                         SETTINGS_ROWS - 1)
        self.assertIn(SETTINGS_PATH, state.surface_labels)

    def test_only_a_link_is_counted_as_folded(self):
        for state in (self.tool.before, self.tool.after):
            self.assertEqual(state.surfaces_folded, len(BOOKS))
            for fold in state.folds:
                self.assertNotEqual(fold.name, fold.counted_as)


class TestByteIdentityIsNeverCountedAlone(StatesTestCase):
    def test_the_pair_count_arrives_with_the_counts_that_read_it(self):
        text = compare.render(self.tool)
        self.assertIn("carrying provenance evidence", text)
        self.assertIn("carrying no provenance evidence", text)
        counts = self.tool.before.pair_counts
        self.assertEqual(counts.total,
                         counts.with_provenance + counts.without_provenance)


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
        # Faked here rather than in the code under test: what the comparison
        # does about two detector sets is a property of the comparison, and a
        # production method whose only caller is a test is a worse way to say so.
        moved = compare.Comparison(
            states=(
                self.tool.before,
                dataclasses.replace(
                    self.tool.after, detector_set_version="1.000000000000"
                ),
            ),
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

    def test_the_repository_a_state_came_from_was_not_written_to(self):
        """Not "left tidy" -- not written to at all.

        A state can come from a repository this project is allowed to read and
        not to touch, and `git worktree add` writes to the repository it is run
        in. So the comparison clones instead, and what that buys is checked
        here rather than asserted in a docstring: every path under `.git`, and
        what each one holds, is the same after a comparison as before it.
        """
        def git_directory() -> dict:
            return {
                str(path.relative_to(self.repo)): path.stat().st_mtime_ns
                for path in sorted((self.repo / ".git").rglob("*"))
            }

        before = git_directory()
        _compare(self.repo, STATES[0], STATES[2], self.db)
        self.assertEqual(git_directory(), before)


class TestTheOutput(StatesTestCase):
    def test_it_carries_no_word_from_the_constrained_vocabulary(self):
        for comparison in (self.tool, self.governance):
            self.assertEqual(offending_words(compare.render(comparison)), [])

    def test_it_says_what_was_indexed_for_each_state(self):
        text = compare.render(self.tool)
        self.assertIn(self.tool.before.commit_sha[:12], text)
        self.assertIn(self.tool.after.commit_sha[:12], text)


class ThreeStatesTestCase(unittest.TestCase):
    """Ticket 14's shape: two repositories descended from one base.

    ``lineage`` is the repository whose own history carries the three states.
    ``sibling`` is a second repository built from the same builder -- the same
    corpus, the same names -- standing for a clone that went its own way. A
    third, ``rewritten``, is that same sibling with every ``full.md`` holding a
    copy of the book it used to name: same corpus, same file count, a base that
    no longer tracks its source.
    """

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-three-"))
        cls.lineage = build(cls.tmp / "lineage")
        cls.sibling = build(cls.tmp / "sibling")
        cls.rewritten = build(cls.tmp / "rewritten", resolve_links=True)
        cls.db = cls.tmp / "graph.duckdb"
        cls.three = compare.compare(
            cls.lineage, STATES[0], STATES[1], f"{cls.sibling}@{STATES[2]}",
            db_path=cls.db,
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


class TestThreeStates(ThreeStatesTestCase):
    def test_every_state_carries_its_own_figures(self):
        for row in self.three.rows():
            self.assertEqual(len(row.values), 3, row.name)

    def test_every_delta_is_taken_against_the_baseline(self):
        # Not a chain. `C2 - C1` is a subtraction between two states that never
        # shared anything but a base, and reporting it would read as a session
        # having done what a whole second repository did.
        for row in self.three.rows():
            self.assertEqual(
                row.deltas,
                (row.values[1] - row.values[0], row.values[2] - row.values[0]),
                row.name,
            )

    def test_the_table_prints_a_column_per_state_and_a_delta_per_state(self):
        lines = compare.render(self.three).splitlines()
        counts = [n for n, line in enumerate(lines) if line.startswith("COUNTS")][0]
        heading = lines[counts + 1]
        for state in self.three.states:
            self.assertIn(state.label[:10], heading)
        # Two deltas, each named for the state it was taken from. One column
        # headed "delta" twice would be two subtractions the reader has to
        # work out from their order.
        self.assertEqual(heading.count("-" + STATES[0]), 2, heading)

    def test_a_state_of_another_repository_is_labelled_by_that_repository(self):
        sibling = self.three.states[2]
        self.assertEqual(sibling.label, f"sibling@{STATES[2]}")
        self.assertEqual(sibling.origin, str(self.sibling))
        self.assertIn(str(self.sibling), compare.render(self.three))

    def test_the_output_says_the_states_are_not_all_one_repository(self):
        # A delta between two repositories measures only what their shared base
        # makes it, and a table that looked identical either way would let a
        # reader take one for the other.
        self.assertIn("not all from one repository",
                      compare.render(self.three))
        two = compare.compare(self.lineage, STATES[0], STATES[1], db_path=self.db)
        self.assertNotIn("not all from one repository", compare.render(two))

    def test_it_carries_no_word_from_the_constrained_vocabulary(self):
        self.assertEqual(offending_words(compare.render(self.three)), [])


class TestWhetherAStateRewroteItsBase(ThreeStatesTestCase):
    """The question asked of the rows, and answered either way.

    Fourteen links weighing 32 bytes each, or fourteen files weighing what the
    books weigh. After the fold both read as fourteen names counted once, so
    the answer has to come from the link count and what the links weigh.
    """

    def _states(self, sibling: Path) -> compare.Comparison:
        return compare.compare(
            self.lineage, STATES[0], f"{sibling}@{STATES[0]}", db_path=self.db,
        )

    def test_a_base_that_is_intact_carries_the_same_links(self):
        intact = self._states(self.sibling)
        self.assertEqual(intact.before.link_rows, len(BOOKS))
        self.assertEqual(intact.after.link_rows, len(BOOKS))
        self.assertEqual(intact.before.link_bytes, intact.after.link_bytes)

    def test_a_base_whose_links_were_resolved_says_so_in_the_rows(self):
        rewritten = self._states(self.rewritten)
        self.assertEqual(rewritten.before.link_rows, len(BOOKS))
        self.assertEqual(rewritten.after.link_rows, 0)
        self.assertEqual(rewritten.after.link_bytes, 0)
        # And the fold that used to happen does not: the names are files now.
        self.assertEqual(rewritten.after.surfaces_folded, 0)
        self.assertGreater(rewritten.after.surface_bytes,
                           rewritten.before.surface_bytes)

    def test_the_file_count_alone_does_not_tell_the_two_apart(self):
        # Which is why the link rows are printed. The walk reaches the same
        # names in the same number, and a comparison reading only that figure
        # would report the two repositories as the same one.
        rewritten = self._states(self.rewritten)
        self.assertEqual(rewritten.before.files_walked,
                         rewritten.after.files_walked)
        self.assertEqual(rewritten.before.files_by_directory,
                         rewritten.after.files_by_directory)

    def test_both_figures_are_printed_per_state(self):
        text = compare.render(self._states(self.rewritten))
        self.assertIn("names that resolve to another name", text)
        self.assertRegex(text, r"names resolving to another name, \d+ bytes")


class TestWhatTheWalkWeighed(ThreeStatesTestCase):
    """Bytes walked, so a share of them can be stated as an observation.

    Nothing here computes a share, sets a threshold or raises anything on one:
    spec 0002 s11 refuses a metric built for a hypothesis before the hypothesis
    was measured. What the table owes a reader is the two figures the share is
    read off, in every state, beside each other.
    """

    def test_the_bytes_the_walk_weighed_are_reported_per_state(self):
        row = [row for row in self.three.rows() if row.name == "bytes walked"][0]
        self.assertEqual(len(row.values), 3)
        for value in row.values:
            self.assertGreater(value, 0)

    def test_the_surface_bytes_sit_inside_the_bytes_walked(self):
        for state in self.three.states:
            self.assertLess(state.surface_bytes, state.bytes_walked)

    def test_no_share_is_computed_and_nothing_is_ranked(self):
        # Spec 0002 s11 refuses a metric built for a hypothesis before the
        # hypothesis was measured. The two figures are printed; dividing them
        # is a reading somebody takes, not a number this tool stands behind.
        text = compare.render(self.three).lower()
        for word in ("%", "ratio", "threshold", "per cent", "percent"):
            self.assertNotIn(word, text, word)


class TestHowAStateIsNamed(unittest.TestCase):
    """Seam A for the argument shape: `ref`, or `path@ref`."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-spec-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_a_bare_ref_is_read_in_the_default_repository(self):
        spec = compare.parse_state("a7d7649", self.tmp)
        self.assertEqual((spec.repo, spec.ref, spec.label),
                         (self.tmp.resolve(), "a7d7649", "a7d7649"))

    def test_a_path_that_is_there_names_another_repository(self):
        other = self.tmp / "other"
        other.mkdir()
        spec = compare.parse_state(f"{other}@782a886", self.tmp)
        self.assertEqual((spec.repo, spec.ref), (other.resolve(), "782a886"))
        self.assertEqual(spec.label, "other@782a886")

    def test_a_ref_carrying_an_at_sign_keeps_its_own_text(self):
        # `main@{yesterday}` is a ref. Splitting on the character alone would
        # take it apart and then report the repository it invented as one that
        # could not be read.
        spec = compare.parse_state("main@{yesterday}", self.tmp)
        self.assertEqual(spec.ref, "main@{yesterday}")
        self.assertEqual(spec.repo, self.tmp.resolve())


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
        # The row the comparison turns on, anchored to its own line: "surfaces"
        # alone appears in several headings, so a bare substring would pass on a
        # table that never printed the row.
        self.assertRegex(result.stdout, r"(?m)^\s*surfaces\s+\S")
        self.assertIn(".md", result.stdout)

    def test_the_exit_code_says_when_the_states_are_not_comparable(self):
        # The command line's own wiring, with the reading faked: two states read
        # by different detector sets cannot arise from one run of this build,
        # and the exit code that reports them still has to be the one the
        # command returns.
        printed = io.StringIO()
        with mock.patch.object(
            compare, "compare_text", return_value=("a table\n", False)
        ), contextlib.redirect_stdout(printed):
            code = main(["compare", STATES[0], STATES[1],
                         "--repo", str(self.repo), "--db", str(self.db)])
        # The table still prints. Every figure in it was measured; what is not
        # established is that subtracting them means anything.
        self.assertEqual(printed.getvalue(), "a table\n")
        self.assertEqual(code, compare.EXIT_NOT_COMPARABLE)

    def test_the_exit_code_says_when_a_state_could_not_be_read(self):
        result = self.run_compare(STATES[0], "no-such-commit")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("no-such-commit", result.stderr)

    def test_three_states_run_from_the_command_line(self):
        # Seam B for ticket 14's shape: two states of this repository and one
        # of another, named the way a person types it.
        sibling = build(self.tmp / "sibling")
        result = self.run_compare(
            STATES[0], STATES[1], f"{sibling}@{STATES[2]}"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"sibling@{STATES[2]}", result.stdout)
        self.assertIn(str(sibling), result.stdout)
        self.assertRegex(result.stdout, r"(?m)^\s*surfaces\s+\d+\s+\d+\s+\d+\s")

    def test_one_state_is_not_a_comparison(self):
        result = self.run_compare(STATES[0])
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("two states", result.stderr)

    def test_a_state_of_a_repository_that_is_not_there_names_it(self):
        # A path that is not there is not a repository, so the whole text stays
        # a ref -- and the message names what was typed rather than a
        # repository or a ref the reader never wrote.
        result = self.run_compare(STATES[0], "/no/such/repository@c0")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("/no/such/repository@c0", result.stderr)


if __name__ == "__main__":
    unittest.main()
