"""Index an estate's context surfaces into Orbit's local DuckDB."""

from __future__ import annotations

import hashlib

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import clauses as clause_module
from . import detectors
from . import ladders as ladder_module
from . import ontology as ontology_module
from . import pointers as pointer_module
from . import provenance as provenance_module
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
EXTERNAL_REF_NODE = "ExternalRef"
# Two tables that record the walk rather than what it found. Neither carries
# edges: without them a count of surfaces has no denominator and no detector
# set beside it, and `repo-map` would have to re-walk the tree to invent both.
INDEX_RUN_NODE = "IndexRun"
COVERAGE_NOTE_NODE = "CoverageNote"
CONTAINS_EDGE = "CONTAINS"
REFERENCES_EDGE = "REFERENCES"
IDENTICAL_BYTES_EDGE = provenance_module.IDENTICAL_BYTES_EDGE
PRODUCES_EDGE = provenance_module.PRODUCES_EDGE
# Spelled once, in the module that reads these edges back. Two spellings of an
# edge type is a rename that half applies, and the half that did not leaves
# `ladder` and `repo-map` reporting zero with nothing raised.
RUNG_OF_EDGE = ladder_module.RUNG_OF_EDGE

# Orbit's own node type. A pointer landing on a file that is not a governance
# surface points at a row in their `gl_file`, in their database -- so the edge
# carries the path, and the join that crosses graphs goes by path.
FILE_NODE = "File"


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
    pointers: int = 0
    # Counted per sub_kind, never summed into one number: the three are
    # different statements about the detector set, and one total says none of
    # them.
    external_refs: dict = field(default_factory=dict)
    # The byte-identity count and the provenance counts, in one dict, because
    # the first over-reads without the second. See provenance.summary.
    identical_bytes: dict = field(default_factory=dict)
    skipped: list[dict] = field(default_factory=list)
    errored: list[dict] = field(default_factory=list)
    # The same outcomes as skipped and errored, in one uniform shape for the
    # coverage table. Kept separate so the JSON statistics keep the shape
    # Orbit's own `index` output uses.
    coverage: list[dict] = field(default_factory=list)
    # Surfaces by how they were recognised. Reported beside the count rather
    # than folded into it: two of the three values are the estate's own
    # statement about a file and the third is this tool's reading of a
    # directory, and a total says which is which about none of them.
    recognition: dict = field(default_factory=dict)
    # The ladders found, and the rungs that could not be attached to one.
    # Reported together for the reason the pair count is reported beside its
    # provenance: a ladder count on its own cannot say what it missed.
    ladders: dict = field(default_factory=dict)
    # The walk, and how much of it these detectors recognise anything in.
    files_walked: int = 0
    files_with_surface_kind: int = 0
    # Rows this repository's write took out of the store, per table. Zero on a
    # first index; on a re-index it is what the run stood on top of, and a
    # reader can tell that from a total that did not move.
    replaced: dict = field(default_factory=dict)


_DIGESTS: dict[tuple, str] = {}


def _digest(path) -> str:
    """SHA-256 of a file, memoised on (path, mtime, size) within a run.

    One file can produce many surface rows -- a settings file holds a row per
    hook -- so this is cached rather than re-read per row.
    """
    try:
        stat = path.stat()
    except OSError:
        return ""
    key = (str(path), stat.st_mtime_ns, stat.st_size)
    if key not in _DIGESTS:
        try:
            _DIGESTS[key] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            _DIGESTS[key] = ""
    return _DIGESTS[key]


