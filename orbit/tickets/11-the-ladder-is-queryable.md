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

## Acceptance

- [ ] The edge type is declared in ontology YAML before any row is written
- [ ] All 14 ladders in Advisor-Desk are found, and the count of rungs per book
      reconciles against the 43 published rule files
- [ ] Rungs come back in size order with byte counts
- [ ] Which rung was loaded is reported as UNKNOWN with the reason named
- [ ] A book with fewer than three rungs is reported as a count, not a finding
- [ ] Output contains no forbidden vocabulary word

## Watch for

The naming convention (`<book>.mini.md`, `<book>.nano.md`) is this repository's,
not a standard. A rule that keys on those two literal suffixes works here and
teaches nothing about the estate — and ticket 14 needs it to work on C2, whose
conventions have not been looked at. State what the rule keys on, and say
plainly that a repository not using that convention has no ladders **found**
rather than no ladders.
