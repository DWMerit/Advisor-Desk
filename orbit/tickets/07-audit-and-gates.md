# 07 — The estate, in two families, and both gates

**Blocked by:** 06, 14. Re-scoped by ticket 14 before it ran, as spec 0002 §8.4
requires.
**Demo when done:** two reports — the lineage comparison and the hand-built
audit — plus two recorded gate decisions.

Phase 1's exit run is **simultaneously** the estate audit and the input to both
gate decisions. Two passes, not three, and they are two because the estate is
two families with two different kinds of answer available.

## Why this ticket was rewritten

It used to be one pass over the whole estate. That conflates spec 0002 §4's two
families, and the difference between them is not presentational:

| family | repositories | shared origin? | what can be said |
|---|---|---|---|
| **clone lineage** | Advisor-Desk, agent-rules-books | yes — one upstream | a delta against a common base |
| **hand built** | Home-system, Estimating-Lab, Merit-knowledge | no | absolute figures, and whatever they are argued against |

A delta is only a measurement where the two states share a base. Run over a
hand-built repository it is a subtraction between two unrelated numbers, and
printing it beside a lineage delta would let one be read as the other.

## Part 1 — the clone lineage, as a controlled comparison

**Runs first, and it is already runnable.** Ticket 14 ran it for C0, C1 and C2:

```sh
orbit-context compare a7d7649 <head> /home/user/agent-rules-books@782a886 --repo .
```

What Part 1 owes beyond that run:

1. **Re-run it against the head this ticket is executed on**, and name that head
   by its commit. C1 moves with every session, so a table that does not name the
   commit it was taken at is not reproducible.
2. **Establish the base before reading any delta**, the way ticket 14 did: the
   fourteen `full.md` links per state from the rows, and the shared corpus by
   git blob id across the trees. Ticket 14's answer — 195 of C0's 201 paths
   identical in C2, no book or `_rule-workbench` file among the six that moved —
   holds for `782a886` and has to be retaken if C2 has moved on.
3. **Carry ticket 14's recognition finding forward.** Three files present and
   byte-identical in both C0 and C2 are recognised in one and not the other,
   because C2's additions took `_rule-workbench/` under the corpus rule's 0.75
   declared share. Any surface delta over a repository whose corpus directories
   changed shape has to say whether the same thing happened there. A count that
   moved because a share moved is not a count of files anyone added.

**agent-rules-books is read-only.** Index it. Never write to it, never push to
it, never open a pull request against it. `compare` materialises every state as
a clone for this reason, so running it is enough.

## Part 2 — the hand-built family, as an audit

**Runs second.** Home-system, Estimating-Lab, Merit-knowledge. No shared origin,
so `compare` is the wrong instrument and `orbit-context index` plus `repo-map`
is the right one.

Report, per repository: git state; surfaces by kind and recognition, with the
number folded beside the count; files and bytes walked; clauses by type; edges
by kind; pointers by detector; the three non-resolutions with the detector set
version; identical-byte pairs with their provenance counts; coverage notes.

**Conditions and evidence only.** Nothing is labelled broken, obsolete,
misplaced or safe to delete. Zero recognised inbound pointers is a statement
about the detector set, not about a file.

**Whatever a figure here is measured against is argued in writing, or it is not
measured against anything.** There is no baseline. An absolute figure is a
result on its own — "this repository holds N surfaces over M files" — and any
comparison to another repository, to a lineage state, or to an expectation is a
claim that has to carry its argument beside it.

## Part 3 — Gate A: does the load ledger earn its place?

Unchanged.

**Before looking at the data**, write down the three questions about loading you
actually want answered. Then attempt each in plain SQL over the phase-1 tables.

- **All three answer** → the ledger is not built. Filename convention plus
  `size_bytes` was enough. Record the result.
- **They do not, and the same column is missing each time** → build **only that
  column**.

Prior signal: phase 1 catches byte-identical `AGENTS.md`/`CLAUDE.md` pairs with a
hash, but cannot say a Claude session pays one and a Codex session the other. So
`client` is the likeliest — possibly the only — surviving column. The honest
first version may be one column, not fourteen.

## Part 4 — Gate B: do evidence columns earn their place?

Unchanged.

Take a **random sample of 50 findings** and hand-classify each as a real estate
condition or a detector artifact.

- **False-positive rate low and uniform across detectors** → not built. A single
  `detector` column suffices to trace a rule that reads wrongly; the four-way
  class is ceremony.
- **Rate high, or varying sharply between detectors** → built. A finding whose
  reliability depends on which rule produced it must carry that rule.

The 1,349-of-1,373 phantom rate is a strong argument, but it came from **one
fixed bug**. The question is the steady-state rate, and only the sample answers
it.

**Sample across both families.** A rate taken only over the lineage is a rate
over one corpus shape, and the hand-built repositories are where the detectors
have seen least.

## Acceptance

- [ ] The lineage comparison is re-run and its head named by commit
- [ ] The base is established from the rows and the trees before any delta is read
- [ ] Every repository in the estate appears in one of the two parts, and which
      part it is in is stated
- [ ] No delta is reported for a repository with no shared base
- [ ] The three questions for Gate A were written down before the data was examined
- [ ] Each Gate A question is marked answerable or not, with the SQL attempted
- [ ] 50 findings sampled and hand-classified, with the rate broken down by
      detector and by family
- [ ] Both gate decisions recorded — including "not built", which is a result
- [ ] Any surface delta that moved because a corpus share moved says so
- [ ] Kill conditions checked against both parts before any phase 2 work starts
- [ ] Output contains no forbidden vocabulary word

## Either gate closing is a result, not a failure

Record it, so a future session sees the additions were tested rather than
re-proposing them from scratch.

---

# Gate A — the three questions, written before the data

**Committed on its own, before any query was run against the phase-1 tables**, so
that the order is in the history rather than asserted afterwards. Nothing below
was chosen for being answerable; the schema was not consulted while writing
them. Head at the time of writing: `38b9dce`.

**Q1 — When a session opens in this repository, which surfaces reach it, and
what do they weigh?** The cold-start bill, per client. Not "which surfaces
exist" — which ones arrive without anybody asking for them.

**Q2 — Of the bytes that reach a session, which are paid for twice?** The same
content arriving under two names, or a smaller rung of a ladder arriving
alongside a larger one that already contains it.

**Q3 — Which of those surfaces can a session stop paying for, and which are
unconditional?** A surface that loads on a trigger costs nothing until the
trigger fires. A surface that loads always is a floor.

Each is attempted below in plain SQL over the phase-1 tables, and marked
answerable or not answerable with the SQL that was attempted either way.
