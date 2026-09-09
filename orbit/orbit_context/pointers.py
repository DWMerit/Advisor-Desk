"""Find the pointers a surface writes down, and say where each one lands.

A governance surface names other things: a Markdown link, an ``@import``, a
frontmatter field, a command in a settings file, a path written in prose, a
sentence saying one file supersedes another. Each is a pointer, each becomes a
``REFERENCES`` edge, and a pointer that does not land on an indexed row becomes
an ``ExternalRef`` carrying which of three non-resolutions it met.

Six detectors, each recorded on the edge as its ``subtype``:

``markdown-link``
    ``[text](target)``, an image link, an autolink, or a reference definition.
``frontmatter-field``
    A path written in the leading ``---`` block.
``import-statement``
    ``@path`` -- the import a client expands into the session, which is what an
    import means in a prose estate.
``config-value``
    A path written as a value inside a hook or MCP entry in a settings file.
``bare-path-literal``
    A path written in prose, in backticks or not.
``supersedes-claim``
    A path named on a line where the estate declares a supersession. It is
    recorded as a claim the estate makes and nothing more: a surface that is
    superseded and still loaded is that pair of facts, and this indexer never
    derives a third one from them.

Boundary handling is the whole game
-----------------------------------

A backtick in a negative lookbehind does **not** skip inline code. It shifts the
match *start* into the middle of the token, so a valid path in backticks matches
as a truncated fragment that then cannot resolve. On one real repository that
produced 1,349 phantom findings out of 1,373 -- ninety-six percent of the report
was the tool talking about itself.

So every prose detector here starts from a **consumed** boundary: line start, or
one of whitespace ``` ` ``` ``'`` ``"`` ``(`` ``<`` ``[``. A leading ``/`` is
excluded, so the path half of a URL is not re-matched as a bare path. And a path
is only a pointer if it carries a file extension, and either a ``/`` or an
extension this indexer recognises -- which is what keeps ``0.118.1`` and
``SipHash-1-3`` out of the report.

If a run comes back with unmatched pointers in the thousands, the detector is
wrong, not the estate.
"""

from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

# The same constant the segmenter uses, imported rather than re-spelled: a
# frontmatter field is addressable as a clause and detectable as a pointer, and
# the two have to agree on where the block ends.
from .clauses import FRONTMATTER_FENCE
from .jsonloc import Document, Node
from .settings import (
    RESOLUTION_NO_INDEXED_TARGET_MATCH as NO_INDEXED_TARGET_MATCH,
    expand_variables,
)

MARKDOWN_LINK = "markdown-link"
FRONTMATTER_FIELD = "frontmatter-field"
IMPORT_STATEMENT = "import-statement"
CONFIG_VALUE = "config-value"
BARE_PATH_LITERAL = "bare-path-literal"
SUPERSEDES_CLAIM = "supersedes-claim"

SUBTYPES = (
    MARKDOWN_LINK,
    FRONTMATTER_FIELD,
    IMPORT_STATEMENT,
    CONFIG_VALUE,
    BARE_PATH_LITERAL,
    SUPERSEDES_CLAIM,
)

# The three non-resolutions, fixed and never merged. `no-indexed-target-match`
# is imported rather than re-spelled: a hook command that lands nowhere and a
# link that lands nowhere are the same finding, and two spellings of one string
# drift apart.
OUTSIDE_INDEXED_ROOTS = "outside-indexed-roots"
UNRESOLVABLE_SCHEME = "unresolvable-scheme"

SUB_KINDS = (OUTSIDE_INDEXED_ROOTS, NO_INDEXED_TARGET_MATCH, UNRESOLVABLE_SCHEME)

# Extensions that make a path-shaped token a pointer without a `/` to vouch for
# it. A token with a `/` needs only some extension; a bare `notes.md` needs to be
# one of these, or every version number in prose becomes a finding.
KNOWN_SUFFIXES = frozenset({
    ".md", ".mdc", ".markdown", ".rst", ".txt",
    ".json", ".jsonc", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".sh", ".bash", ".zsh", ".ps1",
    ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".rb", ".pl", ".rs", ".go",
})

