"""Which client pays for a surface, asserted on rows a caller can query.

Spec 0004's testing decision: assert what a caller can observe -- a row in the
graph after an index run -- and never how the value was derived, which function
produced it, or the shape of any intermediate. The derivation is free to change
so long as the rows do not.

Counts are against fixture estates, never against this repository's live
content. The estate-wide split is live content and is recorded as evidence
instead, which is spec 0002 §6's rule.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from . import support

from build_estate import build as build_phase_one
from build_lineage import build as build_lineage
from orbit_context import clients, detectors, surfaces
from orbit_context.indexer import index


def _query(db_path: Path, sql: str) -> list[tuple]:
    import duckdb

    connection = duckdb.connect(str(db_path), read_only=True)
    try:
        return connection.execute(sql).fetchall()
    finally:
        connection.close()


def _rows(db_path: Path, columns: str, where: str = "") -> list[tuple]:
    clause = f" WHERE {where}" if where else ""
    return _query(
        db_path, f"SELECT {columns} FROM gl_context_surface{clause} ORDER BY path"
    )


def _count(db_path: Path, where: str) -> int:
    return _query(
        db_path, f"SELECT count(*) FROM gl_context_surface WHERE {where}"
    )[0][0]


class TestTheDetectorSetDidNotMove(unittest.TestCase):
    """Spec 0004's constraint on the implementation, not a happy accident.

    The column is an ontology declaration plus a derivation outside the hashed
    set. If this figure moves, a detector was edited and the work has left the
    spec -- and every count in tickets 07 and 14 has stopped being comparable
    with every count taken after it.
    """

    def test_the_version_is_the_one_the_spec_was_written_against(self):
        self.assertEqual(detectors.VERSION, support.DETECTOR_SET_VERSION)

    def test_the_derivation_is_not_in_the_hashed_set(self):
        # Stated as an assertion rather than as a comment: adding `clients` to
        # the detector modules is exactly the edit that would move the version
        # above, and it would do it silently.
        self.assertNotIn(clients, detectors.DETECTOR_MODULES)


class TestEveryVendorNameResolvesToAClient(unittest.TestCase):
    """The guard that replaces the detector version for these tables.

    A name added to a detector's vendor table is a name this module has to know
    about. Without this, it would start producing UNKNOWN for a convention the
    estate does state, and nothing would say so -- the derivation sits outside
    the hashed set, so the version string cannot.
    """

    def test_every_vendor_basename_names_a_client(self):
        for basename in surfaces.SURFACE_BASENAMES:
            with self.subTest(basename=basename):
                client, reason = clients.attribute(basename)
                self.assertNotEqual(client, clients.CLIENT_UNKNOWN)
                self.assertNotEqual(reason, clients.REASON_NO_VENDOR_CONVENTION)

    def test_every_vendor_relative_path_names_a_client(self):
        for relative_path in surfaces.SURFACE_RELATIVE_PATHS:
            with self.subTest(path=relative_path):
                client, _ = clients.attribute(relative_path)
                self.assertNotEqual(client, clients.CLIENT_UNKNOWN)

    def test_every_vendor_directory_names_a_client(self):
        for prefix, suffix, _kind in surfaces.SURFACE_DIRECTORIES:
            with self.subTest(prefix=prefix):
                client, _ = clients.attribute(f"{prefix}whatever{suffix}")
                self.assertNotEqual(client, clients.CLIENT_UNKNOWN)

    def test_every_value_the_module_can_return_is_one_it_declares(self):
        for path in ("CLAUDE.md", "AGENTS.md", "GEMINI.md", ".cursorrules",
                     ".github/copilot-instructions.md", ".mcp.json",
                     ".cursor/mcp.json", ".vscode/mcp.json",
                     ".claude/settings.json", "docs/notes.md"):
            with self.subTest(path=path):
                client, reason = clients.attribute(path)
                self.assertIn(client, clients.CLIENT_KINDS)
                self.assertIn(reason, clients.CLIENT_REASONS)


class TestOneOfEachConvention(unittest.TestCase):
    """The phase-1 estate: every vendor convention, at least once."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-client-"))
        cls.estate = build_phase_one(cls.tmp / "estate")
        cls.db = cls.tmp / "graph.duckdb"
        cls.stats = index(cls.estate, db_path=cls.db)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _in(self, repository: str) -> str:
        """A WHERE clause scoping to one repository.

        Two of this estate's three repositories are on `main`, so a branch name
        is not a repository -- `project_id` is.
        """
        entry = next(item for item in self.stats["repositories"]
                     if item["repository"] == repository)
        return f"project_id = {entry['project_id']}"

    def _client_in(self, repository: str) -> dict[str, str]:
        return dict(_rows(self.db, "path, client", self._in(repository)))

    def test_a_surface_a_vendor_filename_names_carries_that_vendor(self):
        alpha = self._client_in("alpha")
        self.assertEqual(alpha["CLAUDE.md"], clients.CLIENT_CLAUDE)
        self.assertEqual(alpha["AGENTS.md"], clients.CLIENT_CODEX)
        self.assertEqual(alpha[".github/copilot-instructions.md"],
                         clients.CLIENT_COPILOT)
        beta = self._client_in("beta")
        self.assertEqual(beta["GEMINI.md"], clients.CLIENT_GEMINI)
        self.assertEqual(beta["packages/ui/CLAUDE.md"], clients.CLIENT_CLAUDE)

    def test_a_surface_a_vendor_directory_names_carries_that_vendor(self):
        gamma = self._client_in("gamma")
        for path in (".claude/skills/anchor-schedule/SKILL.md",
                     ".claude/agents/takeoff-reviewer.md",
                     ".claude/commands/price-check.md",
                     ".claude/settings.json"):
            with self.subTest(path=path):
                self.assertEqual(gamma[path], clients.CLIENT_CLAUDE)

    def test_a_hook_script_inside_a_vendor_directory_is_that_vendor_s_cost(self):
        # The row is a hook target: a file a settings file names, additive to
        # whatever else it is. Nothing in `check-anchors.sh` says which client
        # reads it; the directory the estate put it in does.
        gamma = self._client_in("gamma")
        self.assertEqual(gamma[".claude/hooks/check-anchors.sh"],
                         clients.CLIENT_CLAUDE)

    def test_a_name_is_read_without_the_file_being_opened(self):
        # `config/.cursorrules` holds bytes that are not valid UTF-8, so it is a
        # row carrying a reason rather than an indexed surface. Its name still
        # says who pays for it, and a derivation that needed the contents would
        # have lost that.
        row = _rows(self.db, "client, client_reason, reason",
                    "path = 'config/.cursorrules'")
        self.assertEqual(len(row), 1)
        client, client_reason, reason = row[0]
        self.assertEqual(client, clients.CLIENT_CURSOR)
        self.assertEqual(client_reason, clients.REASON_VENDOR_BASENAME)
        self.assertEqual(reason, surfaces.REASON_INVALID_UTF8)

    def test_two_byte_identical_files_under_two_vendors_carry_two_values(self):
        # The case the whole column exists for. `alpha/CLAUDE.md` and
        # `alpha/AGENTS.md` are the same bytes -- the graph already reports the
        # pair -- and whether that is one file's worth of burden or two depends
        # on a fact only this column carries.
        found = dict(_rows(
            self.db, "path, content_sha256",
            f"{self._in('alpha')} AND path IN ('CLAUDE.md', 'AGENTS.md')",
        ))
        self.assertEqual(len(found), 2)
        self.assertEqual(found["CLAUDE.md"], found["AGENTS.md"])

        attributed = self._client_in("alpha")
        self.assertNotEqual(attributed["CLAUDE.md"], attributed["AGENTS.md"])
        self.assertEqual(
            {attributed["CLAUDE.md"], attributed["AGENTS.md"]},
            {clients.CLIENT_CLAUDE, clients.CLIENT_CODEX},
        )

    def test_the_reason_says_which_convention_matched(self):
        reasons = dict(_rows(self.db, "path, client_reason", self._in("alpha")))
        gamma_reasons = dict(
            _rows(self.db, "path, client_reason", self._in("gamma"))
        )
        self.assertEqual(reasons["CLAUDE.md"], clients.REASON_VENDOR_BASENAME)
        self.assertEqual(reasons[".github/copilot-instructions.md"],
                         clients.REASON_VENDOR_RELATIVE_PATH)
        self.assertEqual(gamma_reasons[".claude/settings.json"],
                         clients.REASON_VENDOR_DIRECTORY)

    def test_the_split_sums_to_the_surface_count(self):
        self.assertEqual(
            sum(self.stats["graph"]["client"].values()),
            self.stats["graph"]["surfaces"],
        )
        for entry in self.stats["repositories"]:
            with self.subTest(repository=entry["repository"]):
                self.assertEqual(
                    sum(entry["graph"]["client"].values()),
                    entry["graph"]["surfaces"],
                )

    def test_no_row_carries_an_empty_client(self):
        self.assertEqual(_count(self.db, "client IS NULL OR client = ''"), 0)


