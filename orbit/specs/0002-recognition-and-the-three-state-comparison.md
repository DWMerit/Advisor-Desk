# Spec 0002 — Recognition, and the three-state comparison

**Status:** decided, not built. Written after phase 1 tickets 01–06 landed.
**Precedes:** ticket 07. This spec exists to make 07 runnable; it does not run it.

## 1. Goal

Two things, in order.

**Recognition.** Orbit currently finds governance by vendor filename. Run against a
repository whose entire content is governance, it recognises none of it. Until that is
fixed, an estate audit returns honest zeros and teaches nothing.

**Comparison.** Then measure Orbit against three states of the *same* repository —
untouched, worked-on-and-healthy, worked-on-and-collapsed — and use the deltas to decide
whether Orbit works at all.

## 2. The evidence that started this

`orbit-context index .` on Advisor-Desk, 2026-09-09, detector set `1.4e7b60b9df23`:

```
files_walked                   238
files_with_surface_kind          0
surfaces                         0
clauses                          0
pointers                         0
identical_bytes.pairs           28
identical_bytes.with_provenance  0
```

At `main` the repository is 201 files, of which **198 are markdown**: 14 book directories
of distilled rules, 43 published rule files, 45 files under `_rule-workbench/`, 95 under
`docs/`. Every one of them is governance content. Orbit recognised none.

The reason, from `orbit/orbit_context/surfaces.py`:

```
SURFACE_BASENAMES       CLAUDE.md, AGENTS.md, GEMINI.md, .cursorrules, SKILL.md
SURFACE_DIRECTORIES     .claude/agents/, .claude/commands/
SURFACE_RELATIVE_PATHS  .github/copilot-instructions.md, .mcp.json, .cursor/mcp.json,
                        .vscode/mcp.json, .claude/settings*.json
```

Ticket 02 states that *every governance object is a surface*. That claim holds only for
governance objects named the way Anthropic, Cursor and Google name them. This is a
detector gap, not an architecture gap: the store, the ontology, the addressing contracts
and the three negative findings are unaffected.

### What it did see

The 28 byte-identical pairs are real, and were confirmed by hand:

| pair | sha256 (first 12) |
| --- | --- |
| `_rule-workbench/refactoring/nano.md` = `refactoring/refactoring.nano.md` | `ce32dbb86b42` |
| `_rule-workbench/clean-code/mini.md` = `clean-code/clean-code.mini.md` | `a2cd7e30a033` |

Workbench to published, byte for byte, across the books. Provenance for these exists —
`_rule-workbench/refactoring/traceability.md` says `full.md` *"should resolve to
`../../refactoring/refactoring.md`"* — but only in prose. Spec 0001 §14 already lists
prose provenance as a permanent UNKNOWN, so `pairs_with_provenance: 0` is correct
reporting, not a defect.

### What is already here, built by hand

```
refactoring/refactoring.md       17,866 bytes
refactoring/refactoring.mini.md   5,167
refactoring/refactoring.nano.md   1,986
```

Fourteen of these ladders. This is progressive disclosure of rules per workflow — the
stated purpose of the whole project — implemented manually before Orbit existed. Orbit
cannot see the ladder, cannot say which rung a session loaded, cannot say the nano
derives from the full.

## 3. The three states, and why the control is free

Advisor-Desk and agent-rules-books are both clones of one upstream: *AI agents Rules /
Skills from Programming Books* by Maciej Ciemborowicz.

| state | where | what happened |
| --- | --- | --- |
| **C0 — untouched** | Advisor-Desk `main` @ `a7d7649` | 50 commits, one author, no agent work |
| **C1 — healthy** | Advisor-Desk branch head | C0 + 19 commits that built a tool |
| **C2 — collapsed** | agent-rules-books | C0 + work that grew its own governance layer, redirected onto refining ideas, and stopped producing |

`main` in this repository *is* the pristine upstream — verified: every commit on it is
authored by Ciemborowicz. So C0 needs no attached remote and no network. C1 and C0 differ
by exactly the 19 commits of this project.

