"""The three contracts a clause address has to hold, before pointers use it.

Ticket 04 resolves pointers to clause addresses. At that moment an ambiguous
address stops being a local annoyance and becomes a wrong edge in the graph, and
a stale offset stops being a bad read and becomes a wrong edge that also looks
right. So these are pinned here rather than discovered there.
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from . import support  # noqa: F401

from orbit_context import retrieve
from orbit_context.indexer import index

COLLIDING = "# Rules\n\n## Estimating\n\n- M6 anchors\n- M7 other\n- M6 anchors\n"
AMBIGUOUS_FQN = "CLAUDE.md#Rules#Estimating#M6 anchors"


def _repo(root: Path, body: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    (root / "CLAUDE.md").write_text(body, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "fixture"], check=True)
    return root


class TestAddressing(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-address-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = _repo(self.tmp / "repo", COLLIDING)
        self.db = self.tmp / "context.duckdb"
        index(self.repo, db_path=self.db)

    def show(self, address, **kw):
        return retrieve.resolve(address, repo=self.repo, db_path=self.db, **kw)

    # -- contract 1: an fqn is a lookup key, an id is the address -------------

    def test_a_colliding_fqn_is_reported_not_resolved(self):
        """Two siblings with identical text under identical headings collide.

        That is a fact about the file. Resolution must refuse rather than pick.
        """
        with self.assertRaises(retrieve.AmbiguousAddress) as caught:
            self.show(AMBIGUOUS_FQN)
        self.assertEqual(len(caught.exception.candidates), 2)

    def test_the_ambiguity_names_its_candidates_by_id(self):
        with self.assertRaises(retrieve.AmbiguousAddress) as caught:
            self.show(AMBIGUOUS_FQN)
        for candidate in caught.exception.candidates:
            self.assertIn(f"id={candidate.clause_id}", candidate.locator)
        ids = {c.clause_id for c in caught.exception.candidates}
        self.assertEqual(len(ids), 2, "candidates must be separately addressable")

    def test_a_candidate_id_resolves_to_exactly_that_clause(self):
        with self.assertRaises(retrieve.AmbiguousAddress) as caught:
            self.show(AMBIGUOUS_FQN)
        second = caught.exception.candidates[1]
        resolved = self.show(str(second.clause_id))
        self.assertEqual(resolved.clause_id, second.clause_id)
        self.assertEqual(resolved.start_byte, second.start_byte)

    def test_a_unique_fqn_still_resolves(self):
        self.assertEqual(
            self.show("CLAUDE.md#Rules#Estimating#M7 other").read(), b"- M7 other\n")

    # -- contract 2: offsets are only valid against the indexed file ----------

    def test_reading_a_changed_file_raises_rather_than_slicing(self):
        clause = self.show("CLAUDE.md#Rules#Estimating#M7 other")
        (self.repo / "CLAUDE.md").write_text(
            "# Rules\n\nPADDING PADDING\n\n## Estimating\n\n- M7 other\n",
            encoding="utf-8")
        with self.assertRaises(retrieve.StaleIndex):
            clause.read()

    def test_the_stale_error_says_re_index(self):
        clause = self.show("CLAUDE.md#Rules#Estimating#M7 other")
        (self.repo / "CLAUDE.md").write_text("totally different\n", encoding="utf-8")
        with self.assertRaises(retrieve.StaleIndex) as caught:
            clause.read()
        self.assertIn("Re-index", str(caught.exception))

    def test_an_unchanged_file_still_reads(self):
        clause = self.show("CLAUDE.md#Rules#Estimating#M7 other")
        self.assertEqual(clause.read(), b"- M7 other\n")

    def test_a_same_size_edit_is_still_caught(self):
        """Size alone would miss this; the digest is why it is a digest."""
        clause = self.show("CLAUDE.md#Rules#Estimating#M7 other")
        original = (self.repo / "CLAUDE.md").read_text(encoding="utf-8")
        swapped = original.replace("- M7 other", "- M7 OTHER")
        self.assertEqual(len(swapped), len(original))
        (self.repo / "CLAUDE.md").write_text(swapped, encoding="utf-8")
        with self.assertRaises(retrieve.StaleIndex):
            clause.read()


class TestSpanNesting(unittest.TestCase):
    """Contract 3: a parent's span includes its descendants."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-span-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = _repo(
            self.tmp / "repo",
            "# Rules\n\nPreamble line\n\n## Estimating\n\n- M6 anchors\n")
        self.db = self.tmp / "context.duckdb"
        index(self.repo, db_path=self.db)

    def resolve(self, address):
        return retrieve.resolve(address, repo=self.repo, db_path=self.db)

    def test_a_parent_span_contains_its_children(self):
        parent = self.resolve("CLAUDE.md#Rules")
        child = self.resolve("CLAUDE.md#Rules#Estimating")
        self.assertLessEqual(parent.start_byte, child.start_byte)
        self.assertGreaterEqual(parent.end_byte, child.end_byte)

    def test_reading_a_parent_returns_the_whole_subtree(self):
        """Documented, not accidental: this is what GitLab's Definition does too,
        where a class's span covers its methods."""
        body = self.resolve("CLAUDE.md#Rules").read()
        self.assertIn(b"## Estimating", body)
        self.assertIn(b"- M6 anchors", body)

    def test_read_own_removes_descendant_spans(self):
        parent = self.resolve("CLAUDE.md#Rules")
        inner = retrieve.descendants(parent, repo=self.repo, db_path=self.db)
        own = parent.read_own(inner)
        self.assertIn(b"# Rules", own)
        self.assertIn(b"Preamble line", own)
        self.assertNotIn(b"## Estimating", own)
        self.assertNotIn(b"- M6 anchors", own)

    def test_read_own_is_still_the_files_own_bytes(self):
        parent = self.resolve("CLAUDE.md#Rules")
        inner = retrieve.descendants(parent, repo=self.repo, db_path=self.db)
        whole = (self.repo / "CLAUDE.md").read_bytes()
        for line in parent.read_own(inner).split(b"\n"):
            if line:
                self.assertIn(line, whole)

    def test_read_own_on_a_leaf_is_the_leaf(self):
        leaf = self.resolve("CLAUDE.md#Rules#Estimating#M6 anchors")
        inner = retrieve.descendants(leaf, repo=self.repo, db_path=self.db)
        self.assertEqual(leaf.read_own(inner), leaf.read())


if __name__ == "__main__":
    unittest.main()