class TestWhatNothingNames(unittest.TestCase):
    """The lineage estate, whose ladder repository carries no vendor name."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-client-unknown-"))
        cls.estate = build_lineage(cls.tmp / "estate")
        cls.db = cls.tmp / "graph.duckdb"
        cls.stats = index(cls.estate, db_path=cls.db)
        cls.by_repo = {entry["repository"]: entry
                       for entry in cls.stats["repositories"]}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_a_surface_nothing_names_carries_unknown_with_its_reason(self):
        rows = _rows(self.db, "path, client, client_reason", "branch = 'main'")
        self.assertTrue(rows)
        for path, client, reason in rows:
            with self.subTest(path=path):
                self.assertEqual(client, clients.CLIENT_UNKNOWN)
                self.assertEqual(reason, clients.REASON_NO_VENDOR_CONVENTION)

    def test_nothing_the_estate_did_not_vendor_name_is_attributed(self):
        # The anti-inference guard. `declared-marker` and `corpus-adjacent` are
        # the two recognitions that are not a vendor's name, and a client read
        # off either of them would be this tool's reading rather than the
        # estate's statement.
        self.assertEqual(
            _count(
                self.db,
                f"client <> '{clients.CLIENT_UNKNOWN}' AND recognition <> "
                f"'{surfaces.RECOGNITION_VENDOR_NAME}'",
            ),
            0,
        )

    def test_a_skill_package_outside_a_vendor_directory_still_carries_its_vendor(self):
        # `skills/anchors/SKILL.md` sits in a directory nobody defined, under a
        # filename Anthropic did. The name is the statement, so it carries.
        found = dict(_rows(self.db, "path, client",
                           "branch = 'trunk' AND path LIKE 'skills/%'"))
        self.assertEqual(set(found.values()), {clients.CLIENT_CLAUDE})
        self.assertEqual(len(found), 3)

    def test_a_count_grouped_by_the_column_prints_its_unknown_bucket(self):
        grouped = dict(_query(
            self.db, "SELECT client, count(*) FROM current_surface GROUP BY 1"
        ))
        # Present, and the largest bucket in the estate -- which is the figure
        # the column exists to stop anybody reading as a zero.
        self.assertIn(clients.CLIENT_UNKNOWN, grouped)
        self.assertEqual(grouped[clients.CLIENT_UNKNOWN],
                         max(grouped.values()))

    def test_the_tally_carries_unknown_even_where_it_is_zero(self):
        for entry in self.stats["repositories"]:
            with self.subTest(repository=entry["repository"]):
                self.assertIn(clients.CLIENT_UNKNOWN, entry["graph"]["client"])

    def test_the_repository_with_no_vendor_name_is_entirely_unknown(self):
        tally = self.by_repo["ladder"]["graph"]["client"]
        self.assertEqual(tally[clients.CLIENT_UNKNOWN],
                         self.by_repo["ladder"]["graph"]["surfaces"])
        self.assertEqual(
            sum(count for value, count in tally.items()
                if value != clients.CLIENT_UNKNOWN),
            0,
        )

    def test_the_vendor_repository_splits_between_two_clients_and_unknown(self):
        # CLAUDE.md, .claude/agents/takeoff-reviewer.md and three SKILL.md
        # files are Anthropic's names; AGENTS.md is OpenAI's; the three files
        # under rules/ declared themselves with a heading and no vendor named
        # them.
        self.assertEqual(
            self.by_repo["vendor"]["graph"]["client"],
            {
                clients.CLIENT_CLAUDE: 5,
                clients.CLIENT_CODEX: 1,
                clients.CLIENT_GEMINI: 0,
                clients.CLIENT_CURSOR: 0,
                clients.CLIENT_COPILOT: 0,
                clients.CLIENT_UNKNOWN: 3,
            },
        )


if __name__ == "__main__":
    unittest.main()