# Consumed, never a lookbehind. See the module docstring.
_BOUNDARY = r"(?:^|[\s`'\"(<\[])"
_CLOSE = r"(?=$|[\s`'\")>\],.;:!?#*])"
# `~` is in the class so `@~/.claude/rules.md` reads as one token.
_PATH = r"[A-Za-z0-9_.~\-]+(?:/[A-Za-z0-9_.~\-]+)*"

_BARE_PATH = re.compile(_BOUNDARY + r"(?!/)(" + _PATH + r")" + _CLOSE)
_IMPORT = re.compile(_BOUNDARY + r"@(" + _PATH + r")" + _CLOSE)
# `[text](target "title")` and `![alt](target)`. The target is group 1; a title
# after it is left outside the capture.
_INLINE_LINK = re.compile(r"!?\[(?:[^\]\\]|\\.)*\]\(\s*<?([^)>\s]*)>?[^)]*\)")
# `[label]: target` -- a reference definition, at the start of its line.
_LINK_DEFINITION = re.compile(r"^ {0,3}\[(?:[^\]\\]|\\.)+\]:\s*<?(\S+)>?")
# The estate declaring a supersession, in its own words. What follows on the
# line is scanned for addresses and labelled as the claim rather than as prose.
_SUPERSEDES = re.compile(
    r"\b(?:supersedes|superseded\s+by|replaces|replaced\s+by)\b\s*:?",
    re.IGNORECASE,
)
# Two or more characters before the colon, so a Windows drive letter is not read
# as a URI scheme.
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]+:")

_FENCE = re.compile(r"^([ \t]*)(`{3,}|~{3,})[ \t]*(.*)$")


@dataclass(frozen=True)
class Pointer:
    """One address a surface wrote down, and where in the file it wrote it."""

    address: str
    subtype: str
    line: int              # 1-based, for the file:line locator
    start_byte: int
    end_byte: int
    in_code_fence: bool


@dataclass(frozen=True)
class Resolution:
    """Where a pointer landed. Exactly one of the two fields is set."""

    target_path: str | None    # repository-relative, when it landed in the tree
    sub_kind: str | None       # which non-resolution, when it did not

    @property
    def resolved(self) -> bool:
        return self.target_path is not None


def path_shaped(token: str) -> bool:
    """Whether a token written in prose is worth treating as a path.

    An extension is required, and a token without a ``/`` needs a recognised
    one. This is a stated limit of the detector set, not a claim about the
    estate: a directory named in prose, or a file with an extension not listed
    here and no slash, is not reported at all rather than reported as unmatched.
    """
    if not token or token.startswith("/") or token.endswith("/"):
        return False
    if token.split() != [token]:
        # A whitespace-separated line is a command, not an address. Prose paths
        # cannot contain whitespace at all, so this only reaches config values.
        return False
    if any(not part for part in token.split("/")):
        return False
    suffix = PurePosixPath(token).suffix.lower()
    if not suffix or suffix[1:].isdigit():
        return False
    return True if "/" in token else suffix in KNOWN_SUFFIXES


def _line_byte_offsets(lines: list[str]) -> list[int]:
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line.encode("utf-8")))
    return offsets


def _fenced_lines(lines: list[str]) -> set[int]:
    """Line indices sitting inside a fenced code block.

    The fence markers themselves are not included -- what is flagged is the
    content the estate fenced off, not the fence.
    """
    inside: set[int] = set()
    number = 0
    while number < len(lines):
        opening = _FENCE.match(lines[number])
        if not opening:
            number += 1
            continue
        fence = opening.group(2)
        closed_at = len(lines)
        for candidate in range(number + 1, len(lines)):
            closing = _FENCE.match(lines[candidate])
            if (closing and closing.group(2)[0] == fence[0]
                    and len(closing.group(2)) >= len(fence)
                    and not closing.group(3).strip()):
                closed_at = candidate
                break
        inside.update(range(number + 1, min(closed_at, len(lines))))
        number = closed_at + 1
    return inside


def _frontmatter_lines(lines: list[str]) -> range:
    """The line indices between the leading ``---`` fences, if there are any."""
    if not lines or lines[0].strip() != FRONTMATTER_FENCE:
        return range(0)
    for number, line in enumerate(lines[1:], start=1):
        if line.strip() == FRONTMATTER_FENCE:
            return range(1, number)
    return range(0)


