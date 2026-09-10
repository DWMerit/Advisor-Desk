"""Hash the files, pair the matches, and read the provenance that explains them.

Two edge types live here, and they are built together on purpose.

``IDENTICAL_BYTES``
    Two files in one repository hash to the same sha256. Pure observation.
    Whether they are meant to be identical is a permanent UNKNOWN (spec 0001
    §14), so nothing here reaches for a word that would decide it.

``PRODUCES``
    A generator and the artifact it writes, on an evidence ladder, strongest
    first: the artifact's own header naming its producer, then a manifest
    declaring input to output, then a script carrying a literal write path. The
    rung is the edge's ``subtype``.

**Why one module.** On one real repository the first pass reported 28
byte-identical pairs and zero producers. Every pair was a workbench file
matching a published file -- one pipeline run 28 times -- and the provenance
that explained all 28 was invisible to the tool. Byte-identity and provenance
are usually the same phenomenon and only the first is easy to see, so a count
of matching pairs is never emitted without the count of pairs carrying
provenance evidence beside it. :func:`summary` is the only place either number
is produced, which is what makes "never emitted alone" a property of the code
rather than a habit.

Two files are only ever paired **within one repository**. Two repositories are
two snapshots, each with its own branch and commit, and an edge across them
would join two things this indexer has not established are the same.

Zero-byte files are counted and named, and left out of the pairing. An empty
file matches every other empty file, so a repository with twenty of them would
report 190 pairs that say nothing about any of them.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

import yaml

from . import pointers as pointer_module
from .jsonloc import JsonLocationError, Node, parse as parse_json
# Imported rather than re-spelled. A file too large to read and a file the
# filesystem refused are the same outcomes the surface reader already names,
# and two spellings of one string drift apart. A file over the ceiling is
# hashed neither for pairing nor for evidence, and is counted instead.
from .surfaces import (
    MAX_SURFACE_BYTES as MAX_FILE_BYTES,
    REASON_NON_REGULAR_FILE,
    REASON_OVERSIZE,
    REASON_READ_ERROR,
)

# Why a walked file was not hashed. Reported split by reason rather than as one
# number, by the same rule the direction reasons are: "a node this walk lists
# and never opens" and "a file too large to read" are different statements about
# the estate, and a single count of files not read says neither. Every reason is
# present at zero, so a reason that found nothing reads as a reason that found
# nothing.
NOT_READ_REASONS = (REASON_NON_REGULAR_FILE, REASON_OVERSIZE, REASON_READ_ERROR)

IDENTICAL_BYTES_EDGE = "IDENTICAL_BYTES"
PRODUCES_EDGE = "PRODUCES"

# The ladder, strongest first. An artifact keeps the strongest rung found for
# it; a weaker rung is not written beside a stronger one for the same artifact,
# or one fact is counted twice at two strengths.
ARTIFACT_HEADER = "artifact-header"
MANIFEST_DECLARATION = "manifest-declaration"
LITERAL_WRITE_PATH = "literal-write-path"

EVIDENCE_LADDER = (ARTIFACT_HEADER, MANIFEST_DECLARATION, LITERAL_WRITE_PATH)

# Which end of a byte-identical pair the evidence puts first. The pair itself is
# symmetric -- one row per unordered pair, lexicographically first path as the
# source -- so a direction is stated against that ordering rather than by
# reordering the row, and `source` and `target` here are the row's own columns.
SOURCE_PRODUCES_TARGET = "source-produces-target"
TARGET_PRODUCES_SOURCE = "target-produces-source"
DIRECTIONS = (SOURCE_PRODUCES_TARGET, TARGET_PRODUCES_SOURCE)

# And the value for a pair nothing ordered. Spelled the way spec 0001 s14
# spells a permanent unknown, and written on the row rather than left blank: a
# NULL reads as a column nobody filled in, and this is a measurement.
DIRECTION_UNKNOWN = "UNKNOWN"

# Why a pair carries no direction. Three different statements about the estate,
# never merged into one, because "nothing here evidences a producer at all" and
# "something produced one of these and it was not the other" are what a reader
# is trying to tell apart.
#
# The second is the case that makes this worth separating. A pair whose ends are
# both artifacts of one script has provenance -- ticket 05's count sees it -- and
# still nothing that orders the two. Folding it in with the pairs no evidence
# reaches would say something untrue about both.
NO_PRODUCER_AT_EITHER_END = "no-producer-named-at-either-end"
PRODUCER_OUTSIDE_THE_PAIR = "producer-named-outside-the-pair"
EACH_END_NAMES_THE_OTHER = "each-end-names-the-other-as-its-producer"

DIRECTION_UNKNOWN_REASONS = (
    NO_PRODUCER_AT_EITHER_END,
    PRODUCER_OUTSIDE_THE_PAIR,
    EACH_END_NAMES_THE_OTHER,
)

# How far into a file a generation header is looked for. A header is a header:
# past this it is prose about generation, not the artifact declaring itself.
HEADER_LINES = 20

# And within those lines, a header is written where a header can be written: in
# a comment, or in the leading frontmatter block. Without this the detector
# reads prose *about* generation as generation -- the first run of it took the
# sentence in orbit/tickets/05 that warns about trailing comment syntax and
# reported the ticket itself as an artifact of the script that sentence names.
# That is the tool talking about itself, which is the failure this project has
# already paid for once, at 1,349 phantom findings out of 1,373.
_COMMENT_LINE = re.compile(r"^[ \t]*(?:#+|//+|<!--|/\*|\*|;+|%+|--)")

# `Generated by X`. The name is the FIRST token after `by` and nothing else --
# a header comment carries trailing syntax, and
# `Generated by scripts/build.py -- DO NOT EDIT -->` names one file, not four
# tokens' worth of one.
_GENERATED_BY = re.compile(
    r"\b(?:auto-?)?(?:@)?(?:generated|generator|produced|created|written)"
    r"[\s_-]+by\b[:\s]+(\S+)",
    re.IGNORECASE,
)

# A file declaring that it was generated without naming what generated it.
# Evidence that something produced it; not evidence of what, so it names no
# producer and writes no edge. Counted under its own key rather than folded
# into the artifacts with no provenance at all, which would say something
# untrue about the estate.
_GENERATION_DECLARED = re.compile(
    r"@generated\b|\bdo\s+not\s+edit\b|\bauto-?generated\b|\bgenerated[\s_-]+by\b",
    re.IGNORECASE,
)

# Comment syntax a header wraps a name in. Trimmed off the end of the first
# token, so `scripts/build.py-->` is the script and not a token that resolves
# to nothing.
_CLOSING_SYNTAX = ("-->", "*/", "?>", "]]>", "#}", "--}}", "}}")
_SURROUNDING = "`'\"<>()[]{}"
# Sentence punctuation a name can end against, trimmed the way a prose pointer
# is trimmed -- `.` has to be inside the token or no extension would match.
_TRAILING = ".,;:-~"

# Keys a manifest declares its two ends under. Narrow on purpose: a key not
# listed here is not read as a declaration at all, which is a stated limit of
# this detector rather than a claim about the estate.
_INPUT_KEYS = frozenset({"input", "inputs", "source", "sources", "src", "from"})
_OUTPUT_KEYS = frozenset({"output", "outputs", "dest", "destination", "to",
                          "target", "targets", "artifact", "artifacts"})

_MANIFEST_SUFFIXES = frozenset({".json", ".yaml", ".yml"})
_SCRIPT_SUFFIXES = frozenset({".py", ".sh", ".bash", ".zsh", ".js", ".mjs",
                              ".cjs", ".ts", ".rb", ".pl"})
# Where `> path` is a redirect rather than a comparison or an arrow.
_SHELL_SUFFIXES = frozenset({".sh", ".bash", ".zsh"})

# A line only offers write targets if it says it writes. Without this every
# quoted path in a script reads as a producer's output -- an import on a line
# holding an arrow function would be one.
_WRITE_CALLS = re.compile(
    r"""open\s*\([^)]*['"][wax]|write_text|write_bytes|writeFileSync|"""
    r"""appendFileSync|createWriteStream|writeFile\s*\(|\btee\b""",
)
_QUOTED = re.compile(r"""['"]([^'"\n]+)['"]""")
# `2> log.txt` is a redirect; `x -> y`, `a => b` and `a >= b` are not.
_REDIRECT = re.compile(r"(?<![-=<>])>>?\s*([^\s;|&<>'\"]+)")


