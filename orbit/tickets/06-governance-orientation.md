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

- [x] Output fits a stated budget, and the budget cites a measurement
- [x] Every count carries the **detector set version** that produced it
- [x] Coverage is reported explicitly, so a thin result reads as "these detectors found little here" rather than as a description of the estate
- [x] Output contains no forbidden vocabulary word
- [x] Running it on a repository with no governance surface produces a valid map reporting zero, not an error
- [x] Reports commits ahead of base and how many carry the current session's
      `Claude-Session` trailer

## Built

`orbit-context repo-map --repo <path>`, in `orbit/orbit_context/repomap.py`.

**Read from the graph, not from a second walk.** Every number comes out of one
`(project_id, branch, commit_sha)`. Coverage and the indexed boundary were the
only facts the walk knew and the graph did not, so the walk now records itself:
`IndexRun` → `gl_context_run` (one row per snapshot: indexed root, excluded
directories, files walked, files carrying a surface kind, detector set version)
and `CoverageNote` → `gl_context_coverage` (one row per file reached and not
fully indexed, with its reason). Both declared in ontology YAML, neither
carrying edges.

**The detector set version is derived, not declared.**
`orbit/orbit_context/detectors.py` digests the module-level constants and compiled
patterns of the five modules that decide what is recognised, so a boundary fix
moves it whether or not anyone remembers. A constant somebody has to remember to
bump is the mechanism this ticket's own prose objects to. Recorded per snapshot
and printed on every counted section.

**Budget: 12,874 bytes**, their measurement, not re-derived. Held by
construction — fixed detector inventories, capped listings — and the last line
reports what the map cost, counting itself. Fixture estate ≈ 2.5 KB, this
repository ≈ 3 KB.

**Git provenance reports how it knows.** The session id comes from the
environment; where none is available the count is *not measured*, never zero.
Matching is on the id's tail, because one environment exports `cse_01ABC` for a
trailer reading `.../session_01ABC`; the variable that matched is named, and the
full trailer distribution is printed beside it so a reader can settle the
question when the match comes up empty. The base is a stated ladder and the rung
that answered is printed.

**One disagreement found and closed.** `index` counts surfaces it read; the
surface table holds a row for every surface it found, read or not. The map
reports both (`read in full N of M rows`) rather than leaving two numbers to
disagree quietly.

269 tests pass, up from 227.

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
