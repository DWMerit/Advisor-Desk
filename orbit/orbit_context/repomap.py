"""One repository's governance surface, read out of the graph, inside a budget.

Orientation, not a report. The question it answers is "what governance does this
repository carry, and how much of it did these detectors see", in one screen a
session can afford to read before doing anything else.

Everything comes from the graph
-------------------------------

The map re-walks nothing. It reads one snapshot -- one ``(project_id, branch,
commit_sha)`` -- and every number in it comes from a row written by the index
run that recorded ``gl_context_run``. A second walk at map time would be a
second answer to "what is in this repository", taken against a working tree that
has moved on since indexing, and the map would print a denominator its own
numerators were never measured against.

The consequence is that a map can be older than the tree. That is stated rather
than hidden: the snapshot's commit is in the header, and where the detector set
that wrote the graph differs from the one in this build, the map says so instead
of presenting the counts as current.

Why every zero is printed
-------------------------

Each detector this tool has is listed whether or not it found anything -- all
seven surface kinds, all four clause types, all six pointer detectors, all three
non-resolutions, all three evidence rungs. A map that printed only non-zero rows
would read as a description of the estate. Printed in full, a column of zeroes
reads as what it is: the inventory of what these detectors look for, and how
little of it is here. That is the same reason coverage carries its denominator.

The budget
----------

GitLab Orbit's ``repo-map`` emits 12,874 bytes for a 1,775-file repository. That
measurement is the budget, and the map holds to it by construction rather than
by hope: every varying section is a fixed inventory of detectors, the two
sections that list rows are capped, and if the result still exceeds the budget
the lists are dropped and the map says they were dropped. The last line reports
what the map actually cost, counting itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import duckdb

from . import detectors, history, pointers, provenance, store, surfaces
from .clauses import CLAUSE_TYPES
from .retrieve import RetrievalError, repository

# GitLab Orbit's own `repo-map`, measured: 12,874 bytes (~3,200 tokens) for a
# 1,775-file repository. Their command is the reference point because it answers
# the same question over the half of a repository this one does not parse.
BUDGET_BYTES = 12874
BUDGET_CITATION = "GitLab Orbit repo-map, 12,874 bytes for a 1,775-file repository"

# Rows listed as examples before the map stops listing and says how many it did
# not list. Small on purpose: the pair count is the finding, and a listing is
# only there to make it concrete.
EXAMPLE_ROWS = 5

# Longest a path or address is printed at before it is cut. A single very long
# path must not be able to push the map over its budget.
MAX_TEXT_WIDTH = 64

# The edge kinds this domain writes, listed at zero as well as at count.
EDGE_KINDS = ("CONTAINS", "REFERENCES", "IDENTICAL_BYTES", "PRODUCES")


class RepoMapError(Exception):
    """The graph holds no snapshot to map."""


@dataclass
class RepoMap:
    """Everything the map prints, read from one snapshot."""

    name: str
    root: str
    branch: str
    commit_sha: str
    database_path: str

    indexed_root: str = ""
    graph_detector_version: str = ""
    build_detector_version: str = detectors.VERSION
    excluded_directories: str = ""
    files_walked: int = 0
    files_with_surface_kind: int = 0

    coverage_notes: list[tuple[str, int, int]] = field(default_factory=list)
    # Files per recognition value. Two of the three values are the estate's own
    # statement about a file; the third is this tool reading the directory it
    # sits in. A coverage figure that folded them together would put a reading
    # and a declaration behind one number, which is the thing the column exists
    # to stop.
    recognition_by_kind: dict[str, int] = field(default_factory=dict)
    surfaces_by_kind: dict[str, tuple[int, int, int]] = field(default_factory=dict)
    # Rows carrying a reason: a surface that was found and not read through. A
    # candidate that cannot be read still becomes a row, so the row count and
    # the count of surfaces `index` reports are two different numbers, and a map
    # that printed only the first would disagree with the statistics of the run
    # that wrote it.
    surfaces_not_read_in_full: int = 0
    clauses_by_type: dict[str, int] = field(default_factory=dict)
    clause_surfaces: int = 0
    deepest_nesting: int = 0
    deepest_fqn: str = ""
    edges_by_kind: dict[str, int] = field(default_factory=dict)
    pointers_by_subtype: dict[str, int] = field(default_factory=dict)
    pointers_in_code_fence: int = 0
    external_refs_by_sub_kind: dict[str, int] = field(default_factory=dict)
    identical_pairs: int = 0
    pairs_with_provenance: int = 0
    produces_by_evidence: dict[str, int] = field(default_factory=dict)
    pair_examples: list[tuple[str, str, str]] = field(default_factory=list)

    branch_state: history.BranchState | None = None

    @property
    def files_with_no_surface_kind(self) -> int:
        return self.files_walked - self.files_with_surface_kind

    @property
    def inferred_recognitions(self) -> int:
        """Files recognised by this tool's reading rather than by declaration."""
        return sum(
            self.recognition_by_kind.get(value, 0)
            for value in surfaces.INFERRED_RECOGNITIONS
        )

    @property
    def surface_rows(self) -> int:
        return sum(count for count, _, _ in self.surfaces_by_kind.values())

    @property
    def surface_files(self) -> int:
        return self.files_with_surface_kind

    @property
    def surfaces_read_in_full(self) -> int:
        """Rows read through -- the figure `index` reports as its surface count."""
        return self.surface_rows - self.surfaces_not_read_in_full

    @property
    def surface_bytes(self) -> int:
        return sum(size for _, _, size in self.surfaces_by_kind.values())

    @property
    def detectors_agree(self) -> bool:
        return self.graph_detector_version == self.build_detector_version


