# Spec 0005 — Orbit reads true

**Status:** feature specification, written to the project's `to-spec` shape.
**Serves:** spec 0003 §1.1 item 1 — *"Orbit is reliably usable on the local
estate. The store scopes to one snapshot, a documented query runs as written,
and a figure read back is a figure of something that exists at once."*
**Prior description:** `orbit/tickets/16-answers-come-from-a-named-snapshot.md`,
a legacy record written before GitHub Issues became the tracker. It is preserved
unchanged and is not the governing document; this spec is.

## Problem Statement

A figure read out of the graph today is not a figure of anything that exists.

Measured on this estate on 2026-09-12, at two points in one working day:

| | morning | afternoon |
|---|---|---|
| index runs in the store | 5 | **8** |
| `SELECT count(*) FROM gl_context_surface` | 495 | **613** |
| the snapshot that actually exists | 117 | **118** |

The store keeps every run ever indexed, so an unscoped count adds unrelated
snapshots together. **The error grows on its own**: every session indexes, and
nothing has to go wrong for the number to get further from the truth. 613 is not
a wrong measurement of the estate — it is not a measurement of anything.

There is a second, sharper form. `orbit local sql` defaults to GitLab Orbit's
own store rather than this one, and that store holds a table of the same name
with three rows left over from before the gates. So the same query returns **3**
instead of 613, **without failing**:

```
orbit local sql "SELECT count(*) FROM gl_context_surface"           ->   3
orbit local sql --db ~/.orbit-context/context.duckdb  "…"           -> 613
```

An error announces itself. A plausible small number does not, and a reader has
no way to tell it apart from a correct one.

This blocks the archaeology directly. Gate 1's fixtures are built from Orbit
observations, so a fixture resting on an unscoped figure is wrong in a way that
leaves no trace, and the nine reconstructions would inherit it.

## Solution

**Name the current snapshot in the store itself, as views, so that reading the
truth is the short query and reading an aggregate across runs is the long one.**

Today the scoped query is a six-line join that a reader must remember to write.
The unscoped one is `SELECT count(*) FROM gl_context_surface`. The incentive
points the wrong way, and the fix is to reverse it rather than to ask people to
be careful.

The views carry names that exist **only in this store**. That makes the second
problem announce itself: a query written against a current-snapshot view and run
without `--db` cannot return a plausible number, because no such view exists in
GitLab Orbit's graph. It fails, and says which table it could not find.

The view name does the work a wrapper would have done, without this project
owning a second way to ask a question.

## User Stories

1. As Dylan, I want a count I read out of the graph to be a count of files that exist together at one commit, so that I can trust a figure without auditing how it was obtained.
2. As Dylan, I want the short, obvious query to be the correct one, so that being in a hurry does not produce a wrong answer.
3. As Dylan, I want a query pointed at the wrong store to fail rather than answer, so that I never act on a plausible number from the wrong database.
4. As Dylan, I want to know which snapshot an answer came from without asking a second question, so that a figure I paste somewhere carries its own provenance.
5. As Dylan, I want to be able to ask across every run deliberately, so that comparing snapshots is still possible when that is the question.
6. As a session reading the graph, I want the current snapshot addressable by name, so that I do not have to reconstruct a three-column join from memory and get it subtly wrong.
7. As a session, I want the store to tell me how many runs it holds, so that I can see whether an unscoped figure would have been misleading.
8. As a session writing a Gate 1 fixture, I want every Orbit figure I record to name its snapshot, so that a later reader can retake it.
9. As a session, I want a query that names no snapshot to be visibly an aggregate rather than accidentally one, so that the distinction survives being copied into prose.
10. As a maintainer, I want this to work through GitLab Orbit's own CLI, so that the project does not acquire a second query surface and trip spec 0001's kill condition.
11. As a maintainer, I want the fix to live in the store rather than in documentation, so that it holds for a reader who never opens the README.
12. As a maintainer, I want the detector set version unmoved, so that every figure recorded in tickets 07 and 14 stays comparable with figures taken after this.
13. As a maintainer, I want the views declared where the tables are declared, so that a column added later appears in both without a second edit.
14. As a reviewer, I want the difference between the scoped and unscoped readings printed once, so that the size of the problem this fixed is on the record.
15. As a future session, I want the README's documented queries to match what the store offers, so that following the documentation is not its own failure mode.
16. As a future session, I want to know that this did not repair a detector, so that a figure moving after this date is not attributed to it.

## Implementation Decisions

