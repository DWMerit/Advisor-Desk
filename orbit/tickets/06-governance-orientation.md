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

## Acceptance

- [ ] Output fits a stated budget, and the budget cites a measurement
- [ ] Every count carries the **detector set version** that produced it
- [ ] Coverage is reported explicitly, so a thin result reads as "these detectors found little here" rather than as a description of the estate
- [ ] Output contains no forbidden vocabulary word
- [ ] Running it on a repository with no governance surface produces a valid map reporting zero, not an error

## Calibration

Their `repo-map` emits **12,874 bytes (~3,200 tokens)** for a 1,775-file repository. That is the reference point. An earlier draft of this project asserted a 2,000-token budget with no basis — do not re-derive it.