def _file_id(repo: Repository, path: str) -> int:
    """A deterministic handle for a file whose own row lives in Orbit's graph.

    Orbit's `gl_file` is in their database and their ids are not ours, so the
    edge carries a stable id of our own and the join that crosses graphs goes
    by path.
    """
    return stable_id(repo.project_id, repo.branch, repo.commit_sha, FILE_NODE, path)


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
        "recognition": detected.recognition,
        # A node listed without its bytes has no digest of its own, and taking
        # one would follow the link and hash the file it names -- filing one
        # file's bytes under two paths and inventing a byte-identical pair the
        # estate does not have.
        "content_sha256": (
            "" if detected.non_regular
            else _digest(repo.root / detected.relative_path)
        ),
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
              target_id: int, target_kind: str, **extra) -> dict:
    """One edge row's values, checked against the variants the type declares.

    ``extra`` carries what one edge type holds and another does not -- a
    detector, a locator, an address. Values are returned unfiltered; a shared
    table's column set is applied once, at write time, so a column belonging to
    a sibling edge type lands as NULL rather than going missing.
    """
    if not edge.allows(source_kind, target_kind):
        raise OntologyError(
            f"{edge.source_file}: {edge.edge_type} declares no variant "
            f"{source_kind} -> {target_kind}"
        )
    return {
        "source_id": source_id,
        "source_kind": source_kind,
        "relationship_kind": edge.edge_type,
        "target_id": target_id,
        "target_kind": target_kind,
        "traversal_path": LOCAL_TRAVERSAL_PATH,
        "project_id": repo.project_id,
        "branch": repo.branch,
        "commit_sha": repo.commit_sha,
        **extra,
    }


def _segment(clause_node: NodeType, edge: EdgeType, repo: Repository,
             surface_id: int, surface_path: str,
             text: str) -> tuple[list[dict], list[dict], list[tuple[int, int, int]]]:
    """Cut one surface into clause rows, the CONTAINS edges, and the spans.

    Depth is not a column. A clause nested inside another is an edge between
    them, so "how deep does this nest" is a walk of the graph at query time
    rather than a number frozen at index time.

    The spans -- ``(start_byte, end_byte, id)`` per clause -- are what lets a
    pointer be attributed to the rule it was written in rather than to the whole
    file.
    """
    clause_rows: list[dict] = []
    edge_rows: list[dict] = []
    spans: list[tuple[int, int, int]] = []
    ids: list[int] = []
    for clause in clause_module.segment(text, surface_path):
        clause_id, row = _clause_row(clause_node, repo, surface_path, clause)
        ids.append(clause_id)
        clause_rows.append(row)
        spans.append((clause.start_byte, clause.end_byte, clause_id))
        if clause.parent is None:
            source_id, source_kind = surface_id, SURFACE_NODE
        else:
            source_id, source_kind = ids[clause.parent], CLAUSE_NODE
        edge_rows.append(
            _edge_row(edge, repo, source_id, source_kind, clause_id, CLAUSE_NODE)
        )
    return clause_rows, edge_rows, spans


def _external_row(node: NodeType, repo: Repository, address: str,
                  sub_kind: str) -> tuple[int, dict]:
    """One ExternalRef row, and the id it is addressed by.

    Deduplicated on the address and the non-resolution it met, so a path named
    forty times in one repository is one row with forty edges into it rather
    than forty rows.
    """
    identity = (repo.project_id, repo.branch, repo.commit_sha, address, sub_kind)
    values = {
        "id": stable_id(*identity),
        "traversal_path": LOCAL_TRAVERSAL_PATH,
        "project_id": repo.project_id,
        "branch": repo.branch,
        "commit_sha": repo.commit_sha,
        "address": address,
        "sub_kind": sub_kind,
    }
    return values["id"], {name: values.get(name) for name in node.column_names}


def _innermost(spans: list[tuple[int, int, int]], offset: int) -> int | None:
    """The id of the smallest clause span holding ``offset``, or None.

    A parent's span includes its descendants, so the smallest containing span is
    the clause the pointer was actually written in. Text above the first heading
    sits in no clause at all, and that is what None means.
    """
    holding = [span for span in spans if span[0] <= offset < span[1]]
    if not holding:
        return None
    return min(holding, key=lambda span: span[1] - span[0])[2]


