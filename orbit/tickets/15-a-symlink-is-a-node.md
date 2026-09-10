# 15 — A symlink is a node, never read

**Blocked by:** — (nothing; it is the prefactoring 13 and 14 stand on)
**Blocks:** 13
**Demo when done:** `files_walked` 268, the fourteen `full.md` symlinks listed
with GitLab's own reason, the 46 `REFERENCES` edges that point at them landing on
rows that exist, and `surfaces` still 87.

## Why this is a ticket and not a note

This is not a gap in what Orbit can see. It is a **divergence from GitLab Orbit**,
and phase 1's first rule is that we take their architecture, their storage, their
ontology format and their command names, changing only the domain. We wrote our
own answer to symlinks without checking whether they had one. They have one.

Found while closing ticket 12: `_rule-workbench/<book>/full.md` is a symlink to
`../../<book>/<book>.md`, fourteen of them, authored by Maciej Ciemborowicz on
2026-04-26 (`10f71b9`, git mode `120000`) — four months before this project
started. `_rule-workbench/PROCESS.md` states the intent outright: *"Each workbench
directory exposes it as `full.md` via symlink. Do not edit `full.md` in the
workbench."* One canonical source, exposed under a working name, never copied.

`orbit/orbit_context/surfaces.py:414` refuses them:

```python
if entry.is_symlink():
    continue
```

## What GitLab does instead

Read out of `/home/user/gitlabhq/orbit-knowledge-graph`, not inferred.

**A symlink is a node. It is listed, never read, and sized by the link itself.**

`crates/utils/src/walk.rs:37-41` — the walk *accepts* symlinks. Only entries that
are neither a file nor a symlink are skipped:

```rust
let is_file = file_type.is_some_and(|t| t.is_file());
let is_symlink = file_type.is_some_and(|t| t.is_symlink());
if !is_file && !is_symlink { continue; }
```

`walk.rs:53-57` — it is routed away from the reader rather than out of the walk,
with their own comment saying why:

```rust
// A symlink has no content to sniff and is never a parse candidate; the
// hooks settle it, same as the tar source.
meta.decision = if is_symlink { hooks.on_non_regular(&meta) } else { step(...) };
```

`crates/utils/src/fs_stream.rs:114-119` — `on_non_regular` defaults to
`Decision::ListOnly`, which `fs_stream.rs:22` defines as *"Record the file as a
node without loading its bytes."* The routing is deliberate: *"Routed here
(instead of decided in the source) so the filter stays the single decision
point."*

`walk.rs:47` — the size is `symlink_metadata()`, the link's own. `full.md` is 32
bytes, not the 17,866 of the file it names. They do not follow.

`crates/code-graph/src/v2/config/filter.rs:51,148` — the reason is a value,
`FilterSkip::NonRegularFile`, surfaced as the metric label documented at
`crates/orbit-observability/src/indexer/code.rs:152`:

> `non_regular_file` (a symlink — a node, never parsed)

It sits in the same list as `oversize`, `binary`, `not_utf8` — which is our
`REASON_OVERSIZE` / `REASON_READ_ERROR` family. The shelf already exists.

**And they do not refuse links to stay inside the repository — they contain
them.** `crates/utils/src/fs.rs:23-34` canonicalises the target and keeps it only
if it lands under the root, dropping dangling links and `../..` climbs by that
check rather than by a blanket refusal. Our skip was defending against a problem
they solved a better way.

## Do

Adopt their rule, in their vocabulary.

1. **Walk symlinks.** `orbit/orbit_context/surfaces.py:414` stops skipping them.
2. **List, never read.** No bytes are loaded: not for a heading, not for a
   clause, not for a hash. It follows that a symlink is never a byte-identical
   pair and never a rung of a ladder.
3. **Size is the link's own**, from `lstat`, never the target's.
4. **The reason is `non-regular-file`**, their word in our kebab-case, recorded
   the way every other unread candidate's reason is recorded.
5. **Keep it out of the corpus denominator.** See the trap below — this is the
   part that is ours to decide, because the corpus rule is ours.

## The trap, measured before it is hit

`_rule-workbench` is a corpus by the share rule: **42 of 45** Markdown files
declare themselves, 93.3%, against a 75% threshold. That is what recognises
`_rule-workbench/PROCESS.md`, `_rule-workbench/RELEASE.md` and `_rule-workbench/CHECK_COMPATIBILITY.md` — the three
`corpus-adjacent` surfaces in the whole repository.

Listing fourteen unread `.md` files into that directory takes it to **42 of 59 —
71.2%**, under the threshold. The corpus dissolves and those three files stop
being recognised, with `surfaces` going 87 → 84 and nothing in the output saying
that a symlink rule caused it.

**The rule that prevents it:** the corpus share is a share of files that were
**read**. A node the walk listed without loading cannot declare itself, so it
must not count against the files that did. A file that was never opened is not
evidence about the directory either way.

That is an addition to `orbit/orbit_context/surfaces.py`'s corpus rule, and it is a detector input,
so it moves the detector set version on its own — which is the mechanism working.

## What the numbers do