def _scoped(connection, sql: str, snapshot: list, extra: list | None = None) -> list:
    return connection.execute(sql, [*snapshot, *(extra or [])]).fetchall()


def read(repo: str | Path = ".", db_path: str | Path = store.DEFAULT_DB_PATH,
         base: str | None = None, session: str | None = None,
         environ=None) -> RepoMap:
    """Read one repository's snapshot out of the graph.

    ``repo`` is any path inside the repository; its git state selects the
    snapshot, exactly as ``show`` does.
    """
    found = repository(repo)
    if not Path(db_path).exists():
        raise RepoMapError(
            f"no context graph at {db_path}; run `orbit-context index` first"
        )
    snapshot = [found.project_id, found.branch, found.commit_sha]

    result = RepoMap(
        name=found.root.name,
        root=str(found.root),
        branch=found.branch,
        commit_sha=found.commit_sha,
        database_path=str(Path(db_path)),
    )

    connection = store.connect(db_path, read_only=True)
    try:
        try:
            run = _scoped(connection, _RUN_SQL, snapshot)
        except duckdb.CatalogException:
            raise RepoMapError(
                f"{db_path} holds no gl_context_run table; "
                f"run `orbit-context index` first"
            ) from None
        if not run:
            raise RepoMapError(
                f"no index run recorded for {found.root} at {found.commit_sha[:12]} "
                f"on {found.branch}; run `orbit-context index` first"
            )
        (result.indexed_root, result.graph_detector_version,
         result.excluded_directories, result.files_walked,
         result.files_with_surface_kind) = run[0]

        result.coverage_notes = [
            (reason, int(count), int(errored))
            for reason, count, errored in _scoped(connection, _COVERAGE_SQL, snapshot)
        ]
        _read_graph(connection, snapshot, result)
    finally:
        connection.close()

    result.branch_state = history.branch_state(
        found.root, base_override=base, session_override=session, environ=environ
    )
    return result


