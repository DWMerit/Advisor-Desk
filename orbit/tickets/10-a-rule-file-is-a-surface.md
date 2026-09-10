# 10 — A rule file is a surface

**Blocked by:** 09
**Demo when done:** index Advisor-Desk, and every recognised file is named and
reconciles against the hand count in `08`.

## Do

**First deliverable is a decision, not code.** Spec 0002 §5 deliberately left
open what makes a file a governance surface if not its name. Investigate
Advisor-Desk, then come back to Dylan with **two or three candidate rules and the
count each would produce**, and let him pick. This was agreed explicitly: a
recognition rule becomes load-bearing for every count that follows, so it is not
a decision to make from inside the ticket.

Constraints the answer has to satisfy, all already established:

- It recognises the rule corpus — 14 book directories, 43 published rule files,
  45 workbench files.
- It does **not** recognise all 198 markdown files. `LICENSE`, the hero image and
  most of `docs/` are not governance objects.
- No inference is recorded as fact. A rule that guesses produces output marked as
  a guess.
- The derived detector version in `detectors.py` is not bypassed. Adding a table,
  pattern or directory moves it automatically; that mechanism stays.

Then implement the chosen rule, with a **new fixture builder** carrying a
book-ladder repository *and* a `CLAUDE.md`-shaped repository side by side, so both
recognition paths are exercised together. `build_estate` is not extended.

## Acceptance

- [ ] Candidate rules put to Dylan with counts before any is implemented
- [ ] The chosen rule and the reason it was chosen are recorded in this ticket
- [ ] Surfaces on Advisor-Desk reconcile to the named groups in `08`
- [ ] Vendor-named recognition still works — the fixture proves the two paths do
      not interfere
- [ ] The detector version moved, and any output spanning the change says so
- [ ] Output contains no forbidden vocabulary word
- [ ] 269 existing tests still pass, with no count assertion edited

## Watch for

**Both failure directions are silent.**

Come back at or near 198 and the rule has learned nothing `find` did not already
know — spec 0002 §12 lists that as a kill condition, not a tuning problem. Come
back at 0 and nothing changed.

Ticket 04's phantom-finding failure is the precedent: **1,349 of 1,373 findings
were the tool talking about itself**, and the count alone looked like a working
detector. The check is not the number, it is whether the named files are the
files a human would have named.
