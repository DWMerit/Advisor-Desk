# 11 — The ladder is queryable

**Blocked by:** 10
**Demo when done:** ask for one book's ladder, get its rungs with their byte
counts, in size order.

## Do

Advisor-Desk implements progressive disclosure by hand, fourteen times:

```
refactoring/refactoring.md       17,866 bytes
refactoring/refactoring.mini.md   5,167
refactoring/refactoring.nano.md   1,986
```

This is the stated purpose of the whole project, already built, and invisible to
the graph. Make the relation between rungs a first-class edge.

Declare the edge type in ontology YAML before the indexer writes it. The rungs
are surfaces already, after ticket 10 — this ticket adds only the relation and
the query that walks it.

**What stays UNKNOWN.** Which rung a session actually loaded needs the load
ledger, which is Candidate A and still gated. Report it as UNKNOWN, named, never
as zero — spec 0001 §9's rule that an unobservable quantity must not improve the
number by being unobservable.

Whether a book has all three rungs is an observation, not a defect. A book with
two is reported as having two.

## What was built

**The edge.** `RUNG_OF`, declared in `orbit/ontology/edges/context/rung_of.yaml`
before a row was written, routed to the same `gl_context_edge` table as the
other four. It leaves the rung and enters the **base rung** -- the surface in
the same directory named by the stem alone -- so the base rung's path is the
ladder's address, every rung of one ladder carries it in `target_path`, and a
ladder is one walk of these edges. The rung word the filename carried is on the
row as `subtype`. **No new column:** every column it declares was already
declared by a sibling edge type, so the store needed no migration.

**What the row says, and what it does not.** It relates two filenames in one
directory. It does not say the nano rung was derived from the full one: spec
0001 s14 keeps "whether two identical files are intentionally identical" a
permanent UNKNOWN, and a derivation nothing observed would be the same
over-read. Where the estate evidences one, the `PRODUCES` edges beside these
rows carry it.

**What the rule keys on**, `RUNG_WORDS` and `RUNG_SUFFIX` in `orbit/orbit_context/surfaces.py`, both
inside the derived detector version:

    <stem>.md beside <stem>.mini.md or <stem>.nano.md, in one directory

The stem is required to be non-empty, and that single requirement is what
decides the count. `_rule-workbench/<book>/` holds `mini.md` and `nano.md` with
no stem in front of them -- the directory is the book and the filename is the
rung alone -- so the workbench's fourteen ladder-shaped groups are **not**
found by this rule. Reaching them means reading a directory rather than a name,
which is the corpus rule's kind of inference rather than this one's, and it
would put two naming shapes in one count under one word without saying which
was read how. Named here rather than left to be discovered on C2.

Every command that prints a ladder count prints the rule beside it, at zero as
well as above it, because what can be said about a repository naming its rungs
otherwise is that none were **found**.

**The query.** `orbit-context ladder [book]` walks the edges back out of the
graph -- re-walking nothing, on `repo-map`'s argument -- and prints each rung
with its byte count, largest first. `repo-map` carries the same block, capped
and shortened like every other listing it prints, and both read it through one
function so the map and the command cannot disagree about a count.

**A rung word with no base rung** writes no edge: an edge needs both ends, and
inventing the missing one would put a file in the graph the repository does not
hold. It is counted as `rungs_with_no_base_rung` and named in the output.
Advisor-Desk has none; the fixture has one, so the path is exercised.

## The acceptance run -- evidence, hand-checked

Advisor-Desk at `7142ad7`, detector set `1.e2ab2c0e73a6`. Never asserted in a
test: this content changes, including from this work.

| | ticket 10 baseline | this run |
|---|---:|---:|
| detector set | `1.2ee25fd613c9` | `1.e2ab2c0e73a6` |
| files walked | 249 | 252 |
| files with a surface kind | 87 | 87 |
| surfaces · clauses · pointers | 87 · 7,560 · 224 | 87 · 7,560 · 224 |
| edges | 7,812 | **7,840** |
| identical-byte pairs · with provenance | 28 · 0 | 28 · 0 |
| **ladders · rungs** | — | **14 · 42** |

