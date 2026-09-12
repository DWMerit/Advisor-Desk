"""Segment a surface into addressable clauses, by Markdown structure only.

A 17 KB instruction surface is dozens of rules with different lifetimes.
Addressed as one file, *which rule* is unanswerable -- so a surface is cut into
clauses, each carrying the byte span it occupies in the file. The row holds the
span; the caller reads the bytes.

Four kinds, and the order they are found in:

``frontmatter-field``
    One top-level key of the leading ``---`` block.
``heading-section``
    A heading and everything under it, up to the next heading at the same level
    or above.
``list-rule``
    One list item beneath a heading, and any item nested inside it.
``code-block``
    One fenced block.

Structure only. Nothing here classifies what a clause *means* -- that would be
the tool deciding, and it is not what an address is for.

**Byte offsets, never character offsets.** Spans are recorded as
``[start_byte, end_byte)`` into the file's UTF-8 bytes. A character offset shifts
silently against the file the moment anything above it is non-ASCII -- an em
dash, a degree sign, a name -- and the retrieved span comes back off by the
difference with nothing to signal it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

HEADING_SECTION = "heading-section"
LIST_RULE = "list-rule"
FRONTMATTER_FIELD = "frontmatter-field"
CODE_BLOCK = "code-block"

CLAUSE_TYPES = (HEADING_SECTION, LIST_RULE, FRONTMATTER_FIELD, CODE_BLOCK)

# The separator in an fqn, matching their convention:
# CLAUDE.md#Estimating rules#M6 anchors
FQN_SEPARATOR = "#"

_HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.*?)[ \t]*#*[ \t]*$")
_LIST_ITEM = re.compile(r"^([ \t]*)(?:[-*+]|\d{1,9}[.)])[ \t]+(.*)$")
_FENCE = re.compile(r"^([ \t]*)(`{3,}|~{3,})[ \t]*(.*)$")
# A top-level key inside the frontmatter block: no indentation, so a mapping
# value spanning several lines stays part of its key.
_FRONTMATTER_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_.\-]*)[ \t]*:")

FRONTMATTER_FENCE = "---"


@dataclass(frozen=True)
class Clause:
    """One addressable fragment. ``parent`` indexes into the same list."""

    fqn: str
    heading: str
    clause_type: str
    start_line: int
    end_line: int
    start_byte: int
    end_byte: int
    # None means the surface contains it directly; otherwise the position of
    # the enclosing clause in the returned list.
    parent: int | None


def _line_offsets(lines: list[str]) -> list[int]:
    """Byte offset of each line's first byte, plus the file's total size."""
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line.encode("utf-8")))
    return offsets


def _tab_width(prefix: str) -> int:
    """Indentation in columns, so a tab-indented item nests like a spaced one."""
    width = 0
    for character in prefix:
        width += 4 - (width % 4) if character == "\t" else 1
    return width


def _fence_close(lines: list[str], opened_at: int, fence: str) -> int:
    """Index of the line closing a fence, or the last line if it never closes."""
    character = fence[0]
    for number in range(opened_at + 1, len(lines)):
        match = _FENCE.match(lines[number])
        if match and match.group(2)[0] == character and len(match.group(2)) >= len(fence):
            if not match.group(3).strip():
                return number
    return len(lines) - 1


def _trim(lines: list[str], start: int, end: int) -> int:
    """Drop trailing blank lines from a span, so the recorded end is content."""
    while end > start and not lines[end].strip():
        end -= 1
    return end


class _Open:
    """A clause whose span is still being extended as the scan moves down.

    ``rank`` is what closes it: heading level for a heading, indent columns for
    a list item. A clause is closed by the next one of its own kind at the same
    rank or above.
    """

    __slots__ = ("index", "rank", "start")

    def __init__(self, index: int, rank: int, start: int):
        self.index = index
        self.rank = rank
        self.start = start


def segment(text: str, surface_path: str) -> list[Clause]:
    """Cut one surface's text into clauses, outermost first, in file order."""
    lines = text.splitlines(keepends=True)
    if not lines:
        return []
    offsets = _line_offsets(lines)

    # One entry per clause, in the order found. A clause's end line is not known
    # when it starts, so the spans are filled in as later lines close them.
    types: list[str] = []
    fqns: list[str] = []
    headings: list[str] = []             # nearest enclosing heading, per clause
    parents: list[int | None] = []
    spans: list[list[int]] = []          # [start_line_index, end_line_index]

    heading_stack: list[_Open] = []
    list_stack: list[_Open] = []

    def emit(name: str, clause_type: str, start: int, end: int,
             parent: int | None, heading: str) -> int:
        prefix = fqns[parent] if parent is not None else surface_path
        fqns.append(prefix + FQN_SEPARATOR + name)
        types.append(clause_type)
        headings.append(heading)
        parents.append(parent)
        spans.append([start, end])
        return len(spans) - 1

    def close_lists(down_to: int, last_line: int) -> None:
        while list_stack and list_stack[-1].rank >= down_to:
            open_item = list_stack.pop()
            spans[open_item.index][1] = _trim(lines, open_item.start, last_line)

    def close_headings(level: int, last_line: int) -> None:
        while heading_stack and heading_stack[-1].rank >= level:
            open_heading = heading_stack.pop()
            spans[open_heading.index][1] = _trim(lines, open_heading.start, last_line)

    def enclosing_heading() -> tuple[int | None, str]:
        if not heading_stack:
            return None, ""
        top = heading_stack[-1]
        return top.index, headings[top.index]

    number = _frontmatter(lines, surface_path, emit)

    while number < len(lines):
        line = lines[number]

        fence = _FENCE.match(line)
        if fence:
            indent = _tab_width(fence.group(1))
            close_lists(indent, number - 1)
            parent, heading = _list_or_heading_parent(list_stack, enclosing_heading)
            closed_at = _fence_close(lines, number, fence.group(2))
            emit(fence.group(3).strip(), CODE_BLOCK, number, closed_at, parent, heading)
            number = closed_at + 1
            continue

        heading_match = _HEADING.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            text_of_heading = heading_match.group(2).strip()
            close_lists(0, number - 1)
            close_headings(level, number - 1)
            parent = heading_stack[-1].index if heading_stack else None
            index = emit(text_of_heading, HEADING_SECTION, number, number,
                         parent, text_of_heading)
            heading_stack.append(_Open(index, level, number))
            number += 1
            continue

        item = _LIST_ITEM.match(line)
        if item:
            indent = _tab_width(item.group(1))
            close_lists(indent, number - 1)
            parent, heading = _list_or_heading_parent(list_stack, enclosing_heading)
            index = emit(item.group(2).strip(), LIST_RULE, number, number, parent, heading)
            list_stack.append(_Open(index, indent, number))
            number += 1
            continue

        if line.strip():
            # A line flush with or left of an open item ends it: the item's
            # continuation is what stays indented under it.
            close_lists(_tab_width(_indent_of(line)), number - 1)
        number += 1

    # End of file: everything still open ends here.
    close_lists(0, len(lines) - 1)
    close_headings(1, len(lines) - 1)

    return [
        Clause(
            fqn=fqns[index],
            heading=headings[index],
            clause_type=types[index],
            start_line=start + 1,
            end_line=end + 1,
            start_byte=offsets[start],
            end_byte=offsets[end + 1],
            parent=parents[index],
        )
        for index, (start, end) in enumerate(spans)
    ]


