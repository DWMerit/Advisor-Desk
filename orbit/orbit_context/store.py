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

from .ontology import (
    SNAPSHOT_KEY,
    STORE_TABLE_PREFIX,
    TableShape,
    current_view_name,
)

DEFAULT_DB_PATH = Path(os.path.expanduser("~/.orbit-context/context.duckdb"))

# Orbit's own graph. Only ever attached read-only, never opened for writing.
ORBIT_GRAPH_PATH = Path(os.path.expanduser("~/.orbit/graph.duckdb"))

# Orbit's own tables. Guarded so a mistake here fails loudly instead of
# corrupting the code graph.
ORBIT_OWNED_PREFIXES = ("gl_", "_orbit_")
# The prefix on every table this indexer writes, spelled in the ontology because
# that is where the tables are declared.
CONTEXT_PREFIX = STORE_TABLE_PREFIX


class StoreError(Exception):
    """A write was attempted somewhere it is not allowed."""


class SchemaDrift(StoreError):
    """The store carries a column the ontology does not declare.

    Ticket 09 settles what a mismatch is: a failed run, with the remedy named,
    rather than a migration the run performs on its own. Removing a column
    cannot be undone, and a run that prints "surfaces: 214" while having
    removed one is a run whose numbers cannot be read afterwards -- the
    difference between the estate changing and the schema changing is exactly
    what a count is unable to show. So the run stops before writing a row, and
    names the command that resolves it.
    """


class MigrationRefused(StoreError):
    """A column the ontology does not declare is holding values.

    A column with values in it may be a leftover or it may be data, and this
    tool cannot tell which. Removing it is the one thing a migration must never
    do on its own, so it is named with the number of rows holding it and
    nothing is altered -- not the columns that would otherwise have gone, and
    not the declared columns the migration would have added, because a refusal
    that had already changed the schema is not the refusal it says it is.

    ``--remove-values`` is the way past it: the same removal, taken as a
    decision on the command line rather than as a default.
    """


def quoted(name: str) -> str:
    """One identifier, quoted for DuckDB.

    A column the ontology does not declare was named by something other than
    this tool, so its name is not known to be a bare word. An unquoted `order`
    is a parse error rather than a column, which would leave the store at a
    dead end: the run refusing, and the command it names failing.
    """
    escaped = name.replace('"', '""')
    return f'"{escaped}"'


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


def reconcile(connection, node: TableShape) -> dict[str, list[str]]:
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
    return {"columns_added": added, "columns_not_declared_in_ontology": undeclared}


def replace_rows(connection, node: TableShape, traversal_path: str, project_id: int,
                 branch: str, commit_sha: str, rows: list[dict]) -> dict[str, int]:
    """Replace the rows for one indexed snapshot. Returns what moved.

    Re-indexing the same ``(traversal_path, branch, commit_sha)`` replaces its
    rows rather than adding a second copy. ``project_id`` is part of the key
    because every row in the local graph carries the same empty
    ``traversal_path``, so it is the only thing telling two repositories apart.

    Every clause of that key is also what keeps one repository's re-index off
    another's rows: a store holds many repositories, and a DELETE that dropped
    any clause would take rows this run never looked at. The count of rows the
    DELETE took is returned so the run can say which rows it replaced rather
    than leaving a reader to infer it from a total that did not move.
    """
    assert_context_table(node.table)
    connection.execute(
        f"DELETE FROM {node.table} "
        f"WHERE traversal_path = ? AND project_id = ? AND branch = ? AND commit_sha = ?",
        [traversal_path, project_id, branch, commit_sha],
    )
    deleted = _changed_rows(connection)
    if not rows:
        return {"replaced": deleted, "written": 0}
    columns = node.column_names
    placeholders = ", ".join("?" for _ in columns)
    statement = (
        f"INSERT INTO {node.table} ({', '.join(columns)}) VALUES ({placeholders})"
    )
    connection.executemany(statement, [[row[name] for name in columns] for row in rows])
    return {"replaced": deleted, "written": len(rows)}


def _changed_rows(connection) -> int:
    """How many rows the DELETE just executed took.

    DuckDB returns it as the single value of the statement's result. Read from
    there rather than by counting the table either side, because those two
    counts answer a different question on a table other snapshots also hold
    rows in.
    """
    row = connection.fetchone()
    return int(row[0]) if row else 0


def undeclared_columns(connection, shapes) -> dict[str, list[str]]:
    """Per table, the columns present in the store that the ontology omits.

    Read from the store rather than from the ontology, because this is the one
    direction the ontology cannot answer: a column the YAML no longer declares
    leaves no trace in the YAML.
    """
    found: dict[str, list[str]] = {}
    for shape in shapes:
        present = existing_columns(connection, shape.table)
        extra = [name for name in present if name not in shape.column_names]
        if extra:
            found[shape.table] = extra
    return found