The comparison depends on one further property, also verified: **C1 did not rewrite C0.**
`git diff main..HEAD` outside `orbit/` is two lines of `.gitignore` (`__pycache__/`,
`*.pyc`). All 198 markdown rule files are byte-identical at both ends, and HEAD carries 201
non-`orbit/` files against main's 201. C1 is therefore C0 plus additions, and `C1 − C0`
measures what a session *added* against an unmoved base. Whether the same holds for C2 is
not known and is the first thing the acceptance run establishes: if C2 rewrote its base,
the two deltas are not the same kind of measurement and the comparison has to say so.

Identical starting bytes, three end states, one variable each. The deltas `C1 − C0` and
`C2 − C0` are directly comparable in a way that no single absolute figure is. This is a
stronger falsifier than spec 0001 §9's cold-start number, which remains phase 2 and still
depends on the ungated Candidate A.

## 4. The estate has two families

| family | repositories | shared origin? |
| --- | --- | --- |
| **clone lineage** | Advisor-Desk, agent-rules-books (+ C0 in history) | yes — one upstream |
| **hand built** | Home-system, Estimating-Lab, Merit-knowledge | no |

Only the first family supports a controlled comparison. The second has no baseline, so
whatever it is measured against has to be argued rather than differenced. Ticket 07 is
currently written as one pass over the whole estate; that conflates the two.

## 5. The open decision this spec does not make

**What makes a file a governance surface, if not its name?**

Not decided. The first ticket must settle it against evidence, under these constraints,
all of which are already established:

- It must recognise Advisor-Desk's rule corpus.
- It must **not** recognise all 198 markdown files. `LICENSE`, the hero image and most of
  `docs/` are not governance objects.
- No inference may be recorded as fact. If a rule is a guess, its output is a guess.
- The detector version in `detectors.py` is derived from detector inputs, so any table,
  pattern or directory added moves it automatically. That mechanism must not be bypassed.
- Two counts taken either side of this change are not comparable, and the audit must say so.

Recording the constraint rather than the answer is deliberate. Nothing in this section was
decided in conversation, and a spec that invents one is a defective spec.

## 6. Seams

Two, one of them already carrying 8 of 12 test files.

**Seam A — the existing one.**

```
build_*(estate_dir)            writes synthetic repositories to disk, real git
  → index(estate, db_path=…)   walk → detect → clause → pointer → provenance
  → assert on the stats dict and the gl_context_* rows
```

Recognition, the ladder, and the three-state comparison all attach here.

**Seam B — the command line.** The comparison is run by hand, so it is also tested the way
it is run. Catches argument parsing and output shape, which Seam A cannot see.

**Not a seam — the acceptance run.** Indexing the three real states and reading the result.
A fixture cannot show that Orbit works on a repository it has never seen. This produces a
report, hand-checked against what is already known (14 ladders, 43 published rule files,
28 derived copies), recorded as evidence. It is never asserted in a test: a test that
reads live repository content fails whenever that content changes, including from this work.

## 7. Fixtures

Fixtures mirror the two families in §4.

- A **new builder**, separate from `build_estate`. It carries the clone-lineage shape:
  one book-ladder repository in three states, and a `CLAUDE.md`-shaped repository beside
  it so the two recognition paths are exercised together.
- A **second new builder** for the hand-built shape.
- `build_estate` is **not** extended. 269 tests pass against it and many assert absolute
  counts; re-baselining them before any new work starts risks silently disabling a test
  that was catching something.

Same seam either way. This is a blast-radius decision, not a seam decision.

## 8. What ticket 07 needs from this

Ticket 07 becomes runnable when all of these hold:

1. Governance in Advisor-Desk is recognised, and the count is reconcilable by hand.
2. The store is rebuilt. It currently holds a prior index of GitLab's own repository
   (`CLAUDE.md` 17,294 bytes, `crates/indexer/AGENTS.md` 15,133) alongside today's run, and
   `gl_context_surface` carries four columns the ontology no longer declares — `client`,
   `activation`, `evidence_class`, `detector`, all leftovers from the pre-gate design.
   The indexer already warns about this. Contaminated input makes every comparison figure
   arguable.