The three extra files walked are this ticket's own: `ontology/edges/context/
rung_of.yaml`, `orbit/orbit_context/ladders.py` and `orbit/tests/test_ladders.py`. The edge
total reconciles without a remainder:

    7,560 CONTAINS + 224 REFERENCES + 28 IDENTICAL_BYTES + 28 RUNG_OF
        + 0 PRODUCES = 7,840

Recognition, byte identity and provenance did not move -- 87 surfaces at the
same split, 28 pairs with 0 carrying provenance -- which is what ticket 09's
watch-for asks be checked either side of a change that touches counts. Both
detector sets are in the store at once, each snapshot marked
`detector_set_is_current`, so the two columns read as two detector sets rather
than as an estate that changed.

### Reconciled by name

**14 ladders, every one at 3 rungs, 42 rungs in total** -- which is the 42
published rule files exactly, the figure ticket 10 corrected `08` to. The
ladders named are the fourteen book directories and nothing else:

```
a-philosophy-of-software-design   clean-architecture   clean-code
code-complete   designing-data-intensive-applications   domain-driven-design
domain-driven-design-distilled   implementing-domain-driven-design
patterns-of-enterprise-application-architecture   refactoring
refactoring-guru   release-it   the-pragmatic-programmer
working-effectively-with-legacy-code
```

The demo, against the bytes spec 0002 s2 recorded by hand before any of this
was built:

```
$ orbit-context ladder refactoring

LADDERS  14 found, 42 rungs  [1.e2ab2c0e73a6]
  keyed on  <stem>.md beside <stem>.mini.md or <stem>.nano.md, in one directory
  ...
  rungs per ladder
    3 rungs  14
  which rung this session loaded  UNKNOWN: which rung a session loaded needs
    the load ledger, and spec 0001 section 6 keeps it gated (Candidate A)
  rung words with no base rung beside them  0

refactoring/refactoring.md  3 rungs, 25019 bytes
     17866  refactoring/refactoring.md       base
      5167  refactoring/refactoring.mini.md  mini
      1986  refactoring/refactoring.nano.md  nano
```

**The check ticket 04's precedent asks for.** The number is not the evidence.
Of the 14 ladders named, every one is a book a human would have named, at the
height a human would have counted, with byte counts that match the three
recorded by hand a day before the edge existed. 165 of the 252 files walked
carry no surface kind and 45 of the 87 surfaces are in no ladder at all, so the
rule did not widen to everything it could see.

## Found while doing this, and not fixed here

**Fourteen ladder-shaped groups are not keyed on — and the graph reaches them
anyway.** The workbench's `mini.md` / `nano.md` shape is the second naming
convention in one estate, and its full rung is a symlink the walk never enters.
Widening the rule to reach it means reading a directory rather than a name,
which is the corpus rule's kind of inference rather than this one's, so it was
left out.

**What that costs was measured, not assumed, and it is nothing here.** All 28
workbench rungs are byte-identical to their published twins, so each already
reaches its book's ladder in two hops, arriving with the right rung word:

```sql
SELECT i.source_path AS workbench_file, r.target_path AS ladder, r.subtype AS rung
FROM gl_context_edge i
JOIN gl_context_edge r
  ON r.relationship_kind = 'RUNG_OF' AND r.source_path = i.target_path
 AND r.project_id = i.project_id AND r.branch = i.branch
 AND r.commit_sha = i.commit_sha