def assert_matches_ontology(connection, shapes, db_path) -> None:
    """Stop the run where the store's columns and the ontology's disagree.

    The remedy is named in the message rather than left to be worked out: the
    run that hits this is usually months after the column stopped being
    declared, and "which command removes it" is the whole question at that
    point.
    """
    drift = undeclared_columns(connection, shapes)
    if not drift:
        return
    detail = "; ".join(
        f"{table} carries {', '.join(columns)}" for table, columns in sorted(drift.items())
    )
    raise SchemaDrift(
        f"the store at {db_path} carries columns the ontology does not declare: "
        f"{detail}. No rows were written. To bring the store to the ontology, run "
        f"`orbit-context migrate --db {db_path}`, which removes such a column "
        f"where it holds no values and names it where it does."
    )


def _row_count(connection, table: str) -> int:
    return int(connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0])


def migrate(connection, shapes, remove_values: bool = False) -> dict:
    """Bring the store's tables to the ontology, and report what moved.

    Nothing is altered until every column has been examined. A column holding
    values stops the whole migration rather than its own table's part of it: a
    store left half at one schema and half at another is harder to read than the
    drift it was meant to resolve, and a refusal that had already added a column
    would not be the refusal it says it is.

    ``remove_values`` is the human decision, taken once and named on the command
    line: it removes such a column and what it holds. It is not a default,
    because whether those values are a leftover or data is not something this
    tool can tell.

    The row counts either side are in the report because removing a column is
    the cheapest place to move a number without noticing. These columns carry no
    count, so the two figures must match; a report where they do not is the
    signal that something else changed at the same time.
    """
    shapes = list(shapes)
    drift = undeclared_columns(connection, shapes)

    holding: dict[tuple[str, str], int] = {}
    for table, columns in sorted(drift.items()):
        for column in columns:
            rows = int(connection.execute(
                f"SELECT count(*) FROM {table} WHERE {quoted(column)} IS NOT NULL"
            ).fetchone()[0])
            if rows:
                holding[(table, column)] = rows
    if holding and not remove_values:
        named = "; ".join(
            f"{table}.{column} ({rows} rows hold a value)"
            for (table, column), rows in holding.items()
        )
        raise MigrationRefused(
            "nothing was altered. These columns are not declared by the "
            f"ontology and are holding values: {named}. What they hold is not "
            "this tool's to discard on its own: read them first, then run this "
            "again with --remove-values to remove the columns and what they "
            "hold."
        )

    report = []
    for shape in shapes:
        columns = drift.get(shape.table, [])
        # Declared columns are brought up to the ontology in the same pass, and
        # reported: a migration that quietly added one while listing only what
        # it removed would understate what it did.
        added = reconcile(connection, shape)["columns_added"]
        before = _row_count(connection, shape.table)
        for column in columns:
            connection.execute(
                f"ALTER TABLE {shape.table} DROP COLUMN {quoted(column)}"
            )
        report.append({
            "table": shape.table,
            "columns_added": added,
            "columns_removed": columns,
            "values_removed": {
                column: rows for (table, column), rows in holding.items()
                if table == shape.table
            },
            "rows_before": before,
            "rows_after": _row_count(connection, shape.table),
        })
    return {"tables": report}


# `SNAPSHOT_KEY` -- one repository at one commit on one branch -- is imported
# from the ontology, where it is declared beside the tables that carry it. It is
# what `replace_rows` replaces on and what a current-snapshot view joins by, and
# one spelling of it keeps those two from drifting apart.

RUN_TABLE = "gl_context_run"

# The view naming the snapshot each repository is currently at. Every other
# current view joins to it, and it is the one a reader asks which snapshot an
# answer came from. Named by the same rule as every other view rather than
# written out, so the run table and its view cannot come to disagree.
SNAPSHOT_VIEW = current_view_name(RUN_TABLE)


def assert_local_view(name: str) -> None:
    """Refuse a view name another graph could hold.

    The name is the mitigation, not a convenience. ``orbit local sql`` without
    ``--db`` reads GitLab Orbit's own store, finds a ``gl_context_surface``
    there, and answers ``3`` rather than failing -- and a plausible small number
    is the worst kind of wrong answer, because nothing about it looks wrong. A
    view named outside their prefixes cannot be found in their graph, so the
    same query fails there and says which table it could not find.
    """
    for prefix in ORBIT_OWNED_PREFIXES:
        if name.startswith(prefix):
            raise StoreError(
                f"refusing to declare a view named {name!r}: a name beginning "
                f"{prefix!r} is one Orbit's own graph could hold, and a query "
                f"against it run without --db would answer from that graph "
                f"instead of failing"
            )


