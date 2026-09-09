"""Hook and MCP entries inside a settings file, and where their commands land.

Two of the six surface kinds are not files. A hook definition and an MCP server
are entries inside `.claude/settings.json` or `.mcp.json`, so each row carries
the matcher quoted verbatim, a `file:line` locator, and the bytes of that entry
rather than of the file around it.

Command resolution is deliberately unwilling to guess. A command that resolves
to a file in the tree is linked to it; a command that is a PATH lookup is
recorded as a PATH lookup. The two are different findings and stay different --
"the script is not here" and "we cannot see where this program lives" are not
the same statement about the estate.
"""

from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .jsonloc import Document, Node

# The block a settings file keeps its hooks in, and the two spellings of the
# MCP server block: Claude Code and Cursor use `mcpServers`, VS Code `servers`.
HOOKS_KEY = "hooks"
MCP_SERVER_KEYS = ("mcpServers", "servers")

# Where a hook command points, as far as reading it can say.
RESOLUTION_IN_TREE = "in-tree"
RESOLUTION_PATH_LOOKUP = "path-lookup"
RESOLUTION_NO_INDEXED_TARGET_MATCH = "no-indexed-target-match"
RESOLUTION_UNEXPANDED_VARIABLE = "unexpanded-variable"
RESOLUTION_UNPARSABLE_COMMAND = "unparsable-command"

# Expanded before a token is tested against the tree. Claude Code documents
# this one; anything else stays unexpanded and is reported as such.
PROJECT_DIR_VARIABLES = ("$CLAUDE_PROJECT_DIR", "${CLAUDE_PROJECT_DIR}")

# Suffixes that make a token path-shaped even without a slash, so
# `python3 hook.py` is classified on `hook.py` rather than on `python3`.
SCRIPT_SUFFIXES = frozenset(
    {".sh", ".bash", ".zsh", ".py", ".js", ".mjs", ".cjs", ".ts", ".rb", ".pl", ".ps1"}
)


@dataclass(frozen=True)
class HookEntry:
    """One hook command, with the matcher it sits under."""

    event: str
    matcher: str | None          # None where the group declares no matcher key
    command: str
    node: Node                   # the command entry, for locator and size


@dataclass(frozen=True)
class ServerEntry:
    """One MCP server declaration."""

    name: str
    node: Node


def hook_entries(document: Document) -> list[HookEntry]:
    """Every hook command declared in a settings document.

    Shape read: ``hooks -> <Event> -> [ {matcher?, hooks: [{command}, ...]} ]``.
    A group that carries a `command` of its own is read as a single entry, so a
    flatter file still reports its hooks instead of reporting none.
    """
    hooks = document.root.get(HOOKS_KEY)
    if hooks is None:
        return []
    entries: list[HookEntry] = []
    for event, groups in hooks.items():
        for group in groups.elements():
            matcher_node = group.get("matcher")
            matcher = matcher_node.text_value() if matcher_node is not None else None
            commands = group.get(HOOKS_KEY)
            targets = commands.elements() if commands is not None else [group]
            for target in targets:
                command_node = target.get("command")
                command = command_node.text_value() if command_node is not None else None
                if command is None:
                    continue
                entries.append(HookEntry(event, matcher, command, target))
    return entries


def server_entries(document: Document) -> list[ServerEntry]:
    """Every MCP server declared in a settings or `.mcp.json` document."""
    entries: list[ServerEntry] = []
    for key in MCP_SERVER_KEYS:
        block = document.root.get(key)
        if block is None:
            continue
        for name, node in block.items():
            entries.append(ServerEntry(name, node))
    return entries


def _expand(token: str, repo_root: Path) -> str:
    for variable in PROJECT_DIR_VARIABLES:
        token = token.replace(variable, str(repo_root))
    return token


def _path_shaped(token: str) -> bool:
    return "/" in token or PurePosixPath(token).suffix in SCRIPT_SUFFIXES


def _inside_tree(token: str, repo_root: Path) -> str | None:
    """The repository-relative path of ``token``, if it names a file in the tree."""
    if "$" in token:
        return None
    candidate = Path(token) if os.path.isabs(token) else repo_root / token
    normalised = Path(os.path.normpath(candidate))
    try:
        relative = normalised.relative_to(repo_root)
    except ValueError:
        return None
    if not normalised.is_file():
        return None
    return relative.as_posix()


def resolve_command(command: str, repo_root: Path) -> tuple[str | None, str]:
    """Where a hook command points: ``(repository-relative path, resolution)``.

    The path is None for everything except ``in-tree``.
    """
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None, RESOLUTION_UNPARSABLE_COMMAND
    if not tokens:
        return None, RESOLUTION_UNPARSABLE_COMMAND

    expanded = [_expand(token, repo_root) for token in tokens]
    for token in expanded:
        relative = _inside_tree(token, repo_root)
        if relative is not None:
            return relative, RESOLUTION_IN_TREE

    shaped = next((token for token in expanded if _path_shaped(token)), None)
    if shaped is None:
        # Nothing in the line looks like a path: the program is found on PATH,
        # wherever that is. Not a statement about a file that is not there.
        return None, RESOLUTION_PATH_LOOKUP
    if "$" in shaped:
        return None, RESOLUTION_UNEXPANDED_VARIABLE
    if "/" not in shaped and expanded[0] == shaped:
        return None, RESOLUTION_PATH_LOOKUP
    return None, RESOLUTION_NO_INDEXED_TARGET_MATCH
