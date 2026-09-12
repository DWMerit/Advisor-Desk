"""Which assistant's own naming convention claims a surface.

The graph could already say a surface exists, what kind it is, what it weighs
and whether two files hold identical bytes. It could not say **who pays for
it**, and two files of 17,294 bytes each, byte-identical, is 17,294 bytes of
burden or 34,588 depending entirely on that.

What this module reads, and what it refuses to read
---------------------------------------------------

**Only the estate's own naming.** A filename a vendor defined, or a directory a
vendor defined, is a statement the estate made when it wrote that name. Nothing
here opens a file, and nothing here walks the pointer graph: reachability was
attempted in ticket 07 and added one row in each of two repositories and none in
either lineage repository, because reachability does not carry load attribution.

**Where nothing names one, the value is UNKNOWN and carries its reason.** Never
an empty string, never a guess. Two-thirds of this estate's surface bytes sit in
that bucket, and that is the honest answer rather than a gap -- a derivation
that produces materially fewer UNKNOWNs than the 237-of-318 split ticket 07
recorded has begun inferring.

Why it is not a detector
------------------------

``detectors.DETECTOR_MODULES`` hashes the five modules that decide *what is
recognised*. This module decides what is *written about* something already
recognised, so it is outside that set by the same rule that keeps ``ontology``
outside it, and the detector set version does not move when it changes. Spec
0004 makes that a requirement rather than an observation: it is what keeps every
figure in tickets 07 and 14 comparable with figures taken after this column
landed.

The cost of that is real and is stated here rather than discovered later: a
change to the tables below is invisible in the version string. What guards them
instead is ``orbit/tests/test_client.py``, which asserts that every entry in the
three detector-side vendor tables resolves to a client here -- so a name added
to a detector cannot silently start producing UNKNOWN.
"""

from __future__ import annotations

from pathlib import PurePosixPath

# The assistants this estate's naming conventions name. One value per client,
# not per vendor: the column answers "which assistant pays for this", and
# Anthropic defining a name is only interesting because a Claude session reads
# it.
CLIENT_CLAUDE = "claude"
CLIENT_CODEX = "codex"
CLIENT_GEMINI = "gemini"
CLIENT_CURSOR = "cursor"
CLIENT_COPILOT = "copilot"

# The value for a surface no vendor convention names. A value, with a reason
# beside it -- the precedent is `recognition`, which records `corpus-adjacent`
# separately precisely so a query can exclude what was inferred.
CLIENT_UNKNOWN = "UNKNOWN"

CLIENT_KINDS = (
    CLIENT_CLAUDE,
    CLIENT_CODEX,
    CLIENT_GEMINI,
    CLIENT_CURSOR,
    CLIENT_COPILOT,
    CLIENT_UNKNOWN,
)

# What `client_reason` carries: why the row holds the value it holds. Three of
# them name the statement the estate made; the fourth names the absence of one.
#
# The reason is a column beside the value rather than folded into it. Folding it
# in would split the UNKNOWN bucket of `SELECT client, count(*) ... GROUP BY 1`
# across one value per reason, and a single UNKNOWN bucket that prints its own
# size is the whole point of the column.
REASON_VENDOR_RELATIVE_PATH = "a-path-this-vendor-defined"
REASON_VENDOR_DIRECTORY = "a-directory-this-vendor-defined"
REASON_VENDOR_BASENAME = "a-filename-this-vendor-defined"
REASON_NO_VENDOR_CONVENTION = "no-vendor-convention-names-this-surface"

CLIENT_REASONS = (
    REASON_VENDOR_RELATIVE_PATH,
    REASON_VENDOR_DIRECTORY,
    REASON_VENDOR_BASENAME,
    REASON_NO_VENDOR_CONVENTION,
)

# --- The three tables, applied in this order -------------------------------
#
# The order mirrors `surfaces.classify`, which decides whether a path is
# vendor-named at all: exact path, then directory prefix, then basename. Two
# derivations keyed the same way cannot disagree about which rule matched.

# Matched on the repository-relative path. Each of these is a name one vendor
# defined inside a directory another party defined, so the directory rule below
# would attribute them to the wrong party -- `.github/` is GitHub's and
# `.vscode/` is the editor's, while both files are read by Copilot.
CLIENT_RELATIVE_PATHS: dict[str, str] = {
    ".github/copilot-instructions.md": CLIENT_COPILOT,
    ".vscode/mcp.json": CLIENT_COPILOT,
    # Claude Code's own project-level MCP config, at the repository root. The
    # protocol is nobody's; this filename at this path is Anthropic's.
    ".mcp.json": CLIENT_CLAUDE,
}

# Matched on a directory prefix at the repository root, at any depth below it.
# A vendor's own directory is the statement -- everything the estate put inside
# `.claude/`, a settings file, an agent, a command, a skill or a hook script a
# settings file names, is there because a Claude session reads that directory.
#
# **Rooted, the way `surfaces.SURFACE_DIRECTORIES` is rooted.** A first version
# also matched `.claude/` nested anywhere below the root. Across the four
# repositories ticket 07 audited it claimed no row that the rules here do not
# already claim by name, so it was reach without a reading behind it -- the same
# ground on which `DIRECTIVE_HEADING_WORDS` holds one word rather than every
# word a heading could open with. A repository that nests a vendor directory has
# no rows *found* by this rule, which is not the same statement as no rows, and
# adding the case means looking at such a repository first.
CLIENT_DIRECTORIES: tuple[tuple[str, str], ...] = (
    (".claude/", CLIENT_CLAUDE),
    (".cursor/", CLIENT_CURSOR),
)

# Matched on the file's basename, at any path.
CLIENT_BASENAMES: dict[str, str] = {
    "CLAUDE.md": CLIENT_CLAUDE,
    # Ticket 07's own Gate A query reads this one as "Codex, by a filename
    # OpenAI defined", and that reading is the record this repository has.
    "AGENTS.md": CLIENT_CODEX,
    "GEMINI.md": CLIENT_GEMINI,
    ".cursorrules": CLIENT_CURSOR,
    # The Agent Skills filename. It carries wherever it sits, because the name
    # is the statement: a directory of `SKILL.md` files outside `.claude/` is
    # still written in Anthropic's format and is still read by a Claude
    # session that is pointed at it.
    "SKILL.md": CLIENT_CLAUDE,
}


def attribute(relative_path: str) -> tuple[str, str]:
    """The client a repository-relative path names, and why.

    Returns ``(client, reason)``. Nothing is opened: a name is readable without
    reading the file, so a surface that failed to index -- invalid bytes, over
    the size ceiling, a symlink listed and never opened -- is attributed on the
    same evidence as one that read cleanly.
    """
    posix = PurePosixPath(relative_path).as_posix()

    client = CLIENT_RELATIVE_PATHS.get(posix)
    if client is not None:
        return client, REASON_VENDOR_RELATIVE_PATH

    for prefix, directory_client in CLIENT_DIRECTORIES:
        if posix.startswith(prefix):
            return directory_client, REASON_VENDOR_DIRECTORY

    client = CLIENT_BASENAMES.get(PurePosixPath(posix).name)
    if client is not None:
        return client, REASON_VENDOR_BASENAME

    return CLIENT_UNKNOWN, REASON_NO_VENDOR_CONVENTION