def _identical_byte_edges(edge: EdgeType, repo: Repository,
                          ordered: list[provenance_module.Direction]) -> list[dict]:
    """One edge per pair of files whose bytes hash the same.

    The pair itself is pure observation: two paths and the digest they share.
    Whether they are *meant* to be identical is not derived here -- spec 0001
    §14 keeps that a permanent UNKNOWN.

    Which end came first is derived, and only from a ``PRODUCES`` edge between
    the pair's own two ends. Where there is one the row carries the direction,
    the rung it stands on and the file:line it was read from; where there is
    none the row carries UNKNOWN and the reason. Never blank, because a blank
    reads as a column nobody filled in rather than as a measurement.
    """
    return [
        _edge_row(
            edge, repo,
            _file_id(repo, one.pair.first_path), FILE_NODE,
            _file_id(repo, one.pair.second_path), FILE_NODE,
            source_path=one.pair.first_path,
            target_path=one.pair.second_path,
            content_sha256=one.pair.sha256,
            direction=one.direction,
            direction_reason=one.reason,
            subtype=one.evidence,
            evidence_path=one.evidence_path,
            evidence_line=one.evidence_line,
        )
        for one in ordered
    ]


def _produces_edges(edge: EdgeType, repo: Repository,
                    productions: list[provenance_module.Production]) -> list[dict]:
    """One edge per artifact whose producer resolved to a file in the tree.

    A producer the estate named that nothing in the tree matches writes no
    edge: an edge needs both ends, and inventing the missing one would put a
    file in the graph that the repository does not hold. It is counted in the
    statistics instead, so that a producer named but not found does not read as
    a producer never named.
    """
    return [
        _edge_row(
            edge, repo,
            _file_id(repo, production.producer_path), FILE_NODE,
            _file_id(repo, production.artifact_path), FILE_NODE,
            subtype=production.evidence,
            source_path=production.producer_path,
            source_address=production.producer_address,
            target_path=production.artifact_path,
            evidence_path=production.evidence_path,
            evidence_line=production.evidence_line,
        )
        for production in productions
        if production.producer_path is not None
        and production.producer_path != production.artifact_path
    ]


def _rung_edges(edge: EdgeType, repo: Repository,
                whole_file_surfaces: dict[str, int],
                listed: set[str]) -> tuple[list[dict], list[str]]:
    """One edge per rung whose base rung is a surface in the same repository.

    The relation is read off two filenames, so both ends have to be surfaces
    this run already found: a rung of something that is not governance is not a
    ladder this graph can be asked about.

    A rung word whose base rung is not there writes no edge -- an edge needs
    both ends, and inventing the missing one would put a file in the graph the
    repository does not hold. It is returned instead, so that a rung the estate
    wrote and this tool could not attach does not read as a rung never written.

    ``listed`` is the paths this run recorded as nodes without reading them. A
    vendor name reaches a symlink -- `.claude/agents/reviewer.mini.md` beside
    `reviewer.md` is a row and a rung word -- and a link is neither end of a
    ladder: the rung words say two files hold one book at two sizes, and a link
    is one file wearing a second name.

    The two ends are left out differently, because they are different facts:

    - a link **carrying** a rung word is not a rung the estate wrote, so it is
      not counted as one this tool could not attach either. It is skipped.
    - a rung whose **base rung** is a link is a rung the estate did write, and
      this tool could not attach it. That is what ``rungs_with_no_base_rung``
      counts, and it is counted there.
    """
    rows: list[dict] = []
    without_a_base: list[str] = []
    for path in sorted(whole_file_surfaces):
        if path in listed:
            continue
        named = surfaces.rung_of(path)
        if named is None:
            continue
        base_path, rung = named
        base_id = None if base_path in listed else whole_file_surfaces.get(base_path)
        if base_id is None:
            without_a_base.append(path)
            continue
        rows.append(
            _edge_row(
                edge, repo, whole_file_surfaces[path], SURFACE_NODE,
                base_id, SURFACE_NODE,
                subtype=rung,
                source_path=path,
                target_path=base_path,
            )
        )
    return rows, without_a_base


