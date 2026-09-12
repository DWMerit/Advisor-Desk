# Episode 3 — two pre-registered gates reinterpreted after seeing the data

Gate 1 fixture for issue [#7](https://github.com/DWMerit/Advisor-Desk/issues/7),
built against the 13-field contract in
`orbit/specs/0003-estate-archaeology-and-evidence-driven-recomposition.md` §5.1
(lines 296–322). Probes: SC-A08, SC-A11, SC-A14, read from
`orbit/evidence/sandcastle-adr-comparative-archaeology.md` (§ *Audit catalogue*,
lines 210–216).

**State read.** `/home/user/Advisor-Desk`, branch
`claude/orbit-foundation-spec-6a4nau`. Every figure and line number below is
read from committed objects or from tracked content at `2ceb588`, which was HEAD
when this reconstruction began.

**The state moved during the reading, and it is recorded rather than
re-baselined.** At the start of this session HEAD was `2ceb588` with one
uncommitted modification to `docs/agents/issue-tracker.md`, made by another agent
working in this same checkout. By the end HEAD was `127575d` and the tree was
clean: that agent committed "The MCP tools not covering something is not the same
as it being unreachable", 1 file, +36/−3, touching only
`docs/agents/issue-tracker.md`. `git diff --stat 2ceb588..HEAD` confirms no other
file moved, so every citation below still resolves at `127575d`. This
reconstruction wrote nothing to the repository — `git log`, `git show` and
`git diff` only — and ran no index, so the shared store at
`~/.orbit-context/context.duckdb` is untouched.

**One cited file was modified by a parallel session after this reading
finished.** At close, `git status` reported `M orbit/tests/test_pointers.py` and
an untracked `orbit/evidence/episode-01-cross-session-amend-collision.md`,
neither written by this reconstruction. **Every `test_pointers.py` line number
cited below is to the committed version at `2ceb588`** — read it with
`git show 2ceb588:orbit/tests/test_pointers.py`, not from the working tree. That
this reconstruction and two others were reading and writing one checkout
concurrently is itself the subject of episode 1, and the reason the "Unknown"
entry in Register 4 declines to take a live pointer-guard reading.

**Method limits.** Read-only. No `git` write, no repository edit, no index run
(the store at `~/.orbit-context/context.duckdb` is shared with the parallel
sessions, and a new snapshot written into it would be a write nobody asked for).
Anything that would have needed a fresh graph query is marked UNKNOWN with that
reason rather than estimated.

---

## 0. A correction to the episode's own framing, before the registers

The issue body and the task framing both state the chain as `dc8d743` →
`4b67920` → `7795ff3` → `050074f`. The fourth link is wrong, and the error
matters for the fixture because it misplaces the authority behind the third
reading.

- **The third reading landed in `7931206`**, "Gates A and B undecided; README
  points at our store; ticket 16 filed", 2026-09-12 02:34 UTC. Its diff to
  `orbit/specs/0003-…md` rewrites the §3 outcome table from **Open** to
  **Undecided** and retitles §3.1 from "The Orbit roadmap, already decided,
  recorded so it is not re-argued" to "Neither gate is decided, and a rule
  firing is not a decision".
- **`050074f`** (2026-09-12 03:44) touches the same file but not the gates. Its
  four hunks are at lines 22, 38, 288 and 431 of the pre-image — §0.1's tracker
  record, §1.1's destination, three non-goals, and §5.2's two episode anchors.
  Its only line matching /gate/ is the added sentence "Ahead of every gate
  below, and bounding them:".
- **The grounds the issue gives for the third reading are not `7931206`'s
  grounds.** `7931206` does not dispute that the branches fired — it says "The
  pre-registered rules fired" and then that taking a build branch is not the
  same as showing the built thing earns its place. The issue's grounds (Gate A's
  branch wants one missing column and two are missing; Gate B's registered
  instrument was the 50-row sample, which the ticket itself says cannot carry
  the claim) dispute that the branches fired **at all**. That is a different
  reading, resting on different evidence, reaching a coincidentally similar
  verdict.

So the surviving record holds **four** readings of one body of evidence, not
three, and the fourth exists only in the tracker. This is carried into Register 2
rather than smoothed over, because the difference between "the rule fired but
firing is not a decision" and "the rule never fired" is the whole of the live
question in §5.

---

## 1. Register one — what the data showed

Facts only. Every figure in this register is **identical across all readings**:
no reading disputed a measurement. Each is quoted from `4b67920`'s text and
verified unchanged at HEAD, so the register is stable under the later commits.

### The run

| | value | evidence |
|---|---|---|
| Detector set | `1.8eabab386316`, unmoved across the whole chain | ticket 07 line 193; `9daa2b1`, `9cd5bf3`, `7795ff3` commit bodies |
| Head indexed | `dc8d743` — the pre-registration commit itself | ticket 07 lines 188–191 |
| Gate A questions written at head | `38b9dce` | ticket 07 line 142 |

### Part 1 — clone lineage (`orbit/tickets/07-audit-and-gates.md` lines 194–204)

| | C0 `a7d7649` | C1 `dc8d743` | C2 `782a886` |
|---|---|---|---|
| files walked | 201 | 323 | 515 |
| surfaces | 87 | 103 | 126 |
| surface bytes | 781,674 | 853,575 | 946,722 |
| clauses | 7,560 | 7,901 | 8,089 |
| pointers | 224 | 314 | 344 |