def _read_graph(connection, snapshot: list, result: RepoMap) -> None:
    """Fill in the counted sections, every detector present even at zero."""
    counted = {kind: (0, 0, 0) for kind in surfaces.SURFACE_KINDS}
    for kind, rows, files, size in _scoped(connection, _SURFACE_SQL, snapshot):
        counted[kind] = (int(rows), int(files), int(size or 0))
    result.surfaces_by_kind = counted
    result.surfaces_not_read_in_full = int(
        _scoped(connection, _SURFACE_UNREAD_SQL, snapshot)[0][0] or 0
    )

    result.recognition_by_kind = {
        value: 0 for value in surfaces.RECOGNITION_KINDS
    }
    for value, files in _scoped(connection, _RECOGNITION_SQL, snapshot):
        name = value if value in result.recognition_by_kind else RECOGNITION_NOT_RECORDED
        result.recognition_by_kind[name] = (
            result.recognition_by_kind.get(name, 0) + int(files)
        )

    result.clauses_by_type = {clause_type: 0 for clause_type in CLAUSE_TYPES}
    for clause_type, count in _scoped(connection, _CLAUSE_SQL, snapshot):
        result.clauses_by_type[clause_type] = int(count)
    result.clause_surfaces = int(
        _scoped(connection, _CLAUSE_SURFACE_SQL, snapshot)[0][0] or 0
    )

    deepest = _scoped(connection, _DEEPEST_SQL, snapshot + snapshot + snapshot)
    if deepest:
        result.deepest_fqn, depth = deepest[0]
        result.deepest_nesting = int(depth)

    result.edges_by_kind = {kind: 0 for kind in EDGE_KINDS}
    for kind, count in _scoped(connection, _EDGE_SQL, snapshot):
        result.edges_by_kind[kind] = int(count)

    result.pointers_by_subtype = {subtype: 0 for subtype in pointers.SUBTYPES}
    for subtype, count in _scoped(connection, _POINTER_SQL, snapshot):
        result.pointers_by_subtype[subtype] = int(count)
    result.pointers_in_code_fence = int(
        _scoped(connection, _FENCE_SQL, snapshot)[0][0] or 0
    )

    result.external_refs_by_sub_kind = {sub: 0 for sub in pointers.SUB_KINDS}
    for sub_kind, count in _scoped(connection, _EXTERNAL_SQL, snapshot):
        result.external_refs_by_sub_kind[sub_kind] = int(count)

    pairs, with_provenance = _scoped(connection, _IDENTICAL_SQL, snapshot)[0]
    result.identical_pairs = int(pairs or 0)
    result.pairs_with_provenance = int(with_provenance or 0)

    result.produces_by_evidence = {rung: 0 for rung in provenance.EVIDENCE_LADDER}
    for rung, count in _scoped(connection, _PRODUCES_SQL, snapshot):
        result.produces_by_evidence[rung] = int(count)

    result.pair_examples = [
        (first, second, producer or "")
        for first, second, producer in _scoped(
            connection, _PAIR_EXAMPLE_SQL, snapshot, [EXAMPLE_ROWS]
        )
    ]


def _snapshot(alias: str = "") -> str:
    """The three columns that select one indexed snapshot, for one table alias.

    Spelled once. Every query here is scoped to a single
    ``(project_id, branch, commit_sha)``: the graph holds every repository and
    branch that has been indexed, and a query that forgets the scope returns a
    number for the estate under a heading naming one repository.
    """
    prefix = f"{alias}." if alias else ""
    return " AND ".join(
        f"{prefix}{column} = ?"
        for column in ("project_id", "branch", "commit_sha")
    )


_SNAPSHOT = _snapshot()

_RUN_SQL = (
    "SELECT indexed_root, detector_set_version, excluded_directories, "
    "       files_walked, files_with_surface_kind "
    f"FROM gl_context_run WHERE {_SNAPSHOT}"
)

_COVERAGE_SQL = (
    "SELECT reason, count(*), "
    "       count(*) FILTER (WHERE errored) "
    f"FROM gl_context_coverage WHERE {_SNAPSHOT} "
    "GROUP BY 1 ORDER BY 2 DESC, 1"
)

_SURFACE_SQL = (
    "SELECT surface_kind, count(*), count(DISTINCT path), sum(size_bytes) "
    f"FROM gl_context_surface WHERE {_SNAPSHOT} GROUP BY 1"
)

# What a row written before `recognition` existed carries. Reported under its own
# name rather than dropped: a snapshot whose rows all fall outside the table
# would otherwise print an all-zero split beside a surface count that is not
# zero, which is the reading the zero-filled tally exists to prevent.
RECOGNITION_NOT_RECORDED = "not-recorded"

# Distinct files, not rows: a settings file holding four hooks was recognised
# once, and counting its rows would report one vendor name four times. This is
# the figure `files carrying a surface kind` above it counts, so the two add up.
_RECOGNITION_SQL = (
    "SELECT recognition, count(DISTINCT path) "
    f"FROM gl_context_surface WHERE {_SNAPSHOT} GROUP BY 1"
)

# A candidate that could not be read still becomes a row carrying its reason, so
# a row count is not a count of surfaces that were read.
_SURFACE_UNREAD_SQL = (
    "SELECT count(*) FROM gl_context_surface "
    f"WHERE COALESCE(reason, '') <> '' AND {_SNAPSHOT}"
)

_CLAUSE_SQL = (
    "SELECT clause_type, count(*) "
    f"FROM gl_context_clause WHERE {_SNAPSHOT} GROUP BY 1"
)