def _ladder_tally(rung_edges: list[dict], without_a_base: list[str]) -> dict:
    """The ladders those edges make up, with every figure present at zero.

    A ladder is one base rung and the rungs pointing at it, so its height is the
    edges into it plus the base rung itself. How many rungs a book carries is an
    observation: a book at two is reported as two, beside the books at three,
    and never as a book missing one.
    """
    rungs_by_base: dict[str, int] = {}
    for row in rung_edges:
        base = row["target_path"]
        rungs_by_base[base] = rungs_by_base.get(base, 0) + 1
    heights: dict[int, int] = {}
    for count in rungs_by_base.values():
        heights[count + 1] = heights.get(count + 1, 0) + 1
    return {
        "found": len(rungs_by_base),
        "rungs": sum(count + 1 for count in rungs_by_base.values()),
        # Keyed by string because JSON has no other kind of key, and ordered by
        # the number it spells: sorted as text, a ladder of ten rungs sorts
        # before one of two, and the extension point this module documents is
        # adding rung words.
        "ladders_by_rung_count": {
            str(height): heights[height] for height in sorted(heights)
        },
        "rungs_with_no_base_rung": len(without_a_base),
    }


def _pointer_edges(edge: EdgeType, external_node: NodeType, repo: Repository,
                   surface_row: dict, surface_path: str,
                   found: tuple, spans: list[tuple[int, int, int]],
                   whole_file_surfaces: dict[str, int],
                   external_rows: dict[int, dict],
                   counts: dict[str, int]) -> list[dict]:
    """Resolve one surface's pointers into edges, and the ExternalRefs they need."""
    rows: list[dict] = []
    for pointer in found:
        resolution = pointer_module.resolve(
            pointer_module.expanded(pointer.address, repo.root),
            repo.root,
            surface_path,
        )
        if resolution is None:
            continue

        if resolution.resolved:
            target_path = resolution.target_path
            target_id = whole_file_surfaces.get(target_path)
            if target_id is not None:
                target_kind = SURFACE_NODE
            else:
                # Orbit's row, in Orbit's database. The id is a deterministic
                # handle so the edge has a stable identity; the join that
                # crosses graphs goes by target_path.
                target_kind = FILE_NODE
                target_id = _file_id(repo, target_path)
        else:
            target_path = ""
            target_kind = EXTERNAL_REF_NODE
            target_id, row = _external_row(
                external_node, repo, pointer.address, resolution.sub_kind
            )
            if target_id not in external_rows:
                external_rows[target_id] = row
                counts[resolution.sub_kind] = counts.get(resolution.sub_kind, 0) + 1

        clause_id = _innermost(spans, pointer.start_byte)
        source_id = clause_id if clause_id is not None else surface_row["id"]
        source_kind = CLAUSE_NODE if clause_id is not None else SURFACE_NODE
        rows.append(
            _edge_row(
                edge, repo, source_id, source_kind, target_id, target_kind,
                subtype=pointer.subtype,
                source_path=surface_path,
                source_line=pointer.line,
                target_address=pointer.address,
                target_path=target_path,
                in_code_fence=pointer.in_code_fence,
            )
        )
    return rows


def _whole_file_surfaces(rows: dict[int, dict]) -> dict[str, int]:
    """Path to surface id, for the surfaces that are a whole file.

    A hook definition and an MCP server are entries *inside* a settings file, so
    a pointer at that path names the file rather than any one entry, and the
    edge goes to File. Only surfaces that are the whole file can be pointed at
    as themselves.
    """
    whole_file = set(surfaces.SEGMENTED_KINDS) | {surfaces.HOOK_TARGET}
    found: dict[str, int] = {}
    for row in rows.values():
        if row["surface_kind"] in whole_file:
            found.setdefault(row["path"], row["id"])
    return found


def _count(result: RepoResult, path: str, reason: str, detail: str, errored: bool) -> None:
    """One outcome, in the shape Orbit's own statistics use.

    A row that indexed is counted; a row or note that did not carries its
    reason, so a surface that is present but unindexed does not read as one
    that is absent. The same outcome is recorded a second time in the uniform
    shape the coverage table takes, because a reason printed to stdout and
    thrown away reads afterwards as a surface that was never there.
    """
    if not reason:
        result.surfaces += 1
        return
    if errored:
        result.errored.append({"path": path, "kind": reason, "detail": detail})
    else:
        result.skipped.append({"path": path, "reason": reason, "detail": detail})
    result.coverage.append(
        {"path": path, "reason": reason, "detail": detail, "errored": errored}
    )


