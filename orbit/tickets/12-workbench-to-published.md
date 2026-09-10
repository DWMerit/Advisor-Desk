# 12 — Workbench to published carries a direction where evidence allows

**Blocked by:** 11 — **done**
**Demo when done:** all 28 byte-identical pairs, each with a direction or an
explicit UNKNOWN, and the two counts never reported apart.

## Do

Phase 1 already finds the pairs. Verified by hand:

| pair | sha256 (first 12) |
|---|---|
| `_rule-workbench/refactoring/nano.md` = `refactoring/refactoring.nano.md` | `ce32dbb86b42` |
| `_rule-workbench/clean-code/mini.md` = `clean-code/clean-code.mini.md` | `a2cd7e30a033` |

Workbench to published, byte for byte, across the books. Give the pairs a
direction **only where the evidence ladder in `provenance` supports one**.

**The prose case is the whole point of this ticket.**
`_rule-workbench/refactoring/traceability.md` says `full.md` *"should resolve to
`../../refactoring/refactoring.md`"*. That is a producer relationship stated in a
sentence. Spec 0001 §14 lists prose provenance as a **permanent UNKNOWN**. It
stays UNKNOWN. Reading that sentence and writing a `PRODUCES` edge is the
promotion this project exists to refuse, and it would be indistinguishable in the
output from an observed one.

`_rule-workbench/PROCESS.md`, `_rule-workbench/RELEASE.md` and `_rule-workbench/CHECK_COMPATIBILITY.md` describe
how the corpus is produced. They are surfaces to be recognised, not instructions
to be executed or evidence to be promoted.

## What was built

**One rule, and the rest of the ticket is a refusal.** A pair is ordered by a
`PRODUCES` edge between **its own two ends**, and by nothing else. Every
`IDENTICAL_BYTES` row now carries `direction` — `source-produces-target`,
`target-produces-source`, or `UNKNOWN` — and where it is UNKNOWN,
`direction_reason` says which of three cases it is. Where there is a direction
the row also carries the rung (`subtype`) and the `evidence_path:evidence_line`
it was read from, so the claim is checkable against the estate rather than taken
on the tool's word.

`UNKNOWN` rather than an empty column: a blank reads as a column nobody filled
in, and this is a measurement.

**The three reasons are never summed.**

| `direction_reason` | What it says |
|---|---|
| `no-producer-named-at-either-end` | No evidence reaches either file — exactly the pairs `pairs_without_provenance` counts |
| `producer-named-outside-the-pair` | Something produced one or both ends, and it was not the other end. The pair *has* provenance and still nothing orders it |
| `each-end-names-the-other-as-its-producer` | Two claims that contradict each other. Choosing between them would be this tool deciding |

The middle one is the acceptance this ticket turns on. A pair whose two files are
both artifacts of one script and a pair nothing evidences at all are different
findings, and one "no direction" number would say neither.

**`pairs_with_provenance` did not move and is no longer computed twice.** It is
now derived from the reasons — a pair carries provenance exactly where its reason
is not `no-producer-named-at-either-end` — so the index statistics, `repo-map`
and the new `pairs` command cannot come apart on a number all three print.
`repo-map` previously answered it with its own `LEFT JOIN`; it now reads the same
rows through `pairs.from_graph`, on ticket 11's argument that two queries for one
question is how a map and a command end up disagreeing with no way to tell which
is right.

**`orbit-context pairs`** is the demo, and it prints all of them, not a sample.

## The acceptance run — evidence, not a test

Advisor-Desk at `23d19a2`, detector set `1.8516f0a599c4`. Never asserted in a
test: a test that reads live repository content fails whenever that content
changes, including from this work.

| | before | after |
|---|---|---|
| detector set | `1.e2ab2c0e73a6` | `1.8516f0a599c4` |
| files walked | 252 | 254 |
| surfaces | 87 | 87 |
| recognition split | 84 / 0 / 3 | 84 / 0 / 3 |
| ladders / rungs | 14 / 42 | 14 / 42 |
| identical-bytes pairs | 28 | 28 |
| pairs with provenance | 0 | 0 |
| **pairs with a direction** | — | **0** |

