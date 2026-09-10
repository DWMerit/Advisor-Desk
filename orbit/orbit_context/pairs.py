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

And a fourth state, which is not a reason
-----------------------------------------

A row written before the direction existed carries NULL in these columns. That
is not UNKNOWN: UNKNOWN is a measurement, and this is the absence of one. It is
counted under :data:`NOT_MEASURED` and left out of both provenance counts, so a
snapshot from an older detector set cannot read as an estate where every pair
turned out to have a producer. The header's detector-version banner says the
same thing in prose; this is the number saying it.

Everything comes from the graph
-------------------------------

Nothing here re-walks the tree, on ``repo-map``'s argument: a second walk at
query time is a second answer to "what is in this repository", taken against a
tree that has moved on since indexing. One snapshot, one
``(project_id, branch, commit_sha)``, every figure from a row.

The counts come from a ``GROUP BY`` and the listing from an ``ORDER BY ... LIMIT``,
both defined here, because a caller printing five example pairs must not have to
fetch every pair to count them -- pairing is quadratic inside a hash group, so a
repository with five hundred identical files holds a hundred and twenty-four
thousand pairs and ``repo-map`` still prints five. Two statements, one owner:
what ticket 11 refuses is two *derivations* of one number living in two modules,
which is how a map and a command end up disagreeing with no way to tell which is
right.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import duckdb

from . import detectors, provenance, store
from .retrieve import repository

# A pair whose row predates the direction. Not a reason -- the run did not
# measure one -- so it is named apart from the three reasons a run *did* measure
# and found nothing to order the pair with.
NOT_MEASURED = "not-measured"

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

# Said where a snapshot holds rows from before the direction existed, and only
# there. A store in that state is resolved by a command, so the command is
# named rather than left to be worked out.
NOT_MEASURED_REMEDY = (
    "written by a run that recorded no direction. Re-index the repository to "
    "measure them."
)


class PairsError(Exception):
    """The graph holds no snapshot to read pairs from, or holds an older one."""


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
    def measured(self) -> bool:
        return self.direction != NOT_MEASURED

    @property
    def ordered(self) -> bool:
        return self.direction in provenance.DIRECTIONS

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
class PairCounts:
    """How one snapshot's pairs divide, however they were counted.

    Built either from a list of :class:`Pairing` or from a ``GROUP BY``, so a
    caller that needs the numbers without the rows gets the same arithmetic.
    Every reason and every rung is present at zero; a value this build does not
    know is added rather than dropped, because it was read off a row and a
    vocabulary this build has not seen is a finding rather than a crash.
    """

    total: int = 0
    with_a_direction: int = 0
    not_measured: int = 0
    by_reason: dict[str, int] = field(
        default_factory=lambda: {
            reason: 0 for reason in provenance.DIRECTION_UNKNOWN_REASONS
        }
    )
    by_direction_evidence: dict[str, int] = field(
        default_factory=lambda: {rung: 0 for rung in provenance.EVIDENCE_LADDER}
    )

    @property
    def with_provenance(self) -> int:
        """Ticket 05's count: a pair a producer reaches at either end.

        Stated positively -- ordered pairs, plus the pairs whose reason names a
        producer somewhere -- rather than as "everything but one reason". A row
        that carries no reason at all is not a pair with provenance, and
        negative logic would count it as one.
        """
        return self.with_a_direction + sum(
            count for reason, count in self.by_reason.items()
            if reason != provenance.NO_PRODUCER_AT_EITHER_END
        )

    @property
    def without_provenance(self) -> int:
        return self.by_reason.get(provenance.NO_PRODUCER_AT_EITHER_END, 0)

    def add(self, direction: str | None, reason: str | None,
            evidence: str | None, count: int = 1) -> None:
        """Tally one row, or ``count`` rows that share these three values."""
        self.total += count
        if direction is None:
            self.not_measured += count
            return
        if direction in provenance.DIRECTIONS:
            self.with_a_direction += count
            if evidence is not None:
                self.by_direction_evidence[evidence] = (
                    self.by_direction_evidence.get(evidence, 0) + count
                )
            return
        # UNKNOWN, or a direction value this build has not seen. Either way the
        # reason is what the row has to say about it.
        key = reason if reason is not None else NOT_MEASURED
        self.by_reason[key] = self.by_reason.get(key, 0) + count

    @classmethod
    def of(cls, found: list[Pairing]) -> PairCounts:
        counts = cls()
        for one in found:
            counts.add(
                None if not one.measured else one.direction,
                one.reason, one.evidence,
            )
        return counts


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
    counts: PairCounts = field(default_factory=PairCounts)

    @property
    def detectors_agree(self) -> bool:
        return self.graph_detector_version == self.build_detector_version


def _snapshot() -> str:
    return " AND ".join(
        f"{column} = ?" for column in ("project_id", "branch", "commit_sha")
    )


_SNAPSHOT = _snapshot()

_RUN_SQL = f"SELECT detector_set_version FROM gl_context_run WHERE {_SNAPSHOT}"

_WHERE = (
    f"WHERE relationship_kind = '{provenance.IDENTICAL_BYTES_EDGE}' AND {_SNAPSHOT}"
)

_COUNTS_SQL = (
    "SELECT direction, direction_reason, subtype, count(*) "
    f"FROM gl_context_edge {_WHERE} GROUP BY 1, 2, 3"
)

_PAIRS_SQL = (
    "SELECT source_path, target_path, content_sha256, direction, "
    "direction_reason, subtype, evidence_path, evidence_line "
    f"FROM gl_context_edge {_WHERE} ORDER BY source_path, target_path"
)