def _now() -> datetime:
    """This run's moment, UTC and naive -- the shape a DuckDB TIMESTAMP holds."""
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def _run_row(node: NodeType, repo: Repository, indexed_root: Path,
             indexed_at: datetime,
             files_walked: int, files_with_surface_kind: int) -> dict:
    """The one row saying what this run covered, and which detectors read it.

    ``files_with_surface_kind`` counts distinct paths, not rows: a settings file
    holds a row per hook, and counting rows against a denominator of files would
    put coverage above one on an estate with enough hooks.
    """
    values = {
        "id": stable_id(repo.project_id, repo.branch, repo.commit_sha, INDEX_RUN_NODE),
        "traversal_path": LOCAL_TRAVERSAL_PATH,
        "project_id": repo.project_id,
        "branch": repo.branch,
        "commit_sha": repo.commit_sha,
        "path": str(repo.root),
        "indexed_root": str(indexed_root),
        "indexed_at": indexed_at,
        "detector_set_version": detectors.VERSION,
        "excluded_directories": ", ".join(sorted(surfaces.PRUNED_DIRECTORIES)),
        "files_walked": files_walked,
        "files_with_surface_kind": files_with_surface_kind,
    }
    return {name: values.get(name) for name in node.column_names}


def _coverage_rows(node: NodeType, repo: Repository,
                   entries: list[dict]) -> list[dict]:
    """One row per file the walk reached and did not fully index.

    Keyed by path and reason, so a file reached twice under the same reason is
    one row. Two reasons for one file stay two rows: they are two findings.
    """
    rows: dict[int, dict] = {}
    for entry in entries:
        values = {
            "id": stable_id(repo.project_id, repo.branch, repo.commit_sha,
                            COVERAGE_NOTE_NODE, entry["path"], entry["reason"]),
            "traversal_path": LOCAL_TRAVERSAL_PATH,
            "project_id": repo.project_id,
            "branch": repo.branch,
            "commit_sha": repo.commit_sha,
            "path": entry["path"],
            "reason": entry["reason"],
            "detail": entry["detail"],
            "errored": entry["errored"],
        }
        rows.setdefault(values["id"], {name: values.get(name) for name in node.column_names})
    return list(rows.values())


