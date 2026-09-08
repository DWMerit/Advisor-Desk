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
from orbit_context import surfaces
from orbit_context.indexer import index
from orbit_context.ontology import load_domain

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
        kinds = set(surfaces.SURFACE_BASENAMES.values()) | set(
            surfaces.SURFACE_RELATIVE_PATHS.values()
        )
        for kind in kinds:
            self.assertEqual(offending_words(kind), [], kind)

    def test_column_names(self):
        for node in load_domain().values():
            for column in node.column_names:
                self.assertEqual(offending_words(column), [], column)

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