@dataclass(frozen=True)
class _Hit:
    """A detector's raw find: one line, one character span, one address."""

    line_index: int
    start: int
    end: int
    address: str
    subtype: str


def _links(line: str, line_index: int, subtype: str = MARKDOWN_LINK) -> list[_Hit]:
    hits = []
    for pattern in (_INLINE_LINK, _LINK_DEFINITION):
        for match in pattern.finditer(line):
            start, end = match.span(1)
            hits.append(_Hit(line_index, start, end, match.group(1), subtype))
    return hits


# Trailing characters a path can end a sentence against. They are inside the
# token class -- `.` has to be, or no extension would match -- so the greedy
# match takes them and the token has to be trimmed back. Without this,
# `../beta/AGENTS.md.` at the end of a sentence captures the full stop, fails
# the shape test on a suffix of `.`, and the pointer is silently not reported.
_TRAILING = ".,;:-~"


def _trimmed(match: re.Match, group: int = 1) -> tuple[str, int, int]:
    """The captured token with sentence punctuation trimmed off its end."""
    token = match.group(group).rstrip(_TRAILING)
    return token, match.start(group), match.start(group) + len(token)


def _bare_paths(line: str, line_index: int, subtype: str,
                offset: int = 0) -> list[_Hit]:
    hits = []
    for match in _BARE_PATH.finditer(line):
        token, start, end = _trimmed(match)
        if path_shaped(token):
            hits.append(_Hit(line_index, offset + start, offset + end, token, subtype))
    return hits


def _detect(lines: list[str], frontmatter: range) -> list[_Hit]:
    """Every detector, in the order that settles which one owns a span.

    A span claimed by an earlier detector is not offered to a later one, so
    ``[rules](docs/rules.md)`` is one markdown-link rather than also a bare path,
    and a path on a supersession line is the claim rather than prose.
    """
    hits: list[_Hit] = []
    claimed: set[tuple[int, int, int]] = set()

    def take(found: list[_Hit]) -> None:
        for hit in found:
            if any(hit.line_index == line and hit.start < end and start < hit.end
                   for line, start, end in claimed):
                continue
            claimed.add((hit.line_index, hit.start, hit.end))
            hits.append(hit)

    for index, line in enumerate(lines):
        # First: a supersession the estate declares, so the addresses on that
        # line are recorded as the claim rather than as ordinary prose.
        claim = _SUPERSEDES.search(line)
        if claim:
            tail = line[claim.end():]
            take(_links(tail, index, SUPERSEDES_CLAIM))
            take(_bare_paths(tail, index, SUPERSEDES_CLAIM, offset=claim.end()))
        take(_links(line, index))
        imports = []
        for match in _IMPORT.finditer(line):
            token, start, end = _trimmed(match)
            if path_shaped(token):
                imports.append(_Hit(index, start, end, token, IMPORT_STATEMENT))
        take(imports)
        if index in frontmatter:
            take(_bare_paths(line, index, FRONTMATTER_FIELD))
        take(_bare_paths(line, index, BARE_PATH_LITERAL))
    return hits


def extract(text: str) -> list[Pointer]:
    """Every pointer written in one surface's text, in file order."""
    lines = text.splitlines(keepends=True)
    if not lines:
        return []
    line_offsets = _line_byte_offsets(lines)
    fenced = _fenced_lines(lines)
    frontmatter = _frontmatter_lines(lines)

    found = []
    for hit in _detect(lines, frontmatter):
        line = lines[hit.line_index]
        start = line_offsets[hit.line_index] + len(line[: hit.start].encode("utf-8"))
        end = start + len(line[hit.start : hit.end].encode("utf-8"))
        found.append(
            Pointer(
                address=hit.address,
                subtype=hit.subtype,
                line=hit.line_index + 1,
                start_byte=start,
                end_byte=end,
                in_code_fence=hit.line_index in fenced,
            )
        )
    return sorted(found, key=lambda pointer: (pointer.start_byte, pointer.subtype))


