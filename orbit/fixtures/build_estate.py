#!/usr/bin/env python3
"""Build a throwaway two-repository estate for testing.

Built by script, never committed. A committed fixture would mean nested ``.git``
directories that every clone and tool then has to special-case.

    python3 orbit/fixtures/build_estate.py            # into a temp dir
    python3 orbit/fixtures/build_estate.py /some/dir  # into a named dir

Prints the estate root.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

# Byte-identical in both repositories, and under two different names in `alpha`.
SHARED_INSTRUCTIONS = (
    "# Estimating rules\n"
    "\n"
    "## M6 anchors\n"
    "Anchor spacing is stated on the drawing, never assumed.\n"
    "\n"
    "## Takeoff\n"
    "Quantities come from the marked-up set, not from the schedule.\n"
)

# Not valid UTF-8, and named like a surface: it must be recorded with a reason
# rather than silently missed.
BINARY_SURFACE = b"\xff\xfe\x00\x01rules\x80\x81\x82"


def _write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _init_repo(root: Path, branch: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "--initial-branch", branch)
    _git(root, "config", "user.email", "fixture@example.invalid")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "fixture estate")


def build(destination: str | Path | None = None) -> Path:
    """Create the estate and return its root."""
    root = Path(destination) if destination else Path(tempfile.mkdtemp(prefix="orbit-context-estate-"))
    root.mkdir(parents=True, exist_ok=True)

    alpha = root / "alpha"
    # Root surface, and a second name for the same bytes — the pair ticket 05
    # reports as identical bytes.
    _write(alpha / "CLAUDE.md", SHARED_INSTRUCTIONS)
    _write(alpha / "AGENTS.md", SHARED_INSTRUCTIONS)
    _write(alpha / ".github" / "copilot-instructions.md", "# Copilot\nUse the marked-up set.\n")
    _write(alpha / "docs" / "notes.md", "Not a surface. Named like ordinary documentation.\n")
    _write(alpha / "src" / "takeoff.py", "def total(quantities):\n    return sum(quantities)\n")
    _write(alpha / "config" / ".cursorrules", BINARY_SURFACE)
    _init_repo(alpha, "main")

    beta = root / "beta"
    _write(beta / "AGENTS.md", "# Beta\nOne surface at the root.\n")
    _write(beta / "GEMINI.md", "# Beta, Gemini\nA second client at the same root.\n")
    # Nested, path-scoped surface.
    _write(beta / "packages" / "ui" / "CLAUDE.md", "# UI package\nScoped to this subtree.\n")
    _write(beta / "packages" / "ui" / "index.js", "export const noop = () => {};\n")
    # Pruned: a surface here belongs to a vendored tree, not to this estate.
    _write(beta / "node_modules" / "pkg" / "CLAUDE.md", "# Vendored\nNot this estate's.\n")
    _init_repo(beta, "trunk")

    # A directory in the estate that is not a repository at all.
    _write(root / "loose" / "CLAUDE.md", "# Loose\nOutside any repository.\n")

    return root


if __name__ == "__main__":
    print(build(sys.argv[1] if len(sys.argv) > 1 else None))
