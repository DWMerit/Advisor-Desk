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
- The derived detector version in `orbit/orbit_context/detectors.py` is not bypassed. Adding a table,
  pattern or directory moves it automatically; that mechanism stays.

Then implement the chosen rule, with a **new fixture builder** carrying a
book-ladder repository *and* a `CLAUDE.md`-shaped repository side by side, so both
recognition paths are exercised together. `build_estate` is not extended.

## Decision — the file says so, and where it cannot, the corpus does

Put to Dylan with counts before any of it was written, and picked by him.

**What the investigation found.** Every rule file in the corpus opens the same
way — `# OBEY Refactoring by Martin Fowler` — and nothing that is not a rule file
does. That is not a pattern this tool inferred; it is the corpus stating what a
file is for, in the same class of statement as the filename Anthropic defined for
`CLAUDE.md`. Recognition by declaration was available the whole time and phase 1
was looking in the wrong place for it.

Three candidates went up, measured at `main` over the 184 Markdown files the walk
reaches once the 14 `full.md` symlinks are left out:

| rule | surfaces | book dirs | workbench | `docs/` | root |
|---|---:|---:|---:|---:|---:|
| **A** — first heading is a directive marker | 84 | 42 | 42 | 0 | 0 |
| **B** — A, plus a directory that is mostly marker files | **87** | 42 | 45 | 0 | 0 |
| **C** — normative-language density | 18 at best | 12 | 4 | **2** | 0 |

**C was measured, not waved away.** Rule files run 1.07 binding words per KiB at
the median and `docs/` runs 0.58 — two distributions that overlap. Every threshold
either takes `docs/ADDING_THE_BOOK.md` and `docs/USAGE.md` or drops most of the
corpus, and no threshold reconciles against the groups in `08`. Density measures
how a document is written, and both families here are written the same way,
because one is prose about the other.

**B was chosen**, and the reason is the three files A misses:
`_rule-workbench/PROCESS.md`, `_rule-workbench/RELEASE.md`, `_rule-workbench/CHECK_COMPATIBILITY.md`. They carry
no heading of their own and are governance all the same — they are the
instructions for producing the other 42, addressed at an agent. What identifies
them is where they sit, so the corpus rule is what reaches them, and it is the
only thing in the module that reads rather than quotes.

That reading is recorded as a reading. `recognition` is a new column on
`orbit/ontology/nodes/context/surface.yaml` carrying `vendor-name`, `declared-marker` or `corpus-adjacent`;
the first two are the estate's own statement about a file and the third is this
tool's, and every count that spans them prints the split rather than the total.
Ontology YAML before Python, and the column arrives by the mechanism ticket 09
built for exactly this.

**The guards on the corpus rule**, each a constant in `orbit/orbit_context/surfaces.py` and therefore
inside the derived detector version:

- `CORPUS_DECLARED_SHARE = 0.75`. The workbench clears it at 42 of 45.
  Advisor-Desk's `notes`-shaped case is the fixture's: two of three declared is
  under the share, so the two are still surfaces and the third is not.
- `CORPUS_MINIMUM_FILES = 3`. A directory of one or two says nothing about
  itself. This one is not observable at Seam A — a two-file directory that
  cleared the share would be two declared files with nothing left to carry in —
  so it is stated here rather than asserted.
- `CORPUS_MINIMUM_DEPTH = 1`. The repository root is out of reach whatever its
  share. Advisor-Desk's root sits at 84 of 184, well under, but leaving the kill
  condition in spec 0002 §12 to a margin is not a guard. A repository that
  happened to be mostly rule files would otherwise promote every file in it,
  which is that kill condition arriving as a result.
- The share is counted over a directory's whole subtree, not its immediate
  contents. The workbench holds its declared files one level down and its
  undeclared ones at the top; an immediate-directory count reads it as 0 of 3
  and misses exactly the three files the rule exists for.

`DIRECTIVE_HEADING_WORDS` holds one word, `OBEY`, because one word is what has
been observed. Adding `FOLLOW` or `MUST` would be building for a repository
nobody has seen, which spec 0002 §11 already refuses. The table is the extension
point, and adding to it moves the detector version on its own.

Order of application, first match wins: a vendor name, then the file's own
heading, then the directory. `vendor/CLAUDE.md` in the fixture carries both a
vendor name and a directive heading and is recorded under the vendor name — both
say the same thing about the file and the vendor name is the older, narrower
claim.

## The acceptance run — evidence, hand-checked

Advisor-Desk at `4fd66e3`, detector set `1.2ee25fd613c9`. Never asserted in a
test: this content changes, including from this work.

| | ticket 09 baseline | this run |
|---|---:|---:|
| detector set | `1.4e7b60b9df23` | `1.2ee25fd613c9` |
| files walked | 247 | 249 |
| **files with a surface kind** | **0** | **87** |
| surfaces · clauses · pointers | 0 · 0 · 0 | 87 · 7,560 · 224 |
| edges | 28 | 7,812 |
| identical-byte pairs · with provenance | 28 · 0 | 28 · 0 |

The two extra files walked are this ticket's own, `orbit/fixtures/build_lineage.py` and
`orbit/tests/test_recognition.py`. The edge total reconciles without a remainder:
7,560 CONTAINS + 224 REFERENCES + 28 IDENTICAL_BYTES + 0 PRODUCES = 7,812. Byte
identity and provenance did not move, which is what ticket 09's watch-for asked
be checked either side of a change that touches counts.

