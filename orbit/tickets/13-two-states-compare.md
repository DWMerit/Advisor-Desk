# 13 — Two states compare

**Blocked by:** 12
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

## Acceptance

- [ ] C0 is indexed without checking anything out over the working tree
- [ ] The delta table above is reproduced, including the zero
- [ ] Both states carry the same detector version, and the output states it
- [ ] The comparison runs from the command line and its exit code is meaningful
- [ ] Deltas are counts and bytes; nothing is characterised
- [ ] Output contains no forbidden vocabulary word

## Watch for

A comparison is two indexes plus subtraction, and subtraction hides which side
moved. Report both absolute figures beside every delta — a delta alone cannot
distinguish "C1 added 40" from "C0 was miscounted by 40", and the second is the
failure mode that has already happened twice in this project.

Do not let the comparison acquire its own store, its own query language or a
second index path. Spec 0002 §12 lists each of those as a kill condition.
