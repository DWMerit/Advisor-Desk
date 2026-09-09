"""Write ``gl_context_*`` tables into our own DuckDB, beside Orbit's.

Never opens Orbit's file for writing. DuckDB takes an exclusive lock across
processes: while one process holds a file for writing, no other process can
open it at all, not even read-only. Writing into ``~/.orbit/graph.duckdb``
would lock out ``orbit sql``, ``orbit index`` and ``orbit mcp`` for the
duration of every index run, and an open MCP session would lock out ours.

So the context domain lives in its own file and Orbit's graph is ATTACHed
read-only when a cross-domain join is wanted. The table shape comes from the
ontology YAML, so adding a column there adds it here.
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb

from .ontology import NodeType

DEFAULT_DB_PATH = Path(os.path.expanduser("~/.orbit-context/context.duckdb"))

# Orbit's own graph. Only ever attached read-only, never opened for writing.
ORBIT_GRAPH_PATH = Path(os.path.expanduser("~/.orbit/graph.duckdb"))

# Orbit's own tables. Guarded so a mistake here fails loudly instead of
# corrupting the code graph.
ORBIT_OWNED_PREFIXES = ("gl_", "_orbit_")
CONTEXT_PREFIX = "gl_context_"


class StoreError(Exception):
    """A write was attempted somewhere it is not allowed."""


def assert_context_table(table: str) -> None:
    if not table.startswith(CONTEXT_PREFIX):
        raise StoreError(
            f"refusing to write {table!r}: this indexer only writes {CONTEXT_PREFIX}* tables"
        )


def connect(db_path: str | Path = DEFAULT_DB_PATH, read_only: bool = False):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path), read_only=read_only)


def attach_orbit(connection, graph_path: str | Path = ORBIT_GRAPH_PATH, alias: str = "orbit"):
    """Attach Orbit's graph read-only so its tables can be joined.

    Read-only is not a convenience here: attaching read-write would take the
    exclusive lock and shut every Orbit command out. The attach lasts for this
    connection only -- a fresh connection does not inherit it, so anything
    needing the join does it itself.
    """
    path = Path(graph_path)
    if not path.exists():
        raise StoreError(f"Orbit graph not found at {path}; run `orbit index` first")
    connection.execute(f"ATTACH '{path}' AS {alias} (READ_ONLY)")
    return alias


def existing_columns(connection, table: str) -> list[str]:
    rows = connection.execute(
        "SELECT column_name FROM duckdb_columns() WHERE table_name = ?", [table]
    ).fetchall()
    return [row[0] for row in rows]


def reconcile(connection, node: NodeType) -> dict[str, list[str]]:
    """Create the table from the YAML, or bring an existing one up to it.

    Returns the columns added, and any columns the table carries that the YAML
    does not declare.
    """
    assert_context_table(node.table)
    connection.execute(node.create_table_sql())

    present = existing_columns(connection, node.table)
    added = []
    for name in node.column_names:
        if name not in present:
            connection.execute(node.add_column_sql(name))
            added.append(name)
    undeclared = [name for name in present if name not in node.column_names]
    return {"added": added, "undeclared": undeclared}


def replace_rows(connection, node: NodeType, traversal_path: str, project_id: int,
                 branch: str, commit_sha: str, rows: list[dict]) -> int:
    """Replace the rows for one indexed snapshot.

    Re-indexing the same ``(traversal_path, branch, commit_sha)`` replaces its
    rows rather than adding a second copy. ``project_id`` is part of the key
    because every row in the local graph carries the same empty
    ``traversal_path``, so it is the only thing telling two repositories apart.
    """
    assert_context_table(node.table)
    connection.execute(
        f"DELETE FROM {node.table} "
        f"WHERE traversal_path = ? AND project_id = ? AND branch = ? AND commit_sha = ?",
        [traversal_path, project_id, branch, commit_sha],
    )
    if not rows:
        return 0
    columns = node.column_names
    placeholders = ", ".join("?" for _ in columns)
    statement = (
        f"INSERT INTO {node.table} ({', '.join(columns)}) VALUES ({placeholders})"
    )
    connection.executemany(statement, [[row[name] for name in columns] for row in rows])
    return len(rows)
