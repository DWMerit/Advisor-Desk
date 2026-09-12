"""Parse JSON, keeping where each value sits in the source text.

A hook definition is an entry *inside* a settings file, not a file of its own.
Its row has to carry the matcher quoted verbatim and a ``file:line`` locator,
and its size is the size of that entry rather than of the whole file.
``json.loads`` throws all three away, so this reads JSON itself and hands back
every value with its span.

Offsets are character offsets into the decoded text. Line numbers and byte
sizes are derived from them, so a settings file carrying non-ASCII text still
reports the bytes it actually occupies.

Only the escaping and number grammar are delegated to ``json.loads``, on the
exact slice of text a token occupies -- so what this accepts is what the
standard library accepts, minus nothing that matters here.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

_WHITESPACE = " \t\n\r"

_LITERAL = re.compile(
    r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][-+]?\d+)?|true|false|null"
)


class JsonLocationError(Exception):
    """The text is not JSON this reader can place."""


@dataclass(frozen=True)
class Node:
    """One JSON value and the half-open character span it occupies.

    ``value`` is a ``dict[str, Node]`` for an object, a ``list[Node]`` for an
    array, and the plain Python value for anything else. Children stay wrapped
    so an entry nested three levels down still knows where it is.
    """

    value: Any
    start: int
    end: int

    def get(self, key: str) -> "Node | None":
        """The child at ``key``, or None if this is not an object with it."""
        if isinstance(self.value, dict):
            return self.value.get(key)
        return None

    def items(self) -> list[tuple[str, "Node"]]:
        if isinstance(self.value, dict):
            return list(self.value.items())
        return []

    def elements(self) -> list["Node"]:
        if isinstance(self.value, list):
            return list(self.value)
        return []

    def text_value(self) -> str | None:
        """The value if it is a string, else None."""
        return self.value if isinstance(self.value, str) else None


@dataclass(frozen=True)
class Document:
    """A parsed settings file: the text it came from, and its root value."""

    text: str
    root: Node

    def line_of(self, offset: int) -> int:
        """1-based line number of a character offset."""
        return self.text.count("\n", 0, offset) + 1

    def span_lines(self, node: Node) -> tuple[int, int]:
        """The first and last line a node covers."""
        return self.line_of(node.start), self.line_of(max(node.start, node.end - 1))

    def size_bytes(self, node: Node) -> int:
        """UTF-8 bytes the node occupies in the file."""
        return len(self.text[node.start : node.end].encode("utf-8"))

    def slice(self, node: Node) -> str:
        return self.text[node.start : node.end]


def parse(text: str) -> Document:
    """Read ``text`` as JSON, keeping every value's span."""
    node = _value(text, 0)
    end = _skip_whitespace(text, node.end)
    if end != len(text):
        raise JsonLocationError(f"trailing text at offset {end}")
    return Document(text=text, root=node)


def _skip_whitespace(text: str, index: int) -> int:
    while index < len(text) and text[index] in _WHITESPACE:
        index += 1
    return index


def _value(text: str, index: int) -> Node:
    index = _skip_whitespace(text, index)
    if index >= len(text):
        raise JsonLocationError("no value at end of text")
    character = text[index]
    if character == "{":
        return _object(text, index)
    if character == "[":
        return _array(text, index)
    if character == '"':
        value, end = _string(text, index)
        return Node(value, index, end)
    match = _LITERAL.match(text, index)
    if match is None:
        raise JsonLocationError(f"not a JSON value at offset {index}")
    return Node(json.loads(match.group(0)), index, match.end())


def _string(text: str, index: int) -> tuple[str, int]:
    """Find the end of the string literal at ``index``; decode it with json."""
    end = index + 1
    while True:
        if end >= len(text):
            raise JsonLocationError(f"unterminated string from offset {index}")
        character = text[end]
        if character == "\\":
            end += 2
            continue
        end += 1
        if character == '"':
            break
    return json.loads(text[index:end]), end


def _object(text: str, start: int) -> Node:
    pairs: dict[str, Node] = {}
    index = _skip_whitespace(text, start + 1)
    if index < len(text) and text[index] == "}":
        return Node(pairs, start, index + 1)
    while True:
        index = _skip_whitespace(text, index)
        if index >= len(text) or text[index] != '"':
            raise JsonLocationError(f"expected a key at offset {index}")
        key, index = _string(text, index)
        index = _skip_whitespace(text, index)
        if index >= len(text) or text[index] != ":":
            raise JsonLocationError(f"expected ':' at offset {index}")
        child = _value(text, index + 1)
        # Last one wins, matching json.loads on a repeated key.
        pairs[key] = child
        index = _skip_whitespace(text, child.end)
        if index >= len(text):
            raise JsonLocationError(f"unterminated object from offset {start}")
        if text[index] == ",":
            index += 1
            continue
        if text[index] == "}":
            return Node(pairs, start, index + 1)
        raise JsonLocationError(f"expected ',' or '}}' at offset {index}")


def _array(text: str, start: int) -> Node:
    elements: list[Node] = []
    index = _skip_whitespace(text, start + 1)
    if index < len(text) and text[index] == "]":
        return Node(elements, start, index + 1)
    while True:
        child = _value(text, index)
        elements.append(child)
        index = _skip_whitespace(text, child.end)
        if index >= len(text):
            raise JsonLocationError(f"unterminated array from offset {start}")
        if text[index] == ",":
            index += 1
            continue
        if text[index] == "]":
            return Node(elements, start, index + 1)
        raise JsonLocationError(f"expected ',' or ']' at offset {index}")
