"""The table comes from the YAML. Adding a column there must not touch Python.

Acceptance: "Adding a column to the YAML changes the table without touching
Python."
"""

import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from . import support

from orbit_context import store
from orbit_context.ontology import OntologyError, load_domain, load_node


class TestSurfaceYaml(unittest.TestCase):
    def setUp(self):
        self.node = load_node(support.SURFACE_YAML)

    def test_gitlab_node_format(self):
        document = yaml.safe_load(support.SURFACE_YAML.read_text(encoding="utf-8"))
        for key in ("node_type", "domain", "description", "label", "destination_table",
                    "default_columns", "sort_key", "properties", "storage"):
            self.assertIn(key, document, f"node YAML is missing {key!r}")
        self.assertIn("columns", document["storage"])

    def test_destination_table_is_a_context_table(self):
        self.assertTrue(self.node.table.startswith("gl_context_"))

    def test_phase_one_columns(self):
        self.assertEqual(
            self.node.column_names,
            ("id", "traversal_path", "project_id", "branch", "commit_sha",
             "path", "name", "surface_kind", "size_bytes", "frontmatter_bytes",
             "body_bytes", "start_line", "end_line", "matcher", "target_path",
             "target_resolution", "reason"),
        )

    def test_virtual_content_is_not_stored(self):
        document = yaml.safe_load(support.SURFACE_YAML.read_text(encoding="utf-8"))
        self.assertIn("virtual", document["properties"]["content"])
        self.assertNotIn("content", self.node.column_names)

    def test_no_prose_columns(self):
        for banned in ("summary", "purpose", "description_text", "notes"):
            self.assertNotIn(banned, self.node.column_names)

    def test_gated_columns_are_absent_in_phase_one(self):
        for gated in ("client", "activation", "revocable", "evidence_class", "detector"):
            self.assertNotIn(gated, self.node.column_names)


class TestAddingAColumn(unittest.TestCase):
    """Copy the ontology, add a column to the YAML, and index again."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-ontology-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.ontology = self.tmp / "ontology"
        shutil.copytree(support.ONTOLOGY_ROOT, self.ontology)
        self.yaml_path = self.ontology / "nodes" / "context" / "surface.yaml"

    def _add_column(self, name: str, storage_type: str = "String"):
        document = yaml.safe_load(self.yaml_path.read_text(encoding="utf-8"))
        document["properties"][name] = {
            "type": "string", "source": name, "nullable": True,
            "mutable": False, "description": "Added by a test.",
        }
        document["storage"]["columns"].append({"name": name, "type": storage_type})
        self.yaml_path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    def test_column_reaches_the_table(self):
        db = self.tmp / "graph.duckdb"
        node = load_domain(self.ontology)["Surface"]
        connection = store.connect(db)
        store.reconcile(connection, node)
        self.assertNotIn("client", store.existing_columns(connection, node.table))
        connection.close()

        self._add_column("client")

        node = load_domain(self.ontology)["Surface"]
        self.assertIn("client", node.column_names)
        connection = store.connect(db)
        outcome = store.reconcile(connection, node)
        self.assertEqual(outcome["columns_added"], ["client"])
        self.assertIn("client", store.existing_columns(connection, node.table))
        connection.close()

    def test_unmapped_storage_type_is_rejected(self):
        self._add_column("weird", storage_type="Decimal(38, 2)")
        with self.assertRaises(OntologyError):
            load_domain(self.ontology)


class TestOntologyErrors(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="orbit-context-bad-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _write(self, document) -> Path:
        path = self.tmp / "bad.yaml"
        path.write_text(yaml.safe_dump(document), encoding="utf-8")
        return path

    def test_missing_key(self):
        with self.assertRaises(OntologyError):
            load_node(self._write({"node_type": "X", "domain": "context"}))

    def test_storage_column_without_a_property(self):
        document = yaml.safe_load(support.SURFACE_YAML.read_text(encoding="utf-8"))
        document["storage"]["columns"].append({"name": "ghost", "type": "String"})
        with self.assertRaises(OntologyError):
            load_node(self._write(document))

    def test_virtual_property_may_not_be_stored(self):
        document = yaml.safe_load(support.SURFACE_YAML.read_text(encoding="utf-8"))
        document["storage"]["columns"].append({"name": "content", "type": "String"})
        with self.assertRaises(OntologyError):
            load_node(self._write(document))


if __name__ == "__main__":
    unittest.main()
