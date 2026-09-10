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

## Decision — a mismatch is a failed run, with the remedy named

Taken before the code was written, and recorded here because the acceptance asks
for it.

**A column the store carries that the ontology does not declare stops the run.**
No rows are written, and the message names the table, the column and the command
that resolves it:

```
orbit-context: the store at ~/.orbit-context/context.duckdb carries columns the
ontology does not declare: gl_context_surface carries client, activation,
evidence_class, detector. No rows were written. To bring the store to the
ontology, run `orbit-context migrate --db ~/.orbit-context/context.duckdb`,
which removes such a column where it holds no values and names it where it does.
```

Not an automatic migration, for one reason: removing a column cannot be undone,
and a run that prints `surfaces: 214` while having removed one is a run whose
number cannot be read afterwards. A count is exactly the thing that cannot show
the difference between the estate changing and the schema changing — which is
the same argument the detector version already exists for.

So the removal is its own command, `orbit-context migrate`, and it holds two
rules:

- **A column holding values stops the migration**, named with how many rows hold
  it, and nothing is altered — not even the declared columns it would otherwise
  have added, because a refusal that had already changed the schema is not the
  refusal its own message says it is. Whether what such a column holds is a
  leftover or data is not something this tool can tell, so `--remove-values` is
  the decision, taken by hand and named on the command line.
- **One refused column stops the whole migration**, not just its own table's
  part of it. A store left half at one schema and half at another is harder to
  read than the drift it was meant to resolve.

This is the state the real store is in. Its three prototype rows — GitLab
Orbit's own `CLAUDE.md`, `AGENTS.md` and `crates/indexer/AGENTS.md` at
`0fe19ac` on `main` — carry `client`, `activation`, `evidence_class` and
`detector` under detector `proto-0`, so `migrate` names all four and stops. Run
on a copy, the whole sequence completes: the run refuses, the migration refuses,
`--remove-values` takes the four columns with every table's row count unmoved
either side (3 rows before, 3 after), and the next `index` lists both snapshots
the store then holds.

That run also names the three prototype rows for what they are. No `gl_context_run`
row accounts for them, so they appear under `rows_outside_a_recorded_run` as
`gl_context_surface: 3` — rows carrying no detector version and no index time,
reported apart rather than folded into a total that would read as though they
carried both. Removing them is a row decision, separate from the column
decision above, and still Dylan's.

The report carries each table's row count either side of the removal, which is
the guard the section below asks for, run automatically rather than by hand.

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