The detector set moved because the reasons and directions are detector inputs and
the version is derived from them — the mechanism working, not a bump. Two files
walked is exactly what this ticket added to the tree (`orbit/orbit_context/pairs.py`,
`orbit/tests/test_directions.py`), so the walk reconciles by name rather than by
re-baselining. Nothing else moved.

```
$ orbit-context pairs

IDENTICAL BYTES  28 pairs  [1.8516f0a599c4]
  carrying provenance evidence     0
  carrying no provenance evidence  28
  carrying a direction             0
  read off  a PRODUCES edge between the pair's own two ends, on the strongest rung found for it
  by evidence rung
    artifact-header  0
    manifest-declaration  0
    literal-write-path  0
  carrying no direction, by reason
    no-producer-named-at-either-end  28
    producer-named-outside-the-pair  0
    each-end-names-the-other-as-its-producer  0
  pair by pair
    _rule-workbench/refactoring/mini.md = refactoring/refactoring.mini.md  UNKNOWN: no-producer-named-at-either-end
    _rule-workbench/refactoring/nano.md = refactoring/refactoring.nano.md  UNKNOWN: no-producer-named-at-either-end
    ... 26 more, all UNKNOWN for the same reason
```

### Reconciled by name

**28 pairs is 14 books × 2 rungs, and it is every book.** Each of the fourteen
book directories contributes exactly two: `mini.md` and `nano.md`. All 28 cross
from `_rule-workbench/` to a published file; none is workbench-to-workbench or
published-to-published. The third rung is missing from the pairing for a stated
reason rather than an unexplained one — `_rule-workbench/<book>/full.md` is a
**symlink**, and the walk never enters one, which is the same 14 files ticket
`08`'s hand count already listed as never walked.

**The check ticket 04's precedent asks for: the number is not the evidence.**
Every one of the 28 comes back `UNKNOWN: no-producer-named-at-either-end`, and
that is a true statement about this corpus — nothing in the tree declares the
relationship in a header, a manifest or a write path. The tool is reporting
UNKNOWN against something a human reads in ten seconds, which is the discomfort
the ticket said to expect, and the discomfort is the mechanism.

The three shapes the estate does not hold are exercised against fixtures instead,
so that "0" here reads as a rung that found nothing rather than a rung nobody
built: `build_lineage` carries a workbench rung declared in a manifest (a
direction at `manifest-declaration`) beside two stated only in prose, and
`build_estate`'s `build/rules.md` = `dist/rules.md` — both artifacts of one
script — is the `producer-named-outside-the-pair` case.

## Found while doing this, and not fixed here

**`full.md` is a symlink, and that is not prose.** The sentence this ticket was
written about says `full.md` *"should resolve to
`../../refactoring/refactoring.md`"*, and on disk it **does** — all fourteen of
them are symlinks pointing exactly there. That is a machine-readable fact about
the corpus, not a sentence, and it was invisible to this work because the walk
never enters a symlink.

It still is not a direction. A symlink says two names are one file, which is a
stronger statement than byte identity and a different one from production: it
does not say either name was produced from the other. So reading these would
give the estate an observed *relation* it does not currently have, not the
direction this ticket was asked for.

**And "what does a symlink mean" turned out not to be ours to decide.** This was
first recorded here as an open spec question. It is not one: GitLab Orbit has
already answered it, a symlink is a node that is listed and never read
(`crates/utils/src/walk.rs:37-57`), with its own skip reason, `non_regular_file`.
Our walk refuses them outright at `orbit/orbit_context/surfaces.py:414`, which makes this a
divergence from the tool this project exists to emulate rather than a gap in what
it can see. **Ticket 15** adopts their rule and now blocks 13 — it moves
`files_walked` and the detector set version, and a comparison run before it would
measure our divergence in all three states. The separate dedupe rule GitLab
applies to governance surfaces is written into tickets 13 and 14.

**46 `REFERENCES` edges point at paths the walk recorded no row for**, and they
are all these symlinks: `traceability.md` names `full.md`, the pointer resolver
resolves it, and the walk never made the row. One walk and one resolver
disagreeing about what is in the repository, which is the fault
`orbit/orbit_context/surfaces.py:399` names in so many words. It is a side effect of the refusal
rather than its own defect, so ticket 15 closes it and asserts the zero.