@dataclass(frozen=True)
class Contents:
    """One file read once: what it hashes to, and its text if it decoded."""

    relative_path: str
    sha256: str
    size_bytes: int
    text: str | None


@dataclass(frozen=True)
class Pair:
    """Two files in one repository whose bytes hash the same."""

    sha256: str
    first_path: str
    second_path: str


@dataclass(frozen=True)
class Production:
    """One claim that a producer writes an artifact, and where it is written."""

    producer_address: str      # as the estate wrote it, before resolution
    producer_path: str | None  # repository-relative, or None if nothing is there
    artifact_path: str
    evidence: str              # which rung of the ladder
    evidence_path: str
    evidence_line: int


@dataclass(frozen=True)
class Direction:
    """One pair, and which way round the evidence puts it -- or why it does not.

    Exactly one of the two halves is filled in. Where ``direction`` is a
    direction, ``producer_path``, ``artifact_path``, ``evidence`` and the
    locator are set and ``reason`` is None; where it is ``DIRECTION_UNKNOWN``
    they are all None and ``reason`` says which of the three cases this is.
    """

    pair: Pair
    direction: str
    reason: str | None = None
    producer_path: str | None = None
    artifact_path: str | None = None
    evidence: str | None = None
    evidence_path: str | None = None
    evidence_line: int | None = None


