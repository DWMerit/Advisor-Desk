# 13 — Two states compare

**Blocked by:** 12, **15**
**Demo when done:** one command, C0 against C1, a table of deltas — run from the
command line, the way it will actually be run.

## Do

Index Advisor-Desk at two points in its own history and difference them.

- **C0** — `main` @ `a7d7649`. 50 commits, every one authored by Maciej
  Ciemborowicz. The pristine upstream.
- **C1** — branch head. C0 plus the 19 commits of this project.

Get C0 without disturbing the working tree: `git worktree add --detach`. Spec
0001 §7's `git cat-file` slice is still deferred and this ticket does not need it.

Both seams, as agreed:
- **Seam A** — the fixture path, with a fixture repository built in two states.
- **Seam B** — the command line. Argument shape, output shape, exit code. This is
  the seam that catches "it works but you cannot run it".

## The expected shape, pinned in advance

`C1 − C0` is known by hand, and the comparison has to produce it:

| | C0 | C1 | delta |
|---|---|---|---|
| files | 201 | 253 | +52, all under `orbit/` |
| non-`orbit/` files | 201 | 201 | 0 |
| markdown | 198 | 209 | +11, all under `orbit/` |
| governance surfaces | *n* | *n* | **0** |

The last row is the one that matters. **C1 added no governance.** The session
built a tool and left the rule corpus alone — outside `orbit/`, `main..HEAD` is
two lines of `.gitignore`. If the comparison reports governance added by C1, the
comparison is wrong, not the repository.

## Two names for one file are one file

GitLab's rule, not ours, and it arrives with ticket 15's walk: a symlink is a
node, so a repository holding `CLAUDE.md -> AGENTS.md` now holds two rows for one
file. `crates/orbit-local/src/commands/setup.rs:265-271` canonicalises the paths
and keeps one entry, labelled by the **target**; the test at `:292` writes
`AGENTS.md`, symlinks `CLAUDE.md` to it, and asserts one entry named `AGENTS.md`.

The comparison has to apply that, because the row this ticket turns on is
`governance surfaces: delta 0`. Fourteen symlinked `full.md` files sit in both
states; counted as governance in one and not the other, the zero moves and the
comparison reports a session adding rules it did not write.

Note what the rule is *not*. Same-inode is a stronger statement than the byte
identity ticket 12 measures: byte-identical says "same content, cause unknown",
and same-inode says "same file". So the target being the surviving name is an
**observed** ordering, and it does not reopen ticket 12's UNKNOWN — two files
that merely hash the same are still unordered, and nothing here changes that.

- Deduplicate by canonical path, keeping the target's name.
- Report how many rows were folded, per state. A dedupe that silently changes a
  count is the failure mode this whole batch exists to catch.

## Acceptance

- [x] C0 is indexed without checking anything out over the working tree
- [x] The delta table above is reproduced, including the zero
- [x] Both states carry the same detector version, and the output states it
- [x] The comparison runs from the command line and its exit code is meaningful
- [x] Deltas are counts and bytes; nothing is characterised
- [x] Two names for one file count once, labelled by the target, and the number
      folded is reported per state rather than absorbed into the total
- [x] Output contains no forbidden vocabulary word

## Watch for

A comparison is two indexes plus subtraction, and subtraction hides which side
moved. Report both absolute figures beside every delta — a delta alone cannot
distinguish "C1 added 40" from "C0 was miscounted by 40", and the second is the
failure mode that has already happened twice in this project.

Do not let the comparison acquire its own store, its own query language or a
second index path. Spec 0002 §12 lists each of those as a kill condition.

## What the run found

`orbit-context compare a7d7649 e6a6d74 --repo .`, detector set `1.8eabab386316`,
both states read by it:

| | C0 `a7d7649` | C1 `e6a6d74` | delta |
|---|---|---|---|
| files walked | 201 | 253 | +52, every one under `orbit/` |
| files outside `orbit/` | 201 | 201 | **0** |
| markdown | 198 | 209 | +11 |
| governance surfaces | 87 | 87 | **0** |
| two names for one file, folded | 14 | 14 | 0 |
| clauses | 7,560 | 7,560 | 0 |
| pointers | 224 | 224 | 0 |
| governance surface bytes | 781,674 | 781,674 | 0 |

Every row pinned in advance is reproduced, including both zeroes. **C1 added no
governance**, and the comparison says so.

### The 87 ties back to named files

Spec 0002 §9: a number that cannot be tied back to named files is not a result.
101 surface rows at C0, folded to 87:

| group | rows |
|---|---|
| published rule files — 14 books at 3 rungs, each `declared-marker` | 42 |
| `_rule-workbench/` files read — 42 `declared-marker`, 3 `corpus-adjacent` | 45 |
| `_rule-workbench/<book>/full.md` links, folded into the book each names | 14 |

42 + 45 = **87**, and 87 + 14 = the 101 rows the store holds. Both figures come
off ticket 08's hand count, which already had the 42, the 45 and the 14
separately. `docs/`'s 95 files carry no governance in either state, which is the
answer the corpus rule is supposed to give for a documentation tree.

