# Spec 0003 — Estate archaeology and evidence-driven recomposition

**Status:** program specification. It sets the gates the next stage of the
estate work runs under. It is **not** the target architecture, and nothing in it
authorizes a build, a migration, or an edit to any audited repository.
**Written after:** ticket 07 was run, corrected by independent review, and
reviewed again.
**Rests on:** spec 0001 (rev 3), spec 0002, and
`orbit/tickets/07-audit-and-gates.md` at head `7795ff3` — PR 1, draft, 500 tests
and 46 subtests passing at that head.

## 0. Where this document sits, and what its location does not confer

This repository has one spec convention: `orbit/specs/NNNN-<slug>.md`, numbered
in sequence. 0001 and 0002 are taken, so this is **0003**. The number was read
off the directory, not chosen.

The program is wider than Orbit. **Orbit is the observer this program reads
with. It is not the subject, and it does not decide the outcome.** Filing this
beside the Orbit specs gives it no standing over any repository, and no Orbit
observation acquires standing by being quoted here. Where this document says
"the program", it means the sequence of gates in §5 to §9 — a route for finding
things out, not a rule anyone in the estate is being asked to follow.

### 0.1 Where work is tracked, and what that does not confer

**GitHub Issues on `DWMerit/Advisor-Desk` is the current tracker.** All new work
governed through Advisor-Desk is opened there. `docs/agents/issue-tracker.md`
records how it is reached, and that the route differs between a local machine
and a remote session.

**`orbit/tickets/` is a legacy record.** Eighteen files at head `6a772fa`,
numbered `00` through `17`, written under a home-built imitation of these
workflows before a tracker was configured. They are preserved as historical
evidence and are not migrated, archived, rewritten or deleted. **No new ticket
is created there.**

**The coexistence is itself evidence, and it is evidence of drift rather than of
two authorities.** A repository holding two places where work is described is
the condition this program exists to reconstruct in other repositories, and it
now holds one of its own. Recorded here so that a later reader finds the
condition named rather than inferring that both were meant to be live.

**Task-specific authority is progressively disclosed through the active ticket,
its governing spec, and an explicitly invoked workflow.** These sources may
govern together at different levels. Direct human instructions and runtime
constraints still apply. File location, recency, and confident wording do not
independently confer task authority.

**Orbit observes this structure and does not decide it.** Orbit may observe
declarations, pointers, loading relationships, and the surfaces active in a
session. It does not decide effective authority, trust, precedence, or
permission. Those determinations belong to the separately loaded
workflow/authority layer.

## 1. Goal

Decompose and recompose the estate from evidence that already exists — Git
history, Orbit observations, session records, and failures that actually
happened — rather than from the current repository names and directory layout.

Four things have to be true of any eventual design, and each is a gate below:

1. It contains failures that actually occurred, reconstructed from evidence.
2. It reduces governance and authority plumbing rather than adding to it.
3. It preserves estimating capability and improves estimating work.
4. Observations stay observations: nothing here turns a reading into authority.

The program produces **decisions and evidence packages**. The target
architecture is downstream of all five gates and is out of scope here (§10).

### 1.1 The immediate destination

Ahead of every gate below, and bounding them:

1. **Orbit is reliably usable on the local estate.** The store scopes to one
   snapshot, a documented query runs as written, and a figure read back is a
   figure of something that exists at once.
2. **The minimum evidence-backed recomposition needed to resume estimating
   work**, and no more than that.

**Neither is a licence to widen.** Repository cleanup, governance redesign and
hot-context architecture are not prerequisites for estimating, and none of them
becomes one unless historical evidence shows it blocking estimating work. A gate
below that starts to require one has stopped serving this destination and is
answering a question nobody asked.

## 2. Program Gate 0 — the disposition

**The question, as originally set:** *does Orbit report its current observations
correctly, reproducibly, and traceably to named evidence?*

That question is about the observations Orbit makes **now**. Columns that phase
2 and phase 3 will add are not part of it, and are not read back into it.

**Disposition: PASS WITH RECORDED FOLLOW-UPS.**

### 2.1 The evidence the disposition rests on

