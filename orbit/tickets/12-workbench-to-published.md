# 12 — Workbench to published carries a direction where evidence allows

**Blocked by:** 11
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

`_rule-workbench/PROCESS.md`, `RELEASE.md` and `CHECK_COMPATIBILITY.md` describe
how the corpus is produced. They are surfaces to be recognised, not instructions
to be executed or evidence to be promoted.

## Acceptance

- [ ] All 28 pairs carry either a direction with its evidence rung, or UNKNOWN
      with the reason
- [ ] The prose statement in `traceability.md` produces no `PRODUCES` edge
- [ ] `pairs` never appears in any output without `pairs_with_provenance` beside
      it — ticket 05's rule, still binding
- [ ] A pair whose direction is UNKNOWN is not counted as a pair without a
      producer for a different reason; the two are distinguishable
- [ ] Output contains no forbidden vocabulary word

## Watch for

Everything about this ticket pulls toward promotion. The relationship is real,
a human can read it in ten seconds, and the tool is about to report UNKNOWN
against something obvious. That discomfort is the mechanism working: the
difference between *observed* and *a sentence a human found convincing* is the
only thing separating this graph from the hand-built indexes it has to beat.

If a later ticket wants the direction, the honest route is a machine-readable
declaration in the corpus — which is a change to the corpus, and out of scope.
