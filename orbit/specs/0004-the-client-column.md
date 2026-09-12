# Spec 0004 — The `client` column

**Status:** feature specification, written to the project's `to-spec` shape.
**Rests on:** spec 0001 §6 (Candidate A and its gate), ticket 07 Parts 3 and 4,
and spec 0003 §3.1, which records Gate A as **undecided** until a benefit test
shows the column earns its place. **This spec is that test's vehicle.** Building
the column is how the question gets answered; it is not the answer.

## Problem Statement

A session opens in a repository and immediately costs something. Rule files,
skill frontmatter and instruction surfaces arrive before anyone types a word,
and which ones arrive depends on which assistant opened the session — Claude
reads one filename, Codex another, and the same bytes can be paid for twice
under two names.

Dylan cannot see that bill. The graph can say a surface exists, what kind it is,
what it weighs, and whether two files hold identical bytes. It cannot say
**who pays for it**. Three questions written before any data was examined — what
reaches a session, what is paid for twice, what can a session stop paying for —
were all marked not answerable, and the same missing fact sat under all three.

The practical cost is that no estimate of context burden can be made at all.
Two files of 17,294 bytes each, byte-identical, is a fact the tool already
reports. Whether that is 17,294 bytes of burden or 34,588 depends entirely on a
fact nothing records.

## Solution

One column, `client`, on every surface row: which assistant's own naming
convention claims that surface.

Where a vendor's filename or directory names it, the column says so, and says it
from the estate's own statement rather than from a reading. Where nothing names
one, the column carries an explicit UNKNOWN **with the reason it is unknown**,
and never a guess. Two-thirds of this estate's surface bytes will carry that
UNKNOWN, and that is the honest answer rather than a gap.

With it, the cold-start burden becomes a query instead of an argument.

## User Stories

1. As an estimator, I want to know which rule files a fresh session loads before I type anything, so that I can tell whether slow starts are my machine or my estate.
2. As an estimator, I want that figure split per assistant, so that a Claude session and a Codex session are not averaged into a number describing neither.
3. As an estimator, I want to know when the same content is paid for twice under two names, so that I can decide whether to fold the duplicate.
4. As an estimator, I want surfaces that nothing claims to be visible as UNKNOWN rather than absent, so that I do not mistake an unmeasured cost for a zero cost.
5. As an estimator, I want each UNKNOWN to carry its reason, so that I can tell "no vendor names this" from "this was not read".
6. As an estimator, I want the published rule corpus distinguished from what a session actually loads, so that a large repository does not read as a large context bill.
7. As an estimator, I want to compare my repositories on the same measure, so that I can see which of them is expensive to open.
8. As an estimator, I want the measurement taken before any change to my rule files, so that I can prove afterwards whether a change helped.
9. As a session opening in a repository, I want to ask what I am about to load, so that I can report the cost rather than absorb it silently.
10. As a session, I want to distinguish frontmatter that loads at open from a body that loads on invocation, so that a skill's advertised cost is not its full file size.
11. As a session, I want a surface that names no client to be reported as such, so that I do not attribute it to the assistant I happen to be.
12. As a maintainer of the tool, I want the column derived from a convention already recorded on the row, so that a second source of truth is not introduced.
13. As a maintainer, I want the derivation to be a single documented rule, so that a disagreement about a value is settled by reading it rather than by guessing.
14. As a maintainer, I want adding this column to leave the detector set version unmoved, so that every figure recorded in tickets 07 and 14 stays comparable with figures taken after it.
15. As a maintainer, I want the column to be queryable in plain SQL, so that no new query language or second store is needed to read it.
16. As a maintainer, I want the same three questions that opened Gate A to be re-runnable afterwards, so that the column's benefit is measured rather than assumed.
17. As a maintainer, I want a question that still fails after the column to be recorded as still failing, so that partial success is not reported as success.
18. As a reviewer of this work, I want to see which rows changed value and which did not, so that I can check the derivation against files I know.
19. As a reviewer, I want a row whose client is inferred rather than declared to be distinguishable from one the estate stated, so that I can exclude inference from any count.
20. As a reviewer, I want the count of UNKNOWN rows reported beside every total, so that a figure never arrives without its denominator.
21. As Dylan deciding whether Gate A closes, I want the column's cost in bytes and maintenance named, so that I can weigh it against what it answered.
22. As Dylan, I want the option of removing the column if it answers nothing, so that building it is reversible rather than a commitment.
23. As a future session, I want the reason a row is UNKNOWN to survive in the record, so that a later reader does not re-derive it from scratch.
24. As a future session, I want to know that thirteen other ledger columns were considered and not built, so that they are not re-proposed from nothing.

## Implementation Decisions

**The column is declared, not coded.** The surface ontology states in its own
header that the indexer builds the table from the declared columns and that
adding one there adds it to the table with no Python change. The column is
therefore an ontology declaration plus a derivation, not a schema migration.