def index_repository(connection, ontology: ontology_module.Ontology, repo: Repository,
                     nested_repos: list[Path],
                     indexed_root: Path | None = None,
                     indexed_at: datetime | None = None) -> RepoResult:
    """Index one repository: surfaces, clauses, and the pointers between them.

    Two passes, because a pointer can only be resolved once every surface in the
    repository has been found. Resolving as the walk goes would make an edge's
    target depend on directory order -- a link to a file not yet walked would
    land as unmatched, and the same link would resolve on the next run.
    """
    surface_node = ontology.nodes[SURFACE_NODE]
    clause_node = ontology.nodes[CLAUSE_NODE]
    external_node = ontology.nodes[EXTERNAL_REF_NODE]
    run_node = ontology.nodes[INDEX_RUN_NODE]
    coverage_node = ontology.nodes[COVERAGE_NOTE_NODE]
    contains = ontology.edges[CONTAINS_EDGE]
    references = ontology.edges[REFERENCES_EDGE]
    identical_bytes = ontology.edges[IDENTICAL_BYTES_EDGE]
    produces = ontology.edges[PRODUCES_EDGE]
    rung_of = ontology.edges[RUNG_OF_EDGE]

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
    # Held back for the second pass: the row a pointer leaves from, the path it
    # was written in, the pointers themselves, and the clause spans to attribute
    # them to.
    pending: list[tuple[dict, str, tuple, list]] = []
    # The paths this run recorded as nodes without opening them, taken from the
    # walk's own answer as it arrives rather than read back off the row. A link
    # is pointed at like any other node; what it is never is one end of a
    # relation read out of two files' names or two files' bytes.
    listed: set[str] = set()

    # One walk. A surface is one of these files that also carries a name or a
    # location this indexer recognises; every file is hashed, whether it is a
    # surface or not.
    walked = surfaces.walk_files(repo.root, nested_repos)

    for candidate in surfaces.candidates(walked):
        reading = surfaces.read_candidate(candidate)
        detected, notes = surfaces.expand(repo.root, candidate, reading)
        for one in detected:
            row = _row(surface_node, repo, one)
            if row["id"] in rows:
                continue
            rows[row["id"]] = row
            if one.non_regular:
                listed.add(one.relative_path)
            _count(result, one.relative_path, one.reason, one.detail, one.errored)
            # Segmented from the row that *is* the file. A hook-target row at
            # the same path is the same bytes seen from another angle, and
            # segmenting it too would write every clause twice.
            spans: list[tuple[int, int, int]] = []
            if reading.text is not None and one.kind in surfaces.SEGMENTED_KINDS:
                found, edges, spans = _segment(
                    clause_node, contains, repo, row["id"],
                    one.relative_path, reading.text,
                )
                clause_rows.extend(found)
                edge_rows.extend(edges)
            if one.pointers:
                pending.append((row, one.relative_path, one.pointers, spans))
        for note in notes:
            _count(result, note.relative_path, note.reason, note.detail, note.errored)

    whole_file = _whole_file_surfaces(rows)
    rung_rows, rungs_without_a_base = _rung_edges(rung_of, repo, whole_file, listed)
    edge_rows.extend(rung_rows)
    external_rows: dict[int, dict] = {}
    counts: dict[str, int] = {sub_kind: 0 for sub_kind in pointer_module.SUB_KINDS}
    pointer_rows: list[dict] = []
    for row, path, found, spans in pending:
        pointer_rows.extend(
            _pointer_edges(references, external_node, repo, row, path, found,
                           spans, whole_file, external_rows, counts)
        )
    edge_rows.extend(pointer_rows)

    # Byte-identity and provenance, in one pass and reported in one dict: a
    # count of matching pairs on its own over-reads badly, and on one real
    # repository every one of 28 pairs had a producer the tool could not see.
    scan = provenance_module.read_tree(repo.root, walked)
    matched = provenance_module.pairs(scan.contents, scan.zero_byte)
    productions = provenance_module.strongest(scan.productions)
    # A pair is symmetric, so which end came first is a second thing the row
    # would not say. Ordered here from the same productions the PRODUCES rows
    # are written from, so a direction on a pair row and the edge that
    # evidences it cannot disagree.
    ordered = provenance_module.directions(matched, productions)
    edge_rows.extend(_identical_byte_edges(identical_bytes, repo, ordered))
    edge_rows.extend(_produces_edges(produces, repo, productions))

    result.ladders = _ladder_tally(rung_rows, rungs_without_a_base)
    result.recognition = _recognition_tally(rows.values())
    result.files_walked = len(walked)
    # Distinct paths, not rows. A settings file is one file however many hooks
    # it holds, and a hook target is the same file seen from another angle.
    result.files_with_surface_kind = len({row["path"] for row in rows.values()})
    result.clauses = len(clause_rows)
    result.edges = len(edge_rows)
    result.pointers = len(pointer_rows)
    result.external_refs = counts
    result.identical_bytes = provenance_module.summary(scan, matched, productions)

    # Written once per table, not once per shape: CONTAINS and REFERENCES share
    # gl_context_edge, and a second replace_rows for the same snapshot would
    # delete what the first just wrote.
    tables = {shape.table: shape for shape in ontology.tables}
    for shape, written in (
        (tables[surface_node.table], list(rows.values())),
        (tables[clause_node.table], clause_rows),
        (tables[external_node.table], list(external_rows.values())),
        (tables[contains.table], edge_rows),
        (tables[run_node.table],
         [_run_row(run_node, repo, indexed_root or repo.root,
                   indexed_at or _now(),
                   result.files_walked, result.files_with_surface_kind)]),
        (tables[coverage_node.table],
         _coverage_rows(coverage_node, repo, result.coverage)),
    ):
        moved = store.replace_rows(
            connection, shape, LOCAL_TRAVERSAL_PATH, repo.project_id,
            repo.branch, repo.commit_sha,
            [{name: values.get(name) for name in shape.column_names}
             for values in written],
        )
        result.replaced[shape.table] = moved["replaced"]
    return result