Both detector sets are in the store at once, each snapshot marked
`detector_set_is_current`, so the two columns above are readable as two detector
sets rather than as an estate that changed.

### Reconciled by name, against the groups in `08`

| group | files walked | surfaces | recognised by |
|---|---:|---:|---|
| 14 book directories | 42 | 42 | `declared-marker` |
| `_rule-workbench/` | 45 | 45 | 42 `declared-marker`, 3 `corpus-adjacent` |
| `docs/` | 95 | 0 | — |
| root — `README`, `CHANGELOG`, `LICENSE`, `.gitignore`, the `.png` | 5 | 0 | — |
| `orbit/` — this branch's own work | 62 | 0 | — |
| the 14 `full.md` symlinks | 0 | 0 | never walked |
| | **249** | **87** | |

The three inferred rows, named, because a count of three proves nothing:

```
_rule-workbench/CHECK_COMPATIBILITY.md   25,825 bytes
_rule-workbench/PROCESS.md               11,283
_rule-workbench/RELEASE.md                3,619
```

One ladder, checked against the bytes spec 0002 §2 recorded by hand before any of
this was built:

```
refactoring/refactoring.md       17,866   declared-marker
refactoring/refactoring.mini.md   5,167   declared-marker
refactoring/refactoring.nano.md   1,986   declared-marker
```

**Two corrections to `08`'s hand count**, found by reconciling rather than by
counting again. There are **42** published rule files, not 43 — 14 books at three
rungs each — and the root group is five files, not four: `CHANGELOG.md` is not in
that table. 42 + 45 + 95 + 5 + 14 symlinks = 201, which is the figure `08` states
for the repository. `08` is corrected in place.

**The check ticket 04's precedent asks for.** The number is not the evidence. Of
the 87 files named, every one is a file a human would have named: 84 that say what
they are in their own first line, and three whose whole content is instructions
for producing the other 84. 162 files carry no surface kind, `docs/` among them,
so the rule learned something `find` did not already know.

## Found while doing this, and not fixed here

**The derived detector version moves on constants, not on code.** Three defects
came out of `code-review` at the end of this ticket, and one of them —
a vendor-named file being allowed to satisfy a directory's corpus share — changed
what is recognised without moving `detectors.VERSION`, because the fix was in
`candidates()` rather than in a table. Nothing published spans it: both readings
shipped inside this one uncommitted change and the acceptance run was taken again
afterwards, unmoved at 87.

The gap is the design's, stated in `orbit/orbit_context/detectors.py`'s own docstring — a pattern
*is* the detector, and a constant is hashed while the code reading it is not. It
held while every rule was a table lookup. It stops holding the moment a rule has
logic, which is what this ticket added. Recorded here rather than fixed, because
what to hash instead is a decision, not a patch, and it belongs beside the ones
ticket 07 takes.

The other two are fixed and pinned by tests: the recognition split now counts
what `surfaces` counts, so the two add up rather than disagreeing when a
candidate cannot be read, and `repo-map` names a row written before the column
existed instead of dropping it into an all-zero split.

## Acceptance

- [x] Candidate rules put to Dylan with counts before any is implemented
      — three, with the count and the per-group split each would produce, above.
- [x] The chosen rule and the reason it was chosen are recorded in this ticket
      — B, for the three workbench files A cannot reach, with the guards and the
      rejected candidate's measurements beside it.
- [x] Surfaces on Advisor-Desk reconcile to the named groups in `08`
      — the table above, by name and by byte count, and two errors in `08`'s own
      figures found and corrected in the process.
- [x] Vendor-named recognition still works — the fixture proves the two paths do
      not interfere
      — `build_lineage` carries a `CLAUDE.md`-shaped repository beside the
      book-ladder one. `orbit/tests/test_recognition.py::TestTheTwoPathsDoNotInterfere`
      asserts vendor names still resolve, that both paths run in one repository,
      and that a file carrying a vendor name *and* a directive heading is
      recorded under the vendor name. `build_estate` is untouched and its 305
      tests are unmoved.
- [x] The detector version moved, and any output spanning the change says so
      — `1.4e7b60b9df23` to `1.2ee25fd613c9`, derived, with nothing bumped by
      hand. `index` prints it, `repo-map` prints it on every counted section, and
      the store block marks each snapshot `detector_set_is_current` so the
      before and after are readable as two detector sets.
- [x] Output contains no forbidden vocabulary word
      — the three `recognition` values are linted against the full list by
      `orbit/tests/test_vocabulary.py::TestVocabulary::test_recognition_kinds`.
- [x] 269 existing tests still pass, with no count assertion edited
      — 305 was the real figure at the start of this ticket; ticket 09 added
      tests after `08` wrote the number down. 305 pass unmoved and 321 pass in
      total. **One assertion was edited and it is not a count assertion:**
      `orbit/tests/test_ontology.py::test_phase_one_columns` pins the surface table's column
      list, and adding `recognition` is exactly the change it exists to catch. It
      is renamed `test_declared_columns` and names the one addition and why. No
      count was re-baselined.

## Watch for

**Both failure directions are silent.**

Come back at or near 198 and the rule has learned nothing `find` did not already
know — spec 0002 §12 lists that as a kill condition, not a tuning problem. Come
back at 0 and nothing changed.

Ticket 04's phantom-finding failure is the precedent: **1,349 of 1,373 findings
were the tool talking about itself**, and the count alone looked like a working
detector. The check is not the number, it is whether the named files are the
files a human would have named.
