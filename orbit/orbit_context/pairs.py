"""Byte-identical pairs, read out of the graph with the direction each carries.

On the estate this tool was built for, every one of 28 byte-identical pairs is a
workbench file matching a published file:

    _rule-workbench/refactoring/nano.md = refactoring/refactoring.nano.md
    _rule-workbench/clean-code/mini.md  = clean-code/clean-code.mini.md

One pipeline run 28 times, and a human reads the direction off the paths in ten
seconds. This command prints all of them, each with the direction the evidence
supports or an explicit UNKNOWN and the reason there is none.

Why the reason is on every line
-------------------------------

Byte identity is symmetric. A pair on its own says two files are the same bytes
and nothing about which came first, and ticket 05 already established that a
bare pair count over-reads badly. The direction is the same problem one level
in: printing a direction where there is one and a blank where there is not turns
"nothing here evidences an order" into something a reader fills in themselves.
So the block never prints a pair count without the count carrying provenance
beside it, and never prints a pair without a direction or a stated reason.

The reasons stay apart
----------------------

Three of them, never summed. A pair nothing evidences at all, a pair whose
producer is a third file, and a pair whose two ends each name the other are
three different statements about the estate. The second is the one worth the
separation: those pairs *have* provenance -- ticket 05's count sees them -- and
still nothing that orders them, so counting them with the pairs no evidence
reaches would be untrue about both.

Everything comes from the graph
-------------------------------

Nothing here re-walks the tree, on ``repo-map``'s argument: a second walk at
query time is a second answer to "what is in this repository", taken against a
tree that has moved on since indexing. One snapshot, one
``(project_id, branch, commit_sha)``, every figure from a row -- and
:func:`from_graph` is shared with ``repo-map`` so the map and this command
answer the question once rather than twice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import duckdb

from . import detectors, provenance, store
from .retrieve import repository

# What a direction is read off, printed with the count at every value including
# zero. A pair is ordered by a PRODUCES edge between its own two ends and by
# nothing else, and saying so beside the number is what stops the number being
# read as "these are the only pairs with an order".
DIRECTION_RULE = (
    "a PRODUCES edge between the pair's own two ends, on the strongest rung "
    "found for it"
)

DIRECTION_RULE_CAVEAT = (
    "A producer elsewhere in the tree does not order a pair, and neither does a\n"
    "  sentence. Spec 0001 section 14 keeps prose provenance a permanent UNKNOWN:\n"
    "  a direction read out of a sentence would be indistinguishable here from one\n"
    "  something observed."
)


class PairsError(Exception):
    """The graph holds no snapshot to read pairs from."""


@dataclass(frozen=True)
class Pairing:
    """One byte-identical pair as the graph holds it, direction included."""

    source_path: str
    target_path: str
    content_sha256: str
    direction: str
    reason: str | None = None
    evidence: str | None = None
    evidence_path: str | None = None
    evidence_line: int | None = None

    @property
    def ordered(self) -> bool:
        return self.direction != provenance.DIRECTION_UNKNOWN

    @property
    def producer_path(self) -> str | None:
        """The end the evidence puts first, or None where nothing ordered it."""
        if not self.ordered:
            return None
        return (self.source_path
                if self.direction == provenance.SOURCE_PRODUCES_TARGET
                else self.target_path)

    @property
    def artifact_path(self) -> str | None:
        if not self.ordered:
            return None
        return (self.target_path
                if self.direction == provenance.SOURCE_PRODUCES_TARGET
                else self.source_path)

    @property
    def locator(self) -> str:
        """Where the direction was read from, so the claim can be checked."""
        if self.evidence_path is None:
            return ""
        return f"{self.evidence_path}:{self.evidence_line}"


@dataclass
class PairReading:
    """Every byte-identical pair in one snapshot, with its direction."""

    name: str
    root: str
    branch: str
    commit_sha: str
    database_path: str
    graph_detector_version: str = ""
    build_detector_version: str = detectors.VERSION
    pairs: list[Pairing] = field(default_factory=list)

    @property
    def with_a_direction(self) -> int:
        return sum(1 for one in self.pairs if one.ordered)

    @property
    def with_provenance(self) -> int:
        """Ticket 05's count, derived from the reasons rather than re-asked.

        A pair carries provenance where a producer reaches either end, which is
        exactly a pair whose reason is not "no producer named at either end".
        Derived here so the map, this command and the index statistics cannot
        come apart on it.
        """
        return len(self.pairs) - sum(
            1 for one in self.pairs
            if one.reason == provenance.NO_PRODUCER_AT_EITHER_END
        )

    @property
    def by_reason(self) -> dict[str, int]:
        counts = {reason: 0 for reason in provenance.DIRECTION_UNKNOWN_REASONS}
        for one in self.pairs:
            if one.reason is not None:
                counts[one.reason] += 1
        return counts

    @property
    def by_direction_evidence(self) -> dict[str, int]:
        counts = {rung: 0 for rung in provenance.EVIDENCE_LADDER}
        for one in self.pairs:
            if one.ordered and one.evidence is not None:
                counts[one.evidence] += 1
        return counts

    @property
    def detectors_agree(self) -> bool:
        return self.graph_detector_version == self.build_detector_version


def _snapshot() -> str:
    return " AND ".join(
        f"{column} = ?" for column in ("project_id", "branch", "commit_sha")
    )


_SNAPSHOT = _snapshot()

_RUN_SQL = f"SELECT detector_set_version FROM gl_context_run WHERE {_SNAPSHOT}"

_PAIRS_SQL = (
    "SELECT source_path, target_path, content_sha256, direction, "
    "direction_reason, subtype, evidence_path, evidence_line "
    "FROM gl_context_edge "
    f"WHERE relationship_kind = '{provenance.IDENTICAL_BYTES_EDGE}' "
    f"AND {_SNAPSHOT} ORDER BY source_path, target_path"
)


def from_graph(connection, snapshot: list) -> list[Pairing]:
    """One snapshot's pairs, in path order, as the rows hold them.

    Takes an open connection rather than a path so that a caller already reading
    the graph -- ``repo-map`` -- gets the same answer this module's own command
    does. Two queries for one question is how a map and a command end up
    disagreeing about a count with no way to tell which is right.
    """
    return [
        Pairing(
            source_path=source,
            target_path=target,
            content_sha256=sha256 or "",
            direction=direction or provenance.DIRECTION_UNKNOWN,
            reason=reason,
            evidence=evidence,
            evidence_path=evidence_path,
            evidence_line=None if evidence_line is None else int(evidence_line),
        )
        for (source, target, sha256, direction, reason, evidence,
             evidence_path, evidence_line)
        in connection.execute(_PAIRS_SQL, snapshot).fetchall()
    ]


def read(repo: str | Path = ".",
         db_path: str | Path = store.DEFAULT_DB_PATH) -> PairReading:
    """Read one repository's byte-identical pairs out of the graph.

    ``repo`` is any path inside the repository; its git state selects the
    snapshot, exactly as ``show``, ``repo-map`` and ``ladder`` do.
    """
    found = repository(repo)
    if not Path(db_path).exists():
        raise PairsError(
            f"no context graph at {db_path}; run `orbit-context index` first"
        )
    snapshot = [found.project_id, found.branch, found.commit_sha]

    result = PairReading(
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
            raise PairsError(
                f"{db_path} holds no gl_context_run table; "
                f"run `orbit-context index` first"
            ) from None
        if not run:
            raise PairsError(
                f"no index run recorded for {found.root} at {found.commit_sha[:12]} "
                f"on {found.branch}; run `orbit-context index` first"
            )
        result.graph_detector_version = run[0][0]
        result.pairs = from_graph(connection, snapshot)
    finally:
        connection.close()
    return result


def summary_lines(found: list[Pairing], version: str, limit: int | None = None,
                  shorten=None) -> list[str]:
    """The IDENTICAL BYTES block, shared with ``repo-map``.

    ``limit`` caps the pairs listed, for a caller printing inside a budget, and
    ``0`` drops the listing entirely. The counts above them are never capped:
    what is dropped is the listing, and the line saying how many were dropped is
    part of the block rather than the caller's to remember.

    ``shorten`` cuts a path to a printable width for the same caller.
    """
    reading = PairReading("", "", "", "", "", graph_detector_version=version,
                          pairs=found)
    lines = [
        f"\nIDENTICAL BYTES  {len(found)} pairs  [{version}]",
        f"  carrying provenance evidence     {reading.with_provenance}",
        f"  carrying no provenance evidence  {len(found) - reading.with_provenance}",
        f"  carrying a direction             {reading.with_a_direction}",
        f"  read off  {DIRECTION_RULE}",
        f"  {DIRECTION_RULE_CAVEAT}",
        "  by evidence rung",
    ]
    lines += [f"    {rung}  {count}"
              for rung, count in reading.by_direction_evidence.items()]
    lines.append("  carrying no direction, by reason")
    lines += [f"    {reason}  {count}"
              for reason, count in reading.by_reason.items()]

    listed = found if limit is None else found[:limit]
    if listed:
        # Headed, because the reason rows above it are indented the same and a
        # reader scanning down would otherwise read the first pair as a fourth
        # reason.
        lines.append("  pair by pair")
    lines += [f"    {_line(one, shorten)}" for one in listed]
    if len(listed) < len(found):
        lines.append(f"    {len(found) - len(listed)} more pairs not listed")
    return lines


def _line(one: Pairing, shorten=None) -> str:
    """One pair, and what is known about which end came first.

    The direction is spelled with the paths rather than with the row's own
    ``source``/``target`` words: a reader is looking at two paths, and being
    told "source-produces-target" makes them work out which is which.
    """
    cut = shorten or (lambda path: path)
    pair = f"{cut(one.source_path)} = {cut(one.target_path)}"
    if not one.ordered:
        return f"{pair}  {one.direction}: {one.reason}"
    return (f"{pair}  {cut(one.producer_path)} produces "
            f"{cut(one.artifact_path)}  [{one.evidence} {one.locator}]")


def render(reading: PairReading) -> str:
    """The reading as text: the header, then the block with every pair listed."""
    lines = [
        "orbit-context pairs",
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
    lines += summary_lines(reading.pairs, reading.graph_detector_version)
    return "\n".join(lines) + "\n"


def pairs(repo: str | Path = ".",
          db_path: str | Path = store.DEFAULT_DB_PATH) -> str:
    """One repository's byte-identical pairs, with their directions, as text."""
    return render(read(repo, db_path))