| # | Evidence | Where it lives | Confirmed at head `7795ff3` |
|---|---|---|---|
| 1 | Golden lineage reproduced from the repository trees, the base established from rows and trees before any delta was read | ticket 07, Part 1 | recorded; the run is named by its commit `dc8d743` |
| 2 | Counts that tie back to rows, each with its denominator and detector set | ticket 07, Parts 1–4 | recorded |
| 3 | Three calibrated historical states, measurably distinct — 87, 103 and 126 surfaces over 201, 323 and 515 files | ticket 07, Part 1 | recorded |
| 4 | Three repositories the tool had never seen — Home-system, Estimating-Lab, Merit-knowledge | ticket 07, Part 2 | recorded |
| 5 | Merit-knowledge's zero explained exactly, tied to eleven named files and 106,314 bytes, against the three recognition rules that exist | ticket 07, Part 2 | recorded |
| 6 | Two defects found by running the tool over unfamiliar repositories, each repaired with its test in the same commit | commits `9daa2b1`, `9cd5bf3` | recorded |
| 7 | The 157-of-1,306 bare-path-literal class recorded and not repaired, so the detector set stayed at `1.8eabab386316` and every figure stays comparable | ticket 07, Part 4 | recorded |
| 8 | One evidence record excluded from the pointer-drift population, not the whole ticket tree, with both readings kept beside the exclusion — 127 of 373 (34.0%) whole tree, 103 of 348 (29.6%) with that one file out | `orbit/tests/test_pointers.py` | recorded, and the reasoning is in the test |
| 9 | Direct-execution test collection repaired | reported from the session record | **not confirmed from repository state here** — see F5 |
| 10 | Both pre-registered gate decisions corrected back to their written rules by independent review, including one demonstrably false supporting assertion | commit `7795ff3` | recorded |
| 11 | 500 tests and 46 subtests passing | `python3 -m pytest orbit/tests` | **re-run here: 500 passed, 46 subtests, 207s** |
| 12 | No CI | no workflow definitions exist in the repository | **confirmed here** — recorded as a limitation, F1 |

### 2.2 Recorded follow-ups

These travel with the PASS. None of them reopens Gate 0, and none is a defect
finding against the tool.

- **F1 — No CI.** Every figure rests on a local run. Re-running is the only
  reproduction route, and it is a person's action, not a pipeline's.
- **F2 — The link-display-text class.** 157 of 1,306 `bare-path-literal` rows,
  12.0%, recorded and deliberately left. Repairing it moves the detector set,
  and a moved detector set makes ticket 07's figures incomparable with the ones
  they were taken against.
- **F3 — The cold-start condition has no reading.** Spec 0001 §9 sits behind the
  `client` column, so spec 0001 §13's "the cold-start number rises" cannot be
  read until phase 2 lands. Recorded as a coverage gap, not as a pass.
- **F4 — Shallow inputs.** C2 and the three hand-built repositories were read
  from shallow clones with no history. Nothing recorded rests on their lineage.
- **F5 — Direct-execution test collection.** Reported repaired in the session
  record; there is no artifact at this head that shows it either way. Either it
  is confirmed by a named test invocation, or the claim is withdrawn.
- **F6 — Pointer-ceiling headroom is finite, and Gate 1 will spend it.** The
  drift guard is a share: distinct addresses named in this repository's prose
  that resolve to nothing here, ceiling 0.33. The reading with ticket 07
  excluded was 103 of 348 (29.6%) at that head. **Measured again after this
  spec and the committed report: 103 of 350, 29.4%.** The report adds no
  unmatched address of its own — it names its evidence by URL, and 46 of its
  addresses carry a scheme, which the guard does not count — so what moved the
  denominator is this spec naming the file. Gate 1 fixtures are the ones that
  will spend the headroom, because they quote addresses in four other
  repositories by their nature. Each fixture therefore has to say, at the time
  it lands, how its addresses are held — as an evidence record on the same rule
  ticket 07 was granted, or by carrying the addresses outside this repository's
  prose. Lowering the ceiling to fit is refitting, which the guard exists to
  stop.
- **F7 — The Sandcastle report, closed on 2026-09-11.** It was outside this
  repository when the disposition was written. It is now committed at its exact
  bytes as `orbit/evidence/sandcastle-adr-comparative-archaeology.md` (§4.1),
  which is the entry condition Gate 1 was waiting on.