3. agent-rules-books is attached to the session.
4. Ticket 07 is re-scoped: the clone lineage first as a controlled comparison, the
   hand-built family second as an audit. Its Gate A and Gate B rules are unchanged.

## 9. Pass marks, set before any data

Falsifiable, written now, so the answer is not negotiated after the fact.

- **If Orbit cannot show a measurable difference between C0, C1 and C2, it does not work.**
  Not "needs more detectors" — the spec 0001 kill conditions apply and the project stops.
- Recognition on Advisor-Desk must reconcile against the hand count. A number that cannot
  be tied back to named files is not a result.
- No finding may assert something false. Any single false assertion is a stop, not a bug.
- Any question the run cannot address is recorded as a coverage gap, which is a result.

## 10. Build order

1. Rebuild the store. Cheap, and everything downstream is contaminated without it.
2. Settle §5 and extend recognition. Advisor-Desk is the test bed; the answer is known by hand.
3. The ladder and the workbench-to-published relationship, at Seam A.
4. The comparison surface, at Seams A and B.
5. Attach agent-rules-books; re-scope ticket 07.
6. The acceptance run over C0/C1/C2. Evidence, hand-checked.

Only then does ticket 07 run.

## 10a. The layer boundary

**Orbit is the context layer. Its only job is to show what is.**

Governance and authority are a different layer, disclosed progressively as a
workflow needs them. They sit above this one and read from it; they are not built
here and are not named here.

The distinction the two words carry, kept separate because conflating them is
what pulls an observer toward judging:

- **governance** — which rules exist, and where.
- **authority** — which rule wins, and who decides.

Orbit answers neither. It answers *what files exist, what they contain, what
points at what, and what is byte-identical to what*. That a file is loaded by a
convention is observable. That it governs, or that it outranks another file, is
not, and no detector may assert it.

**The practical rule.** In anything the tool writes — a printed row, a column
name, an ontology description, a `--help` string — the noun is `surface`,
`clause`, `pointer`, `pair`, `rung`. Never `governance`, never `authority`. Those
words belong in specs and tickets, where a human is explaining intent to another
human. GitLab Orbit has no such words in its output because it indexes code; a
faithful emulation has none in its output either.

This was checked and five uses were found and removed: two printed row labels and
one section subtitle in `compare.py`, one `--help` string in `cli.py`, and two
ontology descriptions in `references.yaml` that shipped inside the graph itself.
`authority` appeared nowhere. Module docstrings still use `governance` to explain
why a module exists, which is prose to a maintainer rather than output.

## 11. Out of scope — refused, with the reason

- **A SessionStart hook to carry branch state.** Refused during phase 1: *"dont build it if
  its only a band aid until what we are currently building is finished."* Ticket 06's
  `repo-map` provenance is the real replacement and it is built.
- **Building the load ledger or evidence columns.** Both stay gated. Ticket 07 decides
  them, and "not built" is a valid outcome.
- **Specifying recomposition.** Planning it before the audit is precisely the failure this
  work is aimed at: refining the idea of the build instead of building.
- **A governance-bytes-to-product-bytes metric.** The collapse in C2 plausibly has this
  signature, but building a metric for a hypothesis before measuring it is the same
  failure again. It is a question the acceptance run asks, not a feature.
- **The other six repositories.** Not until the lineage comparison has passed.
- **Editing the rule corpus.** Orbit observes. It does not author governance.
- **Cold-start burden (spec 0001 §9).** Still phase 2, still behind Candidate A. This spec
  does not unblock it and does not substitute for it.

## 12. Kill conditions for this spec

In addition to spec 0001 §13:

- Recognition is widened until it matches everything. A detector that finds all 198
  markdown files has learned nothing that `find` did not already know.
- The three states come back indistinguishable.
- The comparison needs a new store, a second index, or a query language of its own.
- Anyone reaches for the comparison to decide something rather than to check something.

## 13. Permanent UNKNOWNs this work adds

- Whether a rule file is loaded by any session, absent Candidate A.
- Which rung of a three-size ladder a session actually read.
- Whether two ladders derive from the same source, where only prose says so.
- Whether governance growth caused a collapse or accompanied one. The comparison shows
  correlation across three states. It does not show cause.
