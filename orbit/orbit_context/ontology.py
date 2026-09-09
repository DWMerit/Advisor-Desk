"""Read GitLab-format ontology YAML and derive the DuckDB table shape from it.

Two kinds of file, in the tree shape GitLab uses: ``nodes/<domain>/*.yaml``
declares node types, ``edges/<domain>/*.yaml`` declares edge types with
``variants`` -- one edge type, many ``from_node``/``to_node`` pairs.

Every table is created from ``storage.columns`` in the YAML, never from a
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
class TableShape:
    """What every ontology file, node or edge, gives the indexer: a table."""

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


@dataclass(frozen=True)
class NodeType(TableShape):
    """One ontology node file, reduced to what the indexer needs."""

    node_type: str
    domain: str


@dataclass(frozen=True)
class EdgeVariant:
    """One from/to pair an edge type is declared for."""

    from_node: str
    to_node: str


@dataclass(frozen=True)
class EdgeType(TableShape):
    """One ontology edge file. Many variants, one destination table."""

    edge_type: str
    domain: str
    variants: tuple[EdgeVariant, ...]

    def allows(self, from_node: str, to_node: str) -> bool:
        return any(
            variant.from_node == from_node and variant.to_node == to_node
            for variant in self.variants
        )


def _columns(path: Path, document: dict) -> tuple[Column, ...]:
    """The storage columns of one ontology file, checked against its properties."""
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
    return tuple(columns)


def _document(path: Path, required: tuple[str, ...]) -> dict:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise OntologyError(f"{path}: not a YAML mapping")
    for key in required:
        if key not in document:
            raise OntologyError(f"{path}: missing {key!r}")
    return document


def load_node(path: str | Path) -> NodeType:
    """Load one node YAML file in GitLab's format."""
    path = Path(path)
    document = _document(
        path, ("node_type", "domain", "destination_table", "properties", "storage")
    )
    return NodeType(
        node_type=document["node_type"],
        domain=document["domain"],
        table=document["destination_table"],
        columns=_columns(path, document),
        source_file=path,
    )


def load_edge(path: str | Path) -> EdgeType:
    """Load one edge YAML file in GitLab's format.

    An edge type is declared once and carries ``variants`` -- the from/to pairs
    it is allowed between -- rather than being declared once per pair.
    """
    path = Path(path)
    document = _document(
        path,
        ("edge_type", "domain", "destination_table", "variants", "properties", "storage"),
    )
    variants = []
    for entry in document["variants"]:
        for key in ("from_node", "to_node"):
            if key not in entry:
                raise OntologyError(f"{path}: a variant is missing {key!r}")
        variants.append(EdgeVariant(entry["from_node"], entry["to_node"]))
    if not variants:
        raise OntologyError(f"{path}: variants is empty")

    return EdgeType(
        edge_type=document["edge_type"],
        domain=document["domain"],
        table=document["destination_table"],
        columns=_columns(path, document),
        source_file=path,
        variants=tuple(variants),
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


def load_edge_domain(root: str | Path = DEFAULT_ONTOLOGY_ROOT,
                     domain: str = "context") -> dict[str, EdgeType]:
    """Load every edge YAML under ``root/edges/<domain>/``, keyed by edge_type."""
    directory = Path(root) / "edges" / domain
    if not directory.is_dir():
        raise OntologyError(f"{directory}: no such ontology directory")
    edges = {}
    for path in sorted(directory.glob("*.yaml")):
        edge = load_edge(path)
        edges[edge.edge_type] = edge
    if not edges:
        raise OntologyError(f"{directory}: no edge YAML files found")
    return edges


@dataclass(frozen=True)
class Ontology:
    """One domain: its node types and its edge types."""

    nodes: dict[str, NodeType]
    edges: dict[str, EdgeType]

    @property
    def shapes(self) -> tuple[TableShape, ...]:
        """Every node and edge type, in load order."""
        return (*self.nodes.values(), *self.edges.values())

    def table_sources(self) -> dict[str, tuple[Path, ...]]:
        """The ontology files that declare each table, in load order."""
        sources: dict[str, list[Path]] = {}
        for shape in self.shapes:
            sources.setdefault(shape.table, []).append(shape.source_file)
        return {table: tuple(paths) for table, paths in sources.items()}

    @property
    def tables(self) -> tuple[TableShape, ...]:
        """Every shape that needs a table, one per table, columns merged.

        Edge types share a destination table -- their whole point -- and they do
        not all carry the same columns: CONTAINS holds only the endpoints, while
        REFERENCES also holds a detector, a locator and an address. The table has
        to be the union, or the columns of whichever file happened to load second
        are silently never created and every write of them fails.

        A column declared in two files must agree in both. Two files disagreeing
        about a column's type is a contradiction in the ontology, and the table
        can only be built from one of them, so it is raised rather than resolved.
        """
        merged: dict[str, dict[str, Column]] = {}
        for shape in self.shapes:
            columns = merged.setdefault(shape.table, {})
            for column in shape.columns:
                declared = columns.get(column.name)
                if declared is not None and declared != column:
                    raise OntologyError(
                        f"{shape.source_file}: {shape.table}.{column.name} is "
                        f"declared as {column.duckdb_type}"
                        f"{'' if column.nullable else ' NOT NULL'} here and as "
                        f"{declared.duckdb_type}"
                        f"{'' if declared.nullable else ' NOT NULL'} in another "
                        f"ontology file for the same table"
                    )
                columns[column.name] = column
        first: dict[str, TableShape] = {}
        for shape in self.shapes:
            first.setdefault(shape.table, shape)
        return tuple(
            TableShape(
                table=table,
                columns=tuple(merged[table].values()),
                source_file=first[table].source_file,
            )
            for table in merged
        )


def load(root: str | Path | None = None, domain: str = "context") -> Ontology:
    """Load a whole domain -- nodes and edges."""
    root = Path(root) if root else DEFAULT_ONTOLOGY_ROOT
    return Ontology(nodes=load_domain(root, domain), edges=load_edge_domain(root, domain))