- **F8 — An SC-A14 generalization test, recorded for Orbit and not added to
  Gate 0's criteria.** The report's own corpus carries four provenance
  conditions: duplicate ADR numbering, a referenced-but-absent ADR, a
  documented decision whose implementation sits outside canonical `main`, and
  prose superseded by later code behaviour. Generalized past Sandcastle, they
  are a test of whether an observer can report the document, branch,
  implementation and drift relationships it can see **without inferring
  authority, correctness, supersession, or local adoption** where no evidence
  supports the inference. Orbit has not been set this test. It is recorded as a
  follow-up, and Gate 0's original criteria stay as they were written.

- **F9 — A write path in a test is read as a production.** Writing a
  `CLAUDE.md` for this repository, which had none, made two test fixtures
  resolve that never had: each builds a `CLAUDE.md` inside a temporary
  directory, and the detector matches that write path to the only `CLAUDE.md`
  indexed here. Two false productions, both checked by hand, both recorded in
  `orbit/tests/test_provenance.py` by name so the guard still fails on a third.
  **Recorded and not repaired**, on F2's rule: repairing it moves the detector
  set, and a moved detector set makes tickets 07 and 14 incomparable with the
  figures they were taken against. It is a condition of the detector meeting a
  tmpdir, not a statement about either test — and the guard that caught it did
  so on the first ordinary file that triggered it, which is the behaviour that
  was wanted.

### 2.3 What Gate 0 does not settle

It says the observer reports honestly. It says nothing about what shape the estate
takes, which responsibilities exist, or whether any repository boundary belongs
where it is. Those are Gates 2 and 3, and they need failures, not readings.

## 3. Ticket 07's gates are not Program Gate 0

Three gates share a vocabulary and settle different things. They stay apart.

| Gate | Question | Outcome |
|---|---|---|
| Ticket 07 Gate A | Does the load ledger earn its place? | **Undecided.** Rule branch taken: *the same column is missing each time* |
| Ticket 07 Gate B | Do evidence columns earn their place? | **Undecided.** Rule branch taken: *the rate varies sharply between detectors* |
| Program Gate 0 | Does Orbit report its current observations correctly, reproducibly, traceably? | **Pass with recorded follow-ups** (§2) |

Gate A and Gate B are Orbit build decisions. Gate 0 is a disposition about the
observer's honesty. Neither is evidence for the other.

### 3.1 Neither gate is decided, and a rule firing is not a decision

**Both gates are undecided until a test shows the addition would be beneficial.**
Dylan's call, 2026-09-12, and it corrects what this section previously recorded.

The pre-registered rules fired. Gate A's rule says that when the same column is
missing from every question, build only that column; Gate B's says that when the
false-positive rate varies sharply between detectors, the finding must carry its
rule. Both branches were taken on the evidence below. **Taking a rule's build
branch is not the same as showing the built thing earns its place** — the rule
establishes that a question could not be answered without the column, not that
answering it is worth a column. This project has drawn that line everywhere
else, and recording "already decided" here crossed it.

What a benefit test would have to show is **not written here**. Writing it is a
pre-registration, and pre-registering a rule after seeing the data it will run
on is the failure both gates exist to avoid. It is Dylan's to write, before any
build ticket is cut.

The measurements stand, and are the input to that test when it is written:

- **Only `client` was ever a candidate.** Thirteen of Candidate A's fourteen
  columns are out regardless of how the gate settles, because no question asked
  for one.
- **`client` is statically observable for 81 of 318 surface rows** (841,220
  surface bytes).