### C1 has moved on since this ticket was written

`e6a6d74` is the state the table above was pinned against — 253 files, 201 of
them outside `orbit/`. The branch has moved well past it since, and the sessions
that moved it installed skill packages under `.claude/`. Those are governance,
added outside `orbit/`, so the same comparison run against the branch head
reports governance added — and is right to. Two correct answers to two different
questions; the pinned one is the falsifier, because its expected values were
written down before it was run.

Run against the head this ticket was built on, `87b6249`:

| | C0 `a7d7649` | head `87b6249` | delta |
|---|---|---|---|
| files walked | 201 | 320 | +119 |
| governance surfaces | 87 | 103 | +16 |
| two names for one file, folded | 14 | 14 | 0 |
| `.claude/` files | 0 | 48 | +48 |
| `orbit/` files | 0 | 70 | +70 |
| every other directory | 196 | 196 | 0 |

The sixteen are named, not inferred: sixteen `skill-package` rows, one per
`.claude/skills/<name>/SKILL.md`, and nothing else. The corpus is still
untouched — every directory holding a book is at delta 0, and so are `docs/` and
`_rule-workbench/`.

## Decisions taken here

**Both states are read from a commit, not one of them from the working tree.**
The ticket asks for C0 in a detached worktree. C1 is materialised the same way,
because a working tree carries whatever is lying around in it and differencing a
clean checkout against one would report somebody's scratch file as something the
session added. Two readings have to be the same kind of reading before their
difference means anything.

**Two columns were added, and neither is a detector.** `link_target` on
`gl_context_surface` is where a link's own name resolves, read from the link and
never through it; `files_walked_by_suffix` and `files_walked_by_directory` on
`gl_context_run` are the walk's own tally, so the markdown row and the
per-directory row come out of the graph rather than out of a second walk. The
detector set version is unmoved by all three, which was checked rather than
assumed: `detectors.py` hashes the module-level constants and patterns of the
five detector modules, and a column added to the YAML is not one.

**The fold happens at compare time, not at index time.** The graph keeps both
names — ticket 15's rule, a symlink is a node — and the comparison counts one
file. That is what lets the number folded be reported per state instead of
disappearing into the walk, and it keeps the two questions apart: what the
repository holds, and how many files those names are.

**Exit code 4 is a finding.** 0 is a comparison whose readings are comparable, 1
is a state that could not be read, and 4 is two states read by different detector
sets — the table still prints and every figure in it was measured; what is not
established is that subtracting them means anything. 1 prints nothing at all to
stdout: half a table is the one shape this command must not produce.

**The zero was shown not to be structural.** `build_states` commits a third
state that does add governance, and the same comparison reports it. A comparison
that returned "no governance added" whatever was added would satisfy this
ticket's headline row while measuring nothing.

**The "non-`orbit/` files" row is generic, and says what it is.** It prints as
*every directory that did not move*, totalled over every directory at delta 0
whether or not the listing had room for it. On this run exactly one directory
moved, so it is the ticket's row; on a run where two directories move it is the
total of the rest, which is what the heading says and not what the ticket
happened to need.

## What the two-axis review found

**The fold was folding rows it had no business folding.** Keyed on
`(path, surface_kind)`, it took the three rows a settings file legitimately
stands up — a row per hook, a row per MCP server — down to one, and reported a
file folded into itself. That is the dedupe quietly changing a count, which is
the failure this batch exists to catch, and it was invisible on Advisor-Desk
because C0 carries no settings file. Rewritten so only a link folds, and
`build_states` now carries a settings file holding two hooks and an MCP server
in every state so the case is pinned at both ends of every comparison.

**A pair count was reaching stdout on its own.** The `EDGES` inventory printed
`IDENTICAL_BYTES` as a plain row, against the README's rule that the count is
never emitted alone. It is now printed as the block `pairs.PairCounts` divides
it into, read through `pairs.counts_from_graph` — the function that owns the
rule — rather than counted again here.

**Only three totals said which kind moved.** Governance, clauses and pointers
arrived as single figures, against the rule that a counted section prints its
whole inventory including its zeroes. Surfaces by kind, clauses by type and
pointers by detector now print in full for both states.

**`link_target` did not hold to its own contract.** `Path.resolve()` is not
strict, so a link naming a file that is not there returned a path all the same,
and the fold would then label an entry with a name this repository does not
hold. It answers empty for that case now, checked by a stat of the name rather
than a read of a file.

**A production method existed for one test.** `State.with_detector_set_version`
is gone; the test fakes the detector set with `dataclasses.replace`, which is
where faking belongs. The command line's exit code for two states that are not
comparable is now exercised at the command line rather than only in-process.

Left alone, and why: `_short`, `_heading` and the snapshot clause are near-copies
of `repo-map`'s, and extracting a shared printing module would edit a command
this ticket has no business in. The comparison's own vocabulary lint lives in
`test_compare.py` beside its fixture and imports the word list from
`test_vocabulary.py`, so there is still one list.
