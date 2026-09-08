"""Read GitLab-format ontology YAML and derive the DuckDB table shape from it.

The table is created from ``storage.columns`` in the YAML, never from a
hardcoded ``CREATE TABLE``. Adding a column to the YAML adds it to the table.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_ONTOLOGY_ROOT = Path(__file__).resolve().parent.parent / "ontology"

# GitLab's storage types are ClickHouse types. The local graph is DuckDB, and
# their own local DDL maps them the same way: Int64 -> BIGINT, String -> VARCHAR.
_CLICKHOUSE_TO_DUCKDB = {
    "Int64": "BIGINT",
    "Int32": "INTEGER",
    "UInt64": "BIGINT",
    "String": "VARCHAR",
    "Bool": "BOOLEAN",
    "DateTime": "TIMESTAMP",
    "DateTime64": "TIMESTAMP",
    "Float64": "DOUBLE",
}

_WRAPPERS = re.compile(r"^(LowCardinality|Nullable)\((.*)\)$")


class OntologyError(Exception):
    """A node YAML file is missing something the indexer needs."""


def duckdb_type(storage_type: str) -> str:
    """Map a ClickHouse storage type from the YAML onto a DuckDB type."""
    inner = storage_type.strip()
    while True:
        match = _WRAPPERS.match(inner)
        if not match:
            break
        inner = match.group(2).strip()
    try:
        return _CLICKHOUSE_TO_DUCKDB[inner]
    except KeyError:
        raise OntologyError(
            f"storage type {storage_type!r} has no DuckDB mapping; "
            f"add it to _CLICKHOUSE_TO_DUCKDB"
        ) from None


@dataclass(frozen=True)
class Column:
    name: str
    duckdb_type: str
    nullable: bool


@dataclass(frozen=True)
class NodeType:
    """One ontology node file, reduced to what the indexer needs."""

    node_type: str
    domain: str
    table: str
    columns: tuple[Column, ...]
    source_file: Path

    @property
    def column_names(self) -> tuple[str, ...]:
        return tuple(column.name for column in self.columns)

    def create_table_sql(self) -> str:
        body = ",\n".join(
            f"    {column.name} {column.duckdb_type}"
            + ("" if column.nullable else " NOT NULL")
            for column in self.columns
        )
        return f"CREATE TABLE IF NOT EXISTS {self.table} (\n{body}\n)"

    def add_column_sql(self, name: str) -> str:
        column = next(c for c in self.columns if c.name == name)
        # Added without NOT NULL: an existing table may already hold rows that
        # have no value for the new column.
        return f"ALTER TABLE {self.table} ADD COLUMN {column.name} {column.duckdb_type}"


def load_node(path: str | Path) -> NodeType:
    """Load one node YAML file in GitLab's format."""
    path = Path(path)
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise OntologyError(f"{path}: not a YAML mapping")

    for required in ("node_type", "domain", "destination_table", "properties", "storage"):
        if required not in document:
            raise OntologyError(f"{path}: missing {required!r}")

    properties = document["properties"]
    storage_columns = document["storage"].get("columns")
    if not storage_columns:
        raise OntologyError(f"{path}: storage.columns is empty")

    columns = []
    for entry in storage_columns:
        name = entry["name"]
        if name not in properties:
            raise OntologyError(
                f"{path}: storage column {name!r} has no matching entry under properties"
            )
        prop = properties[name]
        if "virtual" in prop:
            raise OntologyError(
                f"{path}: {name!r} is virtual and must not have a storage column"
            )
        columns.append(
            Column(
                name=name,
                duckdb_type=duckdb_type(entry["type"]),
                nullable=bool(prop.get("nullable", True)),
            )
        )

    return NodeType(
        node_type=document["node_type"],
        domain=document["domain"],
        table=document["destination_table"],
        columns=tuple(columns),
        source_file=path,
    )


def load_domain(root: str | Path = DEFAULT_ONTOLOGY_ROOT, domain: str = "context") -> dict[str, NodeType]:
    """Load every node YAML under ``root/nodes/<domain>/``, keyed by node_type."""
    directory = Path(root) / "nodes" / domain
    if not directory.is_dir():
        raise OntologyError(f"{directory}: no such ontology directory")
    nodes = {}
    for path in sorted(directory.glob("*.yaml")):
        node = load_node(path)
        nodes[node.node_type] = node
    if not nodes:
        raise OntologyError(f"{directory}: no node YAML files found")
    return nodes
