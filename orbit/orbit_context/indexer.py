"""Index an estate's context surfaces into Orbit's local DuckDB."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from . import clauses as clause_module
from . import ontology as ontology_module
from . import store, surfaces
from .ontology import EdgeType, NodeType, OntologyError
from .workspace import (
    LOCAL_TRAVERSAL_PATH,
    GitError,
    Repository,
    discover_repos,
    git_info,
    stable_id,
)


SURFACE_NODE = "Surface"
CLAUSE_NODE = "Clause"
CONTAINS_EDGE = "CONTAINS"


@dataclass
class RepoResult:
    repository: str
    path: str
    project_id: int
    branch: str
    commit_sha: str
    surfaces: int = 0
    clauses: int = 0
    edges: int = 0
    skipped: list[dict] = field(default_factory=list)
    errored: list[dict] = field(default_factory=list)


def _row(node: NodeType, repo: Repository, detected: surfaces.Detected) -> dict:
    # A settings file holds many rows at one path, so the path alone no longer
    # identifies a surface. Kind and offset complete it -- the offset rather
    # than the line, because a settings file written on one line would
    # otherwise collapse all its hooks into a single row.
    identity = (
        repo.project_id, repo.branch, repo.commit_sha, detected.relative_path,
        detected.kind, detected.start_offset,
    )
    values = {
        "id": stable_id(*("" if part is None else part for part in identity)),
        "traversal_path": LOCAL_TRAVERSAL_PATH,
        "project_id": repo.project_id,
        "branch": repo.branch,
        "commit_sha": repo.commit_sha,
        "path": detected.relative_path,
        "name": detected.name,
        "surface_kind": detected.kind,
        "size_bytes": detected.size_bytes,
        "frontmatter_bytes": detected.frontmatter_bytes,
        "body_bytes": detected.body_bytes,
        "start_line": detected.start_line,
        "end_line": detected.end_line,
        "matcher": detected.matcher,
        "target_path": detected.target_path,
        "target_resolution": detected.target_resolution,
        "reason": detected.reason,
    }
    # Columns added to the YAML but not yet populated by a detector land as
    # NULL rather than blocking the write.
    return {name: values.get(name) for name in node.column_names}


def _clause_row(node: NodeType, repo: Repository, surface_path: str,
                clause: clause_module.Clause) -> tuple[int, dict]:
    """One clause row, and the id it is addressed by.

    The id is derived from the snapshot, the surface, and the clause's own
    start byte. The start byte rather than the fqn alone, because an fqn is
    built from the estate's own headings and two siblings can carry the same
    text -- which is a fact about the file, not a collision to resolve.
    """
    identity = (
        repo.project_id, repo.branch, repo.commit_sha, surface_path,
        clause.clause_type, clause.fqn, clause.start_byte,
    )
    values = {
        "id": stable_id(*identity),
        "traversal_path": LOCAL_TRAVERSAL_PATH,
        "project_id": repo.project_id,
        "branch": repo.branch,
        "commit_sha": repo.commit_sha,
        "surface_path": surface_path,
        "fqn": clause.fqn,
        "heading": clause.heading,
        "clause_type": clause.clause_type,
        "start_line": clause.start_line,
        "end_line": clause.end_line,
        "start_byte": clause.start_byte,
        "end_byte": clause.end_byte,
    }
    return values["id"], {name: values.get(name) for name in node.column_names}


def _edge_row(edge: EdgeType, repo: Repository, source_id: int, source_kind: str,
              target_id: int, target_kind: str) -> dict:
    if not edge.allows(source_kind, target_kind):
        raise OntologyError(
            f"{edge.source_file}: {edge.edge_type} declares no variant "
            f"{source_kind} -> {target_kind}"
        )
    values = {
        "source_id": source_id,
        "source_kind": source_kind,
        "relationship_kind": edge.edge_type,
        "target_id": target_id,
        "target_kind": target_kind,
        "traversal_path": LOCAL_TRAVERSAL_PATH,
        "project_id": repo.project_id,
        "branch": repo.branch,
        "commit_sha": repo.commit_sha,
    }
    return {name: values.get(name) for name in edge.column_names}


def _segment(clause_node: NodeType, edge: EdgeType, repo: Repository,
             surface_id: int, surface_path: str,
             text: str) -> tuple[list[dict], list[dict]]:
    """Cut one surface into clause rows, and the CONTAINS edges holding them.

    Depth is not a column. A clause nested inside another is an edge between
    them, so "how deep does this nest" is a walk of the graph at query time
    rather than a number frozen at index time.
    """
    clause_rows: list[dict] = []
    edge_rows: list[dict] = []
    ids: list[int] = []
    for clause in clause_module.segment(text, surface_path):
        clause_id, row = _clause_row(clause_node, repo, surface_path, clause)
        ids.append(clause_id)
        clause_rows.append(row)
        if clause.parent is None:
            source_id, source_kind = surface_id, SURFACE_NODE
        else:
            source_id, source_kind = ids[clause.parent], CLAUSE_NODE
        edge_rows.append(
            _edge_row(edge, repo, source_id, source_kind, clause_id, CLAUSE_NODE)
        )
    return clause_rows, edge_rows


def _count(result: RepoResult, path: str, reason: str, detail: str, errored: bool) -> None:
    """One outcome, in the shape Orbit's own statistics use.

    A row that indexed is counted; a row or note that did not carries its
    reason, so a surface that is present but unindexed does not read as one
    that is absent.
    """
    if not reason:
        result.surfaces += 1
    elif errored:
        result.errored.append({"path": path, "kind": reason, "detail": detail})
    else:
        result.skipped.append({"path": path, "reason": reason, "detail": detail})


def index_repository(connection, ontology: ontology_module.Ontology, repo: Repository,
                     nested_repos: list[Path]) -> RepoResult:
    surface_node = ontology.nodes[SURFACE_NODE]
    clause_node = ontology.nodes[CLAUSE_NODE]
    contains = ontology.edges[CONTAINS_EDGE]

    result = RepoResult(
        repository=repo.name,
        path=str(repo.root),
        project_id=repo.project_id,
        branch=repo.branch,
        commit_sha=repo.commit_sha,
    )
    # Keyed by id: one hook script targeted by two hooks is one hook-target
    # row, not two identical ones.
    rows: dict[int, dict] = {}
    clause_rows: list[dict] = []
    edge_rows: list[dict] = []
    for candidate in surfaces.walk_repo(repo.root, nested_repos):
        reading = surfaces.read_candidate(candidate)
        detected, notes = surfaces.expand(repo.root, candidate, reading)
        for one in detected:
            row = _row(surface_node, repo, one)
            if row["id"] in rows:
                continue
            rows[row["id"]] = row
            _count(result, one.relative_path, one.reason, one.detail, one.errored)
            # Segmented from the row that *is* the file. A hook-target row at
            # the same path is the same bytes seen from another angle, and
            # segmenting it too would write every clause twice.
            if reading.text is not None and one.kind in surfaces.SEGMENTED_KINDS:
                found, edges = _segment(
                    clause_node, contains, repo, row["id"],
                    one.relative_path, reading.text,
                )
                clause_rows.extend(found)
                edge_rows.extend(edges)
        for note in notes:
            _count(result, note.relative_path, note.reason, note.detail, note.errored)

    result.clauses = len(clause_rows)
    result.edges = len(edge_rows)

    for shape, written in (
        (surface_node, list(rows.values())),
        (clause_node, clause_rows),
        (contains, edge_rows),
    ):
        store.replace_rows(
            connection, shape, LOCAL_TRAVERSAL_PATH, repo.project_id,
            repo.branch, repo.commit_sha, written,
        )
    return result


def index(path: str | Path, db_path: str | Path = store.DEFAULT_DB_PATH,
          ontology_root: str | Path | None = None, detailed: bool = False) -> dict:
    """Index every repository at or under ``path``. Returns JSON statistics."""
    started = time.perf_counter()
    root = Path(path).resolve()

    ontology = ontology_module.load(ontology_root)

    repo_roots = discover_repos(root)
    results: list[RepoResult] = []
    unreadable_repos: list[dict] = []

    connection = store.connect(db_path)
    try:
        schema = [
            {
                "table": shape.table,
                "ontology": str(shape.source_file),
                **store.reconcile(connection, shape),
            }
            for shape in ontology.tables
        ]
        for repo_root in repo_roots:
            nested = [other for other in repo_roots
                      if other != repo_root and repo_root in other.parents]
            try:
                repo = git_info(repo_root)
            except GitError as error:
                unreadable_repos.append(
                    {"path": str(repo_root), "kind": "git_state_unavailable",
                     "detail": str(error)}
                )
                continue
            results.append(index_repository(connection, ontology, repo, nested))
    finally:
        connection.close()

    outside = [
        {"path": candidate.relative_path,
         "reason": surfaces.REASON_OUTSIDE_REPOSITORY,
         "detail": ""}
        for candidate in surfaces.walk_outside_repos(root, repo_roots)
    ]

    elapsed = time.perf_counter() - started
    skipped = [entry for result in results for entry in result.skipped] + outside
    errored = [entry for result in results for entry in result.errored] + unreadable_repos

    statistics = {
        "repository": root.name,
        "path": str(root),
        "time_seconds": round(elapsed, 4),
        "graph": {
            "repositories": len(results),
            "surfaces": sum(result.surfaces for result in results),
            "clauses": sum(result.clauses for result in results),
            "edges": sum(result.edges for result in results),
        },
        "processing": {
            "skipped_files": len(skipped),
            "errored_files": len(errored),
        },
        "database_path": str(Path(db_path)),
        "repositories": [
            {
                "repository": result.repository,
                "path": result.path,
                "project_id": result.project_id,
                "branch": result.branch,
                "commit_sha": result.commit_sha,
                "graph": {
                    "surfaces": result.surfaces,
                    "clauses": result.clauses,
                    "edges": result.edges,
                },
                "processing": {
                    "skipped_files": len(result.skipped),
                    "errored_files": len(result.errored),
                },
            }
            for result in results
        ],
        "schema": schema,
    }

    if detailed:
        statistics["detailed"] = {"skipped_files": skipped, "errored_files": errored}

    return statistics