def _indent_of(line: str) -> str:
    return line[: len(line) - len(line.lstrip(" \t"))]


def _list_or_heading_parent(list_stack: list[_Open],
                            enclosing_heading) -> tuple[int | None, str]:
    """What holds a list item or a fenced block: the open item, else the heading."""
    if list_stack:
        top = list_stack[-1]
        return top.index, enclosing_heading()[1]
    return enclosing_heading()


def _frontmatter(lines: list[str], surface_path: str, emit) -> int:
    """Emit one clause per top-level frontmatter key. Returns where the body starts.

    The frontmatter of a skill is what every session pays at boot, so its fields
    are addressable in their own right rather than folded into the file.
    """
    if not lines or lines[0].strip() != FRONTMATTER_FENCE:
        return 0
    closing = None
    for number, line in enumerate(lines[1:], start=1):
        if line.strip() == FRONTMATTER_FENCE:
            closing = number
            break
    if closing is None:
        return 0

    keys: list[tuple[str, int]] = []
    for number in range(1, closing):
        match = _FRONTMATTER_KEY.match(lines[number])
        if match:
            keys.append((match.group(1), number))

    for position, (key, start) in enumerate(keys):
        end = keys[position + 1][1] - 1 if position + 1 < len(keys) else closing - 1
        emit(key, FRONTMATTER_FIELD, start, _trim(lines, start, end), None, "")

    return closing + 1
