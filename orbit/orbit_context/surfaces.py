"""Detect governance objects, and read them.

Six kinds of thing can put text into an assistant session, and they are not all
files. An instruction surface, a skill package, an agent definition and a slash
command are files; a hook definition and an MCP server are entries inside a
settings file. Both become rows in the same table, told apart by
``surface_kind`` and by whether they carry a line locator.

Rows are additive. A hook script is a hook target *and* whatever else it is;
detecting it twice is the record being honest, not a collision to resolve.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import yaml

from . import pointers as pointer_module
from . import settings as settings_module
from .jsonloc import JsonLocationError, parse as parse_json

INSTRUCTION_SURFACE = "instruction-surface"
SKILL_PACKAGE = "skill-package"
AGENT_DEFINITION = "agent-definition"
COMMAND_DEFINITION = "command-definition"
HOOK_DEFINITION = "hook-definition"
MCP_CONFIG = "mcp-config"
# The additive seventh: a file a hook command resolves to. Written as well as,
# never instead of, whatever else that file is.
HOOK_TARGET = "hook-target"

SURFACE_KINDS = (
    INSTRUCTION_SURFACE,
    SKILL_PACKAGE,
    AGENT_DEFINITION,
    COMMAND_DEFINITION,
    HOOK_DEFINITION,
    MCP_CONFIG,
    HOOK_TARGET,
)

# A candidate kind, never a surface_kind: a settings file is the container for
# hook and MCP rows, and is not itself a row.
SETTINGS_CONTAINER = "settings-container"

# The surfaces cut into clauses. Whole-file, and read as Markdown-shaped text.
# A hook definition and an MCP server are entries inside JSON; a hook target is
# whatever file a command happens to point at. Neither is segmented here.
SEGMENTED_KINDS = (
    INSTRUCTION_SURFACE,
    SKILL_PACKAGE,
    AGENT_DEFINITION,
    COMMAND_DEFINITION,
)

# Matched on the file's basename.
SURFACE_BASENAMES: dict[str, str] = {
    "CLAUDE.md": INSTRUCTION_SURFACE,
    "AGENTS.md": INSTRUCTION_SURFACE,
    "GEMINI.md": INSTRUCTION_SURFACE,
    ".cursorrules": INSTRUCTION_SURFACE,
    "SKILL.md": SKILL_PACKAGE,
}

# Matched on the repository-relative path.
SURFACE_RELATIVE_PATHS: dict[str, str] = {
    ".github/copilot-instructions.md": INSTRUCTION_SURFACE,
    ".mcp.json": MCP_CONFIG,
    ".cursor/mcp.json": MCP_CONFIG,
    ".vscode/mcp.json": MCP_CONFIG,
    ".claude/settings.json": SETTINGS_CONTAINER,
    ".claude/settings.local.json": SETTINGS_CONTAINER,
}

# Matched on a directory prefix plus a suffix, at any depth below the prefix.
SURFACE_DIRECTORIES: tuple[tuple[str, str, str], ...] = (
    (".claude/agents/", ".md", AGENT_DEFINITION),
    (".claude/commands/", ".md", COMMAND_DEFINITION),
)

# --- Recognition without a vendor name -------------------------------------
#
# The three tables above recognise governance by the name a vendor gave it.
# Run against a repository whose whole content is governance and none of it is
# vendor-named, that recognises nothing: Advisor-Desk at `main` is 184 Markdown
# files of distilled engineering rules and phase 1 found 0 of them.
#
# Two further rules, in the order they are applied.

# **The file says so.** Every rule file in that corpus opens the same way --
# `# OBEY Refactoring by Martin Fowler` -- and nothing that is not a rule file
# does. A first heading addressed at the agent is the same class of statement as
# a filename a vendor defined: the estate declaring what a file is for. So it is
# a table, like the vendor tables, holding what has been observed rather than
# what could exist. One word today. Adding a second moves the detector version,
# which is the mechanism that keeps two counts either side of it comparable.
DIRECTIVE_HEADING_WORDS = ("OBEY",)

# What the corpus rule below counts. A governance corpus is Markdown; a
# directory of source files that happens to hold one rule file is not one.
CORPUS_SUFFIXES = (".md",)

# How far into a file the first heading is looked for. A heading past this is
# not read, which is a detector input rather than an accident and is why the
# number is here.
MARKER_SCAN_BYTES = 8 * 1024

# **The corpus says so.** Three files in the rule workbench carry no heading of
# their own -- `PROCESS.md`, `RELEASE.md`, `CHECK_COMPATIBILITY.md` -- and are
# governance all the same: they are the instructions for compressing a book,
# addressed at an agent. What identifies them is where they sit. So a directory
# whose Markdown mostly declares itself is a corpus, and the rest of its
# Markdown is recognised with it.
#
# This is the one inference in the module, and it is recorded as one: rows found
# this way carry `corpus-adjacent` in the `recognition` column and are separable
# from everything the estate stated outright.
CORPUS_DECLARED_SHARE = 0.75
# A directory of one or two files proves nothing about itself. `_rule-workbench`
# clears this at 42 of 45; a directory holding a single rule file does not.
CORPUS_MINIMUM_FILES = 3
# Depth below the repository root a corpus starts at. The root itself is depth
# 0 and is deliberately out of reach: a repository that happened to be mostly
# rule files would otherwise promote every file in it, which is spec 0002 s12's
# kill condition rather than a result. Advisor-Desk's root sits at 84 of 184,
# well under the share, but the guard is not left to that margin.
CORPUS_MINIMUM_DEPTH = 1

# --- The ladder ------------------------------------------------------------
#
# This repository implements progressive disclosure by hand, fourteen times: one
# book at three sizes, so a session loads the rung its workflow can afford.
#
#     refactoring/refactoring.md       17,866 bytes
#     refactoring/refactoring.mini.md   5,167
#     refactoring/refactoring.nano.md   1,986
#
# What relates those three files is their names, and only their names. So the
# rule is a table of the rung words that have been observed, and the relation it
# produces says what the names say and stops there -- not that the nano rung was
# derived from the full one. Spec 0001 s14 keeps "whether two identical files
# are intentionally identical" a permanent UNKNOWN, and a derivation nothing
# observed would be the same over-read. Where the estate evidences one, PRODUCES
# carries it.
#
# **The convention is this repository's, not a standard.** Nobody defined
# `.mini.md` the way Anthropic defined `CLAUDE.md`. A repository naming its
# rungs otherwise has no ladders *found* by this rule, which is not the same
# statement as no ladders, and every command that prints a count prints the rule
# beside it. The table is the extension point, and adding a word to it moves the
# detector set version on its own.
#
# One repository already carries a second shape: `_rule-workbench/<book>/` holds
# `mini.md` and `nano.md` with no stem in front of them, so the directory is the
# book and the filename is the rung alone. That shape is *not* keyed on here.
# Reaching it means a rule that reads a directory rather than a name, which is
# the corpus rule's kind of inference rather than this one's, and it would put
# the workbench's rungs and the published rungs in one count under one word
# without saying which was read how.
#
# **Nothing is lost by that here, and it was measured rather than assumed.** All
# 28 workbench rungs are byte-identical to their published twins, so each one
# already reaches its book's ladder in two hops -- IDENTICAL_BYTES to the
# published rung, then RUNG_OF to the base rung -- carrying the right rung word
# on arrival. The relation is in the graph; only the label is not.
#
# That path holds because the copies are identical, which is a property of this
# repository rather than of the shape. A repository using this shape *without*
# identical twins would not have it, and its ladders would come back low. That
# is the case worth looking at before the rule is widened, and it is C2's --
# spec 0002 s11 refuses a rule built for a repository nobody has looked at.
RUNG_WORDS = ("mini", "nano")

# The suffix a rung carries. A ladder is Markdown; a directory of source files
# named the same way is not one.
RUNG_SUFFIX = ".md"

# Built from the table above, so a word added there reaches the pattern and the
# detector version together. The stem is required to be non-empty: a file named
# `mini.md` is named for the rung alone, which is the workbench's shape and not
# this one.
_RUNG_NAME = re.compile(
    r"^(?P<stem>.+)\.(?P<rung>"
    + "|".join(RUNG_WORDS)
    + r")"
    + re.escape(RUNG_SUFFIX)
    + r"$"
)

# What the `recognition` column carries -- how the tool came to call this a
# surface, which a `surface_kind` alone cannot say.
RECOGNITION_VENDOR_NAME = "vendor-name"
RECOGNITION_DECLARED_MARKER = "declared-marker"
RECOGNITION_CORPUS_ADJACENT = "corpus-adjacent"

RECOGNITION_KINDS = (
    RECOGNITION_VENDOR_NAME,
    RECOGNITION_DECLARED_MARKER,
    RECOGNITION_CORPUS_ADJACENT,
)

# The values that are this tool's reading rather than the estate's statement.
# Named as a table so a count can exclude them without knowing which is which.
INFERRED_RECOGNITIONS = (RECOGNITION_CORPUS_ADJACENT,)

_DIRECTIVE_HEADING = re.compile(
    r"^#[ \t]+(?:" + "|".join(DIRECTIVE_HEADING_WORDS) + r")\b"
)


# Directories never walked. `.git` is Orbit's own convention; the rest hold
# vendored trees whose surfaces belong to another estate.
PRUNED_DIRECTORIES = frozenset(
    {".git", "node_modules", "target", "vendor", "__pycache__", ".venv", "venv"}
)

# A surface larger than this is recorded with a reason instead of read.
MAX_SURFACE_BYTES = 5 * 1024 * 1024

# Reasons written to the `reason` column and to the JSON statistics. Kept
# outside the constrained vocabulary (see orbit/tests/test_vocabulary.py).
REASON_INVALID_UTF8 = "invalid_utf8"
REASON_OVERSIZE = "oversize"
REASON_READ_ERROR = "read_error"
REASON_NOT_A_FILE = "not_a_file"
# GitLab Orbit's word for a symlink, in our kebab-case. Theirs is
# `FilterSkip::NonRegularFile` (crates/code-graph/src/v2/config/filter.rs:51),
# surfaced as the metric label documented at
# crates/orbit-observability/src/indexer/code.rs:152 -- "non_regular_file (a
# symlink -- a node, never parsed)" -- in the same list as `oversize`, `binary`
# and `not_utf8`, which is this family. Adopted rather than invented: we had
# written our own answer to symlinks without checking whether they had one.
REASON_NON_REGULAR_FILE = "non-regular-file"
REASON_OUTSIDE_REPOSITORY = "outside_indexed_repository"
REASON_INVALID_JSON = "invalid_json"
REASON_FRONTMATTER_DECLARATION_ABSENT = "frontmatter_declaration_absent"

INDEXED = ""

# The frontmatter fields a skill package and an agent definition must declare
# to be one. Both load at boot for every session; the body does not.
DECLARED_FIELDS = ("name", "description")

FRONTMATTER_FENCE = "---"


def classify(relative_path: str) -> str | None:
    """The candidate kind for a repository-relative path, or None.

    Provisional: `skill-package` and `agent-definition` still have to declare
    themselves in frontmatter, and `settings-container` expands into rows
    rather than becoming one.
    """
    posix = PurePosixPath(relative_path).as_posix()
    kind = SURFACE_RELATIVE_PATHS.get(posix)
    if kind is not None:
        return kind
    for prefix, suffix, directory_kind in SURFACE_DIRECTORIES:
        if posix.startswith(prefix) and posix.endswith(suffix):
            return directory_kind
    return SURFACE_BASENAMES.get(PurePosixPath(posix).name)


@dataclass(frozen=True)
class WalkedFile:
    """One file the walk reached. Not every file is a candidate."""

    relative_path: str
    absolute_path: Path
    # A symlink: a node this walk lists and never reads. Carried from the walk
    # rather than re-tested downstream, so that "is this a file we opened" has
    # one answer per entry and the corpus rule, the reader and the hasher
    # cannot come apart on it.
    non_regular: bool = False


@dataclass(frozen=True)
class Candidate:
    """A path something says is worth reading, and what said so."""

    relative_path: str
    absolute_path: Path
    kind: str
    recognition: str = RECOGNITION_VENDOR_NAME
    # The walk's answer, carried through: a name is enough to make a link a
    # candidate, and never enough to make it readable.
    non_regular: bool = False


@dataclass(frozen=True)
class Detected:
    """One row-to-be. Fields left None are facts this kind does not carry."""

    relative_path: str
    kind: str
    size_bytes: int
    # How the tool came to call this a surface. Rows expanded out of a
    # container carry the container's, because the chain that reached them
    # starts at the vendor name on the settings file.
    recognition: str = RECOGNITION_VENDOR_NAME
    reason: str = INDEXED
    detail: str = ""
    errored: bool = False
    # A node listed without its bytes. Not a column: it is what tells the row
    # writer there is no digest to take, and taking one would follow the link.
    non_regular: bool = False
    name: str | None = None
    frontmatter_bytes: int | None = None
    body_bytes: int | None = None
    start_line: int | None = None
    end_line: int | None = None
    matcher: str | None = None
    target_path: str | None = None
    target_resolution: str | None = None
    # Character offset of an entry within its file. Not a column: it is what
    # tells two entries apart when the row id is derived, and a settings file
    # written on one line would otherwise collapse all its hooks into one row.
    start_offset: int | None = None
    # The addresses written inside this surface, unresolved. Not columns either:
    # each becomes a row of its own in `gl_context_edge`, and resolving them
    # needs every surface in the repository to have been found first.
    pointers: tuple[pointer_module.Pointer, ...] = ()


@dataclass(frozen=True)
class Note:
    """Something present that did not become a row, and why."""

    relative_path: str
    reason: str
    detail: str = ""
    errored: bool = False


@dataclass(frozen=True)
class Reading:
    """The outcome of reading one candidate."""

    size_bytes: int
    reason: str
    detail: str = ""
    errored: bool = False
    text: str | None = None

    @property
    def indexed(self) -> bool:
        return self.reason == INDEXED


@dataclass(frozen=True)
class Frontmatter:
    """The leading `---` block of a Markdown surface, measured and read.

    ``fields`` is None where the block is absent or is not a YAML mapping. The
    byte split still holds in that case: what the file spends on a header it
    does not spend on a body.
    """

    fields: dict | None
    frontmatter_bytes: int
    body_bytes: int

    def declares(self, *names: str) -> bool:
        if not self.fields:
            return False
        return all(self.fields.get(name) for name in names)

    @property
    def name(self) -> str | None:
        if not self.fields:
            return None
        value = self.fields.get("name")
        return value if isinstance(value, str) else None


def split_frontmatter(text: str) -> Frontmatter:
    """Measure the frontmatter block against the body, and read its fields.

    The description in a skill's frontmatter loads at boot for every session;
    the body loads only when the skill is invoked. Summing them reports the
    boot cost as the whole file, which overstates it by an order of magnitude.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != FRONTMATTER_FENCE:
        return Frontmatter(None, 0, len(text.encode("utf-8")))

    closing = None
    for number, line in enumerate(lines[1:], start=1):
        if line.strip() == FRONTMATTER_FENCE:
            closing = number
            break
    if closing is None:
        return Frontmatter(None, 0, len(text.encode("utf-8")))

    block = "".join(lines[: closing + 1])
    body = "".join(lines[closing + 1 :])
    try:
        document = yaml.safe_load("".join(lines[1:closing]))
    except yaml.YAMLError:
        document = None
    fields = document if isinstance(document, dict) else None
    return Frontmatter(
        fields,
        len(block.encode("utf-8")),
        len(body.encode("utf-8")),
    )