def _query(connection, sql: str, parameters: list, db_path) -> list[tuple]:
    """Run one query, and name the remedy where the store predates the columns.

    A store written before this ticket has no ``direction`` column, and DuckDB
    answers a select on it with a binder error rather than a missing table. Left
    to itself that reaches the command line as a traceback; the store already
    has a command that resolves it, so it is named here the way every other
    schema mismatch in this tool names it.
    """
    try:
        return connection.execute(sql, parameters).fetchall()
    except duckdb.Error as error:
        where = f" at {db_path}" if db_path else ""
        raise PairsError(
            f"the context graph{where} does not carry the columns this build "
            f"reads byte-identical pairs from ({error}). To bring the store to "
            f"the ontology, run `orbit-context migrate"
            + (f" --db {db_path}" if db_path else "")
            + "`, then re-index the repository."
        ) from None


def counts_from_graph(connection, snapshot: list, db_path=None) -> PairCounts:
    """How one snapshot's pairs divide, without fetching one row per pair.

    ``repo-map`` prints five example pairs and the counts over all of them, and
    pairing is quadratic inside a hash group -- so the counts are aggregated in
    the database rather than by reading every row back.
    """
    counts = PairCounts()
    for direction, reason, evidence, total in _query(
        connection, _COUNTS_SQL, snapshot, db_path
    ):
        counts.add(direction, reason, evidence, int(total))
    return counts


def from_graph(connection, snapshot: list, limit: int | None = None,
               db_path=None) -> list[Pairing]:
    """One snapshot's pairs, in path order, as the rows hold them.

    Takes an open connection rather than a path so that a caller already reading
    the graph -- ``repo-map`` -- gets the same answer this module's own command
    does. ``limit`` caps the rows fetched, for a caller that only lists a few.
    """
    sql = _PAIRS_SQL + (" LIMIT ?" if limit is not None else "")
    parameters = snapshot + ([limit] if limit is not None else [])
    return [
        Pairing(
            source_path=source,
            target_path=target,
            content_sha256=sha256 or "",
            # A NULL direction is a row written before the direction existed.
            # It is not UNKNOWN: UNKNOWN is a measurement and this is the
            # absence of one, and reading the first as the second would let an
            # older snapshot report an order nobody looked for.
            direction=direction if direction is not None else NOT_MEASURED,
            reason=reason,
            evidence=evidence,
            evidence_path=evidence_path,
            evidence_line=None if evidence_line is None else int(evidence_line),
        )
        for (source, target, sha256, direction, reason, evidence,
             evidence_path, evidence_line)
        in _query(connection, sql, parameters, db_path)
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
        result.pairs = from_graph(connection, snapshot, db_path=db_path)
        result.counts = PairCounts.of(result.pairs)
    finally:
        connection.close()
    return result


def summary_lines(counts: PairCounts, listed: list[Pairing],
                  version: str, shorten=None) -> list[str]:
    """The IDENTICAL BYTES block, shared with ``repo-map``.

    ``counts`` covers every pair in the snapshot; ``listed`` is the ones this
    caller has room to print, which may be none of them. The counts are never
    capped -- what is dropped is the listing, and the line saying how many were
    dropped is part of the block rather than the caller's to remember.

    ``shorten`` cuts a path to a printable width for the same caller.
    """
    lines = [
        f"\nIDENTICAL BYTES  {counts.total} pairs  [{version}]",
        f"  carrying provenance evidence     {counts.with_provenance}",
        f"  carrying no provenance evidence  {counts.without_provenance}",
        f"  carrying a direction             {counts.with_a_direction}",
    ]
    if counts.not_measured:
        # Named only where there are any, and never folded into either count
        # above: these rows say nothing about provenance, and a total that
        # absorbed them would say something about it on their behalf.
        lines.append(
            f"  no direction recorded            {counts.not_measured}  "
            f"-- {NOT_MEASURED_REMEDY}"
        )
    lines += [
        f"  read off  {DIRECTION_RULE}",
        f"  {DIRECTION_RULE_CAVEAT}",
        "  by evidence rung",
    ]
    lines += [f"    {rung}  {count}"
              for rung, count in counts.by_direction_evidence.items()]
    lines.append("  carrying no direction, by reason")
    lines += [f"    {reason}  {count}"
              for reason, count in counts.by_reason.items()]

    if counts.total:
        # Headed, because the reason rows above it are indented the same and a
        # reader scanning down would otherwise read the first pair -- or the
        # line saying none were listed -- as a fourth reason.
        lines.append("  pair by pair")
    lines += [f"    {_line(one, shorten)}" for one in listed]
    dropped = counts.total - len(listed)
    if dropped > 0:
        more = "more " if listed else ""
        lines.append(f"    {dropped} {more}pairs not listed")
    return lines


def _line(one: Pairing, shorten=None) -> str:
    """One pair, and what is known about which end came first.

    The direction is spelled with the paths rather than with the row's own
    ``source``/``target`` words: a reader is looking at two paths, and being
    told "source-produces-target" makes them work out which is which.
    """
    cut = shorten or (lambda path: path)
    pair = f"{cut(one.source_path)} = {cut(one.target_path)}"
    if not one.measured:
        return f"{pair}  {NOT_MEASURED}"
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
    lines += summary_lines(reading.counts, reading.pairs,
                           reading.graph_detector_version)
    return "\n".join(lines) + "\n"


def pairs(repo: str | Path = ".",
          db_path: str | Path = store.DEFAULT_DB_PATH) -> str:
    """One repository's byte-identical pairs, with their directions, as text."""
    return render(read(repo, db_path))