def _external_totals(results: list[RepoResult]) -> dict[str, int]:
    """The three non-resolutions across the estate, each on its own.

    Every sub_kind is present even at zero, and they are never summed: a single
    total would read as one finding, and they are three different statements
    about what the detector set could see.
    """
    totals = {sub_kind: 0 for sub_kind in pointer_module.SUB_KINDS}
    for result in results:
        for sub_kind, count in result.external_refs.items():
            totals[sub_kind] = totals.get(sub_kind, 0) + count
    return totals


def _recognition_tally(rows) -> dict:
    """Surfaces per recognition value, every value present even at zero.

    Present at zero on purpose. A repository with no inferred rows and a
    repository the inference was never applied to read the same if the key is
    simply absent, and they are not the same thing.

    Counted over rows that indexed, which is what ``surfaces`` beside it counts.
    A candidate that could not be read still becomes a row carrying its reason,
    and folding those in here would print a split that does not add up to the
    total it sits next to.
    """
    tally = {value: 0 for value in surfaces.RECOGNITION_KINDS}
    for row in rows:
        if row.get("reason"):
            continue
        value = row.get("recognition")
        if value in tally:
            tally[value] += 1
    return tally


def _ladder_totals(results: list[RepoResult]) -> dict:
    """The same tally across every repository this run indexed.

    The heights are merged key by key rather than summed into one number: two
    repositories with two ladders each, one at three rungs and one at two, is
    four ladders and two heights, and a total would say neither.
    """
    heights: dict[int, int] = {}
    for result in results:
        for height, count in result.ladders.get("ladders_by_rung_count", {}).items():
            heights[int(height)] = heights.get(int(height), 0) + count
    return {
        "found": sum(result.ladders.get("found", 0) for result in results),
        "rungs": sum(result.ladders.get("rungs", 0) for result in results),
        "ladders_by_rung_count": {
            str(height): heights[height] for height in sorted(heights)
        },
        "rungs_with_no_base_rung": sum(
            result.ladders.get("rungs_with_no_base_rung", 0) for result in results
        ),
    }


def _recognition_totals(results: list[RepoResult]) -> dict:
    """The same tally across every repository this run indexed."""
    return {
        value: sum(result.recognition.get(value, 0) for result in results)
        for value in surfaces.RECOGNITION_KINDS
    }


def _coverage(files_walked: int, files_with_surface_kind: int) -> dict:
    """The denominator beside the numerator, always both.

    A surface count on its own cannot be read: twelve surfaces out of fourteen
    files and twelve out of 1,775 are the same number about two different
    estates. The second figure is what makes a thin result read as "these
    detectors recognise little here" rather than as a description of the estate.
    """
    return {
        "files_walked": files_walked,
        "files_with_surface_kind": files_with_surface_kind,
        "files_with_no_surface_kind": files_walked - files_with_surface_kind,
    }


def _replaced_totals(results: list[RepoResult]) -> dict[str, int]:
    """Rows this run took out of the store, per table, across every repository."""
    totals: dict[str, int] = {}
    for result in results:
        for table, count in result.replaced.items():
            totals[table] = totals.get(table, 0) + count
    return totals


def _coverage_totals(results: list[RepoResult]) -> dict:
    return _coverage(
        sum(result.files_walked for result in results),
        sum(result.files_with_surface_kind for result in results),
    )


def migrate(db_path: str | Path = store.DEFAULT_DB_PATH,
            ontology_root: str | Path | None = None,
            remove_values: bool = False) -> dict:
    """Bring a store to the ontology by removing columns it no longer declares.

    The remedy `index` names when it refuses. Separate from indexing on
    purpose: what it does cannot be undone, so it is a command somebody runs
    having read why, rather than a step inside a run whose output is a count.
    """
    ontology = ontology_module.load(ontology_root)
    connection = store.connect(db_path)
    try:
        report = store.migrate(connection, ontology.tables, remove_values)
    finally:
        connection.close()
    report["database_path"] = str(Path(db_path))
    return report


