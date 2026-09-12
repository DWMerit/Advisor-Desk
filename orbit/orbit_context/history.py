"""The commits on a branch, and which session wrote them.

Absence from a transcript is a fact about the transcript, not about the world.
A session whose context was cleared has no record of its own earlier work and
the repository does, so twice in this project a session read commits it had made
itself, saw an unfamiliar subject line, attributed them to a different session,
and wrote that invention into a scheduled prompt that fed it back hourly. The
disproof was in the commit body it had just printed: a ``Claude-Session``
trailer carrying its own id.

The trailer is the mechanical answer, and this module reads it. Two things about
how it reads it are the whole point:

**A session identifier is taken from the environment, never inferred from the
commits.** Whether this session wrote a commit is decided by comparing the
trailer against an id the environment supplies. Where the environment supplies
none, ``this_session`` is None and the map says the identifier was not
available -- it never reports zero. Zero and unknown are different findings, and
printing the first for the second is the exact error this module exists to stop.

**Every distinct trailer value is reported whatever matched.** The identifier a
client exports and the identifier written into the trailer are not always
spelled the same way -- one environment exports ``cse_01ABC`` for a trailer
reading ``https://claude.ai/code/session_01ABC`` -- so matching is on the id's
tail, and the full distribution is reported beside it. A reader who can see
"seven commits carry session_01ABC" can settle the question themselves when the
match heuristic comes up empty.

The base a branch is measured against is resolved the same way: by a stated
ladder, with the rung that answered reported beside the number.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# `_git` runs one git command and raises GitError on a non-zero exit. Shared
# with workspace rather than re-spelled, so the two agree on what a failed
# git call is -- a second copy would drift on error handling first.
from .workspace import GitError, _git

# The trailer this project writes into every commit a session authors.
TRAILER_KEY = "Claude-Session"

# Environment variables a client may export the current session's id in, in the
# order they are tried. All of them are read: a session is counted as the author
# of a commit whose trailer matches any one, because which variable carries the
# form the trailer was written in differs between environments.
SESSION_VARIABLES = ("CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_REMOTE_SESSION_ID")

# An environment variable naming the branch this work merges into.
BASE_VARIABLE = "CLAUDE_CODE_BASE_REF"

# Tried in order once the environment and `origin/HEAD` have had their turn.
BASE_CANDIDATES = ("origin/main", "origin/master", "main", "master")

# An id's tail must be at least this long to be matched inside a trailer. A
# short tail would match text that is not an id at all, and a false match here
# reports another session's commits as this one's.
MINIMUM_IDENTIFIER_LENGTH = 8

# Field and record separators for `git log`, chosen because a commit subject can
# contain anything a person can type but not these.
_FIELD = "\x1f"
_TRAILER = "\x1d"
_RECORD = "\x1e"

_LOG_FORMAT = (
    f"%H{_FIELD}%s{_FIELD}"
    f"%(trailers:key={TRAILER_KEY},valueonly,separator={_TRAILER}){_RECORD}"
)


def identifier_tail(identifier: str) -> str:
    """The part of an id that survives a change of prefix.

    ``cse_01ABC`` and ``session_01ABC`` are the same session wearing two
    prefixes, and only the tail is common to both.
    """
    return identifier.rsplit("_", 1)[-1]


@dataclass(frozen=True)
class Session:
    """The current session's identifiers, and where they came from."""

    # (variable name, value) for every session id the environment supplied.
    identifiers: tuple[tuple[str, str], ...] = ()

    @property
    def known(self) -> bool:
        return bool(self.identifiers)

    def matching_variable(self, trailer: str) -> str | None:
        """The environment variable whose id names this session, if one does.

        The variable is returned rather than a boolean because which one matched
        is worth printing: an environment can export two ids for one session in
        two spellings, and only one of them is the spelling the trailer was
        written in. A map that named both would be claiming a match it did not
        make.
        """
        for name, value in self.identifiers:
            tail = identifier_tail(value)
            if len(tail) >= MINIMUM_IDENTIFIER_LENGTH and tail in trailer:
                return name
        return None

    def matches(self, trailer: str) -> bool:
        """Whether a trailer value names this session."""
        return self.matching_variable(trailer) is not None


@dataclass(frozen=True)
class Base:
    """The ref a branch's commits are counted against, and which rung named it."""

    ref: str | None
    source: str


@dataclass(frozen=True)
class Commit:
    sha: str
    subject: str
    trailers: tuple[str, ...]