def extract_config(document: Document, entry: Node, repo_root: Path) -> list[Pointer]:
    """Every path-shaped string value inside one settings entry.

    Scoped to hook and MCP entries because those are the rows a pointer can
    leave from: a settings file is a container, not a surface, so a value
    outside every entry has no node to be the source of an edge. That is a
    stated boundary of this detector, and what falls outside it is not reported
    as absent.

    A value still carrying an unexpanded variable is not an address at all --
    it is a template -- so no pointer is made from it. The hook row already
    records that outcome in its own vocabulary.
    """
    found: list[Pointer] = []
    for value, node in _strings(entry):
        start = len(document.text[: node.start].encode("utf-8"))
        end = len(document.text[: node.end].encode("utf-8"))
        for address in _config_addresses(value, repo_root):
            found.append(
                Pointer(
                    address=address,
                    subtype=CONFIG_VALUE,
                    line=document.line_of(node.start),
                    start_byte=start,
                    end_byte=end,
                    in_code_fence=False,
                )
            )
    return found


def _config_addresses(value: str, repo_root: Path) -> list[str]:
    """The addresses inside one settings value, as the estate wrote them.

    A settings value is often a command line rather than a path, so it is split
    the way a shell would split it and each token judged on its own -- the
    address of ``python3 .claude/hooks/build.py`` is the script, not the line.

    Shaping is tested against the *expanded* form, so a command written through
    ``$CLAUDE_PROJECT_DIR`` is judged on where it points, while the address kept
    is still what the file says. The leading ``/`` of an absolute path is set
    aside for the test: a config value is allowed to be absolute, where a path in
    prose is not -- excluding a leading slash there is what stops the path half
    of a URL being re-matched as a bare path, and no URL reaches that detector.
    """
    if _SCHEME.match(value):
        return [value]
    try:
        tokens = shlex.split(value)
    except ValueError:
        tokens = [value]
    return [
        token for token in tokens
        if path_shaped(expand_variables(token, repo_root).lstrip("/"))
    ]


def _strings(node: Node) -> list[tuple[str, Node]]:
    """Every string value at or under a JSON node, with its span."""
    text = node.text_value()
    if text is not None:
        return [(text, node)]
    found: list[tuple[str, Node]] = []
    for _, child in node.items():
        found.extend(_strings(child))
    for child in node.elements():
        found.extend(_strings(child))
    return found


def resolve(address: str, repo_root: Path, surface_path: str) -> Resolution | None:
    """Where an address lands, or None where it is not a pointer to a file.

    Resolution is relative to the repository the pointer was written in: first
    the directory of the file holding it, then the repository root. A sibling
    repository in the same estate is *outside* this root -- it is a different
    snapshot with its own branch and commit, so an edge into it would join two
    things this indexer has not established are the same.

    Three addresses return None rather than a non-resolution, because each names
    something other than a file and reporting them as unmatched files would say
    something untrue about the estate. They are stated limits of this detector
    set, not findings:

    - an anchor in the same document, which names no file;
    - a value still carrying an unexpanded variable, which is a template;
    - a directory that exists in the tree. Phase 1 has a node for a file and a
      node for a surface, and none for a directory, so a link to one has no
      target to point at -- and it is a place that is there, not a file that is
      not.
    """
    if _SCHEME.match(address):
        return Resolution(None, UNRESOLVABLE_SCHEME)

    target = unquote(address.split("#", 1)[0].split("?", 1)[0]).strip()
    if not target:
        # A link to an anchor in the same document names no file.
        return None
    if "$" in target:
        # A template, not an address.
        return None
    if target.startswith("~"):
        return Resolution(None, OUTSIDE_INDEXED_ROOTS)

    if os.path.isabs(target):
        candidates = [Path(target)]
    else:
        parent = repo_root / PurePosixPath(surface_path).parent
        candidates = [parent / target, repo_root / target]

    inside_root = False
    for candidate in candidates:
        normalised = Path(os.path.normpath(candidate))
        try:
            relative = normalised.relative_to(repo_root)
        except ValueError:
            continue
        inside_root = True
        if normalised.is_dir():
            return None
        if normalised.is_file():
            return Resolution(relative.as_posix(), None)
    if not inside_root:
        return Resolution(None, OUTSIDE_INDEXED_ROOTS)
    return Resolution(None, NO_INDEXED_TARGET_MATCH)


def expanded(address: str, repo_root: Path) -> str:
    """A config value with the variables a client documents already expanded."""
    return expand_variables(address, repo_root)
