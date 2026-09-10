# 14 — Three states, and ticket 07 re-scoped

**Blocked by:** 13
**Demo when done:** the three-state table, and ticket 07 rewritten so it can be
run.

## Do

**First, attach agent-rules-books and establish whether C2 rewrote its base.**
C1 did not — outside `orbit/`, `main..HEAD` is two lines of `.gitignore`, so
`C1 − C0` measures what a session *added*. Whether the same holds for C2 is not
known. If C2 rewrote its base, the two deltas are not the same kind of
measurement, and the report says so rather than tabling them side by side.

**The fourteen `full.md` symlinks are a cheap first test of exactly that.** C0
carries them as symlinks (`10f71b9`, git mode `120000`, authored upstream on
2026-04-26 and never touched since), so C2 inherited them. Ticket 15 makes a
symlink a node with its own size, which means the question can be asked of the
rows rather than by hand: if C2 holds fourteen 32-byte links, its base is intact
in this respect; if it holds fourteen full-sized regular files, something
resolved them, and a copy that no longer tracks its source is a base rewrite
whatever else the diff says. Either answer is a result. Report it before any
delta is read as comparable, and report which of the two it is rather than only
that they differ.

Then produce the comparison:

| state | what it is |
|---|---|
| **C0** | Advisor-Desk `main` @ `a7d7649` — untouched upstream |
| **C1** | Advisor-Desk branch head — built a tool, corpus untouched |
| **C2** | agent-rules-books — grew its own governance layer, stopped producing |

**agent-rules-books is read-only.** Index it. Never write to it, never push to
it, never open a pull request against it.

**Ticket 13's dedupe applies to all three states, and C2 is where it can bite.**
Two names for one file count once, labelled by the target — GitLab's rule at
`crates/orbit-local/src/commands/setup.rs:265-271`. A repository that grew its own
governance layer is exactly the shape that acquires a `CLAUDE.md` symlinked to an
`AGENTS.md`, or a rule file exposed under two names, and counting those twice
would report governance growth that is one file wearing two hats. Report the
number folded per state beside the counts, never inside them.

**One question is asked here, not built.** The collapse in C2 plausibly shows up
as governance bytes rising against product bytes. Report the ratio for all three
states as an observation. Do **not** build a metric, a threshold or an alert for
it — spec 0002 §11 refuses that explicitly, because building a measure for a
hypothesis before measuring it is the same failure this whole batch is aimed at.

**Then re-scope ticket 07.** It is currently written as one pass over the whole
estate, which conflates the estate's two families:

- **clone lineage** — Advisor-Desk, agent-rules-books. Shared upstream, so a
  controlled comparison is possible. Runs first.
- **hand built** — Home-system, Estimating-Lab, Merit-knowledge. No shared
  origin, no baseline, so it is an audit and whatever it is measured against has
  to be argued. Runs second.

Gate A and Gate B keep their rules unchanged, including that the three Gate A
questions are written down **before** the data is examined, and that "not built"
is a recorded result.

## Measured before this ticket ran — vocabulary, 2026-09-10

C2 is cloned at `/home/user/agent-rules-books` (`782a886`, 515 tracked files:
386 Markdown, 51 JSON, 35 Python). It holds no Orbit implementation. Our
vocabulary was measured against it before the comparison, so a term appearing in
both is a reading taken on purpose rather than a surprise mid-run.

**Every compound identifier we use appears in zero of its files.** All of
`instruction-surface`, `skill-package`, `agent-definition`,
`command-definition`, `hook-definition`, `hook-target`, `mcp-config`,
`no-indexed-target-match`, `outside-indexed-roots`, `unresolvable-scheme`,
`bare-path-literal`, `frontmatter-field`, `import-statement`, `config-value`,
`supersedes-claim`, `markdown-link`, `artifact-header`,
`manifest-declaration`, `literal-write-path`, `rung_of`, `external_ref`,
`index_run`, `coverage_note`, `gl_context`, `surface_kind`. The compound shape
of the names is what makes them unambiguous; nothing else was needed.

**Our single English words appear throughout, as English.** `surface` in 66 of
515 files — "reliably surface defects", "a large surface with minor helpers" —
and `contains` 47, `references` 41, `produces` 36, `clause` 15. These were never
identifiers. A count of them says nothing about either graph.

**One term is shared with a different meaning.**
`.claude/skills/video-harvest/SKILL.md` runs its own provenance scheme:
`SOURCE: SCREEN-READ` or `SOURCE: INFERRED`, with a named failure,
`source_out_of_contract`, for a model that "graded its own evidence instead of
saying whether it read the frame". `INFERRED` appears in 7 files and `UNKNOWN`
in 4 under that scheme. `OBSERVED` and `DECLARED` appear in none.

**Recorded, not designed against.** Two repositories reaching for the same word
for the same idea is an observation about the estate, and plausibly a symptom of
the layer this project exists to decompose rather than a naming fault to
engineer around. Candidate B is still gated, and whatever ticket 07 decides
about evidence columns it now decides knowing this. Nothing here changes a
detector, a name, or a gate.

