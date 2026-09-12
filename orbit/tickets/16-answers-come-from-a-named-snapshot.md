# 16 — An answer names the snapshot it came from

**Blocked by:** —
**Demo when done:** a query against the store returns the current snapshot, or
says which snapshot it returned. Neither requires the caller to write a join.

## The condition

The store holds one row-set per `(project_id, branch, commit_sha)` — the key
`orbit/orbit_context/store.py` replaces rows on. It holds every run ever
indexed. A query that does not name a snapshot sums them.

Measured on this repository, 2026-09-12, five runs present:

| query | rows |
|---|---|
| `SELECT count(*) FROM gl_context_surface` | 495 |
| the same, scoped to the newest run | 117 |

495 is five runs added together. It is not a count of anything that exists at
once, and nothing in the output says so.

There is a second, sharper form of the same condition. `orbit local sql` without
`--db` reads `~/.orbit/graph.duckdb`, GitLab Orbit's own store, which is not
this one. It **does not fail** when it does:

| invocation | rows |
|---|---|
| `orbit local sql "SELECT count(*) FROM gl_context_surface"` | 3 |
| `orbit local sql --db ~/.orbit-context/context.duckdb "…"` | 495 |

Three is a plausible number. That is what makes it the worse of the two: an
error announces itself, and a small believable figure does not.

Every `orbit local sql` example in `orbit/README.md` was written without `--db`
— fourteen of them — and its prose said "pointed at our file" while the command
was not. Corrected in the README on 2026-09-12, with the snapshot clause shown
once beside the examples. **That fixed the documentation, not the condition.**
The next caller who writes a query by hand meets it again.

## Do

Decide which of these the tool does, and do one:

- an answer is scoped to the newest run for the repository unless another is
  named, and the snapshot it used is printed beside the figure
- a snapshot is named explicitly, and a query that names none is refused the way
  `repo-map` refuses a commit it has no index run for — naming the remedy
- the queryable surface is a set of views already carrying the scope, and the
  raw tables are the thing a caller opts into

The third is the smallest change to what a caller types and the largest to what
the schema looks like from outside. None is chosen here.

**`--db` is the same decision in a different place.** Whatever scoping the tool
grows, a caller reaching our tables through Orbit's CLI has to reach the right
file or be told they have not.

## Acceptance

- [ ] The decision above is made and recorded in this ticket, with the reason
- [ ] A figure read from the store either is the current snapshot or names the
      snapshot it is
- [ ] A query naming no snapshot does not silently sum runs
- [ ] Reaching the wrong store does not return a plausible number
- [ ] `orbit/README.md`'s examples match whatever the tool does after this
- [ ] The detector set version is unmoved by this ticket — this changes which
      rows an answer covers, not what any detector recognises
- [ ] Output contains no forbidden vocabulary word

## Watch for

**This ticket can silently move published figures.** Every count in ticket 07,
ticket 14 and the spec 0003 evidence was taken by a query written by hand. If
scoping changes what an unscoped query returns, a figure retaken afterwards is
not comparable with the one recorded, and the difference will look like the
estate moved. Any figure retaken after this lands says which side of it it was
taken on.

**Five runs is a small number.** The store grows one row-set per index run, and
every session indexes. The gap between 495 and 117 widens on its own.