def walk_files(repo_root: Path, nested_repos: list[Path] | None = None) -> list[WalkedFile]:
    """Every file in one repository, in sorted path order.

    The walk is shared: a surface is one of these files that also carries a
    name or a location this indexer recognises, and everything else is still a
    file that can be hashed. Two walks would be two answers to "what is in this
    repository", and the pruning rules would have to agree by hand.

    Files belonging to a nested repository are left to that repository.

    **A symlink is a node, listed and never read**, which is GitLab Orbit's rule
    and not ours: their walk accepts an entry that is a file *or* a symlink and
    skips only what is neither (`crates/utils/src/walk.rs:37-41`), and it is
    routed away from the reader rather than out of the walk (`:53-57`). Tested
    with ``is_symlink`` before ``is_dir``, so a link to a directory is one node
    and not a second pass over the tree it names -- descending would walk one
    file twice under two paths and count it as two.
    """
    nested = {p.resolve() for p in (nested_repos or [])}
    found: list[WalkedFile] = []
    stack = [repo_root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_symlink():
                found.append(_listed(entry, repo_root))
                continue
            if entry.is_dir():
                if entry.name in PRUNED_DIRECTORIES:
                    continue
                if entry.resolve() in nested:
                    continue
                stack.append(entry)
                continue
            if not entry.is_file():
                continue
            found.append(WalkedFile(entry.relative_to(repo_root).as_posix(), entry))
    return sorted(found, key=lambda walked: walked.relative_path)


def _listed(entry: Path, root: Path) -> WalkedFile:
    """One node the walk lists without opening."""
    return WalkedFile(entry.relative_to(root).as_posix(), entry, non_regular=True)


def link_size(path: Path) -> int:
    """A link's own size, from ``lstat`` -- never its target's.

    GitLab takes the same figure the same way (`crates/utils/src/walk.rs:47`).
    On this estate ``full.md`` is 32 bytes, not the 17,866 of the book it names,
    and reporting the target's would put one book's bytes in the total twice.
    """
    try:
        return path.lstat().st_size
    except OSError:
        return 0


def first_heading(text: str) -> str:
    """The file's first Markdown heading line, or empty where it has none."""
    for line in text.splitlines():
        if line.startswith("#"):
            return line
    return ""


def declares_directive(text: str) -> bool:
    """Whether this text opens with a heading addressed at the agent.

    The file's own statement about what it is for, in the same class as a
    filename a vendor defined. Only the *first* heading counts: a directive
    heading further down is a section of a document rather than the document
    declaring itself, and taking those would recognise anything that quotes a
    rule file, this project's own tickets included.
    """
    return _DIRECTIVE_HEADING.match(first_heading(text)) is not None


def rung_of(relative_path: str) -> tuple[str, str] | None:
    """The base rung this filename names, and the rung word it carries.

    ``refactoring/refactoring.mini.md`` returns
    ``("refactoring/refactoring.md", "mini")``: the file in the same directory
    named by the stem alone, and the word that told us so. None where the name
    carries no rung word.

    Naming the base rung is not the same as finding it. Whether that file is in
    the tree, and whether it is a surface, is the caller's question -- a
    relation needs both ends, and inventing the missing one would put a file in
    the graph that the repository does not hold.
    """
    posix = PurePosixPath(relative_path)
    match = _RUNG_NAME.match(posix.name)
    if match is None:
        return None
    base = posix.with_name(match.group("stem") + RUNG_SUFFIX).as_posix()
    return base, match.group("rung")


def _scan_head(path: Path) -> str:
    """The first bytes of a file, decoded as far as they go.

    A file that cannot be read declares nothing. It is not an error here: if it
    is a surface by name it becomes a row with a reason on it further down, and
    if it is not, an unreadable file is simply not a surface.
    """
    try:
        with path.open("rb") as handle:
            raw = handle.read(MARKER_SCAN_BYTES)
    except OSError:
        return ""
    return raw.decode("utf-8", errors="replace")


def declared_paths(walked_files: list[WalkedFile]) -> set[str]:
    """The walked files whose own first heading declares them governance.

    Only files that were read. A node the walk listed without loading has no
    first heading to offer, and opening one here would read through the link.
    """
    return {
        walked.relative_path
        for walked in walked_files
        if not walked.non_regular
        and walked.relative_path.endswith(CORPUS_SUFFIXES)
        and declares_directive(_scan_head(walked.absolute_path))
    }


def corpus_directories(corpus_files: set[str], declared: set[str]) -> set[str]:
    """The directories whose corpus files mostly declare themselves.

    Counted over the whole subtree rather than the immediate directory. The
    workbench that made this rule necessary holds its declared files one level
    down and its undeclared ones at the top, so an immediate-directory count
    reads it as 0 of 3 and recognises exactly the files the rule exists for.
    """
    tallies: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for path in corpus_files:
        segments = PurePosixPath(path).parts[:-1]
        for depth in range(CORPUS_MINIMUM_DEPTH, len(segments) + 1):
            tally = tallies["/".join(segments[:depth])]
            tally[1] += 1
            if path in declared:
                tally[0] += 1
    return {
        directory
        for directory, (declares, total) in tallies.items()
        if total >= CORPUS_MINIMUM_FILES
        and declares >= total * CORPUS_DECLARED_SHARE
    }


def _within(path: str, directories: set[str]) -> bool:
    segments = PurePosixPath(path).parts[:-1]
    return any(
        "/".join(segments[:depth]) in directories
        for depth in range(CORPUS_MINIMUM_DEPTH, len(segments) + 1)
    )


def candidates(walked_files: list[WalkedFile]) -> list[Candidate]:
    """The walked files something says are worth reading, and what said so.

    Three rules, applied in this order, each a weaker statement than the one
    above it:

    1. a name or location a vendor defined,
    2. a heading the file itself opens with,
    3. the directory the file sits in, where that directory is mostly rule
       files -- the one rule here that reads rather than quotes, and the reason
       the outcome is carried on the row.

    First match wins, so a file carrying both a vendor name and a directive
    heading is recorded under the vendor name. Both say the same thing about
    what the file is; the vendor name is the narrower claim and the older one.

    Only the first rule reaches a node the walk listed without reading: a name
    is readable without opening the file, and the other two are not. Such a
    candidate becomes a row carrying the reason it was not read, the way an
    oversize surface does.
    """
    vendor = {
        walked.relative_path: kind
        for walked in walked_files
        if (kind := classify(walked.relative_path)) is not None
    }
    # **The corpus share is a share of files that were read.** A node the walk
    # listed without loading cannot declare itself, so it must not count against
    # the files that did -- a file that was never opened is not evidence about
    # the directory either way. Measured before it was hit: listing this
    # repository's fourteen `full.md` links into `_rule-workbench` takes it from
    # 42 of 45 declared to 42 of 59, under the share, and the corpus dissolves
    # with nothing in the output saying a symlink rule caused it.
    #
    # It follows that a link is never recognised *by* a corpus either. The
    # corpus rule is this module's one inference and it reads a directory to
    # make it; a file outside what that reading covers is outside its result.
    corpus_files = {
        walked.relative_path
        for walked in walked_files
        if not walked.non_regular
        and walked.relative_path.endswith(CORPUS_SUFFIXES)
    }
    declared = declared_paths(walked_files) - set(vendor)
    # Only files that declared themselves count toward a directory's share. A
    # vendor name is a statement about one file, not about its neighbours: three
    # `SKILL.md` files under `skills/` would otherwise carry `skills/README.md`
    # in as governance, and nothing there said it was.
    corpora = corpus_directories(corpus_files, declared)

    found: list[Candidate] = []
    for walked in walked_files:
        path = walked.relative_path
        if path in vendor:
            recognition, kind = RECOGNITION_VENDOR_NAME, vendor[path]
        elif path in declared:
            recognition, kind = RECOGNITION_DECLARED_MARKER, INSTRUCTION_SURFACE
        elif path in corpus_files and _within(path, corpora):
            recognition, kind = RECOGNITION_CORPUS_ADJACENT, INSTRUCTION_SURFACE
        else:
            continue
        found.append(Candidate(path, walked.absolute_path, kind, recognition,
                               non_regular=walked.non_regular))
    return found


def walk_repo(repo_root: Path, nested_repos: list[Path] | None = None) -> list[Candidate]:
    """Every candidate in one repository, in sorted path order."""
    return candidates(walk_files(repo_root, nested_repos))


def read_candidate(candidate: Candidate) -> Reading:
    """Read a candidate, classifying anything that stops it being indexed.

    A candidate that cannot be read still becomes a row: coverage is a property
    of the record, not a footnote.

    A symlink is settled here rather than in the walk, which is GitLab's own
    arrangement and their reason for it: routed to the filter "so the filter
    stays the single decision point" (`crates/utils/src/fs_stream.rs:114-119`),
    where their default is ``Decision::ListOnly`` -- "record the file as a node
    without loading its bytes" (`fs_stream.rs:22`).
    """
    path = candidate.absolute_path
    if candidate.non_regular:
        return Reading(link_size(path), REASON_NON_REGULAR_FILE, "", errored=False)

    try:
        stat = path.stat()
    except OSError as error:
        return Reading(0, REASON_READ_ERROR, str(error), errored=True)

    if not path.is_file():
        return Reading(0, REASON_NOT_A_FILE, "", errored=False)

    size = stat.st_size
    if size > MAX_SURFACE_BYTES:
        return Reading(size, REASON_OVERSIZE, f"{size} bytes", errored=False)

    try:
        raw = path.read_bytes()
    except OSError as error:
        return Reading(size, REASON_READ_ERROR, str(error), errored=True)

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        return Reading(size, REASON_INVALID_UTF8, f"byte offset {error.start}", errored=False)

    return Reading(size, INDEXED, text=text)


def command_name(relative_path: str) -> str:
    """The name a slash command is invoked by, from its path under commands/."""
    posix = PurePosixPath(relative_path)
    for prefix, _, kind in SURFACE_DIRECTORIES:
        if kind == COMMAND_DEFINITION and posix.as_posix().startswith(prefix):
            return posix.as_posix()[len(prefix) :].removesuffix(posix.suffix)
    return posix.stem


def expand(repo_root: Path, candidate: Candidate,
           reading: Reading) -> tuple[list[Detected], list[Note]]:
    """Turn one read candidate into the rows and notes it produces.

    A whole-file surface becomes a row even when it could not be read -- the
    reason is on the row. A surface that is an *entry* inside a file cannot:
    with the file unparsed there is nothing to say a row about, so it is
    reported in the statistics instead of guessed at.
    """
    container = candidate.kind in (SETTINGS_CONTAINER, MCP_CONFIG)

    if not reading.indexed:
        if container:
            return [], [Note(candidate.relative_path, reading.reason,
                             reading.detail, reading.errored)]
        return [Detected(candidate.relative_path, candidate.kind,
                         reading.size_bytes, candidate.recognition,
                         reading.reason, reading.detail, reading.errored,
                         non_regular=candidate.non_regular)], []

    text = reading.text or ""
    frontmatter = split_frontmatter(text)

    if candidate.kind in (SKILL_PACKAGE, AGENT_DEFINITION):
        if not frontmatter.declares(*DECLARED_FIELDS):
            return [], [Note(candidate.relative_path,
                             REASON_FRONTMATTER_DECLARATION_ABSENT,
                             ", ".join(DECLARED_FIELDS))]
        return [_file_row(candidate, reading, frontmatter, frontmatter.name)], []

    if candidate.kind == COMMAND_DEFINITION:
        return [_file_row(candidate, reading, frontmatter,
                          command_name(candidate.relative_path))], []

    if candidate.kind == INSTRUCTION_SURFACE:
        return [_file_row(candidate, reading, frontmatter, None)], []

    return _expand_container(repo_root, candidate, text)


def _file_row(candidate: Candidate, reading: Reading, frontmatter: Frontmatter,
              name: str | None) -> Detected:
    return Detected(
        relative_path=candidate.relative_path,
        kind=candidate.kind,
        size_bytes=reading.size_bytes,
        recognition=candidate.recognition,
        name=name,
        frontmatter_bytes=frontmatter.frontmatter_bytes,
        body_bytes=frontmatter.body_bytes,
        pointers=tuple(pointer_module.extract(reading.text or "")),
    )


def _expand_container(repo_root: Path, candidate: Candidate,
                      text: str) -> tuple[list[Detected], list[Note]]:
    """Hook and MCP rows from a settings file or an `.mcp.json`."""
    try:
        document = parse_json(text)
    except JsonLocationError as error:
        return [], [Note(candidate.relative_path, REASON_INVALID_JSON, str(error))]

    rows: list[Detected] = []

    for entry in settings_module.hook_entries(document):
        start_line, end_line = document.span_lines(entry.node)
        target_path, resolution = settings_module.resolve_command(entry.command, repo_root)
        rows.append(
            Detected(
                relative_path=candidate.relative_path,
                kind=HOOK_DEFINITION,
                size_bytes=document.size_bytes(entry.node),
                recognition=candidate.recognition,
                name=entry.event,
                start_line=start_line,
                end_line=end_line,
                matcher=entry.matcher,
                target_path=target_path or "",
                target_resolution=resolution,
                start_offset=entry.node.start,
                pointers=tuple(
                    pointer_module.extract_config(document, entry.node, repo_root)
                ),
            )
        )
        if target_path is not None:
            row = _hook_target_row(repo_root, target_path, candidate.recognition)
            if row is not None:
                rows.append(row)

    for server in settings_module.server_entries(document):
        start_line, end_line = document.span_lines(server.node)
        rows.append(
            Detected(
                relative_path=candidate.relative_path,
                kind=MCP_CONFIG,
                size_bytes=document.size_bytes(server.node),
                recognition=candidate.recognition,
                name=server.name,
                start_line=start_line,
                end_line=end_line,
                start_offset=server.node.start,
                pointers=tuple(
                    pointer_module.extract_config(document, server.node, repo_root)
                ),
            )
        )

    return rows, []


def _hook_target_row(repo_root: Path, relative_path: str,
                     recognition: str) -> Detected | None:
    """Mark the file a hook command resolves to as a hook target.

    A command can resolve to a link like anything else, and the rule does not
    change for arriving here rather than through the walk: the size is the
    link's own, and its bytes are not read.
    """
    path = repo_root / relative_path
    if path.is_symlink():
        return Detected(relative_path=relative_path, kind=HOOK_TARGET,
                        size_bytes=link_size(path), recognition=recognition,
                        reason=REASON_NON_REGULAR_FILE, non_regular=True)
    try:
        size = path.stat().st_size
    except OSError:
        return None
    return Detected(relative_path=relative_path, kind=HOOK_TARGET,
                    size_bytes=size, recognition=recognition)


def walk_outside_repos(root: Path, repo_roots: list[Path]) -> list[Candidate]:
    """Candidates under ``root`` that belong to no repository.

    They carry no branch or commit, so they cannot become rows. They are
    reported instead, because a surface that is present but unindexed must not
    read as a surface that is absent.
    """
    repos = {p.resolve() for p in repo_roots}
    walked: list[WalkedFile] = []
    stack = [root]
    while stack:
        current = stack.pop()
        if current.resolve() in repos:
            continue
        try:
            entries = sorted(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_symlink():
                walked.append(_listed(entry, root))
                continue
            if entry.is_dir():
                if entry.name in PRUNED_DIRECTORIES:
                    continue
                stack.append(entry)
                continue
            if not entry.is_file():
                continue
            walked.append(WalkedFile(entry.relative_to(root).as_posix(), entry))
    # The same recogniser the indexed repositories go through. Two would be two
    # answers to "what is a surface", and the one out here would be the answer
    # nobody reads until a count disagrees with itself.
    return sorted(candidates(sorted(walked, key=lambda w: w.relative_path)),
                  key=lambda c: c.relative_path)