def snapshot_view_sql() -> str:
    """The snapshot each repository is currently at, one row per repository.

    Current is the most recent index run, per repository rather than per store:
    a store holds several repositories by design, and one global newest would
    answer for whichever was indexed last and return nothing for the others.

    Two counts ride along, because how many runs sit behind an unscoped figure is
    the whole question the views exist to answer, and the two answer it about
    different things. ``runs_of_this_repository`` is what an unscoped count of
    this repository's rows would have summed -- one run reads the same either
    way, eight does not. ``runs_in_store`` is every run row in the file,
    this repository's and every other's.

    The ordering is ``indexed_at`` descending, and the two columns after it are a
    tiebreak rather than a second reading of time: two runs of one repository can
    only share an ``indexed_at`` if they were written before this column kept its
    microseconds, and nothing in those rows says which of them ran first. So the
    tiebreak is deterministic and not meaningful, it is reachable only by rows
    predating that change, and the next index run of that repository settles it
    for good.

    Written as ``r.*`` with the ordering column excluded again, so a column added
    to the run table appears here without a second edit.
    """
    repository = "r.traversal_path, r.project_id"
    return (
        f"CREATE OR REPLACE VIEW {SNAPSHOT_VIEW} AS\n"
        f"SELECT * EXCLUDE (recency) FROM (\n"
        f"  SELECT r.*,\n"
        f"         count(*) OVER (PARTITION BY {repository})\n"
        f"           AS runs_of_this_repository,\n"
        f"         count(*) OVER () AS runs_in_store,\n"
        f"         row_number() OVER (PARTITION BY {repository}\n"
        f"                            ORDER BY r.indexed_at DESC,\n"
        f"                                     r.commit_sha DESC, r.branch DESC)\n"
        f"           AS recency\n"
        f"    FROM {RUN_TABLE} r\n"
        f") WHERE recency = 1"
    )


def declare_views(connection, shapes) -> list[str]:
    """Declare a current-snapshot view over every table. Returns their names.

    Replaced rather than created-if-absent, on every run, because a view holding
    yesterday's column list is the failure this is meant to remove: a reader who
    never opens the README still gets an answer, so the answer has to be right
    without anyone having remembered to refresh it.

    The run table's view is built here and every other table's in the ontology,
    beside the shape it scopes. That is not a seam papered over: the others are
    one table filtered to the current snapshot, and this one is what says which
    snapshot that is. Which run is current is the store's question, and the
    ontology declares table shapes.
    """
    shapes = list(shapes)
    assert_local_view(SNAPSHOT_VIEW)
    connection.execute(snapshot_view_sql())
    declared = [SNAPSHOT_VIEW]
    for shape in shapes:
        if shape.table == RUN_TABLE:
            # Declared above, as the snapshot every other view joins to.
            continue
        assert_local_view(shape.current_view)
        connection.execute(shape.create_current_view_sql(SNAPSHOT_VIEW))
        declared.append(shape.current_view)
    return sorted(declared)


def _snapshot_counts(connection, table: str) -> dict[tuple, int]:
    key = ", ".join(SNAPSHOT_KEY)
    try:
        rows = connection.execute(
            f"SELECT {key}, count(*) FROM {table} GROUP BY {key}"
        ).fetchall()
    except duckdb.CatalogException:
        return {}
    return {tuple(row[:-1]): int(row[-1]) for row in rows}


def snapshots(connection, shapes, detector_set_version: str) -> list[dict]:
    """Every repository the store holds, not only the one just indexed.

    A count read out of this store is only interpretable if what else is in
    there is on the same screen: multiple repositories in one store is the
    design, and a surfaces total that silently spans two of them is not a
    reading of either.

    The detector version comes from each snapshot's own run row rather than
    from the tool doing the reading, so rows written by a different detector
    set are distinguishable from rows written by this one -- a change in the
    detectors and a change in the estate move the same numbers, and this is the
    only thing that separates them.
    """
    shapes = list(shapes)
    try:
        runs = connection.execute(
            f"SELECT {', '.join(SNAPSHOT_KEY)}, path, indexed_at, detector_set_version "
            f"FROM {RUN_TABLE} ORDER BY path, branch, commit_sha"
        ).fetchall()
    except duckdb.CatalogException:
        return []

    counts = {shape.table: _snapshot_counts(connection, shape.table) for shape in shapes}
    listed = []
    for traversal_path, project_id, branch, commit_sha, path, indexed_at, version in runs:
        key = (traversal_path, project_id, branch, commit_sha)
        listed.append({
            "repository": Path(path).name,
            "path": path,
            "project_id": int(project_id),
            "branch": branch,
            "commit_sha": commit_sha,
            "indexed_at": indexed_at.isoformat(timespec="seconds") if indexed_at else "",
            "detector_set_version": version,
            "detector_set_is_current": version == detector_set_version,
            "rows": {table: counts[table].get(key, 0) for table in sorted(counts)},
        })
    return listed


def rows_outside_a_recorded_run(connection, shapes) -> dict[str, int]:
    """Rows whose snapshot no run row accounts for, per table.

    Normally empty. Where it is not, those rows carry no detector version and
    no index time, so they are named rather than folded into a total that would
    read as if they did.
    """
    shapes = list(shapes)
    try:
        runs = {
            tuple(row) for row in connection.execute(
                f"SELECT {', '.join(SNAPSHOT_KEY)} FROM {RUN_TABLE}"
            ).fetchall()
        }
    except duckdb.CatalogException:
        return {}
    outside: dict[str, int] = {}
    for shape in shapes:
        if shape.table == RUN_TABLE:
            continue
        unaccounted = sum(
            count for key, count in _snapshot_counts(connection, shape.table).items()
            if key not in runs
        )
        if unaccounted:
            outside[shape.table] = unaccounted
    return outside