@dataclass
class Scan:
    """One repository's files, hashed, with the provenance read out of them."""

    contents: dict[str, Contents] = field(default_factory=dict)
    # (path, reason) for a file that could not be hashed. Coverage is a
    # property of the record: a file that was not read must not read as a file
    # that matched nothing.
    not_read: list[tuple[str, str]] = field(default_factory=list)
    zero_byte: list[str] = field(default_factory=list)
    productions: list[Production] = field(default_factory=list)
    # Artifacts declaring they were generated without naming a producer.
    declared_without_producer: list[str] = field(default_factory=list)


def read_tree(repo_root: Path, files) -> Scan:
    """Hash every file in one repository and read its provenance evidence.

    One read per file: the bytes are hashed, and the decoded text -- where it
    decodes -- is offered to each rung of the ladder. Text is not retained,
    only the digest and the evidence, so a large repository costs a digest per
    file rather than its own contents in memory.
    """
    scan = Scan()
    for walked in files:
        relative = walked.relative_path
        # A node the walk listed is never opened, so it is never hashed. Reading
        # through the link would file one book's bytes under two names and
        # invent a byte-identical pair the estate does not have -- and ticket 12
        # has just finished establishing what this estate's 28 pairs are.
        if walked.non_regular:
            scan.not_read.append((relative, REASON_NON_REGULAR_FILE))
            continue
        try:
            size = walked.absolute_path.stat().st_size
        except OSError:
            scan.not_read.append((relative, REASON_READ_ERROR))
            continue
        if size > MAX_FILE_BYTES:
            scan.not_read.append((relative, REASON_OVERSIZE))
            continue
        try:
            raw = walked.absolute_path.read_bytes()
        except OSError:
            scan.not_read.append((relative, REASON_READ_ERROR))
            continue

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = None

        scan.contents[relative] = Contents(
            relative_path=relative,
            sha256=hashlib.sha256(raw).hexdigest(),
            size_bytes=len(raw),
            text=text,
        )
        if not raw:
            scan.zero_byte.append(relative)
        if text is not None:
            _read_evidence(scan, repo_root, relative, text)
    return scan


