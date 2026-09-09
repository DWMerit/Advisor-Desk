# 06 — Governance orientation in one command

**Blocked by:** 03, 04, 05
**Demo when done:** `orbit-context repo-map --repo <path>` prints a compact map of a repository's governance surface, inside a stated budget.

## Do

Mirror their `repo-map`. Report:

- surfaces by kind, with sizes
- clause counts, and the deepest nesting
- edge counts by kind
- coverage: how many files carry no surface kind at all
- the three negative-finding counts
- identical-byte pairs, with the provenance count from 05
- the indexed boundary: roots, exclusions, and what was skipped with reasons
- **git provenance**: branch, commits ahead of base, and how many of them carry
  the current session's `Claude-Session` trailer

## Acceptance

- [ ] Output fits a stated budget, and the budget cites a measurement
- [ ] Every count carries the **detector set version** that produced it
- [ ] Coverage is reported explicitly, so a thin result reads as "these detectors found little here" rather than as a description of the estate
- [ ] Output contains no forbidden vocabulary word
- [ ] Running it on a repository with no governance surface produces a valid map reporting zero, not an error
- [ ] Reports commits ahead of base and how many carry the current session's
      `Claude-Session` trailer

## Why provenance is in an orientation command

A session whose context was cleared has no record of its own earlier work, and
the repository does. Twice in this project a session read commits it had made
itself, saw an unfamiliar subject line, and attributed them to a different
session — while the disproof sat in the commit body it had just printed. It then
wrote that invention into a scheduled check-in, which fed it back hourly as an
established fact.

A stopgap hook shelling out to `git log` was considered and deliberately not
built: a mechanism whose stated lifespan is "until this command exists" is one
nobody remembers to delete, and the estate already has too many of those. This
command is what was chosen instead, so it has to actually cover the hole.

The rule it encodes: **absence from a transcript is a fact about the transcript,
not about the world.** The `Claude-Session` trailer is the mechanical answer, and
it is OBSERVED evidence in this project's own vocabulary — the same standard a
negative finding is held to.

## Calibration

Their `repo-map` emits **12,874 bytes (~3,200 tokens)** for a 1,775-file repository. That is the reference point. An earlier draft of this project asserted a 2,000-token budget with no basis — do not re-derive it.