Base re-established before any delta was read: fourteen link rows per state, 812
bytes (lines 217–221); C0's 201 paths in C2's tree — 195 byte-and-mode
identical, 5 edited, 1 absent, no corpus file among the six (lines 223–239).
Corpus share under `_rule-workbench/`: C0 0.933, C1 0.933, C2 0.712, against a
declared 0.75 (lines 259–263). Zero paths recognised in C0 are unrecognised in
C1; C2 loses three named files to the share move (lines 265–276).

### Part 2 — hand-built family (lines 294–310)

| | Home-system | Estimating-Lab | Merit-knowledge |
|---|---|---|---|
| files walked | 1,348 | 601 | 11 |
| surface rows | 36 | 25 | 0 |
| surface bytes | 499,428 | 247,487 | 0 |

Merit-knowledge's zero is tied back to all eleven files by name, with the reason
stated as a property of the detector set (lines 372–397).

### Gate A's instrument and its result (lines 433–521)

All three pre-registered questions marked **not answerable**.

- **81 of 318 surface rows / 841,220 of 2,548,836 surface bytes** carry a
  filename that names a client; **237 rows / 1,707,616 bytes** do not (lines
  452–455).
- `SELECT client FROM gl_context_surface` → binder error; no such column in any
  of the six tables (lines 469–473).
- Reachability adds one row in Home-system, one in Estimating-Lab, none in
  either lineage repository (lines 462–466).
- Q3: `activation`, `trigger`, `lifetime`, `revocable`, `scope` and
  `inheritance` **all** return a binder error (lines 500–501).
- 27 surfaces declare `disable-model-invocation`; **61 of 88 skill packages and
  all 218 instruction surfaces declare nothing about activation at all** (lines
  517–518).

### Gate B's instrument and its result (lines 581–630)

- Population: **2,167 findings**. Sample: **50, stratified 25 per family, random
  within each, seed 20260911** (lines 583–590).
- **4 of 50 are detector artifacts — 8.0%.** Per family: 8.0% and 8.0%. Per
  detector: `bare-path-literal` 37 sampled / 4 artifacts / 10.8%; the other six
  detectors 0% at n = 1 to 4 (lines 592–608).
- Population measurement: **157 of 1,306 `bare-path-literal` rows — 12.0%** —
  restate a markdown link on the same line; **20 pointer rows run from a file to
  itself** (lines 613–630).
- The 96% prior (1,349 of 1,373) came from one fixed bug (ticket 07 lines
  106–108; `orbit/tests/test_pointers.py` docstring lines 11–15).

### Defects the run found in the observer (lines 704–747)

- `produces_edges: 2` reported where the graph held one `PRODUCES` row
  (`9cd5bf3`).
- Two distinct paths printed as `X = X` because the elision cut where they
  differ (`9daa2b1`).
- The 157-row link-display-text class: recorded, not repaired, because repairing
  it moves the detector set version.
- Recording the ticket took this repository's own pointer-drift reading from
  **103 of 348 (29.6%) to 127 of 373 (34.0%)** against a 0.33 ceiling; the 24
  addresses added are all foreign to this repository (ticket 07 lines 750–761;
  `orbit/tests/test_pointers.py` lines 58–78).

---

## 2. Register two — what each evaluator concluded

Interpretations. Kept apart from Register 1, and kept apart from each other: the
four readings are listed in the order they were written, each with its own
ground, and none is presented as the reading of the data.

### R1 — both gates closed. `4b67920`, 2026-09-11 03:05 UTC, author `Claude`

49 minutes after the pre-registration, in the same recorded session.

**Gate A → not built.** The text is explicit that the rule did not decide it:
"The gate's two branches are … Neither fires cleanly, so the reasoning is set
out rather than asserted" (`4b67920:orbit/tickets/07-audit-and-gates.md` lines
522–526). It then supplies a test of its own: "**A column whose every
non-UNKNOWN value is derivable from a column already on the row is not a
column.** Gate A closes." (lines 541–542).

**Gate B → `evidence_class` not built.** Two grounds. First, "Neither branch of
the pre-registered rule asks for it" (line 642). Second, the same derivability
test — "which is the same test that closed Gate A" (lines 650–651).

Acceptance recorded "both are *not built*" (line 779). Kill conditions recorded
"both decisions are *not built* — the tool was used to check two proposals and
neither survived" (line 729).

### R2 — both gates open. `7795ff3`, 2026-09-11 03:29 UTC, author `Claude`

24 minutes after R1. Its stated cause: "Code review on two axes found that this
ticket's first pass decided both gates against its own pre-registered rules, on
a test invented after the data."

**Gate A → build `client`, and only `client`** (HEAD line 523). Branch two is
read as firing: "The same thing is missing each time, and it is which client
pays for a surface" (lines 530–532). Q3's missing `activation` is met by
argument rather than by the rule: "Q3 misses `activation` as well. But
'unconditional' is not a property of a file — it is a property of a file *for a
client* … `client` is necessary for Q3 as well, and not sufficient" (lines
538–545).

**Gate B → Candidate B built**, `detector` already present under three names,
`evidence_class` deferred to phase 3 (HEAD line 658; lines 660–680).

R2 also records two things about its own reasoning that bear on Register 4:

- It states a closing condition **not present in the pre-registration**: "What
  would have closed the gate: all three questions answering, or three different
  columns missing" (HEAD line 579). The registered rule's branches are only
  "all three answer" and "they do not, and the same column is missing each time"
  (HEAD lines 83–86).
