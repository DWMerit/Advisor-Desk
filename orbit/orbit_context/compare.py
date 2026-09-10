"""Two states of one repository, indexed and differenced.

A comparison is two indexes plus subtraction. Nothing here acquires a store of
its own, an index path of its own or a query language of its own -- spec 0002
s12 lists each of those as a kill condition, and each of them would mean the
figures in this table were taken differently from the figures every other
command prints.

So: each state is materialised with ``git worktree add --detach``, indexed
through the same ``index`` every other run uses, read back out of the same
graph, and subtracted here.

Both states are read from a commit
----------------------------------

Not one from a commit and one from the working tree. A working tree carries
whatever is lying around in it -- an untracked scratch file, a half-written
note -- and a comparison between a clean checkout and a working tree reports
those as things the second state added. The two readings have to be the same
kind of reading before their difference means anything.

It also settles the acceptance rule the cheap way: a detached worktree checks
nothing out over the tree the caller is standing in.

Both absolute figures, beside every delta
-----------------------------------------

Subtraction hides which side moved. ``+40`` cannot distinguish "the second state
added forty" from "the first state was miscounted by forty", and the second is
the failure mode this project has already had twice. Every row here carries both
states' own figures beside the difference between them.

Two names for one file are one file
-----------------------------------

GitLab Orbit's rule, not ours: ``crates/orbit-local/src/commands/setup.rs:265-271``
canonicalises the paths it collected and keeps one entry, labelled by the
**target**. Their test at ``:292`` writes ``AGENTS.md``, symlinks ``CLAUDE.md``
to it, and asserts one entry named ``AGENTS.md``.

It matters here because the row this comparison turns on is a zero. Fourteen
symlinked ``full.md`` files sit in both states of the repository this was built
for; counted as a surface in one state and not in the other, the zero moves and
the comparison reports a session adding rules it did not write.

What the fold is *not*: same-inode is a stronger statement than the byte
identity ``IDENTICAL_BYTES`` carries. Byte-identical says "same content, cause
unknown"; same-inode says "same file". So the target being the surviving name is
observed, and it reopens nothing -- two files that merely hash the same are
still unordered, and nothing here changes that.

The number folded is reported **per state**, beside the counts and never inside
them. A fold that happens in one state and not the other is exactly what moves a
zero, and one summed figure would hide which state it happened in.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from pathlib import Path

import duckdb

from . import clauses, detectors, ladders, pairs, pointers, provenance, store
from . import surfaces
from .indexer import CONTAINS_EDGE, REFERENCES_EDGE, index
from .workspace import Repository, git_info

# The exit code for a comparison that ran and whose deltas are not comparable.
# Distinct from an error: the table is printed, every figure in it was measured,
# and what is not established is that subtracting them means anything.
EXIT_NOT_COMPARABLE = 4

# Said in the output, not implied by a version string the reader has to notice.
NOT_COMPARABLE = (
    "The two states were read by different detector sets, so the deltas below "
    "are not comparable"
)

# Rows listed as examples before a listing stops and says how many it did not
# list. The listing is here to make a count concrete; the count is the finding.
EXAMPLE_ROWS = 3

# Zero rows carried in a per-name section before the rest are summarised. Every
# row that moved is always printed: a cap that could hide a delta would be a cap
# on the finding rather than on the output, and what the cap leaves out is
# totalled into the section's own "did not move" row rather than dropped.
#
# It bites only on the two sections whose names come from the estate -- suffixes
# and top-level directories. Every other section here is a fixed inventory of
# what these detectors look for, all of them shorter than this, and those print
# whole including their zeroes.
ZERO_ROWS = 12

# How wide a path or a state label is printed before it is cut.
MAX_TEXT_WIDTH = 56

# Every edge kind this domain writes, listed at zero as well as at count.
# Sourced from the modules that own them where one does, so that a rename
# reaches this inventory rather than quietly emptying a row of it -- the same
# arrangement `repo-map` makes for its own section.
EDGE_KINDS = (
    CONTAINS_EDGE,
    REFERENCES_EDGE,
    provenance.IDENTICAL_BYTES_EDGE,
    provenance.PRODUCES_EDGE,
    ladders.RUNG_OF_EDGE,
)

# The key a file with no suffix, and a file at the repository root, are tallied
# under. Empty in the store -- it is a key there, not a word -- and named here,
# where it is being printed to a person.
NO_SUFFIX = "(no suffix)"
AT_THE_ROOT = "(root)"


class CompareError(Exception):
    """A state could not be materialised, indexed, or read back."""


@dataclass(frozen=True)
class Row:
    """One measurement in both states, and the difference between them."""

    name: str
    before: int
    after: int

    @property
    def delta(self) -> int:
        return self.after - self.before


@dataclass(frozen=True)
class Fold:
    """One name that was counted as the file it names."""

    name: str
    counted_as: str


@dataclass(frozen=True)
class State:
    """One indexed snapshot, read back out of the graph.

    Every count here is after the fold, except ``surfaces_folded``, which is the
    fold itself.
    """

    label: str
    root: str
    branch: str
    commit_sha: str
    detector_set_version: str

    files_walked: int = 0
    files_by_suffix: dict[str, int] = field(default_factory=dict)
    files_by_directory: dict[str, int] = field(default_factory=dict)

    # Distinct names after the fold, and so **not** the run row's own
    # `files_with_surface_kind`: that one counts a link and the file it names as
    # two. Named apart from the column for that reason -- one table cannot carry
    # a folded count and an unfolded one under two headings and expect a reader
    # to tell which is which.
    surface_files: int = 0
    surface_rows: int = 0
    surfaces_read_in_full: int = 0
    surface_bytes: int = 0
    surfaces_by_kind: dict[str, int] = field(default_factory=dict)
    surfaces_folded: int = 0
    folds: tuple[Fold, ...] = ()
    surface_labels: frozenset[str] = frozenset()

    clauses: int = 0
    clauses_by_type: dict[str, int] = field(default_factory=dict)
    pointers: int = 0
    pointers_by_subtype: dict[str, int] = field(default_factory=dict)
    edges_by_kind: dict[str, int] = field(default_factory=dict)
    external_refs_by_sub_kind: dict[str, int] = field(default_factory=dict)
    # Byte identity, read through `pairs.counts_from_graph` -- the function that
    # owns the rule that a pair count is never emitted alone. The block it
    # divides into is printed here whole, so a hash-match count cannot reach
    # stdout from this command without the counts that make it readable.
    pair_counts: pairs.PairCounts = field(default_factory=pairs.PairCounts)


@dataclass(frozen=True)
class Comparison:
    """Two states, and every measurement taken of both."""

    before: State
    after: State
    database_path: str

    @property
    def comparable(self) -> bool:
        """Whether subtracting these two readings says anything.

        One condition, and it is the one the detector version exists for: a
        change in the detectors and a change in the estate move the same
        numbers, and nothing else tells them apart.
        """
        return (
            self.before.detector_set_version == self.after.detector_set_version
        )

    def rows(self) -> list[Row]:
        """The counted section, in the order it is printed."""
        return [
            Row("files walked", self.before.files_walked, self.after.files_walked),
            Row("files carrying a surface kind, folded",
                self.before.surface_files, self.after.surface_files),
            self.surfaces(),
            Row("of those, read in full",
                self.before.surfaces_read_in_full,
                self.after.surfaces_read_in_full),
            Row("two names for one file, folded",
                self.before.surfaces_folded, self.after.surfaces_folded),
            Row("clauses", self.before.clauses, self.after.clauses),
            Row("pointers", self.before.pointers, self.after.pointers),
            Row("surface bytes",
                self.before.surface_bytes, self.after.surface_bytes),
        ]

    def surfaces(self) -> Row:
        """The row the comparison turns on: surfaces, after the fold."""
        return Row("surfaces",
                   self.before.surface_rows, self.after.surface_rows)

    def suffixes(self) -> dict[str, Row]:
        return _tally_rows(self.before.files_by_suffix, self.after.files_by_suffix)

    def directories(self) -> dict[str, Row]:
        return _tally_rows(self.before.files_by_directory,
                           self.after.files_by_directory)

    def surface_kinds(self) -> dict[str, Row]:
        return _tally_rows(self.before.surfaces_by_kind,
                           self.after.surfaces_by_kind)

    def clause_types(self) -> dict[str, Row]:
        return _tally_rows(self.before.clauses_by_type,
                           self.after.clauses_by_type)

    def pointer_subtypes(self) -> dict[str, Row]:
        return _tally_rows(self.before.pointers_by_subtype,
                           self.after.pointers_by_subtype)

    def edges(self) -> dict[str, Row]:
        return _tally_rows(self.before.edges_by_kind, self.after.edges_by_kind)

    def external_refs(self) -> dict[str, Row]:
        return _tally_rows(self.before.external_refs_by_sub_kind,
                           self.after.external_refs_by_sub_kind)


def _tally_rows(before: dict[str, int], after: dict[str, int]) -> dict[str, Row]:
    """Both tallies, over the union of their keys.

    The union rather than either side's keys: a directory that exists in one
    state and not the other is the thing being looked for, and a row missing
    from the table reads as a directory that did not move.
    """
    return {
        name: Row(name, before.get(name, 0), after.get(name, 0))
        for name in sorted(set(before) | set(after))
    }


# --- Reading a state -------------------------------------------------------


def _snapshot(alias: str = "") -> str:
    prefix = f"{alias}." if alias else ""
    return " AND ".join(
        f"{prefix}{column} = ?"
        for column in ("project_id", "branch", "commit_sha")
    )


_SNAPSHOT = _snapshot()

_RUN_SQL = (
    "SELECT detector_set_version, files_walked, "
    "       files_walked_by_suffix, files_walked_by_directory "
    f"FROM gl_context_run WHERE {_SNAPSHOT}"
)

_SURFACE_SQL = (
    "SELECT path, surface_kind, COALESCE(link_target, ''), "
    "       COALESCE(reason, ''), COALESCE(size_bytes, 0) "
    f"FROM gl_context_surface WHERE {_SNAPSHOT} ORDER BY path"
)

_CLAUSE_SQL = (
    "SELECT clause_type, count(*) "
    f"FROM gl_context_clause WHERE {_SNAPSHOT} GROUP BY 1"
)

_POINTER_SQL = (
    "SELECT subtype, count(*) FROM gl_context_edge "
    f"WHERE relationship_kind = '{REFERENCES_EDGE}' AND {_SNAPSHOT} GROUP BY 1"
)

_EDGE_SQL = (
    "SELECT relationship_kind, count(*) "
    f"FROM gl_context_edge WHERE {_SNAPSHOT} GROUP BY 1"
)

_EXTERNAL_SQL = (
    "SELECT sub_kind, count(*) "
    f"FROM gl_context_external_ref WHERE {_SNAPSHOT} GROUP BY 1"
)


def read_state(connection, found: Repository, label: str,
               db_path: str | Path = "") -> State:
    """Read one indexed snapshot back out of the graph, folded.

    ``db_path`` is carried only so that a store whose columns predate this build
    is named with the file the reader would have to migrate.
    """
    snapshot = [found.project_id, found.branch, found.commit_sha]
    try:
        run = connection.execute(_RUN_SQL, snapshot).fetchall()
    except duckdb.CatalogException as error:
        raise CompareError(
            f"the graph holds no gl_context_run table: {error}"
        ) from None
    except duckdb.BinderException as error:
        # A store whose columns predate this build: the tally is not there to
        # read. Named for the same reason the check below names an empty one.
        raise CompareError(
            f"the graph predates this build: {error}; "
            f"re-index both states, or run `orbit-context migrate`"
        ) from None
    if not run:
        raise CompareError(
            f"no index run recorded for {label} at {found.commit_sha[:12]}"
        )
    version, files_walked, by_suffix, by_directory = run[0]
    for column, serialised in (("files_walked_by_suffix", by_suffix),
                               ("files_walked_by_directory", by_directory)):
        if files_walked and not serialised:
            # A snapshot written before the walk recorded its own tally. Named
            # rather than read as an empty tally: absent and empty are different
            # findings, and one of them is a repository with no files in it.
            raise CompareError(
                f"the snapshot for {label} at {found.commit_sha[:12]} carries "
                f"no {column}; re-index both states with this build"
            )

    state = State(
        label=label,
        root=str(found.root),
        branch=found.branch,
        commit_sha=found.commit_sha,
        detector_set_version=version,
        files_walked=int(files_walked),
        files_by_suffix=_tally(by_suffix),
        files_by_directory=_tally(by_directory),
        edges_by_kind={
            kind: int(count)
            for kind, count in connection.execute(_EDGE_SQL, snapshot).fetchall()
        },
        external_refs_by_sub_kind={
            sub_kind: int(count)
            for sub_kind, count
            in connection.execute(_EXTERNAL_SQL, snapshot).fetchall()
        },
    )
    clauses_by_type = _zero_filled(
        clauses.CLAUSE_TYPES, connection.execute(_CLAUSE_SQL, snapshot).fetchall()
    )
    pointers_by_subtype = _zero_filled(
        pointers.SUBTYPES, connection.execute(_POINTER_SQL, snapshot).fetchall()
    )
    state = replace(
        state,
        clauses=sum(clauses_by_type.values()),
        clauses_by_type=clauses_by_type,
        # Read off the edge tally rather than counted a second time: a pointer
        # is a REFERENCES edge, and two queries for one number is two numbers.
        pointers=state.edges_by_kind.get(REFERENCES_EDGE, 0),
        pointers_by_subtype=pointers_by_subtype,
        # The pair count and the counts that make it readable, from the one
        # function that owns both.
        pair_counts=_pair_counts(connection, snapshot, db_path),
    )
    return _folded(
        state, connection.execute(_SURFACE_SQL, snapshot).fetchall()
    )


def _pair_counts(connection, snapshot: list, db_path) -> pairs.PairCounts:
    """Byte identity, from the function that owns "never counted alone".

    `pairs` raises its own error for a store whose columns predate this build
    and names the command that resolves it; it is re-raised here so the command
    line handles it the way it handles everything else a state cannot be read
    for.
    """
    try:
        return pairs.counts_from_graph(connection, snapshot, db_path=db_path)
    except pairs.PairsError as error:
        raise CompareError(str(error)) from None


def _zero_filled(inventory, counted) -> dict[str, int]:
    """One tally, every name this tool looks for present even at zero.

    A value read off a row that this build has no name for is added rather than
    dropped: a vocabulary this build has not seen is a finding, not a row to
    throw away.
    """
    tally = {name: 0 for name in inventory}
    for name, count in counted:
        tally[name] = tally.get(name, 0) + int(count)
    return tally


def _tally(serialised: str | None) -> dict[str, int]:
    """One walk tally, read back from the JSON the run row carries."""
    if not serialised:
        return {}
    try:
        loaded = json.loads(serialised)
    except ValueError as error:
        raise CompareError(
            f"a walk tally in the graph is not readable: {error}"
        ) from None
    return {str(name): int(count) for name, count in loaded.items()}


@dataclass(frozen=True)
class _Entry:
    """One surface row, in the four fields the fold and the counts need."""

    path: str
    kind: str
    reason: str
    size_bytes: int

    @property
    def read_in_full(self) -> bool:
        return self.reason == ""


def _folded(state: State, rows: list[tuple]) -> State:
    """Fold a name that resolves to another name, keeping the target's.

    **Only a link folds.** Rows are additive here on purpose and several of them
    legitimately stand at one path: a settings file holds a row per hook and a
    row per MCP server, and a fold keyed on the path would take four hooks down
    to one and report a file folded into itself. So the two populations are
    separated first -- rows standing at a name of their own, and rows whose name
    resolves to another -- and only the second can be folded away.

    A link folds onto ``(the path it names, its own kind)`` where the snapshot
    holds a row standing there. The kind is part of that because rows are
    additive: a hook script is a hook target *and* whatever else it is, and
    folding across kinds would turn that record into one argument about which it
    really is.

    Where nothing stands at the target -- a link naming a file that is not
    itself a surface -- the link's own row survives under the target's name, and
    a second link naming the same file folds onto that one. Its ``size_bytes``
    is then the link's own, which is what a node nobody opened weighs.
    """
    standing: list[_Entry] = []
    links: list[tuple[_Entry, str]] = []
    for path, kind, link_target, reason, size in rows:
        entry = _Entry(path, kind, reason, int(size or 0))
        if link_target:
            links.append((entry, link_target))
        else:
            standing.append(entry)

    at = {(entry.path, entry.kind) for entry in standing}
    unmatched: dict[tuple[str, str], _Entry] = {}
    folds: list[Fold] = []
    for entry, target in links:
        key = (target, entry.kind)
        if key in at or key in unmatched:
            folds.append(Fold(entry.path, target))
            continue
        unmatched[key] = entry

    kept = standing + list(unmatched.values())
    labels = (
        frozenset(entry.path for entry in standing)
        | frozenset(target for target, _ in unmatched)
    )
    return replace(
        state,
        surface_files=len(labels),
        surface_rows=len(kept),
        surfaces_read_in_full=sum(1 for entry in kept if entry.read_in_full),
        surface_bytes=sum(entry.size_bytes for entry in kept),
        surfaces_by_kind=_by_kind(kept),
        surfaces_folded=len(folds),
        folds=tuple(sorted(folds, key=lambda fold: fold.name)),
        surface_labels=labels,
    )


def _by_kind(kept: list[_Entry]) -> dict[str, int]:
    """Surfaces per kind, every kind this tool has present even at zero.

    Printed in full for the reason `repo-map` prints every zero: a listing of
    only the kinds that moved reads as a description of the estate, and a column
    of zeroes reads as what it is -- the inventory of what these detectors look
    for.
    """
    tally = {kind: 0 for kind in surfaces.SURFACE_KINDS}
    for entry in kept:
        tally[entry.kind] = tally.get(entry.kind, 0) + 1
    return tally


# --- Materialising a state -------------------------------------------------


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=root, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise CompareError(
            f"git {' '.join(arguments)} failed in {root}: {result.stderr.strip()}"
        )
    return result.stdout.strip()


@contextmanager
def _worktree(repo_root: Path, ref: str):
    """One state, checked out beside the repository rather than over it.

    ``--detach`` because a state is a commit, not a branch: checking a branch
    out into a worktree would move it, and two states of one repository are
    frequently one branch's own history.
    """
    commit = _git(repo_root, "rev-parse", "--verify", f"{ref}^{{commit}}")
    holder = Path(tempfile.mkdtemp(prefix="orbit-context-state-"))
    tree = holder / commit[:12]
    try:
        _git(repo_root, "worktree", "add", "--detach", str(tree), commit)
    except CompareError:
        shutil.rmtree(holder, ignore_errors=True)
        raise
    try:
        yield tree
    finally:
        # Removed even where the index run raised: a worktree left behind is a
        # second checkout of somebody's repository that nothing here will ever
        # come back for.
        subprocess.run(["git", "worktree", "remove", "--force", str(tree)],
                       cwd=repo_root, capture_output=True, text=True, check=False)
        shutil.rmtree(holder, ignore_errors=True)
        subprocess.run(["git", "worktree", "prune"], cwd=repo_root,
                       capture_output=True, text=True, check=False)


def read_ref(repo_root: Path, ref: str, db_path: str | Path,
             ontology_root: str | Path | None = None) -> State:
    """Materialise one state, index it, and read the snapshot back."""
    with _worktree(repo_root, ref) as tree:
        index(tree, db_path=db_path, ontology_root=ontology_root)
        found = git_info(tree)
    connection = store.connect(db_path, read_only=True)
    try:
        return read_state(connection, found, label=ref, db_path=db_path)
    finally:
        connection.close()


def compare(repo: str | Path, before: str, after: str,
            db_path: str | Path = store.DEFAULT_DB_PATH,
            ontology_root: str | Path | None = None) -> Comparison:
    """Index two states of one repository and difference them."""
    root = Path(repo).resolve()
    return Comparison(
        before=read_ref(root, before, db_path, ontology_root),
        after=read_ref(root, after, db_path, ontology_root),
        database_path=str(Path(db_path)),
    )


# --- Printing it -----------------------------------------------------------


def _short(text: str, width: int = MAX_TEXT_WIDTH) -> str:
    text = str(text)
    if len(text) <= width:
        return text
    head = (width - 1) // 2
    return text[:head] + "…" + text[head + 1 - width :]


def _delta(value: int) -> str:
    return f"+{value}" if value > 0 else str(value)


def _table(rows: list[Row], before: str, after: str, indent: str = "  ") -> list[str]:
    """Aligned ``name  before  after  delta`` lines, headed by the two states.

    Both figures are printed on every row, always. That is the whole discipline
    of this file: a column of deltas on its own cannot say which side moved.
    """
    if not rows:
        return [f"{indent}(none)"]
    name_width = max([len(row.name) for row in rows] + [len("state")])
    columns = [
        max([len(str(row.before)) for row in rows] + [len(before)]),
        max([len(str(row.after)) for row in rows] + [len(after)]),
    ]
    delta_width = max([len(_delta(row.delta)) for row in rows] + [len("delta")])
    lines = [
        f"{indent}{'state':<{name_width}}  {before:>{columns[0]}}"
        f"  {after:>{columns[1]}}  {'delta':>{delta_width}}"
    ]
    for row in rows:
        lines.append(
            f"{indent}{row.name:<{name_width}}  {row.before:>{columns[0]}}"
            f"  {row.after:>{columns[1]}}  {_delta(row.delta):>{delta_width}}"
        )
    return lines


def _listed(rows: dict[str, Row], rename=None) -> list[Row]:
    """Every row that moved, then the rows that did not, capped.

    A row at zero is worth printing -- "this directory did not move" is half of
    what the table says -- and there can be a great many of them. So the cap
    falls only on the zeroes, and never on a row carrying a delta.
    """
    named = [
        Row(rename(row.name) if rename else row.name, row.before, row.after)
        for row in rows.values()
    ]
    moved = [row for row in named if row.delta]
    still = [row for row in named if not row.delta]
    return moved + still[:ZERO_ROWS]


def _unlisted(rows: dict[str, Row]) -> int:
    still = [row for row in rows.values() if not row.delta]
    return max(0, len(still) - ZERO_ROWS)


def _suffix_name(suffix: str) -> str:
    return suffix or NO_SUFFIX


def _directory_name(directory: str) -> str:
    return directory or AT_THE_ROOT


def _header(comparison: Comparison) -> list[str]:
    before, after = comparison.before, comparison.after
    lines = [
        "orbit-context compare",
        f"  before       {_short(before.label, 24)}  {before.commit_sha[:12]}"
        f"  {_short(before.root, 48)}",
        f"  after        {_short(after.label, 24)}  {after.commit_sha[:12]}"
        f"  {_short(after.root, 48)}",
    ]
    if comparison.comparable:
        lines.append(
            f"  detectors    {before.detector_set_version}  (both states)"
        )
    else:
        lines.append(f"  detectors    {before.detector_set_version}  before")
        lines.append(f"               {after.detector_set_version}  after")
        lines.append(f"  {NOT_COMPARABLE}.")
        lines.append(
            "  A change in the detectors and a change in the repository move "
            "the same numbers."
        )
    if detectors.VERSION != before.detector_set_version:
        lines.append(
            f"  This build is {detectors.VERSION}; the counts below are what "
            "the set that wrote them found."
        )
    lines.append(f"  graph        {_short(comparison.database_path, 48)}")
    lines.append(
        "  Each state was indexed from a detached worktree of its own commit, "
        "so no"
    )
    lines.append(
        "  working tree was checked out over and neither reading carries "
        "anything its"
    )
    lines.append("  commit does not.")
    return lines


def _heading(title: str, summary: str, version: str) -> str:
    return f"\n{title}  {summary}  [{version}]"


def _counts(comparison: Comparison) -> list[str]:
    return [
        _heading("COUNTS", "both figures beside every delta",
                 comparison.before.detector_set_version),
        *_table(comparison.rows(), comparison.before.label,
                comparison.after.label),
    ]


def _still(rows: dict[str, Row], name: str) -> Row:
    """One row totalling every name that did not move.

    The ticket this was built for asks for exactly this figure -- "files outside
    the directory the session added: 201, 201, 0" -- and a reader cannot add it
    up from a listing that is capped. So it is totalled over every row, listed
    or not, which is also what makes the cap safe: nothing a cap left out is
    missing from the table, only from the listing.
    """
    still = [row for row in rows.values() if not row.delta]
    return Row(name, sum(row.before for row in still),
               sum(row.after for row in still))


def _by_name(comparison: Comparison, title: str, summary: str,
             rows: dict[str, Row], rename=None, still: str = "") -> list[str]:
    """One per-name section: what moved, then what did not, then the cap.

    ``still`` names the row that totals the names at delta 0, and is empty for a
    section whose rows must never be summed -- the three non-resolutions are
    three statements about what a detector set could not see, and one total
    would say none of them.
    """
    listed = _listed(rows, rename)
    if still:
        listed = listed + [_still(rows, still)]
    lines = [
        _heading(title, summary, comparison.before.detector_set_version),
        *_table(listed, comparison.before.label, comparison.after.label),
    ]
    unlisted = _unlisted(rows)
    if unlisted:
        lines.append(
            f"  {unlisted} more are not listed, every one of them at delta 0 "
            f"and every one of them inside the total above"
        )
    return lines


def _folds(comparison: Comparison) -> list[str]:
    """The fold, per state, beside the counts rather than inside them."""
    lines = [
        _heading("TWO NAMES FOR ONE FILE", "counted once, labelled by the target",
                 comparison.before.detector_set_version)
    ]
    for state in (comparison.before, comparison.after):
        lines.append(f"  {_short(state.label, 24)}  {state.surfaces_folded} folded")
        for fold in state.folds[:EXAMPLE_ROWS]:
            lines.append(
                f"      {_short(fold.name, 40)} counted as {_short(fold.counted_as, 40)}"
            )
        if len(state.folds) > EXAMPLE_ROWS:
            lines.append(f"      and {len(state.folds) - EXAMPLE_ROWS} more")
    lines.append(
        "  Two names for one file are one file "
        "(crates/orbit-local/src/commands/setup.rs:265-271)."
    )
    return lines


def _closing(comparison: Comparison) -> list[str]:
    lines = [
        "",
        "Deltas are counts and bytes. Nothing here says what a difference means,",
        "which of the two states is the better one, or what to do about either.",
    ]
    if not comparison.comparable:
        lines.append(f"{NOT_COMPARABLE}.")
    return lines


def _identical_bytes(comparison: Comparison) -> list[str]:
    """Byte identity, printed as the block rather than as a count.

    A bare hash-match count over-reads badly, so the README's rule is that it is
    never emitted alone: it is reported with the count of pairs carrying
    provenance evidence and the count carrying none. That rule is a property of
    `pairs.PairCounts`, which is where these four figures come from, rather than
    a habit this file has to remember.
    """
    before, after = comparison.before.pair_counts, comparison.after.pair_counts
    rows = [
        Row("pairs", before.total, after.total),
        Row("carrying provenance evidence",
            before.with_provenance, after.with_provenance),
        Row("carrying no provenance evidence",
            before.without_provenance, after.without_provenance),
        Row("carrying a direction",
            before.with_a_direction, after.with_a_direction),
    ]
    return [
        _heading("IDENTICAL BYTES", "pairs, and what evidences them",
                 comparison.before.detector_set_version),
        *_table(rows, comparison.before.label, comparison.after.label),
        "  Whether two identical files are intentionally identical stays UNKNOWN.",
    ]


def render(comparison: Comparison) -> str:
    """The comparison as text."""
    lines = _header(comparison)
    lines += _counts(comparison)
    lines += _by_name(
        comparison, "FILES BY SUFFIX", "what kind of file moved",
        comparison.suffixes(), rename=_suffix_name,
        still="every suffix that did not move",
    )
    lines += _by_name(
        comparison, "FILES BY TOP-LEVEL DIRECTORY", "where the difference landed",
        comparison.directories(), rename=_directory_name,
        still="every directory that did not move",
    )
    lines += _folds(comparison)
    lines += _by_name(comparison, "SURFACES BY KIND", "which kinds moved",
                      comparison.surface_kinds())
    lines += _by_name(comparison, "CLAUSES BY TYPE", "by Markdown structure alone",
                      comparison.clause_types())
    lines += _by_name(comparison, "POINTERS BY DETECTOR", "what each one reads",
                      comparison.pointer_subtypes())
    lines += _by_name(comparison, "EDGES", "by kind", _edge_rows(comparison))
    lines += _by_name(
        comparison, "ADDRESSES THAT DID NOT RESOLVE", "never merged",
        _external_rows(comparison),
    )
    lines += _identical_bytes(comparison)
    lines += _closing(comparison)
    return "\n".join(lines) + "\n"


def _edge_rows(comparison: Comparison) -> dict[str, Row]:
    """Every edge kind this domain writes, present at zero as well as at count."""
    rows = comparison.edges()
    for kind in EDGE_KINDS:
        rows.setdefault(kind, Row(kind, 0, 0))
    return dict(sorted(rows.items()))


def _external_rows(comparison: Comparison) -> dict[str, Row]:
    """All three non-resolutions, always. Each names what could not be seen."""
    rows = comparison.external_refs()
    for sub_kind in pointers.SUB_KINDS:
        rows.setdefault(sub_kind, Row(sub_kind, 0, 0))
    return dict(sorted(rows.items()))


def compare_text(repo: str | Path, before: str, after: str,
                 db_path: str | Path = store.DEFAULT_DB_PATH,
                 ontology_root: str | Path | None = None) -> tuple[str, bool]:
    """The comparison, rendered, and whether its deltas are comparable."""
    comparison = compare(repo, before, after, db_path, ontology_root)
    return render(comparison), comparison.comparable