def index(path: str | Path, db_path: str | Path = store.DEFAULT_DB_PATH,
          ontology_root: str | Path | None = None, detailed: bool = False) -> dict:
    """Index every repository at or under ``path``. Returns JSON statistics."""
    started = time.perf_counter()
    root = Path(path).resolve()

    ontology = ontology_module.load(ontology_root)

    repo_roots = discover_repos(root)
    results: list[RepoResult] = []
    unreadable_repos: list[dict] = []

    indexed_at = _now()
    connection = store.connect(db_path)
    try:
        sources = ontology.table_sources()
        schema = [
            {
                "table": shape.table,
                # Every file declaring the table, not just the first: a shared
                # edge table's columns come from several.
                "ontology": ", ".join(str(path) for path in sources[shape.table]),
                **store.reconcile(connection, shape),
            }
            for shape in ontology.tables
        ]
        # Before a row is written, not after. A run that indexes first and
        # reports the mismatch afterwards has already added rows to a store
        # whose shape it just called into question, and the counts it prints
        # cannot be compared with the run before it. See store.SchemaDrift.
        store.assert_matches_ontology(connection, ontology.tables, Path(db_path))
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
            results.append(
                index_repository(connection, ontology, repo, nested, root, indexed_at)
            )
        held = store.snapshots(connection, ontology.tables, detectors.VERSION)
        unaccounted = store.rows_outside_a_recorded_run(connection, ontology.tables)
    finally:
        connection.close()

    written_now = {
        (result.project_id, result.branch, result.commit_sha) for result in results
    }
    for entry in held:
        entry["indexed_by_this_run"] = (
            entry["project_id"], entry["branch"], entry["commit_sha"]
        ) in written_now

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
        # The detector set every count below was produced by. Recorded on each
        # snapshot's run row as well, so a count read back out of the graph
        # months later still carries the version that produced it.
        "detector_set_version": detectors.VERSION,
        "graph": {
            "repositories": len(results),
            "surfaces": sum(result.surfaces for result in results),
            "recognition": _recognition_totals(results),
            "clauses": sum(result.clauses for result in results),
            "edges": sum(result.edges for result in results),
            "pointers": sum(result.pointers for result in results),
            "external_refs": _external_totals(results),
            "identical_bytes": provenance_module.totals(
                [result.identical_bytes for result in results]
            ),
            "ladders": _ladder_totals(results),
        },
        "coverage": _coverage_totals(results),
        "processing": {
            "skipped_files": len(skipped),
            "errored_files": len(errored),
        },
        # What this run took out of the store to put its own rows in. Zero
        # everywhere on a first index; on a re-index it is the run before this
        # one, and without it a total that did not move reads the same whether
        # the run replaced its own snapshot or wrote nothing at all.
        "replaced": _replaced_totals(results),
        "database_path": str(Path(db_path)),
        # Every repository the store holds, not only the ones just indexed. A
        # count read from a store is only interpretable if what else is in
        # there is on the same screen.
        "store": {
            "database_path": str(Path(db_path)),
            "detector_set_version": detectors.VERSION,
            "repositories": held,
            "repositories_from_other_detector_sets": sum(
                1 for entry in held if not entry["detector_set_is_current"]
            ),
            "rows_outside_a_recorded_run": unaccounted,
        },
        "repositories": [
            {
                "repository": result.repository,
                "path": result.path,
                "project_id": result.project_id,
                "branch": result.branch,
                "commit_sha": result.commit_sha,
                "graph": {
                    "surfaces": result.surfaces,
                    "recognition": dict(result.recognition),
                    "clauses": result.clauses,
                    "edges": result.edges,
                    "pointers": result.pointers,
                    "external_refs": dict(result.external_refs),
                    "identical_bytes": dict(result.identical_bytes),
                    "ladders": dict(result.ladders),
                },
                "coverage": _coverage(result.files_walked,
                                      result.files_with_surface_kind),
                "processing": {
                    "skipped_files": len(result.skipped),
                    "errored_files": len(result.errored),
                },
                "replaced": dict(result.replaced),
            }
            for result in results
        ],
        "schema": schema,
    }

    if detailed:
        statistics["detailed"] = {"skipped_files": skipped, "errored_files": errored}

    return statistics