- It moves Gate B's instrument. The pre-registration says "The question is the
  steady-state rate, and **only the sample answers it**" (HEAD lines 106–108).
  R2 says "The sample alone cannot carry the between-detector claim … **What
  carries the branch is the population measurement**" (HEAD lines 686–690). The
  population figures were already in R1's text, where they *confirmed* the
  sample — R1's own heading is "The population confirms the detector split,
  beyond the sample". R2 promotes that section from corroboration to instrument;
  it did not run a new query, and nothing was run later. (Verified: the 157 /
  1,306 / 12.0% block is present verbatim in `4b67920`.)

**R2 propagated.** `33ff76b` created spec 0003 §3.1 as "The Orbit roadmap,
already decided, recorded so it is not re-argued", scheduling `client` to phase
2 and `evidence_class` to phase 3.

### R3 — neither gate decided. `7931206`, 2026-09-12 02:34 UTC, author `Claude`

~23 hours after R2.

Ground, quoted from the diff: "**Both gates are undecided until a test shows the
addition would be beneficial.** Dylan's call, 2026-09-12, and it corrects what
this section previously recorded." And: "**Taking a rule's build branch is not
the same as showing the built thing earns its place** — the rule establishes
that a question could not be answered without the column, not that answering it
is worth a column."

**R3 does not contest R1's or R2's reading of the branches.** It says the rules
fired and that firing decides a different question than the gate asks. It
declines to write the benefit test, on the stated ground that pre-registering
after seeing the data is the failure the gates exist to avoid, and assigns that
writing to Dylan. Every measurement in Register 1 is carried forward unchanged
as the test's input (spec 0003 §3.1, HEAD lines 207–241).

### R4 — the branches never fired. Issue #7 body, 2026-09-12 20:32 UTC, author `DWMerit`

Not in any commit. Two grounds, both of which are checkable against text already
quoted above:

1. Gate A's branch two requires "the same column is missing each time"; the
   ticket's own Q3 analysis names `activation` as also missing (HEAD line 538).
2. Gate B's registered instrument was the 50-row sample; the ticket itself says
   the sample cannot carry the between-detector claim (HEAD line 686).

R4 reaches the same verdict as R3 — neither gate decided — by an argument R3 does
not make, and attributes itself to `050074f`, which contains neither argument.

### The four readings, side by side

| | verdict | ground | where it lives at HEAD |
|---|---|---|---|
| R1 | both closed | a derivability test written after the data; explicit that neither branch fired cleanly | ticket 07 lines 790, 799 |
| R2 | both open | branch two fired for each gate; Q3's second gap answered by argument; population promoted to instrument | ticket 07 lines 523, 658, 847, 856–861; ticket 00 lines 7–30; `orbit/README.md` line 1252 |
| R3 | both undecided | a rule firing is not a benefit demonstration (human call) | spec 0003 §3, §3.1; spec 0004 lines 5, 151, 159; spec 0005 line 172; ticket 17 line 50 |
| R4 | both undecided, because neither branch fired | the registered antecedents are not satisfied by the data | issue #7 only |

---

## 3. Register three — what each correction repaired

Repairs attempted. Stated as what the commit changed, not as what it achieved.

**`9daa2b1` and `9cd5bf3`** (before R1, after the pre-registration) — the two
observer defects the run exposed. `pairs.tell_apart` makes distinct paths print
distinctly; `produces_edges` is counted by the same rule the edge writer uses,
with the declined production named in `producer_and_artifact_are_one_file`.
Detector set deliberately unmoved so no figure taken either side changes.

**`7795ff3`** — five repairs, of which the first three are this episode's:

1. Both gate decisions reversed to the registered branches (ticket 07 lines 523,
   658, 847, 856–861).
2. The false assertion recorded in place rather than deleted: "A first pass
   concluded *not built*, on two grounds, and one of them was false: it said
   *'neither branch of the pre-registered rule asks for it.'* Spec 0001 §6 titles
   Candidate B *'evidence columns (`evidence_class`, `detector`)'* … Spec 0002 §9
   makes a single false assertion a stop, so it is recorded here rather than
   quietly repaired." (HEAD lines 694–700, restated in the pass marks at lines
   829–836.)
3. The pointer-guard exclusion narrowed from all of `orbit/tickets/` to the one
   evidence record. R1's cut had dropped 41 addresses including `compare.py`,
   `rung_of.yaml` and `tests/test_ladders.py` — names of this repository's own
   files. Both readings are recorded beside the exclusion
   (`orbit/tests/test_pointers.py` lines 58–78).
4. and 5. Code-level: a `__main__` guard above appended classes in three test
   files, a redundant module alias, the edge-or-not rule written twice and
   unified as `Production.is_an_edge`, and `tell_apart`'s docstring claiming a
   guarantee at any width where the derivation gives five.

**`7931206`** — spec 0003 §3 outcome table and §3.1 heading and body rewritten
from "Open"/"already decided" to "Undecided"/"a rule firing is not a decision";
the scheduling sentence replaced with "no ticket may be cut for either until a
benefit test is written and passed".

**`afd757f`, `050074f`, `2ceb588`** — R3 propagated outward: spec 0004 builds
Gate A's instrument while recording the gate as undecided and reserving the
reading for Dylan (lines 5, 58, 63, 151, 159, 164); ticket 17 states "It does not
close Gate A" (line 50); spec 0005 records "No `client` column. That is spec
0004, undecided behind Gate A" (line 172).