def _read_evidence(scan: Scan, repo_root: Path, relative: str, text: str) -> None:
    """Every rung this one file has something to say about."""
    header = header_producer(text)
    if header is not None:
        address, line = header
        scan.productions.append(
            _production(repo_root, address, relative, ARTIFACT_HEADER, relative, line)
        )
    elif declares_generation(text):
        scan.declared_without_producer.append(relative)

    suffix = PurePosixPath(relative).suffix.lower()
    if suffix in _MANIFEST_SUFFIXES:
        scan.productions.extend(manifest_productions(repo_root, relative, text))
    if suffix in _SCRIPT_SUFFIXES:
        scan.productions.extend(script_productions(repo_root, relative, text))


def _production(repo_root: Path, address: str, artifact_path: str,
                evidence: str, evidence_path: str, line: int) -> Production:
    """Resolve one producer address against the repository it was written in."""
    resolution = pointer_module.resolve(address, repo_root, evidence_path)
    resolved = resolution.target_path if resolution and resolution.resolved else None
    return Production(
        producer_address=address,
        producer_path=resolved,
        artifact_path=artifact_path,
        evidence=evidence,
        evidence_path=evidence_path,
        evidence_line=line,
    )


def producer_name(token: str) -> str:
    """The first token of a parsed producer name, with header syntax trimmed.

    A generation header is written inside a comment, and the comment's own
    closing syntax rides along on the token: `Generated by scripts/build.py --
    DO NOT EDIT -->`. Only the first token is the name, and the trailing syntax
    is trimmed off it -- otherwise the name resolves to nothing and a producer
    the estate did name is reported as one it did not.
    """
    name = token.strip(_SURROUNDING)
    trimming = True
    while trimming:
        trimming = False
        for closing in _CLOSING_SYNTAX:
            if name.endswith(closing):
                name = name[: -len(closing)]
                trimming = True
        trimmed = name.rstrip(_TRAILING).strip(_SURROUNDING)
        if trimmed != name:
            name = trimmed
            trimming = True
    return name


def header_lines(text: str) -> list[tuple[int, str]]:
    """The opening lines a generation header could be written on, 1-based.

    A comment, or a line inside the leading frontmatter block. A sentence in
    prose is neither, however much it says about generation: reading one as a
    header makes an artifact out of a document that only mentions one.
    """
    lines = text.splitlines(keepends=True)
    frontmatter = set(pointer_module.frontmatter_lines(lines))
    return [
        (index + 1, line)
        for index, line in enumerate(lines[:HEADER_LINES])
        if index in frontmatter or _COMMENT_LINE.match(line)
    ]


def header_producer(text: str) -> tuple[str, int] | None:
    """The producer a file's header names, with the 1-based line, or None."""
    for number, line in header_lines(text):
        match = _GENERATED_BY.search(line)
        if not match:
            continue
        name = producer_name(match.group(1))
        if pointer_module.path_shaped(name.lstrip("/")):
            return name, number
    return None


def declares_generation(text: str) -> bool:
    """Whether a file's header says it was generated, naming nothing."""
    return any(_GENERATION_DECLARED.search(line) for _, line in header_lines(text))


def _declarations(text: str, suffix: str) -> list[tuple[dict[str, list[str]], int]]:
    """Every mapping in a manifest, as its string values and its first line.

    JSON is read by the locating parser this project already uses for settings
    files; YAML through ``yaml.compose``, whose nodes carry their own marks.
    Both come back in one shape so the rule that reads a declaration is written
    once.
    """
    if suffix == ".json":
        try:
            document = parse_json(text)
        except JsonLocationError:
            return []
        return _json_mappings(document, document.root)
    try:
        node = yaml.compose(text)
    except yaml.YAMLError:
        return []
    return _yaml_mappings(node)