_CLAUSE_SURFACE_SQL = (
    f"SELECT count(DISTINCT surface_path) FROM gl_context_clause WHERE {_SNAPSHOT}"
)

# Depth is not a column -- a clause nested in another is an edge between them --
# so how deep the nesting goes is walked over CONTAINS at query time.
_DEEPEST_SQL = (
    "WITH RECURSIVE walk(id, depth) AS ("
    "  SELECT target_id, 1 FROM gl_context_edge "
    f"  WHERE relationship_kind = 'CONTAINS' AND source_kind = 'Surface' AND {_SNAPSHOT}"
    "  UNION ALL "
    "  SELECT e.target_id, walk.depth + 1 FROM gl_context_edge e "
    "    JOIN walk ON e.source_id = walk.id "
    f"  WHERE e.relationship_kind = 'CONTAINS' AND e.source_kind = 'Clause' AND {_snapshot('e')}"
    ") "
    "SELECT c.fqn, walk.depth FROM walk "
    f"  JOIN gl_context_clause c ON c.id = walk.id WHERE {_snapshot('c')} "
    "ORDER BY walk.depth DESC, c.fqn LIMIT 1"
)

_EDGE_SQL = (
    "SELECT relationship_kind, count(*) "
    f"FROM gl_context_edge WHERE {_SNAPSHOT} GROUP BY 1"
)

_POINTER_SQL = (
    "SELECT subtype, count(*) FROM gl_context_edge "
    f"WHERE relationship_kind = 'REFERENCES' AND {_SNAPSHOT} GROUP BY 1"
)

_FENCE_SQL = (
    "SELECT count(*) FROM gl_context_edge "
    f"WHERE relationship_kind = 'REFERENCES' AND in_code_fence AND {_SNAPSHOT}"
)

_EXTERNAL_SQL = (
    "SELECT sub_kind, count(*) "
    f"FROM gl_context_external_ref WHERE {_SNAPSHOT} GROUP BY 1"
)

# A pair count on its own over-reads, so it is never read without the count that
# carries provenance evidence. Both come out of one query for that reason.
_PAIRS_SUBQUERY = (
    "SELECT i.source_path, i.target_path, max(p.source_path) AS producer "
    "FROM gl_context_edge i "
    "LEFT JOIN gl_context_edge p "
    "  ON p.relationship_kind = 'PRODUCES' "
    " AND p.project_id = i.project_id AND p.branch = i.branch "
    " AND p.commit_sha = i.commit_sha "
    " AND p.target_path IN (i.source_path, i.target_path) "
    f"WHERE i.relationship_kind = 'IDENTICAL_BYTES' AND {_snapshot('i')} "
    "GROUP BY i.source_path, i.target_path"
)

_IDENTICAL_SQL = (
    "SELECT count(*), count(*) FILTER (WHERE producer IS NOT NULL) "
    f"FROM ({_PAIRS_SUBQUERY})"
)

_PAIR_EXAMPLE_SQL = (
    f"SELECT * FROM ({_PAIRS_SUBQUERY}) ORDER BY source_path, target_path LIMIT ?"
)

_PRODUCES_SQL = (
    "SELECT subtype, count(*) FROM gl_context_edge "
    f"WHERE relationship_kind = 'PRODUCES' AND {_SNAPSHOT} GROUP BY 1"
)


def _short(text: str, width: int = MAX_TEXT_WIDTH) -> str:
    """A path or address cut to a printable width, elided in the middle.

    The middle rather than the tail, because the two ends are what tell paths
    apart. Two files under one long directory prefix, cut from the right, print
    as the same string -- which turns a listing of distinct pairs into what
    looks like the same pair five times.
    """
    text = str(text)
    if len(text) <= width:
        return text
    head = (width - 1) // 2
    return text[:head] + "…" + text[head + 1 - width :]


def _percent(part: int, whole: int) -> str:
    return "0.0%" if not whole else f"{100 * part / whole:.1f}%"


def _heading(title: str, summary: str, version: str) -> str:
    """A section heading carrying the detector set its counts came from.

    Repeated per section rather than stated once, because a count is quoted out
    of a map into a ticket one section at a time, and a count that arrives
    somewhere without its detector version cannot be compared with a later one.
    """
    return f"\n{title}  {summary}  [{version}]"


def _rows(pairs, indent: str = "  ") -> list[str]:
    """Aligned ``name  count`` lines, every entry printed including zeroes."""
    if not pairs:
        return [f"{indent}(none)"]
    width = max(len(str(name)) for name, _ in pairs)
    return [f"{indent}{str(name):<{width}}  {value}" for name, value in pairs]


