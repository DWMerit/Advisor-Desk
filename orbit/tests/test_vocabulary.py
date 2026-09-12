"""The constrained output vocabulary, over tool-authored fields only.

Paths, addresses and quotes are exempt: they carry the estate's own words.
What is linted here is what the tool itself writes — surface kinds, reasons,
column names, and the JSON statistics keys.
"""

import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from . import support  # noqa: F401

from build_estate import build
from orbit_context import (
    clauses, detectors, pointers, provenance, repomap, settings, surfaces,
)
from orbit_context.indexer import index
from orbit_context.ontology import load

BANNED = (
    "broken", "dangling", "orphaned", "obsolete", "stale", "dead", "unused",
    "duplicate", "redundant", "misplaced", "wrong", "should", "safe to delete",
)

_WORD = re.compile(r"[a-z]+")


def offending_words(text: str) -> list[str]:
    words = set(_WORD.findall(text.lower()))
    found = [banned for banned in BANNED if " " not in banned and banned in words]
    found += [banned for banned in BANNED if " " in banned and banned in text.lower()]
    return sorted(found)


class TestVocabulary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-vocab-"))
        cls.estate = build(cls.tmp / "estate")
        cls.stats = index(cls.estate, db_path=cls.tmp / "graph.duckdb", detailed=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_reasons(self):
        for name in dir(surfaces):
            if name.startswith("REASON_"):
                value = getattr(surfaces, name)
                self.assertEqual(offending_words(value), [], f"{name} = {value!r}")

    def test_surface_kinds(self):
        detected = (
            set(surfaces.SURFACE_BASENAMES.values())
            | set(surfaces.SURFACE_RELATIVE_PATHS.values())
            | {kind for _, _, kind in surfaces.SURFACE_DIRECTORIES}
        )
        for kind in set(surfaces.SURFACE_KINDS) | detected:
            self.assertEqual(offending_words(kind), [], kind)

    def test_recognition_kinds(self):
        # Written to a column and printed beside every count, so they are this
        # tool's words rather than the estate's.
        for kind in surfaces.RECOGNITION_KINDS:
            self.assertEqual(offending_words(kind), [], kind)

    def test_hook_command_resolutions(self):
        for name in dir(settings):
            if name.startswith("RESOLUTION_"):
                value = getattr(settings, name)
                self.assertEqual(offending_words(value), [], f"{name} = {value!r}")

    def test_clause_types(self):
        for clause_type in clauses.CLAUSE_TYPES:
            self.assertEqual(offending_words(clause_type), [], clause_type)

    def test_pointer_detector_names(self):
        for subtype in pointers.SUBTYPES:
            self.assertEqual(offending_words(subtype), [], subtype)

    def test_external_ref_sub_kinds(self):
        # The three negative findings. Each names what the detector set could
        # see, and none of them names a defect.
        for sub_kind in pointers.SUB_KINDS:
            self.assertEqual(offending_words(sub_kind), [], sub_kind)

    def test_evidence_rung_names(self):
        # The ladder PRODUCES stands on. Each names how well a claim is
        # evidenced, and none of them names a defect.
        for rung in provenance.EVIDENCE_LADDER:
            self.assertEqual(offending_words(rung), [], rung)

    def test_identical_bytes_is_the_measurement_not_a_judgement(self):
        # The word for byte-identity is the measurement that produced it. Two
        # files being the same bytes is an observation; what it means about
        # either of them is not in this graph, and spec 0001 §14 keeps it out.
        for name in (provenance.IDENTICAL_BYTES_EDGE, provenance.PRODUCES_EDGE):
            self.assertEqual(offending_words(name), [], name)

    def test_provenance_statistics_keys(self):
        # Built from an empty scan, so every key the block can carry is linted
        # whether or not this estate happens to produce it.
        for key, value in provenance.summary(provenance.Scan(), [], []).items():
            self.assertEqual(offending_words(key), [], key)
            if isinstance(value, dict):
                for name in value:
                    self.assertEqual(offending_words(name), [], name)

    def test_detector_set_version(self):
        # Tool-authored, printed beside every count, and derived rather than
        # chosen -- so it is linted as output and not assumed safe.
        self.assertEqual(offending_words(detectors.VERSION), [])

    def test_the_digest_guard_lists_every_word_hexadecimal_can_spell(self):
        # detectors.FORBIDDEN_IN_A_DIGEST claims to be the subset of this list
        # that hexadecimal can spell. Checked here rather than believed: a word
        # added to BANNED that hex can spell would otherwise slip through the
        # guard silently, and only show up as a version string that prints it.
        spellable = tuple(
            word for word in BANNED
            if set(word) <= set("0123456789abcdef")
        )
        self.assertEqual(sorted(detectors.FORBIDDEN_IN_A_DIGEST), sorted(spellable))

    def test_a_digest_that_spells_one_is_not_printed(self):
        # The window slides one character at a time and stops at the first that
        # spells nothing, so the answer is deterministic and still a function of
        # the digest alone.
        chosen = detectors.printable_slice("dead" + "1" * 60)
        self.assertEqual(offending_words(chosen), [])
        self.assertEqual(chosen, "ead111111111")

    def test_repo_map_output(self):
        """Spec 0001 §10: the vocabulary lint over every command's output.

        Linted whole. The estate's own words appear in it -- paths, addresses,
        the fqn of the deepest clause -- and those are exempt by the rule, but
        the fixture estate does not contain any, so linting the whole text
        checks the tool's own words without an exemption list to get wrong.
        """
        repositories = [
            path for path in sorted(self.estate.iterdir())
            if path.is_dir() and (path / ".git").exists()
        ]
        self.assertTrue(repositories)
        for repository in repositories:
            text = repomap.repo_map(
                repository, db_path=self.tmp / "graph.duckdb", environ={},
            )
            self.assertEqual(offending_words(text), [], repository.name)

    def test_column_names(self):
        # Nodes and edges alike: every column name is the tool's own word.
        for shape in load().tables:
            for column in shape.column_names:
                self.assertEqual(offending_words(column), [], column)

    def test_current_snapshot_view_names(self):
        # The names a reader types, and the columns the snapshot view adds. All
        # of them are this tool's own words rather than the estate's.
        for shape in load().tables:
            self.assertEqual(offending_words(shape.current_view), [],
                             shape.current_view)
        for column in ("runs_of_this_repository", "runs_in_store"):
            self.assertEqual(offending_words(column), [], column)

    def test_edge_and_variant_names(self):
        for edge in load().edges.values():
            self.assertEqual(offending_words(edge.edge_type), [], edge.edge_type)
            for variant in edge.variants:
                for node_type in (variant.from_node, variant.to_node):
                    self.assertEqual(offending_words(node_type), [], node_type)

    def test_statistics_keys_and_tool_authored_values(self):
        """Lint every key, and every value the tool authored.

        Values under `path`, `repository` and `detail` are exempt — they are the
        estate's own words, or a quoted system message.
        """
        exempt_keys = {"path", "repository", "database_path", "detail", "ontology",
                       "commit_sha", "branch"}

        def walk(node, key=None):
            if isinstance(node, dict):
                for child_key, child in node.items():
                    self.assertEqual(offending_words(child_key), [], child_key)
                    walk(child, child_key)
            elif isinstance(node, list):
                for child in node:
                    walk(child, key)
            elif isinstance(node, str) and key not in exempt_keys:
                self.assertEqual(offending_words(node), [], f"{key} = {node!r}")

        walk(self.stats)
        # The serialized form too, so nothing slips in via JSON encoding.
        json.dumps(self.stats)


if __name__ == "__main__":
    unittest.main()