def _json_mappings(document, node: Node) -> list[tuple[dict[str, list[str]], int]]:
    found: list[tuple[dict[str, list[str]], int]] = []
    items = node.items()
    if items:
        values: dict[str, list[str]] = {}
        for key, child in items:
            strings = _json_strings(child)
            if strings:
                values[key] = strings
        if values:
            found.append((values, document.line_of(node.start)))
    for _, child in items:
        found.extend(_json_mappings(document, child))
    for child in node.elements():
        found.extend(_json_mappings(document, child))
    return found


def _json_strings(node: Node) -> list[str]:
    """A string value, or the strings of an array of them. Nothing else."""
    text = node.text_value()
    if text is not None:
        return [text]
    return [value for child in node.elements()
            if (value := child.text_value()) is not None]


def _yaml_mappings(node) -> list[tuple[dict[str, list[str]], int]]:
    if node is None:
        return []
    found: list[tuple[dict[str, list[str]], int]] = []
    if isinstance(node, yaml.MappingNode):
        values: dict[str, list[str]] = {}
        for key_node, child in node.value:
            if not isinstance(key_node, yaml.ScalarNode):
                continue
            strings = _yaml_strings(child)
            if strings:
                values[str(key_node.value)] = strings
        if values:
            found.append((values, node.start_mark.line + 1))
        for _, child in node.value:
            found.extend(_yaml_mappings(child))
    elif isinstance(node, yaml.SequenceNode):
        for child in node.value:
            found.extend(_yaml_mappings(child))
    return found


def _yaml_strings(node) -> list[str]:
    if isinstance(node, yaml.ScalarNode):
        return [str(node.value)]
    if isinstance(node, yaml.SequenceNode):
        return [str(child.value) for child in node.value
                if isinstance(child, yaml.ScalarNode)]
    return []


def manifest_productions(repo_root: Path, relative: str,
                         text: str) -> list[Production]:
    """Rung 2: a mapping that declares an input and an output, both in the tree.

    Both ends have to resolve to files that are there. A declaration naming
    something absent is a statement about a build that has not run, and reading
    it as a producer would put a pair in the graph that the tree does not hold.
    """
    suffix = PurePosixPath(relative).suffix.lower()
    found: list[Production] = []
    for values, line in _declarations(text, suffix):
        inputs = [value for key in values if key.lower() in _INPUT_KEYS
                  for value in values[key]]
        outputs = [value for key in values if key.lower() in _OUTPUT_KEYS
                   for value in values[key]]
        if not inputs or not outputs:
            continue
        for produced in outputs:
            artifact = _in_tree(repo_root, relative, produced)
            if artifact is None:
                continue
            for consumed in inputs:
                if _in_tree(repo_root, relative, consumed) is None:
                    continue
                found.append(
                    _production(repo_root, consumed, artifact,
                                MANIFEST_DECLARATION, relative, line)
                )
    return found


def script_productions(repo_root: Path, relative: str, text: str) -> list[Production]:
    """Rung 3: a script naming, literally, a path in the tree that it writes.

    A line offers targets only if it says it writes -- an open in a write mode,
    one of the write calls, or a shell redirect. The target then has to be a
    file that is there, which is what keeps a format string, a URL fragment or
    an option value out of the graph.
    """
    shell = PurePosixPath(relative).suffix.lower() in _SHELL_SUFFIXES
    found: list[Production] = []
    for number, line in enumerate(text.splitlines(), start=1):
        candidates: list[str] = []
        if _WRITE_CALLS.search(line):
            candidates += [match.group(1) for match in _QUOTED.finditer(line)]
        if shell:
            candidates += [match.group(1) for match in _REDIRECT.finditer(line)]
        if not candidates:
            continue
        for candidate in candidates:
            artifact = _in_tree(repo_root, relative, candidate)
            if artifact is None or artifact == relative:
                continue
            found.append(
                Production(
                    producer_address=relative,
                    producer_path=relative,
                    artifact_path=artifact,
                    evidence=LITERAL_WRITE_PATH,
                    evidence_path=relative,
                    evidence_line=number,
                )
            )
    return found