- **The other 237 rows are an explicit UNKNOWN carrying its reason** (1,707,616
  bytes, two-thirds of the estate's surface bytes). A value guessed for those
  rows would record inference as fact.
- **`evidence_class` is the only column Gate B would add.**
- **Detector identity already exists**, on every row, as
  `gl_context_edge.subtype`, `gl_context_surface.recognition` and
  `gl_context_edge.direction_reason`. Half of what Gate B opened for is built.
- **Neither decision authorizes a wider load-ledger scheme.** Whether
  `client` and `evidence_class` are stored columns, derived views or declared
  tables beside the detector name is a design question for the ticket that
  builds each one — and not a second gate.
- **The reachability figures are an archaeology question, not an architecture
  conclusion.** Advisor-Desk 16 of 117 surface rows reachable from a
  client-named root, against Home-system's 33 of 36. Both were taken by one
  query over one graph in one run, and what is *not* established is that the
  two numbers mean the same thing about a published rule corpus and a set of
  working skills. Gate 1 may ask what produced the difference. No gate treats
  the low number as a defect.

Neither column is scheduled, and neither is a condition of any gate here.

**The benefit test for `client` is not new work.** It is Gate A's own three
questions, committed before any data was seen, re-run unchanged after the column
lands. `orbit/specs/0004-the-client-column.md` builds the instrument and
`orbit/tickets/17-a-surface-says-which-client-pays-for-it.md` is the unit of
work; neither closes the gate, and reading the result stays Dylan's. Writing a
different rule now would be pre-registering after seeing the data, which is the
move both gates exist to stop.

## 4. The Sandcastle material, and the standing it has

The comparative archaeology report is an **audit-hypothesis catalogue**. It is
read as evidence about how a different estate failed, never as a ruleset this
estate adopts.

| Report content | Standing here |
|---|---|
| 21 decisions examined, across 20 files and 19 numbers on `main` | Input, catalogued. The arithmetic is itself the report's first finding |
| 12 independently corroborated principles | **Replay lenses** for Gate 3. Not estate rules |
| 5 decisions worth testing | **Hypotheses**, each carrying a falsifier before it is used |
| 2 Sandcastle-specific decisions | Not imported |
| 2 container/UID decisions | Irrelevant here, recorded so they are not revisited |
| 14 audit probes, SC-A01–SC-A14 | **Test probes** applied to fixtures and replays. Not fourteen governance requirements |
| 8 reusable audit families | The twelve corroborated principles, collapsed |
| 6 cross-repository failure episodes, A–F | The crosswalk: which repositories show the same chain |
| 8 recommended replay seeds | The Gate 1 backlog (§5.2) |
| The failure-episode ledger structure | The origin of the fixture contract in §5.1 |

**Five things stay separate and are never collapsed into one status:** an
external ADR's identity; whether it is canonical *there*; whether there is
implementation evidence behind it; whether it was superseded; and whether
anything here has adopted it. A principle being corroborated in that estate is
not adoption in this one.

### 4.1 The report, committed as evidence

The complete report is committed at
`orbit/evidence/sandcastle-adr-comparative-archaeology.md`, at its exact bytes.
It names its own review date, the repositories and commits it examined, its
scope and its limitations, and Git holds its blob identity. **Gate 1's entry
condition is met.**

All fourteen probes, SC-A01 to SC-A14, are defined there, with the evidence each
one needs for a `PASS` and the replay seed it came from. They are not reproduced
here: one copy, in the file that carries its own provenance. A probe applied
from a paraphrase is not a probe.

Committing it changes nothing about its standing. It is comparative evidence
about another estate, its location grants it no authority, and neither Sandcastle
nor any mechanism of Sandcastle's becomes a dependency of this one.

## 5. Gate 1 — historical reconstruction

**Build evidence-complete fixtures for failures that actually happened.**

### 5.1 What a fixture contains

Each episode is one package, and every field is either filled from evidence or
marked UNKNOWN with the reason it is unavailable. An absent runtime fact stays
absent: **a fixture never invents a fact the record cannot supply.**

1. Pre-state commits.
2. Prompting evidence.
3. Changed files, and the graph relationships around them.
4. Writer, reader, and enforcing boundary.
5. Authority and activation path.
6. Lifecycle and supersession.
7. Secondary failures.
8. Repair attempted.
9. Evidence that the repair held, failed, or remains unknown.
10. Estimating effect.
11. Sandcastle cross-reference, in the report's own four dispositions: a
    corroborated principle, a Sandcastle-specific contrast, a test hypothesis,
    or an irrelevant operating condition — with the SC-A probes that apply
    where they are useful. Never automatic authority.
12. Replay scenario.
13. Falsifier — what reading of the evidence would show the reconstruction
    does not hold.

Facts, interpretations, repairs, and proof that a repair held are **four
separate registers** inside every package. A package that reads as one narrative
has lost the distinction that makes replay possible.

### 5.2 The episodes

The first three are selected.

| # | Episode | Probes |
|---|---|---|
| 1 | Cross-session `git commit --amend` collision | SC-A01, SC-A03, SC-A08 |
| 2 | A pricing review that exited successfully after pricing nothing | SC-A05, SC-A06 |
| 3 | The ticket 07 evaluator reinterpreting both pre-registered gates after seeing the data, including one demonstrably false supporting assertion; independent review forced both decisions back to the written rules | SC-A08, SC-A11, SC-A14 |

Episodes 1 and 2 come from the report's eight recommendations. Episode 3 was
observed in this program, not in the report, so the Gate 1 backlog is **nine**:
the report's eight, plus this one.

**The anchors the report supplies for the first two**, each named beside its own
episode rather than left to be paired by position:

| # | Episode | Anchor |
|---|---|---|
| 1 | Cross-session `git commit --amend` collision | Estimating-Lab `077776de` |
| 2 | A pricing review that exited successfully after pricing nothing | Home-system `5ffc8bfb` |

The chain around each is set out in the report. They are starting addresses for
a reconstruction, not the reconstruction: a fixture is built from the evidence
around a commit, not from the commit's own message.

The six remaining recommended episodes, instantiated after the first three:

4. A lab observation becomes accepted truth.
5. Generated boot drifts from its source.
6. PROVEN is read as promoted or adopted.
7. A convenience index becomes authority, and maintenance work.
8. Imported Orbit vocabulary changes meaning in its new home.
9. A session closes before its evidence lands.

Each one's probes are named beside it in the report's recommended replay set,
and are read from there when its fixture is built.

### 5.3 Pass mark, and what Gate 1 may not produce

**Passes when the episodes are reproducible evidence packages** — every field
either evidenced or explicitly UNKNOWN with its reason, and the replay scenario
runnable by someone who was not there.

**It may not produce a target architecture**, a responsibility model, or a
repository layout. An episode that arrives with a proposed design attached has
answered a question Gate 2 has not asked yet.

Nothing is cleaned up while history is being read. Corrections belong to a
ticket of their own, after the episode that found them is recorded.

## 6. Gate 2 — responsibility decomposition

**Derive responsibilities from mechanisms that failed more than once**, not from
the names of current repositories or the shape of their directories.

For each candidate responsibility, nine fields:

1. Owned state.
2. Writers.
3. Readers, and which of them is a real consumer.
4. Authority.
5. Activation path.
6. Lifecycle.
7. Enforcing boundary.
8. Product effect.
9. The historical evidence that justifies separating it from its neighbours.

**Advisor-Desk is historical evidence.** It is not automatically an active
authority, and it is not automatically a boundary in anything that comes after.
The report reaches the same place from outside: it inspected Advisor-Desk and
excluded it as an active estate authority, on the ground that its `main` history
ends in May and the later Desk failures are recorded in `agent-rules-books`. It
examined `main` at `a7d7649`, which is not the branch this program's own record
sits on — a difference to keep in view rather than argue from.
The same holds for every other repository in the estate: appearing in the
evidence confers nothing.

**Passes when the estate can be described as coherent responsibilities without
naming the final repository layout.** A decomposition that can only be stated as
a list of repositories has not decomposed anything.

A responsibility that rests on a single episode is recorded as a hypothesis
rather than a responsibility. Repetition is what separates the two.

## 7. Gate 3 — candidate recomposition and historical replay

**Produce a small number of competing candidate designs** — few enough that each
can be replayed in full against every Gate 1 fixture, using the probes each
fixture names.

A candidate **passes a replay only if it prevents the failure, contains it, or
makes it explicitly diagnosable**, and does so with:

- fewer implicit authority transitions than the historical arrangement;
- fewer unnecessary surfaces;
- a real enforcing boundary — one that refuses, at the point of use;
- a negative control that shows the failure still reproduces without the
  intervention;
- a named consumer that reads the thing being added.

**Adding prose, a checker, a registry, a pointer, or a state field is not by
itself a passing intervention.** Each of those is a claim, and the negative
control and the named consumer are what turn a claim into a result. A repair
with no consumer is a surface that will need maintaining and will teach nothing.

Replay results are recorded per candidate per fixture, including the replays
that fail. A candidate that passes eight fixtures and fails one has one result,
not eight.

## 8. Gate 4 — estimating-work validation

**Test the surviving candidates on real estimating work.** At minimum, compare:

1. Time to a usable estimating decision.
2. Source coverage — what the decision actually rested on.
3. Rate of plausible wrong results.
4. Human clarification and repair turns.
5. Context loaded, and the cost of reconstructing it.
6. Non-product files and maintenance obligations created.
7. Durability and retrievability of accepted decisions.
8. Whether estimator judgment is visible without reading governance machinery.

**Confidential and negotiated-pricing inputs stay runtime-only.** They are not
committed, not published, and not quoted into any artifact this program
produces. A comparison that needs them names the shape of the input rather than
its content.

**A design that improves graph cleanliness and not estimating work fails this
gate.** That is the whole point of having it, and it is the final test in the
program.

## 9. Gate 5 — deliberate adoption and migration

**Passing Gate 4 does not authorize migration.** It produces a candidate worth
deciding about.

Adoption is a separate human decision, taken by Dylan, recorded as such. Any
migration that follows is:

- staged, one responsibility at a time;
- reversible at each stage;
- preserving of accepted estimating knowledge, which moves before anything is
  retired;
- and retires an old surface **only after** behavioural and product parity is
  demonstrated for what replaced it.

No gate before this one grants permission to move anything.

## 10. Non-goals

- **No target architecture in this spec.** It defines the route, not the
  destination's shape.
- **No repository migration**, and no edit to any audited repository while it is
  being read.
- **No Sandcastle-derived ruleset**, and no adoption of Sandcastle mechanisms.
- **No cleanup during archaeology.** A finding is recorded where it was found.
- **No assumption that an Orbit observation indicates a defect.** A reading is a
  reading until an episode shows it cost something.
- **No automatic promotion** from an experiment, a replay, or a passing gate. A
  gate opening is a decision recorded, not a change made.
- **No new governance mechanism built solely to operate this program.** If the
  program needs a registry to run, that is a finding about the program.
- **No agent-facing hot-context system.** Building retrieval or hydration that
  assembles context for an agent, at session start or on demand, is a later
  layer. It is also a one-way door with respect to measurement: a mechanism that
  delivers context changes the cold-start cost before the cost has been read.
  Orbit is itself an indexed context graph, and querying it is not what this
  excludes.
- **No additional authority machinery.** No registry of what governs what, no
  authority projection, no precedence scheme. §0.1 states how authority is
  disclosed, and stating it is the whole of the work this program does on it.
- **No production transcript-mining, transcript-to-skill or video-to-skill
  system.** Historical session records **may** be inspected as Gate 1
  archaeological evidence, and episode 9 is about one. What is out of scope is
  building a system that mines them as a product.

## 11. Operating rules that hold across every gate

- Every decision is recorded as a question and its answer, with the rule written
  before the data where a rule applies.
- Facts, interpretations, repairs, and proof that a repair held stay in separate
  registers.
- **A PASS needs evidence at the boundary it claims.** Prose describing a
  boundary is not evidence that the boundary holds.
- A proposed repair carries a negative control and a real consumer (§7).
- A question the work cannot address is recorded as a coverage gap, which is a
  result rather than a gap in the record.
- One ticket per session, and no concurrent mutating sessions in one checkout —
  which is episode 1's own subject matter.
- UNKNOWN with a reason outranks a value that was inferred.

## 12. Kill conditions for this program

Written now, so stopping is a planned outcome rather than a failure.

- The fixtures cannot be reconstructed from evidence, and filling them needs
  runtime facts nobody recorded. The program stops at Gate 1 and says so.
- Every candidate design passes every replay. A replay that nothing fails is not
  measuring anything.
- The responsibilities come back matching the current repository layout exactly.
  Either the layout was right, and the program is finished, or the derivation
  read the layout instead of the failures.
- The program starts producing rules, registries or checks for itself.
- Anyone reaches for a fixture or a replay result to settle a question it was
  not built to answer.
- Gate 4 shows no estimating difference between candidates, at which point the
  estate is not what is limiting the work.

## 13. Permanent UNKNOWNs this program adds

- Whether a reconstructed episode is the failure that happened, or the best
  account the surviving evidence supports.
- What was in a session's context at the moment of a failure, where no record of
  it was written.
- Whether a repair held because it was right, or because the conditions that
  produced the failure did not recur.
- Whether a candidate that prevents nine historical failures prevents the tenth.

## 14. Reserved for Dylan

1. Whether this program runs at all. §12 stands.
2. Which estimating work Gate 4 is measured on, and what "a usable estimating
   decision" means for it.
3. How many candidate designs Gate 3 carries.
4. The adoption decision at Gate 5, and the order of any migration.
5. Whether Advisor-Desk stays the home of this program's record, given §0.
