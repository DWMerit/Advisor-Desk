"""One book's ladder, read out of the graph: its rungs, in size order.

Progressive disclosure of rules is the stated purpose of this whole estate, and
it was built by hand before Orbit existed -- fourteen books, each written three
times at three sizes, so a session loads the rung its workflow can afford:

    refactoring/refactoring.md       17866
    refactoring/refactoring.mini.md   5167
    refactoring/refactoring.nano.md   1986

Until the ``RUNG_OF`` edge those were fourteen sets of three unrelated files.
This is the query that walks the edge back.

Everything comes from the graph
-------------------------------

Nothing here re-walks the tree, on ``repo-map``'s argument: a second walk at
query time is a second answer to "what is in this repository", taken against a
tree that has moved on since indexing, and the sizes printed would not be the
sizes anything else was measured against. One snapshot, one
``(project_id, branch, commit_sha)``, every figure from a row.

What this command cannot say, and says instead
----------------------------------------------

**Which rung a session actually loaded.** That needs the load ledger, which is
Candidate A and still gated (spec 0001 s6). It is printed as UNKNOWN with the
reason named, never as a zero -- spec 0001 s9's rule that an unobservable
quantity must not improve a number by being unobservable.

**That a shorter rung was derived from a longer one.** The edge relates two
filenames and nothing else. Where the estate evidences a derivation, PRODUCES
carries it; where only prose says so, spec 0001 s14 keeps it a permanent
UNKNOWN.

**That a repository has no ladders.** What can be said is that none were
*found*, by a rule that keys on one repository's naming convention. So the rule
is printed with the count, at zero as well as above it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

import duckdb

from . import detectors, store, surfaces
from .retrieve import repository

RUNG_OF_EDGE = "RUNG_OF"

# This tool's word for the file named by the stem alone. It carries no rung word
# of its own, so unlike `mini` and `nano` this one is not the estate's word --
# which is why it is spelled once, here, rather than written into a row.
BASE_RUNG = "base"

# What the ladders were keyed on, built from the table in `surfaces` so a rung
# word added there reaches this sentence and the detector set version together.
LADDER_RULE = (
    f"<stem>{surfaces.RUNG_SUFFIX} beside "
    + " or ".join(
        f"<stem>.{word}{surfaces.RUNG_SUFFIX}" for word in surfaces.RUNG_WORDS
    )
    + ", in one directory"
)

# Printed wherever a ladder is, at every count including zero.
LADDER_RULE_CAVEAT = (
    "That is this repository's naming convention, not a standard. A repository\n"
    "  naming its rungs otherwise has no ladders found here, which is not the\n"
    "  same statement as no ladders."
)

# The one figure this command is asked for and cannot answer.
RUNG_LOADED_UNKNOWN = (
    "UNKNOWN: which rung a session loaded needs the load ledger, and spec 0001 "
    "section 6 keeps it gated (Candidate A)"
)


class LadderError(Exception):
    """The graph holds no snapshot to read ladders from."""


@dataclass(frozen=True)
class Rung:
    """One file of a ladder, and the word its name carries."""

    path: str
    rung: str
    size_bytes: int


@dataclass(frozen=True)
class Ladder:
    """One base rung and the rungs whose names point at it, in size order."""

    base_path: str
    rungs: tuple[Rung, ...]

    @property
    def stem(self) -> str:
        return PurePosixPath(self.base_path).name.removesuffix(surfaces.RUNG_SUFFIX)

    @property
    def directory(self) -> str:
        return PurePosixPath(self.base_path).parent.as_posix()

    @property
    def total_bytes(self) -> int:
        return sum(rung.size_bytes for rung in self.rungs)


@dataclass
class LadderReading:
    """Every ladder in one snapshot, and the rungs that reach none of them."""

    name: str
    root: str
    branch: str
    commit_sha: str
    database_path: str
    graph_detector_version: str = ""
    build_detector_version: str = detectors.VERSION
    ladders: list[Ladder] = field(default_factory=list)
    # Rung words whose base rung is not a surface in this snapshot. Named rather
    # than dropped: a rung the estate wrote and this tool could not attach is not
    # the same as a rung never written.
    rungs_with_no_base_rung: list[str] = field(default_factory=list)

    @property
    def rungs(self) -> int:
        return sum(len(one.rungs) for one in self.ladders)

    @property
    def detectors_agree(self) -> bool:
        return self.graph_detector_version == self.build_detector_version


def _snapshot(alias: str = "") -> str:
    prefix = f"{alias}." if alias else ""
    return " AND ".join(
        f"{prefix}{column} = ?"
        for column in ("project_id", "branch", "commit_sha")
    )


_SNAPSHOT = _snapshot()

_RUN_SQL = f"SELECT detector_set_version FROM gl_context_run WHERE {_SNAPSHOT}"

_RUNG_SQL = (
    "SELECT source_path, target_path, subtype FROM gl_context_edge "
    f"WHERE relationship_kind = '{RUNG_OF_EDGE}' AND {_SNAPSHOT} "
    "ORDER BY target_path, source_path"
)

# One size per path. A settings file holds a row per hook and would answer this
# several times, so the rows are folded to the file they were read from -- and a
# rung is a whole file, so the file's own size is the figure either way.
_SIZE_SQL = (
    "SELECT path, max(size_bytes) FROM gl_context_surface "
    f"WHERE {_SNAPSHOT} GROUP BY path"
)


def from_graph(connection, snapshot: list) -> tuple[list[Ladder], list[str]]:
    """One snapshot's ladders, and the rungs that reach none of them.

    Takes an open connection rather than a path so that a caller already
    reading the graph -- ``repo-map`` -- gets the same two answers this
    module's own command does. Two queries for one question is how a map and a
    command end up disagreeing about a count with no way to tell which is
    right.
    """
    edges = connection.execute(_RUNG_SQL, snapshot).fetchall()
    sizes = dict(connection.execute(_SIZE_SQL, snapshot).fetchall())
    # Read off the surface paths this snapshot holds, not off the tree. A rung
    # with no base rung has no edge to walk -- an edge needs both ends -- so the
    # only place it can be seen is the names of the rows themselves.
    #
    # This is the one figure here re-derived at read time rather than written by
    # the run, so on a snapshot written by another detector set it is this
    # build's answer over that run's rows. Both versions are in the header for
    # exactly that case, and `index` records its own count beside the rows.
    without_a_base = sorted(
        path for path in sizes
        if (named := surfaces.rung_of(path)) is not None and named[0] not in sizes
    )
    return _assemble(edges, sizes), without_a_base


def read(repo: str | Path = ".",
         db_path: str | Path = store.DEFAULT_DB_PATH) -> LadderReading:
    """Read one repository's ladders out of the graph.

    ``repo`` is any path inside the repository; its git state selects the
    snapshot, exactly as ``show`` and ``repo-map`` do.
    """
    found = repository(repo)
    if not Path(db_path).exists():
        raise LadderError(
            f"no context graph at {db_path}; run `orbit-context index` first"
        )
    snapshot = [found.project_id, found.branch, found.commit_sha]

    result = LadderReading(
        name=found.root.name,
        root=str(found.root),
        branch=found.branch,
        commit_sha=found.commit_sha,
        database_path=str(Path(db_path)),
    )

    connection = store.connect(db_path, read_only=True)
    try:
        try:
            run = connection.execute(_RUN_SQL, snapshot).fetchall()
        except duckdb.CatalogException:
            raise LadderError(
                f"{db_path} holds no gl_context_run table; "
                f"run `orbit-context index` first"
            ) from None
        if not run:
            raise LadderError(
                f"no index run recorded for {found.root} at {found.commit_sha[:12]} "
                f"on {found.branch}; run `orbit-context index` first"
            )
        result.graph_detector_version = run[0][0]
        result.ladders, result.rungs_with_no_base_rung = from_graph(
            connection, snapshot
        )
    finally:
        connection.close()
    return result


def _assemble(edges: list[tuple], sizes: dict[str, int]) -> list[Ladder]:
    """Group the edges by the base rung they enter, largest rung first.

    Size order rather than rung order: how big a rung is, is measured, and which
    word its name carries is not an ordering the estate stated anywhere. Where
    two rungs are the same size the path decides, so the answer is stable.
    """
    by_base: dict[str, list[Rung]] = {}
    for source_path, target_path, subtype in edges:
        rungs = by_base.setdefault(
            target_path,
            [Rung(target_path, BASE_RUNG, int(sizes.get(target_path, 0)))],
        )
        rungs.append(Rung(source_path, subtype or "", int(sizes.get(source_path, 0))))
    return [
        Ladder(base, tuple(sorted(rungs, key=lambda rung: (-rung.size_bytes, rung.path))))
        for base, rungs in sorted(by_base.items())
    ]


def find(reading: LadderReading, name: str) -> list[Ladder]:
    """The ladders one name asks for.

    A book is asked for the way it is talked about -- ``refactoring`` -- and the
    graph addresses it by the base rung's path. Both are accepted, along with the
    directory and the filename, because all four name the same thing and which
    one a caller has to hand is not a decision worth making them take.
    """
    wanted = name.strip().strip("/")
    return [
        one for one in reading.ladders
        if wanted in (one.base_path, one.stem, one.directory,
                      PurePosixPath(one.base_path).name)
    ]


def render(reading: LadderReading, chosen: list[Ladder]) -> str:
    """The reading as text: the summary first, then each ladder rung by rung."""
    lines = [
        "orbit-context ladder",
        f"  repository   {reading.name}  {reading.root}",
        f"  branch       {reading.branch}",
        f"  commit       {reading.commit_sha[:12]}",
        f"  detectors    {reading.graph_detector_version}",
        f"  graph        {reading.database_path}",
    ]
    if not reading.detectors_agree:
        lines.append(
            f"  The graph was written by detector set "
            f"{reading.graph_detector_version}; this build is "
            f"{reading.build_detector_version}."
        )
        lines.append(
            "  Every count below is what that detector set found, not what this "
            "one would."
        )
    lines += summary_lines(
        reading.ladders, reading.rungs_with_no_base_rung,
        reading.graph_detector_version,
    )
    lines += _rungs(chosen)
    return "\n".join(lines) + "\n"


def summary_lines(found: list[Ladder], without_a_base: list[str], version: str,
                  limit: int | None = None, shorten=None) -> list[str]:
    """The LADDERS block, shared with ``repo-map``.

    ``limit`` caps the rungs named at the end, for a caller printing inside a
    budget, and ``0`` drops the listing entirely. The count above them is never
    capped: what is dropped is the listing, and the line that says how many were
    dropped is part of the block rather than the caller's to remember.

    ``shorten`` cuts a path to a printable width for the same caller. A single
    very long path must not be able to push a map over the budget it printed on
    its own last line.
    """
    heights: dict[int, int] = {}
    for one in found:
        heights[len(one.rungs)] = heights.get(len(one.rungs), 0) + 1
    rungs = sum(len(one.rungs) for one in found)
    lines = [
        f"\nLADDERS  {len(found)} found, {rungs} rungs  [{version}]",
        f"  keyed on  {LADDER_RULE}",
        f"  {LADDER_RULE_CAVEAT}",
        "  rungs per ladder",
    ]
    if heights:
        # How many rungs a book carries is an observation. A book at two is
        # reported at the height it has, beside the books at three.
        lines += [
            f"    {height} rungs  {heights[height]}" for height in sorted(heights)
        ]
    else:
        lines.append("    (none)")
    lines.append(f"  which rung this session loaded  {RUNG_LOADED_UNKNOWN}")
    lines.append(
        f"  rung words with no base rung beside them  {len(without_a_base)}"
    )
    # Named, because an edge needs both ends and these have one. A count on its
    # own would read as a defect rather than as what the estate wrote.
    named = without_a_base if limit is None else without_a_base[:limit]
    cut = shorten or (lambda path: path)
    lines += [f"    {cut(path)}" for path in named]
    if len(named) < len(without_a_base):
        lines.append(f"    {len(without_a_base) - len(named)} more not listed")
    return lines


def _rungs(chosen: list[Ladder]) -> list[str]:
    lines: list[str] = []
    for one in chosen:
        lines.append(
            f"\n{one.base_path}  {len(one.rungs)} rungs, {one.total_bytes} bytes"
        )
        width = max(len(rung.path) for rung in one.rungs)
        for rung in one.rungs:
            lines.append(
                f"  {rung.size_bytes:>8}  {rung.path:<{width}}  {rung.rung}"
            )
    return lines


def ladder(repo: str | Path = ".", db_path: str | Path = store.DEFAULT_DB_PATH,
           name: str | None = None) -> str:
    """One repository's ladders, or the one a name asks for, as text."""
    reading = read(repo, db_path)
    if name is None:
        return render(reading, reading.ladders)
    chosen = find(reading, name)
    if not chosen:
        raise LadderError(
            f"no ladder in {reading.name} at {reading.commit_sha[:12]} is named "
            f"{name!r}. Ladders are keyed on {LADDER_RULE}, and this snapshot "
            f"holds {len(reading.ladders)} of them"
            + (": " + ", ".join(one.stem for one in reading.ladders[:10])
               if reading.ladders else "")
        )
    return render(reading, chosen)