def _boundary(result: RepoMap) -> list[str]:
    lines = [
        "\nBOUNDARY",
        f"  indexed root   {_short(result.indexed_root, 72)}",
        f"  never entered  {result.excluded_directories}",
        f"  files walked   {result.files_walked}",
    ]
    total = sum(count for _, count, _ in result.coverage_notes)
    lines.append(f"  read in part   {total}")
    for reason, count, errored in result.coverage_notes[:8]:
        suffix = f", {errored} on a read failure" if errored else ""
        lines.append(f"                   {count}  {reason}{suffix}")
    return lines


def _coverage(result: RepoMap) -> list[str]:
    return [
        _heading("COVERAGE", "what these detectors recognise",
                 result.graph_detector_version),
        f"  files carrying a surface kind     {result.files_with_surface_kind}"
        f" of {result.files_walked} ({_percent(result.files_with_surface_kind, result.files_walked)})",
        f"  files carrying no surface kind    {result.files_with_no_surface_kind}",
        "  Every count below is of what this detector set looks for. A low count",
        "  is a statement about these detectors, not a description of the estate.",
        "",
        "  recognised by",
        *_rows(list(result.recognition_by_kind.items()), indent="    "),
        f"  of which read off a directory rather than stated by the estate:"
        f" {result.inferred_recognitions}",
    ]


def _surfaces(result: RepoMap) -> list[str]:
    lines = [
        _heading("SURFACES",
                 f"{result.surface_rows} rows across {result.surface_files} files, "
                 f"{result.surface_bytes} bytes",
                 result.graph_detector_version)
    ]
    lines.append(
        f"  read in full  {result.surfaces_read_in_full} of {result.surface_rows} rows"
    )
    width = max(len(kind) for kind in result.surfaces_by_kind)
    for kind, (rows, files, size) in result.surfaces_by_kind.items():
        lines.append(f"  {kind:<{width}}  {rows:>4} rows  {files:>4} files  {size:>8} bytes")
    return lines


def _clauses(result: RepoMap) -> list[str]:
    total = sum(result.clauses_by_type.values())
    lines = [
        _heading("CLAUSES", f"{total} in {result.clause_surfaces} surfaces",
                 result.graph_detector_version)
    ]
    lines += _rows(list(result.clauses_by_type.items()))
    nesting = f"  deepest nesting  {result.deepest_nesting}"
    if result.deepest_fqn:
        nesting += f"  {_short(result.deepest_fqn)}"
    lines.append(nesting)
    return lines


def _edges(result: RepoMap) -> list[str]:
    total = sum(result.edges_by_kind.values())
    lines = [_heading("EDGES", str(total), result.graph_detector_version)]
    return lines + _rows(list(result.edges_by_kind.items()))


def _pointers(result: RepoMap) -> list[str]:
    total = sum(result.pointers_by_subtype.values())
    lines = [
        _heading("POINTERS", f"{total} REFERENCES edges, "
                             f"{result.pointers_in_code_fence} written inside a fenced block",
                 result.graph_detector_version)
    ]
    return lines + _rows(list(result.pointers_by_subtype.items()))


def _external(result: RepoMap) -> list[str]:
    total = sum(result.external_refs_by_sub_kind.values())
    lines = [
        _heading("ADDRESSES THAT DID NOT RESOLVE", f"{total} addresses",
                 result.graph_detector_version)
    ]
    lines += _rows(list(result.external_refs_by_sub_kind.items()))
    lines.append("  Never merged: each names something this detector set could not see.")
    return lines


def _identical(result: RepoMap, examples: bool) -> list[str]:
    without = result.identical_pairs - result.pairs_with_provenance
    lines = [
        _heading("IDENTICAL BYTES", f"{result.identical_pairs} pairs",
                 result.graph_detector_version),
        f"  carrying provenance evidence     {result.pairs_with_provenance}",
        f"  carrying no provenance evidence  {without}",
    ]
    lines += _rows(list(result.produces_by_evidence.items()), indent="  PRODUCES ")
    if examples and result.pair_examples:
        for first, second, producer in result.pair_examples:
            named = f"  <- {_short(producer, 44)}" if producer else ""
            lines.append(f"    {_short(first, 44)} = {_short(second, 44)}{named}")
        remaining = result.identical_pairs - len(result.pair_examples)
        if remaining > 0:
            lines.append(f"    {remaining} more pairs not listed")
    return lines


