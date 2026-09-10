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

- [ ] C0 is indexed without checking anything out over the working tree
- [ ] The delta table above is reproduced, including the zero
- [ ] Both states carry the same detector version, and the output states it
- [ ] The comparison runs from the command line and its exit code is meaningful
- [ ] Deltas are counts and bytes; nothing is characterised
- [ ] Two names for one file count once, labelled by the target, and the number
      folded is reported per state rather than absorbed into the total
- [ ] Output contains no forbidden vocabulary word

## Watch for

A comparison is two indexes plus subtraction, and subtraction hides which side
moved. Report both absolute figures beside every delta — a delta alone cannot
distinguish "C1 added 40" from "C0 was miscounted by 40", and the second is the
failure mode that has already happened twice in this project.

Do not let the comparison acquire its own store, its own query language or a
second index path. Spec 0002 §12 lists each of those as a kill condition.