## The pass mark, set before any data

**If Orbit cannot show a measurable difference between C0, C1 and C2, it does not
work.** Not "needs more detectors" — spec 0001 §13's kill conditions apply and
the project stops. This was agreed before the run for exactly the reason that it
would be negotiable afterwards.

Also binding: no finding may assert something false. A single false assertion is
a stop, not a bug. Any question the run cannot address is recorded as a coverage
gap, which is a result.

## What the run found

`orbit-context compare a7d7649 dc16a3e /home/user/agent-rules-books@782a886
--repo .`, detector set `1.8eabab386316`, all three states read by it. C2 is
addressed as `path@ref`, and every state is materialised as a clone rather than
a worktree, so nothing was written to any of the three repositories.

| | C0 `a7d7649` | C1 `dc16a3e` | C2 `782a886` | C1 − C0 | C2 − C0 |
|---|---|---|---|---|---|
| files walked | 201 | 323 | 515 | +122 | +314 |
| bytes walked | 2,172,106 | 3,239,053 | 10,432,071 | +1,066,947 | +8,259,965 |
| surfaces | 87 | 103 | 126 | +16 | +39 |
| two names for one file, folded | 14 | 14 | 14 | 0 | 0 |
| clauses | 7,560 | 7,901 | 8,089 | +341 | +529 |
| pointers | 224 | 314 | 344 | +90 | +120 |
| surface bytes | 781,674 | 853,575 | 946,722 | +71,901 | +165,048 |

### C2 did not rewrite its base, and the fourteen links are how the question was put

**All three states hold fourteen names that resolve to another name, 812 bytes
of them, all fourteen folded.** Not fourteen in one state and fourteen in
another: the same fourteen paths naming the same fourteen targets, read off the
rows rather than counted by hand — `_rule-workbench/<book>/full.md` naming
`<book>/<book>.md`, in every state. C2 inherited them as symlinks and still
holds them as symlinks. Had something resolved them, the rows would carry
fourteen regular files weighing what the books weigh, and the fold — which
reports fourteen either way — would not have said so on its own. That is why the
link count and what the links weigh are now printed beside it.

**The rest of the base was checked by hand, because the tool cannot yet ask it.**
Byte identity is measured inside one snapshot, so "is this file the same file in
another repository" is not a question the graph answers. Compared by git blob id
across the two trees, C0's 201 paths land in C2 as:

| | paths |
|---|---|
| identical in bytes and mode | 195 |
| present and edited | 5 — `.gitignore`, `CHANGELOG.md`, `README.md`, `docs/CRITICISM.md`, `docs/USAGE.md` |
| absent | 1 — `docs/ADDING_THE_BOOK.md` |

**No book file and no `_rule-workbench` file is among the six.** The rule corpus
C0 and C2 share is byte-identical at both ends, so `C2 − C0` and `C1 − C0` are
the same kind of measurement — additions against an unmoved corpus — with the
one qualification that C2's figures are net of one removed file, which is where
`docs` reads 95 → 98 for four files added.

**A coverage gap, recorded as a result.** The C2 clone available to this session
is shallow: one commit, no history. Whether `a7d7649` is an ancestor of
`782a886` could not be established from it, so the base question was answered
from content and not from lineage. A repository that reproduced C0's bytes
without descending from C0 would be indistinguishable here, and nothing in this
run rules that out.

### The deltas tie back to named files

Spec 0002 §9: a number that cannot be tied back to named files is not a result.

**C1 − C0 is +16, and all sixteen are named.** Sixteen `skill-package` rows, one
per `.claude/skills/<name>/SKILL.md`, and nothing else. No row of C0 is missing
from C1. The corpus is untouched: every directory holding a book is at delta 0,
and so are `docs/` and `_rule-workbench/`.

**C2 − C0 is +39, which is 42 rows C0 does not carry, less 3 of C0's that C2
does not.**

| rows C2 carries and C0 does not | count |
|---|---|
| `skill-package` — under `.claude/skills/`, `skills/`, and three under `evals/` | 25 |
| `instruction-surface`, `corpus-adjacent` — `_rule-workbench/<book>/skill.frontmatter.md`, one per book | 14 |
| `instruction-surface`, `vendor-name` — `AGENTS.md`, `CLAUDE.md`, `evals/AGENTS.md` | 3 |

**The three rows C2 does not carry are the finding to be careful with.**
`_rule-workbench/CHECK_COMPATIBILITY.md`, `PROCESS.md` and `RELEASE.md` are
present in C2, byte-identical to C0's, and are not recognised there. Nothing
happened to those files. The corpus rule reads a directory's share of files that
declare themselves, and C2 added one undeclared `skill.frontmatter.md` per book
to that subtree:

| | read Markdown under `_rule-workbench/` | declared | share |
|---|---|---|---|
| C0 | 45 | 42 | 0.933 |
| C2 | 59 | 42 | 0.712 |