def _in_tree(repo_root: Path, written_in: str, address: str) -> str | None:
    """The repository-relative path an address lands on, or None."""
    if not pointer_module.path_shaped(address.lstrip("/")):
        return None
    resolution = pointer_module.resolve(address, repo_root, written_in)
    if resolution is None or not resolution.resolved:
        return None
    return resolution.target_path


def pairs(contents: dict[str, Contents], zero_byte: list[str]) -> list[Pair]:
    """Every unordered pair of files whose bytes hash the same.

    One row per pair, with the lexicographically first path as the source: the
    relation is symmetric, and writing it both ways would be one fact counted
    twice.
    """
    empty = set(zero_byte)
    groups: dict[str, list[str]] = {}
    for path, content in sorted(contents.items()):
        if path in empty:
            continue
        groups.setdefault(content.sha256, []).append(path)
    found: list[Pair] = []
    for sha256, paths in sorted(groups.items()):
        if len(paths) < 2:
            continue
        for index, first in enumerate(paths):
            for second in paths[index + 1:]:
                found.append(Pair(sha256, first, second))
    return found


def strongest(productions: list[Production]) -> list[Production]:
    """One artifact's strongest rung, and only that rung.

    An artifact whose header names its producer is not also reported from the
    script that writes it: that is one fact, and the ladder exists to say how
    well it is evidenced, not to count it once per rung. Two producers on the
    same rung are both kept -- that is two facts.
    """
    by_artifact: dict[str, list[Production]] = {}
    for production in productions:
        by_artifact.setdefault(production.artifact_path, []).append(production)

    kept: list[Production] = []
    for artifact in sorted(by_artifact):
        found = by_artifact[artifact]
        rung = min(EVIDENCE_LADDER.index(one.evidence) for one in found)
        seen: set[tuple[str | None, str]] = set()
        for production in found:
            if EVIDENCE_LADDER.index(production.evidence) != rung:
                continue
            key = (production.producer_path, production.producer_address)
            if key in seen:
                continue
            seen.add(key)
            kept.append(production)
    return kept


def directions(matched: list[Pair],
               productions: list[Production]) -> list[Direction]:
    """Order each pair where the evidence orders it, and say why where it does not.

    **A pair is ordered only by a ``PRODUCES`` edge between its own two ends.**
    That is the whole rule, and everything else about it is a refusal.

    A producer somewhere else in the tree does not order a pair. Two files that
    are the same bytes, one of which some script wrote, says that the script
    wrote one of them -- not that the other is where it came from. Reading the
    second out of the first is the promotion this project exists to refuse, and
    a promoted direction is indistinguishable in the output from an observed
    one, which is what makes it worse than no direction at all.

    A relationship stated in prose does not order a pair either, and it does not
    reach this function to be refused: nothing upstream turns a sentence into a
    ``Production``, so a sentence arrives here as the absence of evidence. Spec
    0001 s14 keeps prose provenance a permanent UNKNOWN.

    Where a later ticket wants the direction the corpus only describes, the
    honest route is a machine-readable declaration in the corpus -- which is a
    change to the corpus, not to this rule.
    """
    ordered: list[Direction] = []
    # Keyed on both ends, so the lookup is the question being asked: is there a
    # production whose producer is one end of *this* pair and whose artifact is
    # the other. Only resolved producers -- an edge needs both ends, and a
    # producer named but not in the tree cannot be one of them.
    between = {
        (one.producer_path, one.artifact_path): one
        for one in productions if one.producer_path is not None
    }
    produced = {one.artifact_path for one in productions
                if one.producer_path is not None}

    for pair in matched:
        first, second = pair.first_path, pair.second_path
        forward = between.get((first, second))
        backward = between.get((second, first))
        if forward is not None and backward is not None:
            # Two claims, each naming the other end as its producer. Choosing
            # between them would be this tool deciding, and it has no basis to.
            ordered.append(_unordered(pair, EACH_END_NAMES_THE_OTHER))
            continue
        found = forward or backward
        if found is not None:
            ordered.append(Direction(
                pair=pair,
                direction=(SOURCE_PRODUCES_TARGET if forward is not None
                           else TARGET_PRODUCES_SOURCE),
                producer_path=found.producer_path,
                artifact_path=found.artifact_path,
                evidence=found.evidence,
                evidence_path=found.evidence_path,
                evidence_line=found.evidence_line,
            ))
            continue
        ordered.append(_unordered(
            pair,
            PRODUCER_OUTSIDE_THE_PAIR
            if first in produced or second in produced
            else NO_PRODUCER_AT_EITHER_END,
        ))
    return ordered


