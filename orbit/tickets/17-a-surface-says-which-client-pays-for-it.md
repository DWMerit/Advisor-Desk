# 17 — A surface says which client pays for it

**Blocked by:** —
**Spec:** `orbit/specs/0004-the-client-column.md`
**Demo when done:** a query groups every surface in a fixture estate by the
assistant whose own naming claims it, with an UNKNOWN bucket that carries its
reason, and Gate A's three questions re-run with their answers marked.

## Do

**Declare the column in the surface ontology.** The file's own header states
that the indexer builds the table from the declared columns and that adding one
there needs no Python. Take it at its word; if the work starts editing a
detector module, it has left the spec.

**Derive the value from the estate's own naming and nothing else.** A vendor's
filename or directory is a statement the estate made, already recorded on the
row as `recognition = 'vendor-name'`. Name which vendor. Do not walk the pointer
graph for it — that was attempted in ticket 07 and carries no load attribution.

**UNKNOWN carries its reason.** Never an empty string, never a guess. The
precedent is on the same table: `corpus-adjacent` is recorded apart from the
declared recognitions exactly so a query can exclude what was inferred.

**Then re-run Gate A's three questions, unchanged**, and mark each answerable or
not with the SQL attempted either way. They were committed in `dc8d743` before
any data was seen, which is what makes them usable as an after-check. Write no
new rule now: a rule pre-registered after seeing the data it will run on is the
move both gates exist to stop.

## Acceptance

- [ ] The column is declared in the ontology, and no detector module is edited
- [ ] The detector set version is `1.8eabab386316` before and after, asserted
      in a test rather than stated in prose
- [ ] A surface a vendor filename names carries that vendor, in a fixture
      holding one of each convention
- [ ] A surface nothing names carries UNKNOWN, and the UNKNOWN carries its reason
- [ ] Two byte-identical files under two vendors' filenames carry different
      values — the case the column exists for
- [ ] A count grouped by the column prints its UNKNOWN bucket rather than
      omitting it
- [ ] Tests assert against a fixture estate, not this repository's live content
- [ ] Gate A's three questions are re-run and each marked, with the SQL shown
- [ ] The estate-wide split is recorded as evidence, not asserted in a test
- [ ] Output contains no forbidden vocabulary word

## What this ticket does not decide

**It does not close Gate A.** Spec 0003 §3.1 records the gate as undecided until
a benefit test shows the column earns its place. This ticket builds the
instrument and runs the questions. Reading the result is Dylan's.

**It does not build `activation`**, and Q3 is expected to stay unanswerable.
Recording that it does is part of the result. A run in which all three questions
suddenly answer should be disbelieved before it is believed: it means something
started inferring.

## Watch for

**The UNKNOWN count is the honesty check.** Ticket 07 measured 81 of 318 surface
rows carrying a vendor filename and 237 not — two-thirds of the estate's surface
bytes. A derivation that produces materially fewer UNKNOWNs than that has begun
guessing, and the number to check it against is already recorded.

**This ticket adds prose naming files to a repository with finite pointer
headroom.** The drift guard stood at 103 of 352 addresses, 29.3%, against a
ceiling of 0.33 when this was written. Name files by repository-root path so
they resolve. If the guard breaches, the ceiling is not the thing that moves.