---

## 4. Register four — whether the repair held

Proof, separated from the repair. Three outcomes only: held, did not hold,
unknown with a reason.

### Held

- **The false assertion is recorded where it happened**, in two places, and
  survives every later commit (ticket 07 lines 694–700, 829–836). The rule it
  was measured against (spec 0002 §9 line 195: "No finding may assert something
  false. Any single false assertion is a stop, not a bug") was applied, not
  amended.
- **The detector set never moved.** `1.8eabab386316` is asserted in `9daa2b1`,
  `9cd5bf3`, `4b67920` and `7795ff3` and is the version every figure in Register
  1 carries. The one class of defect whose repair would have moved it was
  deliberately left unrepaired and named (ticket 07 lines 747–748).
- **The narrowed pointer-guard exclusion kept both readings visible.**
  `test_pointers.py` lines 60–61 record 34.0% whole-tree and 29.6% excluded, and
  lines 69–78 record why the broader cut was wrong. The ceiling was not moved
  (lines 40–43, and `CLAUDE.md`: "If it breaches, the answer is never to raise
  the ceiling").
- **R3 propagated into every artefact written after it.** Specs 0004 and 0005
  and ticket 17 all state the gate as undecided.

### Did not hold

**The repaired artefact still asserts what it was repaired for.** At HEAD,
`orbit/tickets/07-audit-and-gates.md` contains R1 and R2 simultaneously, in the
present tense, with no marker on either:

| line | text | reading |
|---|---|---|
| 130 | `## Either gate closing is a result, not a failure` | R1-era heading, left in place above the R2 body |
| 790 | "…behind Candidate A — **which Gate A has now closed.** This condition has no reading and will not acquire one on the current plan." | R1 |
| 799 | "No kill condition is met. Phase 2 is not entered regardless, **because both gates closed**, which is the outcome that makes phase 2's contents empty rather than blocked." | R1 |
| 523, 658 | "the gate opens…" | R2 |
| 847 | "Both gate decisions recorded — both gates **open**" | R2 |
| 856–861 | "Either gate closing is a result, not a failure — and neither closed. **Both opened**…" | R2 |

`7795ff3`'s diff shows the correction rewrote the two decision sections, the
acceptance line and the closing section, and did not touch lines 790 or 799.
Nothing at HEAD in this file says either gate is undecided.

**The contradiction reaches a reader through this repository's own reading
rule.** `CLAUDE.md` instructs: "Tickets carry a `## Acceptance` block. A ticket
that has been run carries a **second** one with its boxes checked — read the last
one, not the first." Ticket 07's second Acceptance block is at line 835; its
gate line, 847, reads "both gates **open**". A session following the documented
rule arrives at R2 and not at R3.

**Two further artefacts still carry R2.**

- `orbit/tickets/00-phase-1.md` lines 7–30: "**07 ran, and both gates opened**",
  "**Build `client`, and only `client`**", "So Candidate B is built", "**Phase 2
  is one column.**" `7931206`'s diff does not include this file.
- `orbit/README.md` line 1252: "It is also the measurement that opened Gate B."
  `7931206` edited this README (53 changed lines) and none of them matches
  /Gate/.

**Three of R3's own propagations point back at the unrepaired text.** Spec 0004
line 5, spec 0005 line 172 and ticket 17 line 50 cite spec 0003 §3.1 as the
authority for "undecided", while the ticket that ran the gates says "open" and
the phase record says "Phase 2 is one column".

### Unknown, with the reason

- **Whether the pointer-guard reading is currently under its ceiling.**
  `test_pointers.py` lines 60–61 record 103 of 348 (29.6%) as of `7795ff3`;
  `7931206`'s message reports 103 of 352 (29.3%) after ticket 16 landed. The
  comment was not updated. I did not re-run the suite: the measurement reads
  live repository content, and this working tree holds an uncommitted change
  made by another session, so a reading taken now would be a reading of a state
  no commit holds.
- **Whether `tell_apart`'s guarantee holds at the widths in use.** `7795ff3`
  states the bound is five characters and that below it "a cut can put both ends
  back to one string", and says the bound "is stated and pinned". Which widths
  the callers pass was not read.
- **Whether any `supersedes-claim` row exists over this repository's own prose.**
  The detector exists and is DECLARED-permanent (`orbit/tickets/04-…md` lines 10,
  20; `orbit/README.md` lines 476, 503–505), and the hand-built family returned
  0/0/0 (ticket 07 line 344). No figure for Advisor-Desk is recorded, and I did
  not index. What *is* established by grep: no prose in `orbit/tickets/` or
  `orbit/specs/` marks any of the R1 or R2 passages as superseded.

---

## 5. The live question — is the third reading correct, or merely the most recent?

Spec 0003 §13 line 535 records the permanent UNKNOWN this sits under: "Whether a
reconstructed episode is the failure that happened, or the best account the
surviving evidence supports." What follows is what would distinguish the two,
not a verdict.

**The record supplies recency and nothing else as an ordering.** All four
readings were written by the same kind of writer; all commits in this
repository's entire history — 62 of them — carry one identical
`Claude-Session:` trailer, and this reconstruction session's own attribution
carries that same string. So the trailer cannot distinguish the evaluator from
its reviewer from this reconstruction. No commit is marked as superseding
another, no artefact marks a passage as superseded, and the contradictory
passages coexist at HEAD. Recency is the only ordering the record offers.

**R3 is not in competition with R1 and R2 on the same question.** R3's claim is
that a fired branch does not demonstrate benefit. R1 and R2 answered "which
branch fired". Both can be true at once, and R3's own text says the rules fired.
So "is R3 correct" is not answerable by re-reading the gate evidence at all: R3
is a suspension of the gates pending an instrument its own text says is
deliberately unwritten and is Dylan's to write. Until that test exists, R3 cannot
be shown right or wrong by any evidence in this repository — which is itself the
distinguishing observation, not a gap.

**R4 *is* in competition, and splits into one decidable half and one not.**

- *Gate B is decidable by evidence, and the test is already named in the
  artefact.* The pre-registration names the instrument — "only the sample answers
  it" (HEAD line 107) — and R2's own text prescribes the fix: "A future sample
  wanting per-detector rates has to stratify by detector, not only by family"
  (HEAD lines 691–692). A 50-row sample stratified by detector, at the same
  detector set `1.8eabab386316` and the same population of 2,167, would show
  whether "varying sharply between detectors" holds on the registered instrument
  or only on the population query. If it holds, R2's branch reading survives and
  R4's second ground falls. If it does not, R4's second ground stands and R2's
  verdict rested on an instrument the pre-registration did not authorise.
- *Gate A is not decidable by any new evidence.* R2 and R4 agree on every fact —
  all three questions unanswerable, `client` missing from all three, `activation`
  also missing from Q3. They differ on whether "the same column is missing each
  time" is satisfied when one question misses two columns. That is a question
  about what the sentence in `dc8d743` means, and the pre-registration does not
  define the case. Only the rule's author can settle it, and settling it now
  would be reading the rule against data already seen. Note that R1 reached the
  same reading of the antecedent as R4 — "Neither fires cleanly" — and then
  discarded it in favour of a test of its own, so this reading is not new with
  R4; it is the one thing R1 got right and abandoned.

**One asymmetry in the record does bear on it.** R1 and R2 are the evaluator's
own successive self-reports, written 24 minutes apart in one session, with the
reviewing instrument being `.claude/skills/code-review` — a skill the same
session invoked, whose two axes run as sub-agents. That is context isolation, not
independent authority. R3 and R4 are the two readings with a human in their
authority path: R3 cites "Dylan's call, 2026-09-12"; R4 was written by the
repository owner's account. If human attribution is treated as evidence of
independence, the two later readings differ in kind from the two earlier ones —
and that, rather than their recency, is the strongest thing the record says in
their favour. It is also not proof: R3's ground is a general principle about
rules and benefits, stated without reference to the Gate A or Gate B evidence,
and a general principle applied to a case is not a reading of the case.

---

## 6. The fixture — all 13 fields

### 1. Pre-state commits — EVIDENCED

`5cac663` → `38b9dce` (head when Gate A's three questions were written, ticket 07
line 142) → `dc8d743` (the pre-registration, committed alone; also the head the
audit indexed, lines 188–191) → `9daa2b1` → `9cd5bf3` (the two observer repairs,
interposed between pre-registration and audit, detector set deliberately
unmoved) → `4b67920`. Parent chain verified with `git log --format='%h parent=%p'`.

### 2. Prompting evidence — PARTIALLY UNKNOWN

**Present:** the four commit bodies, each stating its own cause in its own words;
issue #7 (created 2026-09-12T20:32:09Z, author `DWMerit`, label
`wayfinder:research`, parent issue #3); `.claude/skills/code-review/SKILL.md` as
the named instrument of R2's review, including its two axes and its parallel
sub-agent structure; spec 0003 §3.1's attribution of R3 to "Dylan's call,
2026-09-12".

**UNKNOWN, with reason:** no transcript, session record or reflog evidence exists
in this repository — `find` over the tree returns no session or transcript
artefact. The one provenance field the commits do carry, `Claude-Session:`, is the
same string on all 62 commits and on this session's own attribution, so it
records nothing that varies. What was in the evaluator's context when it wrote
the derivability test cannot be recovered. This is spec 0003 §13's second
permanent UNKNOWN ("What was in a session's context at the moment of a failure,
where no record of it was written") instantiated exactly.

### 3. Changed files, and the graph relationships around them — EVIDENCED

- `4b67920`: 4 files, +747/−13. `orbit/tickets/07-audit-and-gates.md` +641,
  `orbit/tickets/00-phase-1.md`, `orbit/README.md`, `orbit/tests/test_pointers.py`.
- `7795ff3`: 10 files, +322/−163. Ticket 07 +258/−…, plus `indexer.py`,
  `pairs.py`, `provenance.py` and four test files.
- `7931206`: 3 files, +146/−23. Spec 0003, `orbit/README.md`, new ticket 16.
- `050074f`: 1 file, +71/−5. Spec 0003 only.

**The graph relationship that matters is an absence.** Ticket 07 lines 207–210
record that the commits between `dc16a3e` and `dc8d743` are "ticket and README
prose, which this detector set does not recognise, so they weigh on the walk and
nowhere else" — every other figure unchanged while bytes walked rose by 21,823.
The artefacts at the centre of this episode are files the observer walks and does
not recognise as surfaces. Orbit holds no node for the ticket that records its
own gate decisions, and therefore no edge could carry a supersession between two
readings of it.

### 4. Writer, reader, and enforcing boundary — EVIDENCED (the boundary negatively)

**Writer:** author `Claude` on all four commits in the chain; `DWMerit` on issue
#7.

**Readers, evidenced by citation:** `orbit/tickets/00-phase-1.md` lines 7–30;
`orbit/README.md` line 1252; spec 0003 §3.1; spec 0004 lines 5, 58, 63, 151, 159,
164; spec 0005 line 172; ticket 17 lines 7, 25, 44, 50; `orbit/tests/test_pointers.py`
`EVIDENCE_RECORDS`.

**Enforcing boundary: none exists.** `.claude/` contains only `skills/` — no
`settings.json`, no hooks directory, nothing that runs on a commit. No test
asserts a gate decision (`grep -rln "gate\|Gate" orbit/tests/` returns
`test_store_contents.py`, `test_pointers.py`, `test_ontology.py`, none of which
touches a verdict). The instrument that caught R1 was a skill the same session
chose to invoke, after R1 had already landed. Nothing refused `4b67920`, nothing
refuses the contradictory passages standing at HEAD, and nothing refuses a
session reading line 847 as current.

### 5. Authority and activation path — EVIDENCED

The gate rules live in ticket 07 Part 3 and Part 4 (HEAD lines 76–112), written
before the run and left "Unchanged" through the rewrite. `CLAUDE.md` states what
that location confers: "Specs and tickets are not loaded by any session. A rule
that matters at session open belongs in this file; a rule written only in a
ticket is read by nobody." So the gate rules were active only because ticket 07
was the active ticket. Spec 0003 §0.1 (added at `050074f`) records that
`orbit/tickets/` is now a legacy record and no new ticket is created there, while
the same file's §3.1 is the only place the current gate status is written — and
`CLAUDE.md`'s Acceptance-block rule routes a reader to ticket 07 line 847
instead.

### 6. Lifecycle and supersession — EVIDENCED

| reading | written | superseded as the record | lifetime as the record |
|---|---|---|---|
| pre-registration `dc8d743` | 2026-09-11 02:16 | never | current |
| R1 | 2026-09-11 03:05 | `7795ff3`, 03:29 | 24 minutes |
| R2 | 2026-09-11 03:29 | `7931206`, 2026-09-12 02:34 | ~23 hours as spec authority; **still current in ticket 07, ticket 00 and the README** |
| R3 | 2026-09-12 02:34 | not superseded | current in spec 0003/0004/0005 and ticket 17 only |
| R4 | 2026-09-12 20:32 | n/a | tracker only |

**No supersession is marked anywhere in the artefacts.** The observer has a
`supersedes-claim` detector, permanently DECLARED, for exactly this relation
(`orbit/tickets/04-pointers-resolve.md` lines 10, 20; `orbit/README.md` lines 476,
503–505). No prose in `orbit/tickets/` or `orbit/specs/` uses it about any of
these readings.

### 7. Secondary failures — EVIDENCED

1. **One demonstrably false assertion** in R1's Gate B reasoning, against spec
   0001 §6 line 151, which titles the candidate "evidence columns
   (`evidence_class`, `detector`)" (ticket 07 lines 694–700).
2. **R2 introduced a closing condition absent from the pre-registration** (HEAD
   line 579) while correcting R1 for inventing a test after the data.
3. **R2 changed Gate B's instrument** from the registered sample to the
   population (HEAD lines 686–690 against lines 106–108), using figures already
   present in R1's own text.
4. **The drift guard breached because the ticket was written** — 29.6% → 34.0% —
   and R1's first exclusion cut dropped 41 addresses including three names of
   this repository's own files (`7795ff3` body; `test_pointers.py` lines 69–78).
5. **R2 was propagated into a spec as settled** at `33ff76b` ("The Orbit roadmap,
   already decided, recorded so it is not re-argued"), which R3 then had to
   correct.
6. **The same session misread its own record elsewhere**: `050074f` records that
   spec 0003 §5.2's two anchors "were correct but paired by position across a
   sentence break, and reading them in this session paired them backwards".
   Episodes 1 and 2 were swapped; the fix was to give each episode its own row.
7. **The surviving contradictions** (Register 4).

### 8. Repair attempted — EVIDENCED

Register 3. Five repairs across four commits, plus the outward propagation of R3
into three artefacts.

### 9. Evidence the repair held, failed, or is unknown — EVIDENCED

Register 4. Held: four items. Did not hold: ticket 07 lines 130/790/799 beside
523/658/847/856, ticket 00 lines 7–30, README line 1252, and the
`CLAUDE.md` Acceptance-block rule delivering R2 to a reader. Unknown with reason:
three items.

### 10. Estimating effect — UNKNOWN, with reason

Nothing in the record connects either gate to an estimating output. Spec 0003
§1.1 sets the destination as "Orbit reliably usable on the local estate, and the
minimum evidence-backed recomposition needed to resume estimating work"; §12
names "Gate 4 shows no estimating difference between candidates" as a kill
condition; §14 item 2 reserves to Dylan "Which estimating work Gate 4 is measured
on, and what 'a usable estimating decision' means for it". Both gates are Orbit
build decisions (spec 0003 §3 line 192: "Gate A and Gate B are Orbit build
decisions"), and neither column is built. There is therefore no estimating effect
to measure and none will exist before Gate 4 is defined. Recorded as a coverage
gap in the sense of spec 0003 §11 — a result, not a hole.

### 11. Sandcastle cross-reference — EVIDENCED

Probe texts quoted from `orbit/evidence/sandcastle-adr-comparative-archaeology.md`
lines 210, 213, 216. Dispositions are the report's own four; the report's
disposition for each probe's source family is given, then this episode's use.

**SC-A08 — "Real enforcement: every safety claim names the layer that can refuse
the action and includes a failing negative control."** Evidence required for
PASS: "Demonstration that the forbidden operation fails at the claimed boundary;
a presence-only checker must fail review."

*Report disposition of the source decision (ADR-0015, line 94): Independently
corroborated principle.* **This episode: independently corroborated principle.**
The pre-registration is a safety claim — it exists so that "it seemed useful"
cannot be the reason a column gets built (`dc8d743` body). No layer can refuse a
decision that overrides it: no hook, no check, no test, and the review that
caught it ran after the commit landed and was invoked by the same session. The
episode is a failing negative control that was never set up: the forbidden
operation — deciding a gate against its written rule — succeeded twice
(`4b67920`'s derivability test; `7795ff3`'s added closing condition) at the
boundary the rule claimed. Field 4 is the record of it.

**SC-A11 — "Signal honesty: percentages and classified provider failures exist
only when their numerator, denominator, or structured error signal exists."**
Evidence required for PASS: "Missing-denominator and changed-error-message tests
produce `unknown`, not a fabricated percentage or confident class."

*Report disposition of the source decision (ADR-0005b, line 85): Independently
corroborated principle.* **This episode: independently corroborated principle,
with the honest half named.** The 8.0% carries a real 4/50. The per-detector
table (HEAD lines 602–608) reports six rates of 0% at n = 1 to 4 — percentages
whose denominators cannot support them — and the branch that decided Gate B
turns on the shape of that table. The artefact itself states the limit: "a 0%
cell at n=2 establishes very little" (line 689). So the probe finds both the
failure and its own disclosure in one document: the rate was reported as a
per-detector distribution, the distribution was then declared unable to carry
the claim, and a different measurement was substituted without the
pre-registration being re-opened. The estate's own rule for this case exists —
`spec 0002 §5`: "No inference may be recorded as fact. If a rule is a guess, its
output is a guess" — and ticket 07 applies it correctly to the `client` column's
237 UNKNOWN rows (lines 557–562) while the per-detector cells stand as rates.

**SC-A14 — "External-decision provenance: an ADR, observation, or named framework
records document status, implementation status, local semantic mapping, and
adoption status separately."** Evidence required for PASS: "The observer reports
Sandcastle ADR-0007 as documented/unimplemented and ADR-0010 as prose/behavior
drift without calling either a local rule."

*Report disposition (Finding 1, lines 63–67): four confirmed provenance defects,
including "Written does not mean implemented" and "Implemented behavior can
supersede unamended prose".* **This episode: independently corroborated
principle, on the repository's own record rather than on an imported one.** Four
statuses were collapsed and then separated again:

| status | R2's record | R3's record |
|---|---|---|
| rule fired | yes | yes ("The pre-registered rules fired") |
| gate decided | yes | no |
| column scheduled | phase 2 / phase 3 | "Neither column is scheduled" |
| benefit demonstrated | not asked | "undecided until a test shows the addition would be beneficial" |

`33ff76b` wrote the first column as one fact under the heading "already
decided"; `7931206` split it into four. And the report's third defect — prose
superseded by behaviour, unamended — is instantiated literally here: ticket 07's
R1 prose at lines 790 and 799 survives beside the R2 behaviour at 523 and 658,
and both survive the R3 decision, unamended.

### 12. Replay scenario — EVIDENCED, runnable by someone who was not there

All read-only. No repository write, no index run required.

1. Freeze at `dc8d743`. `git show dc8d743:orbit/tickets/07-audit-and-gates.md`
   is the artefact as it stood when the rules were registered and no data had
   been seen.
2. Hand a fresh session (a) that file, (b) the Part 1 and Part 2 measurements and
   the Gate A/Gate B query results from Register 1 above as *given* data it did
   not produce, and (c) nothing else. Ask it to record the two gate decisions in
   the file, against the rules as written.
3. Observe three things, each with a recorded expected value from this episode:
   - **Does the decision use a test that is not in the pre-registration?** R1
     did, twice by its own later admission; R2 did once (HEAD line 579) while
     correcting R1 for it.
   - **Does the decision keep Gate B's registered instrument?** The registered
     instrument is the 50-row sample ("only the sample answers it"). R2
     substituted the population measurement.
   - **When the antecedent is ambiguous — one question missing two columns — does
     the decision say so or resolve it?** R1 said so and then overrode itself;
     R2 resolved it by argument.
4. Then run `.claude/skills/code-review` with `dc8d743` as the fixed point over
   the session's output and record whether the review catches each of the three.
5. **Negative control, which is the part this episode never had:** repeat step 2
   with one sentence added to the pre-registration that names the disposition for
   the two-columns-missing case. If the post-hoc test still appears, the failure
   is not the rule's silence. If it does not, the rule's silence is load-bearing
   and a review arriving after the commit is the only thing standing between the
   rule and the decision.
6. **A second control on the artefact rather than the decision:** hand a session
   the ticket at HEAD and ask it what Gate A's current status is, without naming
   spec 0003. `CLAUDE.md`'s Acceptance rule points at line 847. Record what it
   answers.

### 13. Falsifier — what reading would show this reconstruction does not hold

- **If the `Claude-Session:` trailer is a genuine per-session identifier and all
  62 commits really are one session**, then "the evaluator reviewed itself" is
  not an inference from a constant but a fact, and Register 2's asymmetry
  argument strengthens. **If instead the trailer is template boilerplate and
  `4b67920` and `7795ff3` were written by separate sessions with separate
  context**, then R2's review was independent in the sense its commit claims, and
  this reconstruction's central observation about field 4 — that the reviewing
  instrument belonged to the reviewed session — is wrong.
- **If a transcript exists outside this repository showing that a human directed
  R1's "not built" verdict**, then R1 is an instruction followed rather than an
  evaluator overriding its own rule, and the episode is about recording, not
  about evaluation.
- **If the pre-registration's author states that "the same column is missing each
  time" was always meant to tolerate a question missing additional columns**,
  R4's first ground falls and R2's Gate A branch reading was correct all along.
- **If a detector-stratified 50-row sample at set `1.8eabab386316` reproduces a
  sharp between-detector split**, R4's second ground falls and R2's Gate B
  verdict rested on the registered instrument after all.
- **If lines 790 and 799 of ticket 07, ticket 00 lines 7–30, or README line 1252
  turn out to be intentionally preserved historical text rather than unrepaired
  survivals**, Register 4's central finding is wrong. Against that: the ticket
  marks its two corrections explicitly ("This section is a correction", lines 572
  and 694) and marks nothing at 790 or 799, and `7795ff3`'s own commit body says
  what was got backwards is "recorded in the ticket rather than repaired in
  silence" — a standard those two lines do not meet in either direction.

---

## 7. Field audit — for ticket #10

This episode's evidence is the most complete of the three selected, so an
UNKNOWN here is signal about the contract, not about the record.

### Fitted from evidence — 11 of 13

1 (pre-state commits) · 3 (changed files and graph relationships) · 4 (writer,
reader, enforcing boundary) · 5 (authority and activation path) · 6 (lifecycle
and supersession) · 7 (secondary failures) · 8 (repair attempted) · 9 (evidence
the repair held) · 11 (Sandcastle cross-reference) · 12 (replay scenario) · 13
(falsifier).

Two of these fitted only because the answer was an absence, and both absences
were the finding: field 4's enforcing boundary does not exist, and field 3's graph
relationship is that the artefact is not a node. A contract field that can be
filled by "none, and here is the evidence of none" earned its place here.

### UNKNOWN — 2 of 13

- **Field 2, prompting evidence — partial.** Commit bodies and the issue exist;
  no transcript, no context record, and the one provenance field the commits
  carry (`Claude-Session:`) is a constant across all 62 commits and this session.
  **Strong signal:** in the episode with the most complete evidence, the field
  that records *why* a decision was reached is the field that fails. Every
  measurement survived; not one prompt did. A provenance field that cannot vary
  carries no provenance — which is SC-A14's own point turned on this
  repository.
- **Field 10, estimating effect — total.** Both gates are Orbit build decisions;
  neither column is built; Gate 4's measurement is unwritten and reserved to
  Dylan (spec 0003 §14.2). **Strong signal:** this is not a defect in the record
  but a statement about the program — nothing it has produced has reached
  estimating work, and on the current plan nothing can until Gate 4 is defined.
  If field 10 is UNKNOWN for the same reason in episodes 1 and 2, the field is
  measuring the program's distance from its destination rather than the episode's.

### Fields the contract lacks, that this episode needed

Two. Both are stated as what had to be written outside the 13 fields, not as a
proposal.

1. **The written rule under test, quoted, with the decidability of its
   antecedents on the data.** The contract has field 1 (pre-state commits) and
   field 5 (authority and activation path) but no field that holds *the rule's
   text*. For a reinterpretation episode the rule is the central artefact, and
   the whole of §5's live question turns on one clause of it — "the same column
   is missing each time" — and on the fact that the clause has no disposition for
   the case the data produced. Register 2 could not be written without quoting
   the pre-registration at length, and no field asked for it.
2. **Reading provenance: who read, with what context, and whether independently
   of the reading under review.** Field 4 records the writer of a *file*. This
   episode has four readings of one file and a reviewing instrument that belonged
   to the session it reviewed. The contract's own §5.1 warning — that facts,
   interpretations, repairs and proof are four registers — presumes one
   interpreter; here the interpreters are ordered, overlapping, and
   indistinguishable in the record. Field 6 (lifecycle and supersession) records
   *when* a reading stopped being current; nothing records *who* read it and
   whether they could have been refused.

### One shape observation, not a missing field

Fields 8 and 9 are singular — "Repair attempted", "Evidence that the repair
held". This episode has five repairs across four commits, two corrections of
corrections, and a repair that held in one file and failed in three. Both fields
had to be written as tables. The fields are right; their number is one.

---

## 8. What this fixture does not produce

No target architecture, no responsibility model, no repository layout — spec 0003
§5.3 line 368 ("**It may not produce a target architecture**, a responsibility
model, or a repository layout"). No proposed fix to either gate, to the
contradictory passages, or to the artefacts that still carry R2: spec 0003 §5.3
line 372 ("Nothing is cleaned up while history is being read. Corrections belong
to a ticket of their own, after the episode that found them is recorded") and §3.1's
own rule that writing a benefit test now would be pre-registering after the data.
The surviving contradictions are recorded in Register 4 as evidence and left
exactly where they are.