def _unordered(pair: Pair, reason: str) -> Direction:
    return Direction(pair=pair, direction=DIRECTION_UNKNOWN, reason=reason)


def summary(scan: Scan, matched: list[Pair],
            productions: list[Production]) -> dict:
    """The one place a pair count is produced -- always beside its provenance.

    A bare count of byte-identical pairs over-reads badly, so the count of
    pairs carrying provenance evidence, and the count carrying none, are
    returned in the same dict rather than left to a caller to remember. Every
    key is present at zero, including each rung of the ladder, so a rung that
    found nothing reads as a rung that found nothing.

    The direction counts are here for the same reason and by the same rule.
    ``pairs_with_a_direction`` and ``pairs_with_no_direction`` sum to ``pairs``,
    and the second is split by *why* rather than reported as one number: a pair
    nothing evidences at all and a pair whose producer is a third file are
    different statements, and a single "no direction" count says neither.

    :func:`directions` is called here rather than passed in, so that a caller
    holding pairs and productions cannot produce these counts against a
    different reading of them than the rows carry.
    """
    ordered = directions(matched, productions)
    not_read_by_reason = {reason: 0 for reason in NOT_READ_REASONS}
    for _, reason in scan.not_read:
        not_read_by_reason[reason] = not_read_by_reason.get(reason, 0) + 1
    by_reason = {reason: 0 for reason in DIRECTION_UNKNOWN_REASONS}
    by_direction_evidence = {rung: 0 for rung in EVIDENCE_LADDER}
    with_a_direction = 0
    for one in ordered:
        if one.direction == DIRECTION_UNKNOWN:
            by_reason[one.reason] += 1
            continue
        with_a_direction += 1
        by_direction_evidence[one.evidence] += 1

    # Ticket 05's count, unmoved: a pair carries provenance where a producer
    # reaches either end. Derived from the reasons rather than recomputed, so
    # the two readings cannot come apart -- a pair with no producer at either
    # end is exactly the pair ticket 05 counted as carrying none.
    without_provenance = by_reason[NO_PRODUCER_AT_EITHER_END]
    with_provenance = len(matched) - without_provenance

    by_evidence = {rung: 0 for rung in EVIDENCE_LADDER}
    unresolved = 0
    for production in productions:
        if production.producer_path is None:
            unresolved += 1
            continue
        by_evidence[production.evidence] += 1
    return {
        "pairs": len(matched),
        "pairs_with_provenance": with_provenance,
        "pairs_without_provenance": without_provenance,
        "pairs_with_a_direction": with_a_direction,
        "pairs_by_direction_evidence": by_direction_evidence,
        "pairs_with_no_direction": by_reason,
        "produces_edges": sum(by_evidence.values()),
        "produces_by_evidence": by_evidence,
        "generation_declared_without_producer_named":
            len(scan.declared_without_producer),
        "producer_named_no_indexed_target_match": unresolved,
        "files_hashed": len(scan.contents),
        "files_not_read": len(scan.not_read),
        "files_not_read_by_reason": not_read_by_reason,
        "zero_byte_files_not_paired": len(scan.zero_byte),
    }


def totals(summaries) -> dict:
    """Sum per-repository summaries, keeping every key and the same shape."""
    total = summary(Scan(), [], [])
    for one in summaries:
        for key, value in one.items():
            if isinstance(value, dict):
                for rung, count in value.items():
                    total[key][rung] += count
            else:
                total[key] += value
    return total