**The detector set version does not move.** The version digests the five modules
that decide what is recognised — surfaces, clauses, pointers, settings,
provenance. The ontology is deliberately outside that set, on the stated ground
that a column added to the YAML does not change what was detected. Verified
before writing this spec. This is what keeps ticket 07's figures comparable, and
it is a constraint on the implementation rather than a happy accident: **if the
work finds itself editing a hashed detector module, it has left this spec.**

**Derivation is from the estate's own naming, and nothing else.** A vendor's
filename or a vendor's directory is a statement the estate made. The same
convention is already recorded on each row as `recognition = 'vendor-name'`, so
the column names which vendor rather than introducing a new judgement.

**Reachability is not a source.** Walking the pointer graph from named roots was
attempted during ticket 07 and added one row in each of two repositories and
none in either lineage repository. Reachability does not carry load attribution
and is not used.

**UNKNOWN is a value with a reason, never an empty string and never a guess.**
The precedent is on the same table: `recognition` records `corpus-adjacent`
separately precisely so a query can exclude what was inferred. `client` follows
it. A row for which no vendor convention applies is UNKNOWN because none
applies, and that sentence is the value's reason.

**Expected distribution, measured in advance:** 81 of 318 surface rows across
the estate carry a filename that names a client, 841,220 surface bytes. 237 rows
and 1,707,616 bytes do not. Two-thirds of the estate's surface bytes will be
UNKNOWN. A derivation that produces materially fewer UNKNOWNs than this has
started inferring, and is wrong.

**Whether it is a stored column, a derived view, or a table beside the
recognition name is open**, and ticket 07 explicitly left it open as a design
question for this work rather than as a second gate. Any of the three satisfies
this spec provided the value is queryable in plain SQL and carries its reason.

**Only `client`.** The other thirteen columns of Candidate A are not built, and
not because they failed — because no question asked for one.

## Testing Decisions

**A good test here asserts what a caller can observe**: a row in the graph after
an index run. It does not assert how the value was derived, which function
produced it, or the shape of any intermediate. The derivation is free to change
so long as the rows do not.

**One seam, and it already exists.** Build a fixture estate, index it, query the
graph. Every existing test of recognition, pointers and provenance uses it, and
no new seam is proposed. Asserting on the fixture rather than on this repository
also keeps the tests off live content, which spec 0002 §6 requires.

What is tested:

- a surface a vendor filename names carries that vendor, from a fixture that
  contains one of each convention;
- a surface nothing names carries UNKNOWN, and the UNKNOWN carries its reason;
- two byte-identical files under two vendors' filenames carry different values,
  which is the case the whole column exists for;
- a count grouped by the column reports its UNKNOWN bucket rather than omitting
  it;
- the detector set version is unchanged across the work, asserted rather than
  described.

**Prior art** is the existing fixture-estate tests: they build an estate holding
one of every case, index it once in `setUpClass`, and query the resulting graph
with the same SQL a reader would write.

**Not tested by assertion:** the estate-wide 81/237 split. That is live content,
and spec 0002 §6 keeps live figures in evidence records rather than in tests.

## Out of Scope

- **`activation`**, and the other twelve Candidate A columns. Ticket 07 found
  that Q3 needs `activation` as well and that `client` is necessary but not
  sufficient for it. That finding stands and is not addressed here.
- **Answering Q3.** It is expected to remain unanswerable after this work, and
  recording that it does is part of the benefit test rather than a failure of it.
- **`evidence_class`** and Gate B, which are a separate undecided gate.
- **Any hot-context layer** — retrieval, hydration, session-start hooks,
  authority projection, transcript mining. This column measures a cost; it does
  not deliver context, and a hook that delivered context would change the cost
  before it could be measured.
- **Runtime payloads.** What a hook or an MCP server puts into a session is not
  statically observable and stays a named UNKNOWN, never a zero.
- **Any change to a detector**, the recognition rules, or the pointer set.
- **Deciding Gate A.** This spec builds the instrument. Dylan decides.

## Further Notes

**The benefit test is already written, and was written before the data.** It is
Gate A's three questions, committed on their own in `dc8d743` before any query
was run. After the column lands, they are re-run unchanged and each is marked
answerable or not, with the SQL attempted either way — exactly as ticket 07
marked them. No new rule is pre-registered, because pre-registering one now
would be writing a rule after seeing the data it will run on, which is the
failure both gates exist to avoid.

**The honest expectation is one of three.** Q1 should answer for the 81 rows.
Q2's answerable half already answers and its other half will not. Q3 will not.
If all three suddenly answer, something has started inferring and the result
should be disbelieved before it is celebrated.

**A column that answers nothing comes out.** That is what makes this a test
rather than a commitment, and it is cheap to reverse precisely because the
detector set does not move.