@dataclass(frozen=True)
class BranchState:
    """A branch, its base, and who authored the commits between them."""

    branch: str
    head: str
    base: Base
    commits: tuple[Commit, ...]
    session: Session
    # Empty where git answered. Set where it could not, so a map prints the
    # reason rather than a zero it cannot stand behind.
    unavailable: str = ""

    @property
    def ahead(self) -> int | None:
        """Commits reachable from HEAD and not from the base, or None."""
        return None if self.unavailable or self.base.ref is None else len(self.commits)

    @property
    def with_trailer(self) -> int:
        return sum(1 for commit in self.commits if commit.trailers)

    @property
    def this_session(self) -> int | None:
        """Commits ahead carrying this session's trailer, or None if unknown.

        None, never zero, where the environment supplied no identifier. The
        count of commits a session cannot recognise as its own is not zero; it
        is unmeasured, and the two read identically once printed.
        """
        if not self.session.known:
            return None
        return sum(
            1 for commit in self.commits
            if any(self.session.matches(value) for value in commit.trailers)
        )

    def matched_variables(self) -> tuple[str, ...]:
        """The variables that actually matched a trailer, in the order tried."""
        names: list[str] = []
        for commit in self.commits:
            for value in commit.trailers:
                name = self.session.matching_variable(value)
                if name is not None and name not in names:
                    names.append(name)
        return tuple(names)

    def by_trailer(self) -> list[tuple[str, int]]:
        """Every distinct trailer value ahead of base, most commits first."""
        counts: dict[str, int] = {}
        for commit in self.commits:
            for value in commit.trailers:
                counts[value] = counts.get(value, 0) + 1
        return sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))


def current_session(environ=None, override: str | None = None) -> Session:
    """The session ids the environment supplies, in a stated order."""
    if override:
        return Session((("--session", override),))
    environ = os.environ if environ is None else environ
    found = tuple(
        (name, environ[name].strip())
        for name in SESSION_VARIABLES
        if environ.get(name, "").strip()
    )
    return Session(found)


def _exists(root, ref: str) -> bool:
    try:
        _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    except GitError:
        return False
    return True


def resolve_base(root, override: str | None = None, environ=None) -> Base:
    """The ref this branch is measured against, and the rung that named it.

    The rung is reported because the answer differs between checkouts of the
    same repository -- a clone with no ``origin/HEAD`` falls through to a
    guessed default name -- and a count of commits ahead means nothing without
    saying ahead of what.
    """
    environ = os.environ if environ is None else environ
    if override:
        if _exists(root, override):
            return Base(override, "--base")
        return Base(None, f"--base named {override}, which git does not resolve here")

    from_environment = environ.get(BASE_VARIABLE, "").strip()
    if from_environment and _exists(root, from_environment):
        return Base(from_environment, BASE_VARIABLE)

    try:
        head = _git(root, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    except GitError:
        head = ""
    if head:
        ref = head.removeprefix("refs/remotes/")
        if _exists(root, ref):
            return Base(ref, "origin/HEAD")

    for candidate in BASE_CANDIDATES:
        if _exists(root, candidate):
            return Base(candidate, "first of " + ", ".join(BASE_CANDIDATES))

    return Base(None, "no base ref resolved from --base, "
                      f"{BASE_VARIABLE}, origin/HEAD or " + ", ".join(BASE_CANDIDATES))


def _parse(output: str) -> tuple[Commit, ...]:
    commits = []
    for record in output.split(_RECORD):
        record = record.strip("\n")
        if not record:
            continue
        fields = record.split(_FIELD)
        if len(fields) < 3:
            continue
        trailers = tuple(
            value.strip() for value in fields[2].split(_TRAILER) if value.strip()
        )
        commits.append(Commit(fields[0], fields[1], trailers))
    return tuple(commits)


def branch_state(root, base_override: str | None = None,
                 session_override: str | None = None, environ=None) -> BranchState:
    """Read one repository's branch, its base, and the commits between them."""
    session = current_session(environ, session_override)
    try:
        branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
        head = _git(root, "rev-parse", "HEAD")
    except GitError as error:
        return BranchState("", "", Base(None, ""), (), session, str(error))

    base = resolve_base(root, base_override, environ)
    if base.ref is None:
        return BranchState(branch, head, base, (), session)

    try:
        output = _git(root, "log", f"--format={_LOG_FORMAT}", f"{base.ref}..HEAD")
    except GitError as error:
        return BranchState(branch, head, base, (), session, str(error))
    return BranchState(branch, head, base, _parse(output), session)