The threshold is 0.75, so `_rule-workbench/` is a corpus in C0 and is not one in
C2, while all fourteen book directories inside it are a corpus in both. Three
files lost recognition because of what was added beside them. That is a property
of the detector set and not of those files, it is the same detector set at both
ends, and a reader taking the −3 as three files C2 removed would be reading
something false out of a correct number.

### The byte share, as an observation and nothing else

Surface bytes against bytes walked, all three states:

| state | surface bytes | bytes walked | share | not recognised |
|---|---|---|---|---|
| C0 | 781,674 | 2,172,106 | 0.360 | 1,390,432 |
| C1 | 853,575 | 3,239,053 | 0.264 | 2,385,478 |
| C2 | 946,722 | 10,432,071 | 0.091 | 9,485,349 |

The hypothesis this was to look at is governance bytes rising against product
bytes in C2. **The share falls, and it falls furthest in C2.** Two things stop
that being read as an answer either way:

- **What is not a surface is not thereby product.** On this estate most of the
  bytes these detectors do not recognise are the rule corpus itself — 198
  Markdown files of distilled rules that no vendor named and that mostly do not
  declare themselves. A share of surface bytes is a share of what the detectors
  recognise, and calling the remainder product would assert something false.
- **C2's denominator is one directory.** `evals/` is 7,656,107 of its
  10,432,071 bytes, 73%, against nothing of the kind in C0 or C1. Excluding it
  would give a different share; so would excluding anything else. This run picks
  no denominator beyond the walk's own, because picking one is the metric spec
  0002 §11 refuses.

No metric, threshold or alert was built, and nothing in the tool divides these
two columns. They are printed beside each other, and the division above is a
reading taken here, in prose, where it can be argued with.

### The pass mark

**Applied, and passed.** The three states are measurably different on the
detector set that existed when the run started: 87, 103 and 126 surfaces; 201,
323 and 515 files; 781,674, 853,575 and 946,722 surface bytes; 0, 16 and 25
skill packages. No detector was added to find any of it — `1.8eabab386316` is
the set ticket 13 ran, unmoved by this ticket's two new columns, which was
checked rather than assumed.

Every figure above is a count or a byte total read off the rows, and the three
statements that go beyond counting — the base is intact, the shared corpus is
byte-identical, three files lost recognition to a share rule — are each shown
above with the figures they rest on.

## Decisions taken here

**A state is `path@ref`, and the `@` is read from the right.** Only where the
text before it names a directory that is there. A git ref may hold one —
`main@{yesterday}` — and a rule that split on the character alone would take a
ref apart and then report a repository it invented as one that could not be
read.

**Every delta is against the baseline, never chained.** `C2 − C1` is a
subtraction between two repositories that never shared anything but C0. Printed
as a delta it would read as one session having done what a second repository
did.

**A state is materialised by cloning, not by `git worktree add`.** The ticket
says agent-rules-books is never written to, and `worktree add` writes to the
repository it is run in. A clone leaves nothing behind in the repository it
read, and it is the same operation for all three states — a materialisation
that wrote to one repository and not to another would also be two kinds of
reading. The test asserts the source `.git` is unchanged path for path and
mtime, rather than asserting it was tidied up afterwards.

**`bytes walked` is on the run row, and nothing divides it.** The walk's own
figure, each entry taken by `lstat` so a link weighs its own name. It is the
denominator the share above is read against, and the division stays in prose.

**The link count is printed beside the fold rather than inside it.** After the
fold, fourteen links and fourteen full copies read the same. Before it, they do
not. Both figures are per state, for the reason the fold is: a number that moved
in one state has to say which.

## Acceptance

- [x] agent-rules-books attached, indexed, and never written to
- [x] Whether C2 still carries the fourteen `full.md` symlinks is established
      from the rows and stated, either way, as part of the base-rewrite question
- [x] Two names for one file count once in every state, with the number folded
      reported per state
- [x] Whether C2 rewrote its base is established and stated before any delta is
      read as comparable
- [x] The three-state table is produced, with absolute figures beside every delta
- [x] The governance-to-product byte ratio appears as an observation for all
      three states, with no metric, threshold or alert built
- [x] The pass mark is applied and the result recorded — including a stop
- [x] Ticket 07 rewritten: lineage first as a controlled comparison, hand-built
      family second as an audit, both gates unchanged
- [x] Output contains no forbidden vocabulary word

## Watch for

**C2 is somebody's failed work, and the vocabulary constraint is at its most
load-bearing here.** A repository whose governance grew until work stopped is a
condition, reported as counts and bytes. It is not broken, obsolete or wrong, and
the tool does not say which parts to remove — that is the recomposition decision,
which spec 0002 §11 keeps out of scope until after the audit.

**The pass mark cuts both ways.** A difference that only appears after the fourth
attempt at a new detector is not a difference Orbit found — it is one that was
built to be found. Record what the comparison showed on the detector set that
existed when the run started.
