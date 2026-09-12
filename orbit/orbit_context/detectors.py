"""What this tool recognises, and the version that identifies it.

Every count in the graph is a count of what these detectors recognise. Two
counts taken a month apart are only comparable if the same detectors produced
them, and the failure that makes this worth a mechanism is quiet: ticket 04's
boundary fix moved one detector's match start by one character and took a
finding count from 1,373 to 24. Read without a detector version beside them,
those two numbers describe an estate that changed. It did not.

So the version is **derived, not declared**. A constant somebody has to
remember to bump is the class of mechanism this project has already decided it
has too many of; this one is computed from the detector inputs themselves, so
editing a basename table, a pruned directory, a regex or an evidence rung
changes it whether or not anyone remembers.

What goes into it
-----------------

The module-level constants of the five modules that decide what is recognised:

``surfaces``
    which names and locations are governance objects, which are cut into
    clauses, which directories are never walked, and the size a surface stops
    being read at.
``clauses``
    how a surface is cut into addressable fragments.
``pointers``
    the six pointer detectors, their patterns, and the three non-resolutions.
``settings``
    where a hook command is looked for, and how its target is classified.
``provenance``
    byte identity, and the evidence ladder ``PRODUCES`` stands on.

Every compiled pattern is included, private ones too: a pattern *is* the
detector, and a boundary change that shifts a match start changes every count
downstream of it. What is deliberately not included is anything that decides
where rows are written rather than what is found -- ``workspace``'s two Orbit
conventions, ``store``'s table guards, ``ontology``'s loader. A column added to
the YAML does not change what was detected.

The recipe number
-----------------

``RECIPE`` versions the digest itself. Changing which constants are hashed, or
how they are serialised, moves every version string without any detector having
changed -- so the recipe is stated in the version rather than hidden inside it,
and ``1.4f2a...`` and ``2.4f2a...`` are readable as "computed differently"
rather than as "detects differently".
"""

from __future__ import annotations

import hashlib
import re

from . import clauses, pointers, provenance, settings, surfaces

# Versions the digest recipe, not the detectors. Bump when the set of hashed
# constants or their serialisation changes.
RECIPE = 1

# Hex characters kept from the digest. Twelve is short enough to sit on a line
# of output beside a count and long enough that two detector sets colliding is
# not a thing that happens.
DIGEST_CHARACTERS = 12

# The constrained output vocabulary applies to what this tool writes, and a
# version string is tool-authored. Hexadecimal can spell exactly one word on
# that list, so a digest is capable of printing it by accident -- roughly once
# in seven thousand detector changes, which is rare enough to be a surprise and
# common enough to happen. The window is moved along the digest instead.
# orbit/tests/test_vocabulary.py checks this list against the full one rather
# than trusting the claim that only this word is spellable.
FORBIDDEN_IN_A_DIGEST = ("dead",)

# The modules that decide what is recognised, in a fixed order.
DETECTOR_MODULES = (surfaces, clauses, pointers, settings, provenance)

_PUBLIC_CONSTANT = re.compile(r"^[A-Z][A-Z0-9_]*$")

# Serialised, in this order, whatever their names. Anything else at module level
# -- a class, a function, an import -- is code rather than a detector input, and
# is left out because its identity is not stable across runs.
_HASHED_TYPES = (str, bytes, bool, int, float, frozenset, set, tuple, list, dict)


def _canonical(value) -> str:
    """One value as a string that is the same on every run.

    Sets are sorted and dicts are sorted by key: iteration order of a set is not
    stable across interpreter runs, and a version that moves on its own would be
    worse than no version at all.
    """
    if isinstance(value, re.Pattern):
        return f"pattern({value.pattern!r},{value.flags})"
    if isinstance(value, (frozenset, set)):
        return "{" + ",".join(sorted(_canonical(item) for item in value)) + "}"
    if isinstance(value, (tuple, list)):
        return "[" + ",".join(_canonical(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(
            f"{_canonical(key)}:{_canonical(value[key])}"
            for key in sorted(value, key=repr)
        ) + "}"
    return repr(value)


def _inputs(module) -> list[tuple[str, str]]:
    """One module's detector inputs, as ``(name, canonical value)`` pairs.

    Public constants and compiled patterns. Patterns are taken whatever they are
    called, because the ones that carry the hardest boundary decisions are
    private by convention and excluding them would leave the version blind to
    exactly the changes it exists to catch.
    """
    found = []
    for name, value in vars(module).items():
        pattern = isinstance(value, re.Pattern)
        if not pattern and not _PUBLIC_CONSTANT.match(name):
            continue
        if not pattern and not isinstance(value, _HASHED_TYPES):
            continue
        found.append((name, _canonical(value)))
    return sorted(found)


def manifest() -> list[tuple[str, str, str]]:
    """Every hashed input, as ``(module, name, canonical value)``.

    Exposed so a version that moved can be explained -- diffing two manifests
    names the detector that changed, which a digest on its own cannot.
    """
    return [
        (module.__name__.rsplit(".", 1)[-1], name, value)
        for module in DETECTOR_MODULES
        for name, value in _inputs(module)
    ]


def digest() -> str:
    """The digest over every detector input, freshly computed."""
    hasher = hashlib.sha256()
    for module, name, value in manifest():
        hasher.update(f"{module}.{name}={value}\n".encode("utf-8"))
    return hasher.hexdigest()


def printable_slice(hexdigest: str) -> str:
    """The first window of the digest that spells no constrained word.

    Deterministic: the same digest always yields the same window, so the version
    is still a function of the detectors alone. A 64-character digest makes
    running out of windows unreachable, and it raises rather than returning a
    word this tool is not allowed to print.
    """
    for start in range(len(hexdigest) - DIGEST_CHARACTERS + 1):
        window = hexdigest[start : start + DIGEST_CHARACTERS]
        if not any(word in window for word in FORBIDDEN_IN_A_DIGEST):
            return window
    raise ValueError(f"no printable window in digest {hexdigest}")


def version() -> str:
    """The detector set version: the recipe number, then the digest."""
    return f"{RECIPE}.{printable_slice(digest())}"


# Computed once at import. The detectors cannot change while the process runs,
# and every count written by one index run must carry one version.
VERSION = version()