def _git(result: RepoMap) -> list[str]:
    state = result.branch_state
    lines = ["\nGIT  (git state, not a detector finding)"]
    if state is None or state.unavailable:
        detail = state.unavailable if state else "no branch state was read"
        return lines + [f"  git could not answer: {_short(detail, 72)}"]

    if state.base.ref is None:
        lines.append(f"  base            none  ({state.base.source})")
        lines.append("  commits ahead   not measured, because no base resolved")
    else:
        lines.append(f"  base            {state.base.ref}  (from {state.base.source})")
        lines.append(f"  commits ahead   {state.ahead}")
        lines.append(f"    carrying a {history.TRAILER_KEY} trailer  {state.with_trailer}")
        counted = state.this_session
        if counted is None:
            # Not zero. An id the environment never supplied leaves the question
            # unmeasured, and a zero here reads as "none of these are mine" --
            # the exact inversion this section exists to prevent.
            lines.append(
                "    carrying this session's trailer  not measured: no session id in "
                + " or ".join(history.SESSION_VARIABLES)
            )
        elif counted:
            names = ", ".join(state.matched_variables())
            lines.append(f"    carrying this session's trailer  {counted}  (id from {names})")
        else:
            names = ", ".join(name for name, _ in state.session.identifiers)
            lines.append(
                f"    carrying this session's trailer  0  (no trailer carries the id in {names})"
            )
        for value, count in state.by_trailer()[:EXAMPLE_ROWS]:
            lines.append(f"      {count:>4}  {_short(value, 56)}")
    return lines


def _body(result: RepoMap, examples: bool) -> str:
    lines = [
        "orbit-context repo-map",
        f"  repository   {result.name}  {_short(result.root, 60)}",
        f"  branch       {result.branch}",
        f"  commit       {result.commit_sha[:12]}",
        f"  detectors    {result.graph_detector_version}",
        f"  graph        {_short(result.database_path, 60)}",
    ]
    if not result.detectors_agree:
        lines.append(
            f"  The graph was written by detector set {result.graph_detector_version}; "
            f"this build is {result.build_detector_version}."
        )
        lines.append(
            "  Every count below is what that detector set found, not what this one would."
        )
    lines += _boundary(result)
    lines += _coverage(result)
    lines += _surfaces(result)
    lines += _clauses(result)
    lines += _edges(result)
    lines += _pointers(result)
    lines += _external(result)
    lines += _identical(result, examples)
    lines += _git(result)
    return "\n".join(lines) + "\n"


def _with_footer(body: str, budget: int) -> str:
    """Append the line that reports the map's own size, counting itself.

    Self-accounting, on the same argument spec 0001 makes for the tool's managed
    section: a command that reports what governance costs and does not report
    its own cost is exempting itself from its own measurement. The size includes
    the footer, so the number is the number, which takes a couple of rounds to
    settle when adding it grows a digit.
    """
    measured = len(body.encode("utf-8"))
    total = measured
    for _ in range(5):
        footer = (
            f"\nmap {total} bytes of {budget} budget ({BUDGET_CITATION})\n"
        )
        settled = measured + len(footer.encode("utf-8"))
        if settled == total:
            break
        total = settled
    return body + footer


def render(result: RepoMap, budget: int = BUDGET_BYTES) -> str:
    """The map as text, inside the budget.

    The budget is held by construction: every section but two is a fixed
    inventory of detectors, and the two that list rows are capped. The retry
    below is the guarantee rather than the mechanism -- if a repository ever
    finds a way past the caps, the map drops its listings and says so instead of
    quietly exceeding the figure it just printed.
    """
    rendered = _with_footer(_body(result, examples=True), budget)
    if len(rendered.encode("utf-8")) <= budget:
        return rendered
    trimmed = _body(result, examples=False).rstrip("\n")
    trimmed += "\n  Example listings left out: the full map exceeded its budget.\n"
    return _with_footer(trimmed, budget)


def repo_map(repo: str | Path = ".", db_path: str | Path = store.DEFAULT_DB_PATH,
             base: str | None = None, session: str | None = None,
             environ=None, budget: int = BUDGET_BYTES) -> str:
    """Read one repository's snapshot and render it."""
    return render(read(repo, db_path, base=base, session=session, environ=environ),
                  budget=budget)
