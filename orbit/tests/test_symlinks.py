"""A symlink is a node: listed, never read, sized by the link itself.

Ticket 15. Not a gap in what this tool can see -- a divergence from GitLab
Orbit, whose walk accepts symlinks (`crates/utils/src/walk.rs:37-41`), routes
them away from the reader (`:53-57`), records them under
`FilterSkip::NonRegularFile` (`crates/code-graph/src/v2/config/filter.rs:51`)
and sizes them by `symlink_metadata()` (`walk.rs:47`). Ours refused them
outright, which was invisible in every count taken before this.

Counts are against ``build_symlinks``, never against a live repository: a test
that reads real repository content fails whenever that content changes,
including from this work. The acceptance run is evidence, recorded in the
ticket.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from . import support

from build_symlinks import BOOKS, LINKS, PRUNED_LINK, build
from orbit_context import provenance, repomap, surfaces
from orbit_context.indexer import index

# Every link the fixture writes, as a repository-relative path.
LINKED_PATHS = frozenset(LINKS) - {PRUNED_LINK}

# The four the estate exposes under a working name, which is the shape this
# ticket was found on: `_rule-workbench/<book>/full.md`, fourteen times on the
# real repository and four times here.
FULL_LINKS = frozenset(f"_rule-workbench/{book}/full.md" for book in BOOKS)


def _query(db_path: Path, sql: str) -> list[tuple]:
    import duckdb

    connection = duckdb.connect(str(db_path), read_only=True)
    try:
        return connection.execute(sql).fetchall()
    finally:
        connection.close()


def _in(paths) -> str:
    """A SQL ``IN`` list, written out rather than rendered from a tuple.

    `tuple(...)` of one element renders `('x',)`, which is not SQL. These sets
    are the fixture's, so today they hold nine and four; a fixture edit that
    took one of them to a single path would otherwise fail as a syntax error
    somewhere else entirely.
    """
    return "(" + ", ".join(f"'{path}'" for path in sorted(paths)) + ")"


# Seam A, run once for the whole module: build the estate, index it, and let
# every class below ask its own question of that one run. Per-class would be
# three runs that then have to be argued to be the same one.
_RUN: dict = {}


def setUpModule():
    tmp = Path(tempfile.mkdtemp(prefix="orbit-context-symlinks-"))
    estate = build(tmp / "estate")
    root = estate / "workbench"
    db = tmp / "graph.duckdb"
    stats = index(estate, db_path=db)
    _RUN.update(
        tmp=tmp,
        root=root,
        db=db,
        stats=stats,
        repo=stats["repositories"][0],
        walked={walked.relative_path for walked in surfaces.walk_files(root)},
    )


def tearDownModule():
    shutil.rmtree(_RUN["tmp"], ignore_errors=True)


class IndexedEstate(unittest.TestCase):
    """The one index run, named the way a class attribute would be."""

    @property
    def root(self) -> Path:
        return _RUN["root"]

    @property
    def db(self) -> Path:
        return _RUN["db"]

    @property
    def repo(self) -> dict:
        return _RUN["repo"]

    @property
    def walked(self) -> set:
        return _RUN["walked"]


class TestASymlinkIsANode(IndexedEstate):
    def test_a_symlink_is_walked(self):
        """25 files and 10 links. The links are the whole of the difference."""
        self.assertEqual(self.repo["coverage"]["files_walked"], 35)
        self.assertLessEqual(LINKED_PATHS, self.walked)

    def test_a_link_wearing_a_pruned_name_is_refused_by_the_name(self):
        """Before this ticket every link was refused, so a link named
        `node_modules` was too. Listing it now would carry another estate's
        surfaces in through a name this walk has always refused.
        """
        self.assertIn(PRUNED_LINK, LINKS)
        self.assertNotIn(PRUNED_LINK, self.walked)
        self.assertEqual(
            [path for path in self.walked if path.startswith(f"{PRUNED_LINK}/")], []
        )

    def test_a_link_to_a_directory_is_listed_once_and_never_descended(self):
        """Descending would walk one tree twice and count one file as two."""
        self.assertIn("mirror", self.walked)
        self.assertEqual(
            [path for path in self.walked if path.startswith("mirror/")], []
        )

    def test_a_link_to_nothing_is_listed_and_is_not_an_error(self):
        """Listing a link needs nothing from its target, so there is nothing
        for a target that is not there to break."""
        self.assertIn("docs/missing.md", self.walked)
        self.assertEqual(self.repo["processing"]["errored_files"], 0)

    def test_a_vendor_named_link_that_names_a_rung_is_still_a_row(self):
        """The row is the point: it is a node, listed with its reason. What it
        is not is one end of a relation read out of two files."""
        self.assertEqual(
            _query(
                self.db,
                "SELECT surface_kind, reason FROM gl_context_surface "
                "WHERE path = '.claude/agents/reviewer.mini.md'",
            ),
            [(surfaces.AGENT_DEFINITION, surfaces.REASON_NON_REGULAR_FILE)],
        )

    def test_a_vendor_named_link_is_a_row_carrying_the_reason_it_was_not_read(self):
        """A name is readable without opening the file, so a link that carries
        one is a candidate -- and is then recorded the way every other unread
        candidate is, with the reason on the row."""
        rows = _query(
            self.db,
            "SELECT reason, size_bytes, content_sha256 FROM gl_context_surface "
            "WHERE path = 'CLAUDE.md'",
        )
        self.assertEqual(len(rows), 1)
        reason, size_bytes, digest = rows[0]
        self.assertEqual(reason, surfaces.REASON_NON_REGULAR_FILE)
        self.assertEqual(digest, "")
        self.assertEqual(size_bytes, len("AGENTS.md"))
        self.assertNotEqual(size_bytes, (self.root / "AGENTS.md").stat().st_size)

    def test_the_reason_reaches_the_coverage_table_like_any_other(self):
        self.assertEqual(
            _query(
                self.db,
                "SELECT reason, errored FROM gl_context_coverage "
                "WHERE path = 'CLAUDE.md'",
            ),
            [(surfaces.REASON_NON_REGULAR_FILE, False)],
        )

    def test_a_link_is_cut_into_no_clauses(self):
        self.assertEqual(
            _query(
                self.db,
                "SELECT count(*) FROM gl_context_clause "
                f"WHERE surface_path IN {_in(LINKED_PATHS)}",
            ),
            [(0,)],
        )

    def test_no_link_is_hashed(self):
        """Hashing through a link files one file's bytes under two names."""
        self.assertEqual(
            _query(
                self.db,
                "SELECT count(*) FROM gl_context_surface "
                "WHERE COALESCE(content_sha256, '') <> '' "
                f"AND path IN {_in(LINKED_PATHS)}",
            ),
            [(0,)],
        )

    def test_a_link_is_in_no_byte_identical_pair(self):
        """Three pairs, each two files on disk holding the same bytes.

        `clean-code/clean-code.mini.md` is a link to `clean-code/clean-code.md`,
        and the workbench copy beside it holds those same bytes. Followed, the
        link would be a third end of that pair and a fourth pair of its own.
        """
        pairs = _query(
            self.db,
            "SELECT source_path, target_path FROM gl_context_edge "
            "WHERE relationship_kind = 'IDENTICAL_BYTES' ORDER BY source_path",
        )
        self.assertEqual(self.repo["graph"]["identical_bytes"]["pairs"], 3)
        self.assertEqual(len(pairs), 3)
        named = {path for pair in pairs for path in pair}
        self.assertEqual(named & LINKED_PATHS, set())
        self.assertIn(
            ("_rule-workbench/clean-code/mini.md", "clean-code/clean-code.md"),
            pairs,
        )

    def test_a_link_carrying_a_rung_word_is_in_no_ladder(self):
        """One ladder: `refactoring`, at three rungs.

        Two links name a base rung in their own directory.
        `clean-code/clean-code.mini.md` is recognised by nothing, so it is not
        even a row. `.claude/agents/reviewer.mini.md` *is* a row -- a vendor
        name reaches it -- and is still not a rung: the rung words say two
        files hold one book at two sizes, and a link is one file wearing a
        second name. It is not counted as a rung with no base rung either.
        """
        self.assertEqual(self.repo["graph"]["ladders"]["found"], 1)
        self.assertEqual(self.repo["graph"]["ladders"]["rungs"], 3)
        rungs = _query(
            self.db,
            "SELECT source_path FROM gl_context_edge "
            "WHERE relationship_kind = 'RUNG_OF'",
        )
        self.assertEqual({path for (path,) in rungs} & LINKED_PATHS, set())

    def test_a_rung_whose_base_rung_is_a_link_is_counted_as_unattached(self):
        """The other half of the rule, and a different fact from the first.

        `.claude/commands/audit.mini.md` is a rung word the estate wrote, in a
        file this run read. Its base rung, `audit.md`, is a link -- a node
        nothing opened. The rung is real and this tool could not attach it,
        which is exactly what `rungs_with_no_base_rung` counts.
        """
        self.assertEqual(self.repo["graph"]["ladders"]["rungs_with_no_base_rung"], 1)

    def test_a_link_is_not_read_and_so_is_not_hashed_for_provenance(self):
        identical = self.repo["graph"]["identical_bytes"]
        self.assertEqual(identical["files_hashed"], 25)
        self.assertEqual(
            identical["files_not_read_by_reason"],
            {
                surfaces.REASON_NON_REGULAR_FILE: len(LINKED_PATHS),
                surfaces.REASON_OVERSIZE: 0,
                surfaces.REASON_READ_ERROR: 0,
            },
        )
        self.assertEqual(identical["files_not_read"], len(LINKED_PATHS))


