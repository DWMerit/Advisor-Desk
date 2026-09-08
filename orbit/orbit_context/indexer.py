"""Index an estate's context surfaces into Orbit's local DuckDB."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from . import store, surfaces
from .ontology import NodeType, load_domain
from .workspace import (
    LOCAL_TRAVERSAL_PATH,
    GitError,
    Repository,
    discover_repos,
    git_info,
    stable_id,
)


@dataclass
class RepoResult:
    repository: str
    path: str
    project_id: int
    branch: str
    commit_sha: str
    surfaces: int = 0
    skipped: list[dict] = field(default_factory=list)
    errored: list[dict] = field(default_factory=list)


def _row(node: NodeType, repo: Repository, candidate: surfaces.Candidate,
         reading: surfaces.Reading) -> dict:
    values = {
        "id": stable_id(repo.project_id, repo.branch, repo.commit_sha, candidate.relative_path),
        "traversal_path": LOCAL_TRAVERSAL_PATH,
        "project_id": repo.project_id,
        "branch": repo.branch,
        "commit_sha": repo.commit_sha,
        "path": candidate.relative_path,
        "surface_kind": candidate.kind,
        "size_bytes": reading.size_bytes,
        "reason": reading.reason,
    }
    # Columns added to the YAML but not yet populated by a detector land as
    # NULL rather than blocking the write.
    return {name: values.get(name) for name in node.column_names}


def index_repository(connection, node: NodeType, repo: Repository,
                     nested_repos: list[Path]) -> RepoResult:
    result = RepoResult(
        repository=repo.name,
        path=str(repo.root),
        project_id=repo.project_id,
        branch=repo.branch,
        commit_sha=repo.commit_sha,
    )
    rows = []
    for candidate in surfaces.walk_repo(repo.root, nested_repos):
        reading = surfaces.read_candidate(candidate)
        rows.append(_row(node, repo, candidate, reading))
        if reading.indexed:
            result.surfaces += 1
        elif reading.errored:
            result.errored.append(
                {"path": candidate.relative_path, "kind": reading.reason,
                 "detail": reading.detail}
            )
        else:
            result.skipped.append(
                {"path": candidate.relative_path, "reason": reading.reason,
                 "detail": reading.detail}
            )

    store.replace_rows(
        connection, node, LOCAL_TRAVERSAL_PATH, repo.project_id,
        repo.branch, repo.commit_sha, rows,
    )
    return result


def index(path: str | Path, db_path: str | Path = store.DEFAULT_DB_PATH,
          ontology_root: str | Path | None = None, detailed: bool = False) -> dict:
    """Index every repository at or under ``path``. Returns JSON statistics."""
    started = time.perf_counter()
    root = Path(path).resolve()

    nodes = load_domain(ontology_root) if ontology_root else load_domain()
    node = nodes["Surface"]

    repo_roots = discover_repos(root)
    results: list[RepoResult] = []
    unreadable_repos: list[dict] = []

    connection = store.connect(db_path)
    try:
        schema = store.reconcile(connection, node)
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
            results.append(index_repository(connection, node, repo, nested))
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
                "graph": {"surfaces": result.surfaces},
                "processing": {
                    "skipped_files": len(result.skipped),
                    "errored_files": len(result.errored),
                },
            }
            for result in results
        ],
        "schema": {
            "table": node.table,
            "ontology": str(node.source_file),
            "columns_added": schema["added"],
            "columns_not_declared_in_ontology": schema["undeclared"],
        },
    }

    if detailed:
        statistics["detailed"] = {"skipped_files": skipped, "errored_files": errored}

    return statistics
