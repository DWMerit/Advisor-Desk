"""project_id and traversal_path must match orbit-local exactly.

Get either wrong and a join to gl_file returns zero rows silently rather than
erroring — it looks like "no surfaces found".
"""

import unittest

from . import support  # noqa: F401  (path setup)

from orbit_context.workspace import (
    LOCAL_TRAVERSAL_PATH,
    project_id_from_path,
    stable_id,
)


class TestProjectId(unittest.TestCase):
    # Read out of a graph.duckdb written by orbit 0.118.1. These pin the
    # reimplementation of Rust's DefaultHasher to orbit's actual output.
    VECTORS = {
        "/home/user/gitlabhq/orbit-knowledge-graph": 5082509622355918818,
        "/home/user/Advisor-Desk": 5723226579916806896,
    }

    def test_matches_orbit_local(self):
        for path, expected in self.VECTORS.items():
            with self.subTest(path=path):
                self.assertEqual(project_id_from_path(path), expected)

    def test_deterministic(self):
        self.assertEqual(
            project_id_from_path("/estate/repo"), project_id_from_path("/estate/repo")
        )

    def test_different_paths_differ(self):
        self.assertNotEqual(
            project_id_from_path("/estate/repo-a"), project_id_from_path("/estate/repo-b")
        )

    def test_always_positive(self):
        for path in ("/a", "/b", "/c" * 100, ""):
            self.assertGreaterEqual(project_id_from_path(path), 0)


class TestTraversalPath(unittest.TestCase):
    def test_local_graph_uses_the_empty_string(self):
        # orbit's local linker pushes "" for every row. Anything else here and
        # the join to gl_file returns nothing.
        self.assertEqual(LOCAL_TRAVERSAL_PATH, "")


class TestStableId(unittest.TestCase):
    def test_same_inputs_same_id(self):
        self.assertEqual(stable_id(1, "main", "abc", "CLAUDE.md"),
                         stable_id(1, "main", "abc", "CLAUDE.md"))

    def test_different_inputs_differ(self):
        self.assertNotEqual(stable_id(1, "main", "abc", "CLAUDE.md"),
                            stable_id(1, "main", "abc", "AGENTS.md"))


if __name__ == "__main__":
    unittest.main()