Measured on Advisor-Desk at `5caa25d`, detector set `1.8516f0a599c4`:

| | before | after, expected |
|---|---|---|
| files walked | 254 | **268** (+14, the symlinks) |
| surfaces | 87 | **87** — unchanged, and the trap above is why that needs asserting |
| corpus-adjacent | 3 | **3** |
| identical-bytes pairs | 28 | **28** — never loaded, never hashed |
| ladders / rungs | 14 / 42 | 14 / 42 |
| `REFERENCES` edges landing on a path with no row | 46 | **0** |

The last row is the defect this closes as a side effect. Today
`_rule-workbench/<book>/traceability.md` writes a pointer to `full.md`, the
pointer resolver resolves it (`pointers.resolve` returns the path), and the walk
never made a row for it — 46 edges pointing at files our own walk decided are not
there. `orbit/orbit_context/surfaces.py:399` states the rule those two are breaking: *"Two walks
would be two answers to 'what is in this repository'."* This is one walk and one
resolver disagreeing, which is the same fault.

## Why it blocks 13

Spec 0002's own rule: **two counts either side of a detector change are not
comparable.** This change moves `files_walked` and the detector set version. Run
after the comparison, every figure 13 and 14 recorded is from a superseded
detector set and the comparison has to be re-run to mean anything.

Worse for 14: C2 (`agent-rules-books`) is a clone of the same upstream and
carries the same fourteen symlinks. A three-state comparison run on the current
walk measures our divergence from Orbit in all three states, and calls the result
a finding about governance.

Ticket 09 is the precedent. It went first for the same reason, in the same words:
every count taken against a contaminated store is arguable until it is not.

## Acceptance

- [x] `orbit/orbit_context/surfaces.py` walks symlinks, and the skip at line 414 is gone
- [x] A symlink's bytes are never read — no heading, no clause, no hash — and a
      test asserts it is in no byte-identical pair and no ladder
- [x] A symlink's recorded size is the link's own, not its target's
- [x] The reason is `non-regular-file`, and the ticket's quotation of
      `indexer/code.rs:152` is what it was taken from
      — **taken in their spelling, `non_regular_file`; see the decisions below**
- [x] The corpus share counts only files that were read, and a test builds a
      directory where the unread files would sink it below the threshold
- [x] `surfaces` is still 87 on this repository, reconciled by name against
      ticket `08`'s hand count, not re-baselined
- [x] No `REFERENCES` edge points at a path the walk recorded no row for
- [x] The acceptance run states both detector set versions
- [x] Output contains no forbidden vocabulary word

## The acceptance run

Advisor-Desk, branch head. **Detector set `1.8516f0a599c4` before,
`1.8eabab386316` after** — the version moved on its own, off the new reason
constant and the corpus rule's new input, which is the mechanism working.

The walk is the figure this ticket moves, so it is reported as a set difference
over one tree rather than as two totals taken at two moments:

```
old walk 306 -> new walk 320
added   14: _rule-workbench/<book>/full.md, one per book
removed  0
```

The fourteen, in full, each listed and never read, each 30–104 bytes of link
rather than the 17,866 of the book it names:

```
_rule-workbench/a-philosophy-of-software-design/full.md
_rule-workbench/clean-architecture/full.md
_rule-workbench/clean-code/full.md
_rule-workbench/code-complete/full.md
_rule-workbench/designing-data-intensive-applications/full.md
_rule-workbench/domain-driven-design-distilled/full.md
_rule-workbench/domain-driven-design/full.md
_rule-workbench/implementing-domain-driven-design/full.md
_rule-workbench/patterns-of-enterprise-application-architecture/full.md
_rule-workbench/refactoring-guru/full.md
_rule-workbench/refactoring/full.md
_rule-workbench/release-it/full.md
_rule-workbench/the-pragmatic-programmer/full.md
_rule-workbench/working-effectively-with-legacy-code/full.md
```

Each is a row in `gl_context_surface` and a row in `gl_context_coverage`,
carrying `non_regular_file`, an empty `content_sha256` and the link's own size —
recorded the way every other unread candidate's reason is recorded. `repo-map`
reads them back:

```
  files walked   320
  read in part   14
                   14  non_regular_file
```

and the reasons are counted where a walked file that was not hashed is counted:

```json
"files_hashed": 306,
"files_not_read": 14,
"files_not_read_by_reason": {"non_regular_file": 14, "oversize": 0,
                             "read_error": 0}
```

Everything the ticket said must not move, did not:

| | before | after | expected |
|---|---|---|---|
| surfaces read in full | 103 | **103** | unchanged |
| recognition | 16 / 84 / 3 | **16 / 84 / 3** | unchanged |
| corpus-adjacent | 3 | **3** | 3 — the trap, not sprung |
| identical-bytes pairs | 28 | **28** | 28 — never loaded, never hashed |
| ladders / rungs | 14 / 42 | **14 / 42** | 14 / 42 |
| `REFERENCES` edges landing on a path with no row | 46 | **0** | 0 |
| errored files | 0 | **0** | 0 |