WHERE i.relationship_kind = 'IDENTICAL_BYTES'
```

    28 of 28, at 7142ad7. _rule-workbench/refactoring/mini.md
      -> refactoring/refactoring.mini.md -> refactoring/refactoring.md  (mini)

The relation is in the graph. Only the label is not, and a label is not a
finding.

**The case that would change the answer is C2's.** The two-hop path holds
because the copies are identical, which is a property of this repository rather
than of the shape. A repository using the workbench shape *without* identical
twins would not have it, and its ladder count would come back low with nothing
saying why. That is worth looking at when agent-rules-books is attached at
ticket 14, and not before: spec 0002 s11 refuses a rule built for a repository
nobody has looked at. Recorded here so it is re-opened on the measurement rather
than on the shape.

**The detector-version gap ticket 10 recorded still applies here, and this
ticket widened it.** `rung_of()` is logic reading a table: the table moves the
version and the function does not. Nothing published spans it -- both the rule
and its acceptance run shipped inside this one change -- but the gap is now
carried by two rules rather than one. It stays where ticket 10 left it, beside
the decisions ticket 07 takes.

**`rungs_with_no_base_rung` is re-derived at read time**, because a rung with no
edge has nothing in the graph to walk. On a snapshot written by another detector
set that figure is this build's answer over that run's rows; both versions are
in the header for exactly that case, and `index` records its own count when it
writes.

**Three defects came out of `code-review` and are fixed and pinned by tests:**
the documented SQL joined on path alone and left the base rung out, so it
returned each rung of 14 books twice and none of their base rungs; `repo-map`'s
ladder block printed its listing even after the map had said it dropped its
listings, and printed paths at unbounded width; and `ladders_by_rung_count` was
ordered as text, so a ladder of ten rungs would have sorted before one of two.
Two further findings -- one edge-type name spelled in three modules, one query
run twice -- were fixed by giving each a single owner.

## Acceptance

- [x] The edge type is declared in ontology YAML before any row is written
      — `orbit/ontology/edges/context/rung_of.yaml`, written and loading before
      `orbit/orbit_context/indexer.py` knew the name. It declares no column a sibling edge type had
      not already declared, so `gl_context_edge` is unchanged and no migration
      was needed. `tests/test_ladders.py::test_the_edge_type_is_one_the_ontology
      _declares` reads the variant back out of the YAML, and `_edge_row` refuses
      any pair the type does not declare.
- [x] All 14 ladders in Advisor-Desk are found, and the count of rungs per book
      reconciles against the 43 published rule files
      — 14 found, 3 rungs each, 42 rungs. **42, not 43**: ticket 10 corrected
      `08`'s hand count to 14 books at three rungs, and this run reconciles
      against the corrected figure exactly. The fourteen are named above.
- [x] Rungs come back in size order with byte counts
      — largest first, ties broken by path so the answer is stable. Size order
      rather than rung order, because how big a rung is was measured and the
      order of the words was not stated anywhere. Pinned at Seam A and at Seam
      B, and the byte counts are checked against the files' own sizes.
- [x] Which rung was loaded is reported as UNKNOWN with the reason named
      — one line, on every ladder printed, naming the load ledger and the gate
      that holds it. A test asserts the line is present and that the figure is
      not a zero.
- [x] A book with fewer than three rungs is reported as a count, not a finding
      — `rungs per ladder` is a distribution, so a book at two prints beside the
      books at three under its own height. `build_lineage` carries a two-rung
      book for it; Advisor-Desk has none, which is itself the observation.
- [x] Output contains no forbidden vocabulary word
      — `ladder` and `repo-map` output are both linted whole, on a repository
      with ladders and on one without, and `test_vocabulary` lints the edge type
      and every column name it declares.
- [x] 326 existing tests still pass, no assertion re-baselined without naming
      what moved it
      — 359 pass in total. Four count assertions in `orbit/tests/test_recognition.py` moved,
      and all four moved by the same three files this ticket added to
      `build_lineage`: `clean-code/clean-code.md`,
      `clean-code/clean-code.nano.md` and `drafts/takeoff.mini.md`. Each is
      named in the test beside the number. `build_estate` is untouched.

## Watch for

The naming convention (`<book>.mini.md`, `<book>.nano.md`) is this repository's,
not a standard. A rule that keys on those two literal suffixes works here and
teaches nothing about the estate — and ticket 14 needs it to work on C2, whose
conventions have not been looked at. State what the rule keys on, and say
plainly that a repository not using that convention has no ladders **found**
rather than no ladders.
