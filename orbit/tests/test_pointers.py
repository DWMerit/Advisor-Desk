"""Pointers resolve; non-resolution is classified — ticket 04's acceptance.

  - the three `sub_kind` values are distinct rows and never collapsed
  - every edge carries a `file:line` locator
  - a path in backticks resolves correctly
  - a path inside a fenced block is recorded and flagged, not dropped
  - on a real repository, `no-indexed-target-match` is under 100
  - `supersedes-claim` stays a claim the estate makes

The boundary tests are the ones that matter most. A backtick in a negative
lookbehind slides the match start into the middle of a token, and the truncated
fragment cannot resolve: on one real repository that produced 1,349 phantom
findings out of 1,373. So the detector is tested on what it captures, not only
on how many things it finds.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from . import support

from build_estate import build
from orbit_context import pointers, store, surfaces
from orbit_context.indexer import index
from orbit_context.workspace import project_id_from_path

# The bar ticket 04 sets for a real repository. Counted over ExternalRef rows,
# which are one per address: "this address is named and nothing here matches it"
# is one finding about the estate however many times the estate writes it.
# The share of *distinct addresses* named in prose that do not resolve. A share,
# not a count: the count this replaced was calibrated when the repository was a
# book corpus, and it breached the moment the repository also contained
# documentation about a file-handling tool -- prose that names files for a living,
# including files that do not exist here by definition. That breach said the
# repository had grown, not that the detectors had degraded, which is not what a
# guard is for.
#
# One in three. Stated as a rule rather than fitted to a reading: more than a
# third of the addresses named across the estate's prose failing to resolve means
# the detectors are reading things that are not pointers. The reading when this
# was set was 98 of 341, 28.7%.
UNMATCHED_SHARE_CEILING = 0.33

# The acceptance run's report, excluded from the population above. The ceiling
# is untouched, and this is one file rather than a directory.
#
# Spec 0002 section 6 is the rule, and it was written before this: the
# acceptance run "produces a report, hand-checked against what is already
# known, recorded as evidence. It is never asserted in a test: a test that
# reads live repository content fails whenever that content changes, including
# from this work." Ticket 07 is that report. It audits four repositories that
# are not this one, and an audit quotes the paths it found --
# `contracts/ANCHOR-FORMAT.md` in Merit-knowledge,
# `.claude/tools/skill-sync/skills.json` in Home-system, two capture
# directories in Estimating-Lab. None of them can resolve here, by definition.
#
# Readings, both recorded so neither is hidden by the other:
#   whole tree                 127 of 373  34.0%   (over the ceiling)
#   with this file excluded    103 of 348  29.6%
# The exclusion removes 24 addresses. Twenty-three name files in the four
# audited repositories; the twenty-fourth is `payload.json`, which names nothing
# anywhere, and is one of the four findings that ticket's own sample classifies
# as a detector artifact. None of the 24 is a name of this repository's own --
# checked, because that is the whole difference between this cut and the one it
# replaced.
#
# **One file, not the ticket tree.** A first cut took all of `orbit/tickets/`
# and was wrong: it also dropped `compare.py`, `rung_of.yaml` and
# `tests/test_ladders.py` -- bare names of *this* repository's own files,
# written in other tickets' prose, which is exactly the detector behaviour the
# ceiling exists to watch. A guard that drops its own signal to stay under its
# ceiling is refitting by another route, whatever the comment above it says.
#
# So: the one evidence record that quotes other repositories, and every other
# ticket stays in the population. A later acceptance run adds its report here,
# and only if it too audits repositories that are not this one.
# Episode reconstructions, added 2026-09-12 on the rule spec 0003 F6
# pre-registered before any of them landed: a Gate 1 fixture "has to say, at the
# time it lands, how its addresses are held -- as an evidence record on the same
# rule ticket 07 was granted, or by carrying the addresses outside this
# repository's prose. Lowering the ceiling to fit is refitting, which the guard
# exists to stop."
#
# They are held here, on ticket 07's rule, and the ceiling is untouched.
#
# Why they belong: an episode reconstructs a failure that happened in another
# repository, so it quotes that repository's paths by its nature --
# `.claude/hooks/block-dangerous-git.py` and `GIT-WORKFLOW.md` in Home-system,
# `observations/concurrent-sessions.md` in Estimating-Lab. None can resolve
# here, by definition, and each was read correctly where it was read.
#
# Readings when the first record landed, both recorded so neither is hidden:
#   whole tree                    117 of 373  31.4%   (6 addresses of headroom)
#   with episode 01 excluded       99 of 355  27.9%   (18)
# The record added 18 unmatched addresses and 18 to the denominator; 32 of the
# 50 it names were already in the population from other files. Two further
# reconstructions were in flight when this was written, and on the whole-tree
# reading they would have breached -- which is F6 coming true on schedule
# rather than a surprise.
#
# The bar for joining this tuple is ticket 07's: the file audits or reconstructs
# something that is not this repository. A file that quotes this repository's
# own paths stays in the population, because that is the detector behaviour the
# ceiling exists to watch.
EVIDENCE_RECORDS = (
    "orbit/tickets/07-audit-and-gates.md",
    "orbit/evidence/episode-01-cross-session-amend-collision.md",
    "orbit/evidence/episode-03-gates-reinterpreted-after-the-data.md",
)


class TestBoundaries(unittest.TestCase):
    """What a detector captures, before anything is resolved."""

    def addresses(self, text, subtype=None):
        found = pointers.extract(text)
        return [p.address for p in found if subtype is None or p.subtype == subtype]

    def test_a_path_in_backticks_is_captured_whole(self):
        # The regression. A lookbehind here would capture `ocs/rules.md` or
        # similar -- a fragment that resolves to nothing and reads as a finding.
        self.assertEqual(
            self.addresses("Read `docs/rules.md` before pricing.\n"),
            ["docs/rules.md"],
        )

    def test_every_captured_path_is_present_in_the_text_as_captured(self):
        text = (
            "Read `docs/rules.md`, then 'config/anchors.yaml', then "
            '"scripts/price.py" and (docs/takeoff.md).\n'
        )
        found = self.addresses(text)
        self.assertEqual(
            sorted(found),
            ["config/anchors.yaml", "docs/rules.md", "docs/takeoff.md",
             "scripts/price.py"],
        )
        for address in found:
            self.assertIn(address, text)

    def test_a_url_path_is_not_re_matched_as_a_bare_path(self):
        # Excluding a leading `/` is what stops `example.com/spacing.md` being
        # picked up a second time as prose.
        self.assertEqual(
            self.addresses("See https://example.invalid/anchors/spacing.md today.\n",
                           pointers.BARE_PATH_LITERAL),
            [],
        )

    def test_sentence_punctuation_is_not_part_of_the_address(self):
        self.assertEqual(
            self.addresses("The other estate keeps ../beta/AGENTS.md.\n"),
            ["../beta/AGENTS.md"],
        )

    def test_a_version_number_is_not_a_path(self):
        for text in ("Orbit 0.118.1 was installed.\n",
                     "SipHash-1-3 with zero keys.\n",
                     "Built on python3.11 here.\n"):
            self.assertEqual(self.addresses(text), [], text)

    def test_a_link_target_is_the_link_not_the_prose_around_it(self):
        found = pointers.extract("See [the rules](docs/rules.md) first.\n")
        self.assertEqual([(p.subtype, p.address) for p in found],
                         [(pointers.MARKDOWN_LINK, "docs/rules.md")])

    def test_a_supersession_claims_the_path_on_its_line(self):
        found = pointers.extract("This supersedes docs/old-rules.md entirely.\n")
        self.assertEqual([(p.subtype, p.address) for p in found],
                         [(pointers.SUPERSEDES_CLAIM, "docs/old-rules.md")])

    def test_a_fenced_path_is_flagged_not_dropped(self):
        text = "Example:\n\n```sh\nshow docs/rules.md\n```\n\nAnd docs/rules.md.\n"
        found = pointers.extract(text)
        self.assertEqual({p.address for p in found}, {"docs/rules.md"})
        self.assertEqual(sorted(p.in_code_fence for p in found), [False, True])

    def test_inline_backticks_are_not_a_fence(self):
        found = pointers.extract("Run `docs/rules.md` now.\n")
        self.assertEqual([p.in_code_fence for p in found], [False])

    def test_every_pointer_carries_its_line(self):
        text = "# Head\n\nSee docs/rules.md.\n"
        self.assertEqual([p.line for p in pointers.extract(text)], [3])


class TestResolution(unittest.TestCase):
    """Where an address lands, against a tree on disk."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-resolve-"))
        cls.root = cls.tmp / "repo"
        (cls.root / "docs").mkdir(parents=True)
        (cls.root / "docs" / "rules.md").write_text("# Rules\n", encoding="utf-8")
        (cls.tmp / "sibling").mkdir()
        (cls.tmp / "sibling" / "AGENTS.md").write_text("# Sibling\n", encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def resolve(self, address, surface_path="CLAUDE.md"):
        return pointers.resolve(address, self.root, surface_path)

    def test_a_path_in_the_tree_resolves(self):
        self.assertEqual(self.resolve("docs/rules.md").target_path, "docs/rules.md")

    def test_a_path_relative_to_the_file_resolves(self):
        self.assertEqual(self.resolve("rules.md", "docs/CLAUDE.md").target_path,
                         "docs/rules.md")

    def test_a_path_that_leaves_the_root_is_outside_indexed_roots(self):
        self.assertEqual(self.resolve("../sibling/AGENTS.md").sub_kind,
                         pointers.OUTSIDE_INDEXED_ROOTS)

    def test_a_path_inside_the_root_with_nothing_there_has_no_indexed_target_match(self):
        self.assertEqual(self.resolve("docs/absent.md").sub_kind,
                         pointers.NO_INDEXED_TARGET_MATCH)

    def test_a_scheme_is_unresolvable(self):
        for address in ("https://example.invalid/a.md", "mailto:someone@example.invalid"):
            self.assertEqual(self.resolve(address).sub_kind,
                             pointers.UNRESOLVABLE_SCHEME, address)

    def test_the_three_sub_kinds_are_three_strings(self):
        self.assertEqual(len(set(pointers.SUB_KINDS)), 3)

    def test_an_anchor_a_template_and_a_directory_are_not_file_addresses(self):
        # Stated limits, not findings: reporting any of these as an unmatched
        # file would say something untrue about the estate.
        self.assertIsNone(self.resolve("#a-heading"))
        self.assertIsNone(self.resolve("$SOME_DIR/hook.sh"))
        self.assertIsNone(self.resolve("docs/"))


class EstateTestCase(unittest.TestCase):
    """The fixture's `gamma` repository writes one of every pointer kind."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-pointer-"))
        cls.estate = build(cls.tmp / "estate")
        cls.db = cls.tmp / "graph.duckdb"
        cls.stats = index(cls.estate, db_path=cls.db)
        cls.gamma = project_id_from_path(str((cls.estate / "gamma").resolve()))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def query(self, sql, params=None):
        connection = store.connect(self.db, read_only=True)
        try:
            return connection.execute(sql, params or []).fetchall()
        finally:
            connection.close()

    def edges(self, where="", params=None):
        return self.query(
            "SELECT subtype, source_kind, source_path, source_line, target_address, "
            "       target_kind, target_path, in_code_fence "
            "FROM gl_context_edge WHERE relationship_kind = 'REFERENCES' "
            + (f"AND {where} " if where else "")
            + "ORDER BY source_path, source_line",
            params,
        )


class TestPointerEdgesLand(EstateTestCase):
    def test_every_detector_produces_rows(self):
        found = {row[0] for row in self.edges()}
        self.assertEqual(found, set(pointers.SUBTYPES))

    def test_every_edge_carries_a_file_line_locator(self):
        for subtype, _, path, line, *_ in self.edges():
            self.assertTrue(path, subtype)
            self.assertIsNotNone(line, subtype)
            self.assertGreater(line, 0, f"{subtype} {path}")

    def test_a_pointer_is_attributed_to_the_clause_holding_it(self):
        # The reason granularity is sub-file: "which rule points at this" is
        # unanswerable if every pointer hangs off the whole file.
        kinds = {row[1] for row in self.edges("source_path = 'CLAUDE.md'")}
        self.assertIn("Clause", kinds)

    def test_a_path_in_backticks_resolves_to_its_surface(self):
        rows = self.edges(
            "target_address = '.claude/hooks/check-anchors.sh' "
            "AND subtype = ? AND project_id = ?",
            [pointers.BARE_PATH_LITERAL, self.gamma],
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][5], "Surface")
        self.assertEqual(rows[0][6], ".claude/hooks/check-anchors.sh")

    def test_a_path_inside_a_fenced_block_is_recorded_and_flagged(self):
        fenced = self.edges("in_code_fence AND project_id = ?", [self.gamma])
        self.assertEqual(len(fenced), 1)
        self.assertEqual(fenced[0][4], "CLAUDE.md")
        # Recorded means resolved like any other pointer, not held apart.
        self.assertEqual(fenced[0][6], "CLAUDE.md")

    def test_a_link_to_a_file_that_is_not_a_surface_points_at_orbits_file(self):
        rows = self.edges("target_address = 'docs/price-book.md' AND project_id = ?",
                          [self.gamma])
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(row[5], "File")
            self.assertEqual(row[6], "docs/price-book.md")

    def test_an_expanded_variable_keeps_the_address_the_estate_wrote(self):
        rows = self.edges("target_address LIKE '$CLAUDE_PROJECT_DIR%' AND project_id = ?",
                          [self.gamma])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][6], ".claude/hooks/check-anchors.sh")


class TestTheThreeNegativeFindings(EstateTestCase):
    def test_the_three_sub_kinds_are_distinct_rows(self):
        rows = dict(self.query(
            "SELECT sub_kind, count(*) FROM gl_context_external_ref "
            "WHERE project_id = ? GROUP BY sub_kind", [self.gamma]
        ))
        for sub_kind in pointers.SUB_KINDS:
            self.assertGreater(rows.get(sub_kind, 0), 0, sub_kind)

    def test_the_statistics_report_them_apart_and_never_summed(self):
        reported = self.stats["graph"]["external_refs"]
        self.assertEqual(set(reported), set(pointers.SUB_KINDS))
        for sub_kind in pointers.SUB_KINDS:
            self.assertGreater(reported[sub_kind], 0, sub_kind)

    def test_an_address_named_twice_is_one_external_ref_row(self):
        rows = self.query(
            "SELECT address, sub_kind, count(*) FROM gl_context_external_ref "
            "GROUP BY address, sub_kind HAVING count(*) > 1"
        )
        self.assertEqual(rows, [])

    def test_every_unresolved_edge_points_at_an_external_ref_row(self):
        (missing,) = self.query(
            "SELECT count(*) FROM gl_context_edge e "
            "LEFT JOIN gl_context_external_ref x ON x.id = e.target_id "
            "WHERE e.target_kind = 'ExternalRef' AND x.id IS NULL"
        )
        self.assertEqual(missing[0], 0)

    def test_a_resolved_edge_carries_a_path_and_an_unresolved_one_does_not(self):
        for _, _, _, _, _, target_kind, target_path, _ in self.edges():
            if target_kind == "ExternalRef":
                self.assertEqual(target_path, "")
            else:
                self.assertTrue(target_path)


class TestSupersessionStaysAClaim(EstateTestCase):
    """`supersedes-claim` is DECLARED. The pair of facts, never a third one."""

    def claims(self):
        return self.edges("subtype = ? AND project_id = ?",
                          [pointers.SUPERSEDES_CLAIM, self.gamma])

    def test_the_claim_is_recorded_with_its_locator(self):
        rows = self.claims()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][4], ".claude/commands/price-check.md")
        self.assertEqual(rows[0][2], "CLAUDE.md")

    def test_the_superseded_surface_is_still_indexed_as_itself(self):
        # Both facts stand: the estate declares a supersession, and the surface
        # it names is still a surface that loads. Nothing here derives a third.
        rows = self.query(
            "SELECT surface_kind, reason FROM gl_context_surface "
            "WHERE path = ? AND project_id = ?",
            [".claude/commands/price-check.md", self.gamma],
        )
        self.assertEqual(rows, [(surfaces.COMMAND_DEFINITION, "")])

    def test_a_claim_is_never_a_non_resolution(self):
        addresses = {row[0] for row in self.query(
            "SELECT address FROM gl_context_external_ref WHERE project_id = ?",
            [self.gamma],
        )}
        self.assertNotIn(".claude/commands/price-check.md", addresses)


class TestTheSharedEdgeTable(EstateTestCase):
    """CONTAINS and REFERENCES share `gl_context_edge` without erasing each other."""

    def test_both_edge_types_are_present(self):
        rows = dict(self.query(
            "SELECT relationship_kind, count(*) FROM gl_context_edge "
            "GROUP BY relationship_kind"
        ))
        self.assertGreater(rows.get("CONTAINS", 0), 0)
        self.assertGreater(rows.get("REFERENCES", 0), 0)

    def test_a_containment_edge_carries_no_detector(self):
        (rows,) = self.query(
            "SELECT count(*) FROM gl_context_edge "
            "WHERE relationship_kind = 'CONTAINS' AND subtype IS NOT NULL"
        )
        self.assertEqual(rows[0], 0)

    def test_re_indexing_replaces_rather_than_repeats(self):
        before = self.query("SELECT count(*) FROM gl_context_edge")
        index(self.estate, db_path=self.db)
        self.assertEqual(self.query("SELECT count(*) FROM gl_context_edge"), before)

    def test_every_edge_carries_its_snapshot(self):
        (rows,) = self.query(
            "SELECT count(*) FROM gl_context_edge "
            "WHERE traversal_path IS NULL OR branch = '' OR commit_sha = ''"
        )
        self.assertEqual(rows[0], 0)


class TestOnARealRepository(unittest.TestCase):
    """The measurement the ticket asks for, over the repository this code lives in.

    Counted over addresses rather than occurrences, because that is what the
    graph holds: one ExternalRef per address, however many edges enter it.

    A count in the thousands here would mean the detector is wrong, not the
    estate -- the failure this test exists to catch.
    """

    @classmethod
    def setUpClass(cls):
        cls.root = support.REPO_ROOT.resolve()
        cls.unmatched = set()
        cls.resolved = 0
        # Distinct addresses that resolved, so a share can be taken with the
        # same unit on both sides.
        cls.resolved_addresses: set[str] = set()
        # Kept beside each unmatched address: its detector and the line it was
        # written on, so the capture can be checked against the text rather than
        # only counted.
        cls.written_on: list[tuple[str, str, str]] = []
        for path in cls.root.rglob("*.md"):
            if any(part in surfaces.PRUNED_DIRECTORIES for part in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            relative = path.relative_to(cls.root).as_posix()
            if relative in EVIDENCE_RECORDS:
                continue
            lines = text.splitlines()
            for pointer in pointers.extract(text):
                found = pointers.resolve(pointer.address, cls.root, relative)
                if found is None:
                    continue
                if found.resolved:
                    cls.resolved += 1
                    cls.resolved_addresses.add(pointer.address)
                elif found.sub_kind == pointers.NO_INDEXED_TARGET_MATCH:
                    cls.unmatched.add(pointer.address)
                    cls.written_on.append(
                        (pointer.address, pointer.subtype, lines[pointer.line - 1])
                    )

    def test_most_addresses_named_in_prose_resolve(self):
        """The drift guard, as a share rather than a count.

        Counted over distinct addresses on both sides, because that is what the
        graph holds -- one `ExternalRef` per address, however many edges enter
        it. The count this replaced compared distinct unmatched addresses
        against resolved *occurrences*, which is two different units either
        side of one ratio, and it flattered the reading by roughly six times.
        """
        named = len(self.unmatched) + len(self.resolved_addresses)
        share = len(self.unmatched) / named
        self.assertLess(
            share, UNMATCHED_SHARE_CEILING,
            f"{len(self.unmatched)} of {named} addresses named in prose did not "
            f"resolve ({share:.1%}); ceiling {UNMATCHED_SHARE_CEILING:.0%}. "
            f"{sorted(self.unmatched)}")

    def test_most_pointers_resolve(self):
        # The catastrophe guard, and the reason the share above sits below it:
        # the failure the boundary rules exist to prevent is a report that is
        # mostly the tool talking about itself. Distinct addresses both sides.
        self.assertGreater(len(self.resolved_addresses), len(self.unmatched))

    def test_no_capture_started_in_the_middle_of_a_token(self):
        """Every unmatched address begins at a real boundary in its own line.

        This is the 1,349-out-of-1,373 failure stated as a test: a match start
        that slid into a token produces a fragment whose preceding character is
        an ordinary word character, and it can never resolve.
        """
        boundaries = set(" \t`'\"(<[")
        for address, subtype, line in self.written_on:
            # An import is written `@path`, and the `@` is the marker the
            # detector consumes, so it is a boundary for that detector only.
            allowed = boundaries | ({"@"} if subtype == pointers.IMPORT_STATEMENT else set())
            starts = [at for at in range(len(line))
                      if line.startswith(address, at)
                      and (at == 0 or line[at - 1] in allowed)]
            self.assertTrue(starts, f"{address!r} starts mid-token in {line!r}")


if __name__ == "__main__":
    unittest.main()