Two figures did move, and both are the fourteen: `files carrying a surface kind`
103 → 117, and `skipped_files` 0 → 14. Neither is a surface that was read.

**Reconciled against `08`'s hand count by name, not re-derived.** 103 rather than
the ticket's 87 because the branch head carries `orbit/` and `.claude/` on top of
the 201 files `08` counts. The reconciliation is by path set, not by total: the
paths carrying a row that indexed are the same set before and after, added to 0
and removed 0, so the 87 that came from those 201 are the same 87 file for file.
The fourteen links are the same fourteen `08` lists. The `files_hashed` figure is
306 rather than the 304 of the run before this one because this ticket added two
files of its own — `orbit/fixtures/build_symlinks.py` and
`orbit/tests/test_symlinks.py`. Neither is Markdown, so neither is a surface, a
pair or a rung, and every row of the table above except the walk itself is
comparable as it stands.

**The 46 edges are still 46 edges.** They now land on `Surface` rows, which is
the fix: one walk and one resolver giving one answer to "what is in this
repository". Nothing was dropped to reach zero.

**The suite is not green, and the red test is not this ticket's.**
`orbit/tests/test_pointers.py`'s `test_unmatched_addresses_stay_in_the_tens` reads 119
against a ceiling of 100. It read 119 at `f70fbcb` too, before any of this: the
two commits that installed the `/implement` and `/tdd` skills brought 25
unmatched addresses with them, this ticket's own prose 3, and without
`.claude/skills/**` the figure is 94. It measures a property of the repository
to make a statement about a detector, which is the shape `08`'s own rule warns
about — recorded here rather than re-baselined, because the ceiling is a bar this
project set deliberately.

## Decisions taken against the ticket's own words

**The reason is spelled `non_regular_file`, not `non-regular-file`.** The ticket
asked for their word in our kebab-case. Taken in their spelling instead, on the
ticket's own closing rule: this is a faithfulness fix, and where their answer and
a nicer answer differ, theirs wins. It also keeps one separator across the
`reason` column, beside `invalid_utf8`, `oversize`, `read_error` and
`not_a_file`.

**A link inside a corpus is recognised with the rest of that directory.** Do-item
5 says to keep it out of the *denominator*, and that is all it says. The share
that decides whether a directory is a corpus counts only files that were read;
the corpus it then recognises reaches a link like any other Markdown file in it,
which is what makes the fourteen rows rather than an aggregate count. Built the
other way first — a link recognised by nothing — and the demo line and the
`REFERENCES` acceptance box were both only satisfiable by redefining "row".

**`repo-map`'s recognition split now counts rows that were read.** It is what the
line above changed and the one edit this ticket makes outside its own area. The
split exists to separate what the estate stated about a file from what this tool
read off the directory around it, and a file nobody opened is evidence of
neither. Left alone it would have reported `corpus-adjacent 17` on this
repository — fourteen inferences about files whose bytes nothing has seen,
against three real ones. It now sums to `surfaces read in full` rather than to
`files carrying a surface kind`, and the block says which.

**Containment is not implemented, and the disagreement is recorded rather than
resolved.** `crates/utils/src/fs.rs:23-34` canonicalises a link's target and
keeps it only if it lands under the root. We never resolve a target at all — the
row is the link's own name and the link's own size — so there is nothing here for
containment to guard. It becomes real the day something follows a link, and that
day is not this ticket.

**Two names for one file still count as two nodes.** GitLab's dedupe
(`crates/orbit-local/src/commands/setup.rs:265-271`) is written into 13 and 14,
where two states can disagree about it, and is deliberately not here.

**A link wearing a pruned name is refused by the name.** Every link was refused
before this ticket, `node_modules` among them; listing one now would carry
another estate's surfaces in through a name this walk has always refused. The
name is checked before anything asks what the entry is, because telling a link to
a directory from a link to a file means following it.

## Watch for

**Do not follow the link.** Every part of this is about listing the link, not
reading through it. Following it hashes one file twice under two names, which
would invent byte-identical pairs the estate does not have — and ticket 12 has
just finished establishing what those 28 pairs are.

**`08`'s hand count changes and must be edited, not re-derived.** It currently
reads *"`_rule-workbench/<book>/full.md` symlinks, never walked | 14"*. They are
now walked and never read, which is a different sentence about the same fourteen
files. The 201-file total does not move.

**The dedupe rule is not this ticket.** GitLab also canonicalises paths and keeps
one entry per real file, labelled by the target
(`crates/orbit-local/src/commands/setup.rs:265-271`, tested at `:292`, where a
`CLAUDE.md` symlinked to `AGENTS.md` yields one entry named `AGENTS.md`). That is
a statement about two names being **one file**, which is stronger than the
byte-identity ticket 12 works on and answers a question ticket 12 deliberately
left UNKNOWN. It belongs with the comparison, where two states can disagree about
it, and it is written into 13 and 14. Doing it here would put two tickets in one
diff.

**This is a faithfulness fix, and it will be tempting to improve on it.** The
value is in matching GitLab, not in a better symlink policy. Where their answer
and a nicer answer differ, take theirs and record the disagreement.