**The honest route to the direction is still a change to the corpus.** A manifest
declaring input → output is already read, at rung 2, and `build_lineage` now
proves it end to end on the workbench shape. Nothing in Advisor-Desk writes one.
That is a corpus change and out of scope, exactly as the ticket said.

**`producer-named-outside-the-pair` is 0 on this estate and non-zero on the phase
1 fixture.** The reason exists because it is a real shape, not because this
repository has it. A reason that only ever reads zero on every estate anyone has
looked at is worth re-opening at ticket 07; this one is not, and the fixture says
so.

**`ladders.from_graph` has the unbounded fetch this ticket's review caught here.**
`repo-map` briefly read every `IDENTICAL_BYTES` row to print five of them, on the
reasoning that the counts and the listing must come off the same rows. That is
fixed — the counts come from a `GROUP BY` and the listing from a `LIMIT`, both
owned by `pairs`, which keeps one owner without one fetch. `ladders.from_graph`
still fetches every `RUNG_OF` edge for a block that prints one row per ladder
height, which is bounded by the estate rather than by construction. Left alone:
it is ticket 11's code and fixing it here would put two tickets in one diff.

**The direction is written at index time, not derived at read time.** It could
have been a join between `IDENTICAL_BYTES` and `PRODUCES` rows at query time.
Writing it means the row carries the answer the run computed, on the same
argument `repo-map` makes for not re-walking the tree — but it also means a
snapshot written by an older detector set carries that set's answer, which is
what the version in every header is for.

**Five defects came out of `code-review` and are fixed and pinned by tests.**
Four of them were one mistake in two shapes: the read seam assumed the new
columns exist and are filled. On a snapshot written before this ticket they are
NULL, and `pairs_with_provenance` — stated as "every reason but one" — counted
all of them as carrying provenance, which is a false assertion and spec 0002 §9
calls that a stop rather than a bug. A NULL is now `not-measured`, named apart
from the three reasons and left out of both provenance counts, because UNKNOWN
is a measurement and this is the absence of one. On a store with no `direction`
column at all, `pairs` and `repo-map` answered with a raw DuckDB error; they now
name `orbit-context migrate`, the way `index` already does. With the listing
dropped for budget, the "N pairs not listed" line printed at the reasons'
indent with no heading above it — the exact misreading the heading exists to
prevent. And the two tallies indexed pre-seeded dicts with no membership check,
so a reason or rung written by another detector set would have surfaced as a
`KeyError` from a property; an unknown value is now counted beside the known
ones, because it is what a version mismatch looks like in the numbers.

## Acceptance

- [x] All 28 pairs carry either a direction with its evidence rung, or UNKNOWN
      with the reason — 28 of 28, every one UNKNOWN with
      `no-producer-named-at-either-end`, written on the row and printed by
      `orbit-context pairs`
- [x] The prose statement in `traceability.md` produces no `PRODUCES` edge —
      0 `PRODUCES` rows on this repository, and
      `orbit/tests/test_directions.py::TestThisRepository` reads the sentence out of the real
      file rather than a copy, so rewording it cannot quietly retire the test
- [x] `pairs` never appears in any output without `pairs_with_provenance` beside
      it — ticket 05's rule, still binding. `provenance.summary` is still the
      only place either number is produced, and `pairs.summary_lines` is now the
      only place either is printed, shared by `pairs` and `repo-map`
- [x] A pair whose direction is UNKNOWN is not counted as a pair without a
      producer for a different reason; the two are distinguishable —
      `direction_reason` separates them on the row and in
      `pairs_with_no_direction`, and both are non-zero at once on `build_estate`
- [x] Output contains no forbidden vocabulary word — linted over `pairs` and
      `repo-map` output, over every statistics key and value, and over the two
      new column names

## Watch for

Everything about this ticket pulls toward promotion. The relationship is real,
a human can read it in ten seconds, and the tool is about to report UNKNOWN
against something obvious. That discomfort is the mechanism working: the
difference between *observed* and *a sentence a human found convincing* is the
only thing separating this graph from the hand-built indexes it has to beat.

If a later ticket wants the direction, the honest route is a machine-readable
declaration in the corpus — which is a change to the corpus, and out of scope.
