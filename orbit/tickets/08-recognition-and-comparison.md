# Spec 0002 — Recognition, and the three-state comparison

Spec: `orbit/specs/0002-recognition-and-the-three-state-comparison.md`

Seven tickets. Work top to bottom; each is blocked by the one before it, because
each measures something the previous one made measurable.

**Five are done. The frontier is 13.**

| # | Ticket | Blocked by | State |
|---|---|---|---|
| 09 | The store holds only what this run put there | — | done |
| 10 | A rule file is a surface | 09 | done |
| 11 | The ladder is queryable | 10 | done |
| 12 | Workbench to published carries a direction where evidence allows | 11 | done |
| 15 | A symlink is a node, never read | — | done |
| 13 | Two states compare | 12, 15 | **frontier** |
| 14 | Three states, and ticket 07 re-scoped | 13 | |

**15 is out of numerical order on purpose.** It was written after 12 and belongs
before 13: it moves `files_walked` and the detector set version, and spec 0002's
own rule is that two counts either side of a detector change are not comparable.
Run after the comparison, every figure 13 and 14 record is from a superseded
detector set. Renumbering the batch to make the order read left to right would
break every reference already in the tickets and the git history, so the order
is stated instead.

Each closed ticket carries its own acceptance run as evidence, hand-checked and
never asserted in a test.

**Prefactoring: ticket 09.** The store carries four columns the ontology no
longer declares and holds a prior index of another repository. Every count taken
against it is arguable until neither is true. Nothing else in this batch is worth
measuring first.

**Second prefactoring, found at ticket 12: ticket 15, now done.** Our walk
refused symlinks; GitLab Orbit's lists them as nodes it never reads, with a
reason of its own (`non_regular_file`). That is a divergence from the tool this
project exists to emulate faithfully, it was invisible in every count taken
before it, and it is carried by all three comparison states — so a three-state
comparison run on the old walk would have measured our divergence in each of
them and called the result a finding about governance. Same argument as 09,
found later.

## What this batch is

Phase 1 built an observer that recognises governance by vendor filename. Run
against a repository whose entire content is governance, it recognised **0 of 238
files walked**. This batch closes that gap, then uses three states of one
upstream to decide whether the whole thing works.

**Ticket 07 does not run until 14 is done.** That is the point of the batch.

## The three states

| state | where | what happened |
|---|---|---|
| **C0** | Advisor-Desk `main` @ `a7d7649` | 50 commits, one author, no agent work |
| **C1** | Advisor-Desk branch head | C0 + 19 commits that built a tool |
| **C2** | agent-rules-books | C0 + work that grew its own governance layer and stopped producing |

C0 is in this repository's own history — no remote, no network. C1 did not
rewrite C0: outside `orbit/`, `main..HEAD` is two lines of `.gitignore`. Whether
C2 rewrote its base is **not known** and ticket 14 establishes it first.

## Known by hand — the reconciliation target

Advisor-Desk at `main`: **201 files, 198 of them markdown.**

| group | count |
|---|---|
| book directories | 14 |
| published rule files (`<book>/<book>[.mini|.nano].md`) | 42 |
| `_rule-workbench/` files | 45 |
| `docs/` files | 95 |
| `README.md`, `CHANGELOG.md`, `LICENSE`, `.gitignore`, one `.png` | 5 |
| `_rule-workbench/<book>/full.md` symlinks | 14 |

The fourteen symlinks were written down as *never walked*. Ticket 15 changes that
sentence, not the count: they are walked, listed as nodes and never read, which is
what GitLab Orbit does with a symlink. The 201 total does not move.

Two figures corrected by ticket 10, which reconciled against this table rather
than counting again: published rule files were written down as 43 and are 42 —
14 books at three rungs — and `CHANGELOG.md` was missing from the root group.
42 + 45 + 95 + 5 + 14 = 201, the total this ticket already states.

The 42 was then reached a second way by ticket 11, which found the same files as
**14 ladders of 3 rungs** off their filenames rather than off their contents. Two
routes to one figure is what makes it a reconciliation rather than a count.

Byte-identical pairs found by phase 1: **28**, with provenance: **0**.
Ticket 12 reached the same 28 a second way — 14 books at two rungs each, `mini`
and `nano`, every one crossing from `_rule-workbench/` to a published file, with
the third rung absent because `full.md` is a symlink — ticket 15 lists it as a
node and never reads it, so it is in no pair. All 28 carry an explicit
`UNKNOWN: no-producer-named-at-either-end`: nothing in this corpus declares the
relationship anywhere a tool can read it.
One ladder, for reference: `refactoring.md` 17,866 / `.mini.md` 5,167 /
`.nano.md` 1,986 bytes — the three ticket 11 printed back, byte for byte.

A count that cannot be tied back to these named groups is not a result.

## Rules for every ticket

All of `00-phase-1.md` still applies — the vocabulary constraint, no prose
columns, ontology YAML before Python, tests ship with the ticket, never open
GitLab Orbit's file for writing. Added for this batch:

- **On resuming after a clear or a restart, run `repo-map` before describing
  state.** Branch, commits ahead, and which of them carry this session's
  `Claude-Session` trailer are read off disk, not recalled. A context window is
  not a record of what was done: work committed and pushed fifteen minutes
  earlier has already been described in this project as having "no record",
  which was a statement about memory phrased as one about the repository.
  Ticket 06 built the command for exactly this moment; reaching for ad-hoc
  `git log` instead is how the wrong sentence gets written.
- **Recognition must reconcile by hand.** Against the table above, naming files,
  not just producing a number.
- **The acceptance run is evidence, never a test assertion.** Tests that read
  live repository content fail whenever that content changes, including from
  this work. Seam A and Seam B carry the assertions; the real run produces a
  report a human checks.
- **Two counts either side of a detector change are not comparable.** The
  detector version is derived from detector inputs and moves on its own; any
  output that spans the change says so.
- **agent-rules-books is read-only.** Index it, never write to it, never push to
  it, never open a pull request against it.
- **Nothing in C2 is labelled.** The vocabulary constraint is at its most
  load-bearing here: a repository whose governance grew is a condition, reported
  as counts and bytes.
- **Seams, both agreed:** Seam A is `build_*(estate) → index(estate, db_path) →
  assert on the stats dict and `gl_context_*` rows`. Seam B is the command line.
  No third seam without going back to the spec.
- **Fixtures: new builders, `build_estate` untouched.** 415 tests assert against
  it, many on absolute counts. Re-baselining them risks switching off a test that
  was catching something.