class TestTheCorpusShareCountsOnlyFilesThatWereRead(IndexedEstate):
    """The trap, measured rather than argued.

    Listing unread nodes into a directory that is a corpus by the share rule
    takes the share down without anything having declared or undeclared itself.
    On the real estate that costs `_rule-workbench` its three corpus-adjacent
    surfaces and nothing in the output says a symlink rule caused it.

    A node the walk listed without loading cannot declare itself, so it must not
    count against the files that did: a file that was never opened is not
    evidence about the directory either way.
    """

    def _workbench_markdown(self, linked: bool) -> set[str]:
        prefix = "_rule-workbench/"
        return {
            walked.relative_path
            for walked in surfaces.walk_files(self.root)
            if walked.relative_path.startswith(prefix)
            and walked.relative_path.endswith(surfaces.CORPUS_SUFFIXES)
            and (linked or walked.relative_path not in LINKED_PATHS)
        }

    def test_the_fixture_really_does_spring_the_trap(self):
        """12 declared of 15 read is over the share; of 19 walked is under it.

        Asserted so that a fixture edit which stops the counts straddling the
        threshold fails here rather than quietly switching the test below off.
        """
        declared = 3 * len(BOOKS)
        read = len(self._workbench_markdown(linked=False))
        walked = len(self._workbench_markdown(linked=True))
        self.assertEqual((declared, read, walked), (12, 15, 19))
        self.assertGreaterEqual(declared, read * surfaces.CORPUS_DECLARED_SHARE)
        self.assertLess(declared, walked * surfaces.CORPUS_DECLARED_SHARE)

    def test_the_three_files_the_share_alone_recognises_are_still_surfaces(self):
        found = _query(
            self.db,
            "SELECT path FROM gl_context_surface "
            f"WHERE recognition = '{surfaces.RECOGNITION_CORPUS_ADJACENT}' "
            "AND COALESCE(reason, '') = '' ORDER BY path",
        )
        self.assertEqual([path for (path,) in found], [
            "_rule-workbench/CHECK_COMPATIBILITY.md",
            "_rule-workbench/PROCESS.md",
            "_rule-workbench/RELEASE.md",
        ])
        self.assertEqual(
            self.repo["graph"]["recognition"][surfaces.RECOGNITION_CORPUS_ADJACENT], 3
        )

    def test_a_link_inside_a_corpus_is_a_row_that_says_it_was_not_read(self):
        """A directory is readable without opening the files in it, so the
        corpus rule reaches a link like anything else and the link becomes a
        node -- which is what GitLab lists a symlink as. What it does not become
        is evidence: it is not in the share that made the corpus, and it carries
        the reason nothing read it.
        """
        rows = _query(
            self.db,
            "SELECT recognition, reason FROM gl_context_surface "
            f"WHERE path IN {_in(FULL_LINKS)}",
        )
        self.assertEqual(len(rows), len(FULL_LINKS))
        self.assertEqual(
            set(rows),
            {(surfaces.RECOGNITION_CORPUS_ADJACENT,
              surfaces.REASON_NON_REGULAR_FILE)},
        )

    def test_the_inference_count_is_of_files_that_were_read(self):
        """`repo-map`'s split separates what the estate stated from what this
        tool read off a directory. A file nobody opened is evidence of neither,
        so the four links here do not join the three.
        """
        found = repomap.read(self.root, db_path=self.db, environ={})
        self.assertEqual(
            found.recognition_by_kind[surfaces.RECOGNITION_CORPUS_ADJACENT], 3
        )
        self.assertEqual(found.inferred_recognitions, 3)
        self.assertEqual(
            sum(found.recognition_by_kind.values()), found.surfaces_read_in_full
        )
        # Seven of the ten links are rows: the four in the corpus, and the three
        # a vendor name reaches. The other three are links nothing recognised --
        # `clean-code/clean-code.mini.md` and `docs/missing.md` sit in
        # directories with too few read Markdown files to be a corpus, and
        # `mirror` is not Markdown at all. A link is a node when something
        # recognises the path, on the same three rules as any other file.
        rows = _query(
            self.db,
            "SELECT path FROM gl_context_surface "
            f"WHERE path IN {_in(LINKED_PATHS)}",
        )
        self.assertEqual(len(rows), 7)
        self.assertEqual(found.surfaces_not_read_in_full, 7)


class TestOneWalkAndOneResolverAgree(IndexedEstate):
    """The defect ticket 15 closes as a side effect.

    `traceability.md` writes a pointer to `full.md`, the resolver resolves it,
    and the walk made no row for it: edges pointing at files our own walk had
    decided were not there. Two answers to "what is in this repository", which
    is the fault `surfaces.walk_files` exists to prevent.
    """

    def test_every_reference_that_resolved_landed_on_a_path_the_walk_found(self):
        resolved = _query(
            self.db,
            "SELECT DISTINCT target_path FROM gl_context_edge "
            "WHERE relationship_kind = 'REFERENCES' "
            "AND COALESCE(target_path, '') <> ''",
        )
        self.assertEqual(
            sorted(path for (path,) in resolved if path not in self.walked), []
        )

    def test_the_pointers_at_the_links_are_still_edges(self):
        """The fix is that the walk found them, not that the edges went away."""
        landed = _query(
            self.db,
            "SELECT DISTINCT target_path FROM gl_context_edge "
            "WHERE relationship_kind = 'REFERENCES' "
            f"AND target_path IN {_in(FULL_LINKS)}",
        )
        self.assertEqual({path for (path,) in landed}, FULL_LINKS)


if __name__ == "__main__":
    unittest.main()