**The scope lives in the store, as views over the existing tables.** Not in a
new command, and not only in documentation. A reader who never opens the README
still gets a correct answer, which is the whole difference between a mechanism
and a hope.

**The views are named so they exist only in this store.** A query against a
current-snapshot view, run without `--db`, fails and names the table it could
not find. This is the entire mitigation for the wrong-store problem, and it is
chosen over wrapping GitLab's CLI because the wrapper would be a second way to
ask the same question.

**This is not a second query language, and the distinction matters** because
spec 0001 §13 makes one a kill condition: *"It needs its own store, its own
query language, or a second implementation."* A view is plain SQL over the same
DuckDB file, read with the same CLI. Nothing new is learned to use it, and
`gl_context_*` remains queryable exactly as before. **If the work finds itself
adding a query command, a second store, or a syntax, it has hit the kill
condition and stops.**

**"Current" means the most recent index run for a repository**, keyed on
`(project_id, branch, commit_sha)` — the same key the store already replaces
rows on. Where the store holds several repositories, current is per repository,
not one global winner.

**An answer names its snapshot.** The views expose the snapshot key alongside
the rows rather than hiding it, so a figure can carry its provenance into prose
without a second query. Spec 0002 §9's rule — a number that cannot be tied back
to named files is not a result — is the reason.

**Aggregating across runs stays possible and stays explicit.** The base tables
are untouched and remain the way to ask a question about several snapshots. The
change is which of the two is the short query.

**The detector set version does not move.** The five hashed modules decide what
is recognised; views decide which rows an answer covers. Verified before writing
this spec: the ontology and the store are deliberately outside the digest.
**Editing a hashed detector module means the work has left this spec.**

**The declaration sits with the ontology**, so a column added to a table appears
in the view without a second edit. A view that lists columns by hand is a second
place to forget one.

## Testing Decisions

**A good test here asserts what a reader can observe** — the rows a query
returns from a store built by the test. It does not assert how the view is
declared or which SQL the tool emitted.

**One seam, and it already exists.** Build a fixture estate, index it, query the
store. Every recognition, pointer and provenance test uses it, and no new seam
is proposed.

What is tested:

- a store holding **two index runs of one repository** returns only the newer
  run's rows from the current view, and the sum of both from the base table —
  the defect, reproduced and then fixed, in one test;
- the row count from the current view equals the count of surfaces at that
  commit, so the view is not merely smaller but correct;
- a store holding **two repositories** returns each repository's own current
  snapshot, not one global newest;
- an answer carries its snapshot key;
- the view exists in a store this project built and is absent from one it did
  not, which is what makes a wrong-store query fail rather than answer;
- the detector set version is unchanged across the work, asserted rather than
  described.

**Prior art** is the existing fixture-estate tests, which build an estate
holding one of every case, index once in `setUpClass`, and query the result with
the same SQL a reader would write. The two-run case is the new fixture shape
this needs, and indexing the same estate twice is the whole of it.

**Not asserted:** the live 613-against-118 reading. That is this repository's
own content, and spec 0002 §6 keeps live figures in evidence records rather than
in tests, because a test that reads live content fails whenever the content
changes.

## Out of Scope

- **No change to what is recognised.** No detector, no recognition rule, no
  pointer detector, no repair of the classes F2 and F9 record.
- **No new command, no second store, no query syntax.** Spec 0001 §13's kill
  condition, named above.
- **No writing to GitLab Orbit's store.** The three leftover rows there are not
  this project's to remove, and ticket 09 records that several repositories in
  one store is the design rather than a fault.
- **No migration of existing runs.** The store keeps what it has; this changes
  which rows an answer covers, not which rows exist.
- **No `client` column.** That is spec 0004, undecided behind Gate A.
- **No hot-context retrieval or hydration.** Spec 0003 §10.

## Further Notes

**This is calibration, not a convenience.** Gate 1 reconstructs nine historical
failures from evidence, and Orbit observations are part of that evidence. An
unscoped figure in a fixture is wrong without any sign of being wrong, and the
fixtures would carry it forward into Gates 2 and 3. Doing this first is not
deferring the archaeology; it is the first step of doing it honestly.

**The figures in the Problem Statement are evidence and will move.** They were
taken at 5 and then 8 runs on one day. After this lands, a figure retaken is not
comparable with one taken before it, and any figure retaken says which side of
this change it came from. That is the same rule ticket 16 recorded and the
reason it recorded it.

**What would show this was the wrong fix:** a reader still writing the long join
out of habit, or a figure appearing in prose without its snapshot. Either means
the incentive was not actually reversed, and the answer is not to add a rule
telling people to use the views.
