# 09 — The store holds only what this run put there

**Blocked by:** —
**Demo when done:** index Advisor-Desk, and the output names every repository in
the store, not only the one just indexed.

## Do

Two conditions, both currently untrue.

**The schema matches the ontology.** `orbit-context index` prints, today:

```
orbit-context: gl_context_surface carries columns the ontology does not declare:
client, activation, evidence_class, detector
```

Those four are leftovers from the pre-gate design — `evidence_class` and
`client` are the two candidates spec 0001 §6 put behind gates that have not been
opened. The tool already detects the drift. Decide whether a mismatch is a failed
run with the remedy named, or an automatic migration, and make it one of them.

**The store's contents are visible.** The store also holds a prior index of
GitLab Orbit's own repository — `CLAUDE.md` 17,294 bytes, `AGENTS.md` 17,294,
`crates/indexer/AGENTS.md` 15,133 — alongside today's Advisor-Desk run. Multiple
repositories in one store is the design, not a fault. Not being able to see them
is the fault: a count read from the store is only interpretable if what else is
in there is on the same screen.

So the index output states every repository present, with its branch, commit and
the detector version that produced its rows.

## Acceptance

- [ ] Every `gl_context_*` table's columns match its ontology YAML exactly, and a
      mismatch either fails the run naming the remedy or migrates, by a decision
      recorded in this ticket
- [ ] The four pre-gate columns are gone from the store
- [ ] Index output lists every repository in the store — branch, commit, index
      time, detector version — not only the one indexed
- [ ] Re-indexing one repository leaves the others' rows untouched, and the
      output says which rows it replaced
- [ ] Rows written under a different detector version are distinguishable from
      rows written under the current one

## Watch for

Removing a column is the cheapest place in this batch to move a number without
noticing. Before and after the rebuild, the counts for surfaces, clauses, edges,
pointers and identical-byte pairs must be identical — those four columns carry no
count. If any of them moves, something else changed at the same time and it needs
finding before ticket 10 starts.
