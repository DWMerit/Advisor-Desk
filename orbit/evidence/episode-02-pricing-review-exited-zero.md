# Gate 1 fixture — Episode 2: a pricing review that exited successfully after pricing nothing

**Wayfinder research ticket #5, `DWMerit/Advisor-Desk`.**
Built against the 13-field contract in
`/home/user/Advisor-Desk/orbit/specs/0003-estate-archaeology-and-evidence-driven-recomposition.md`
§5.1, and probed with SC-A05 and SC-A06 read at their exact bytes from
`/home/user/Advisor-Desk/orbit/evidence/sandcastle-adr-comparative-archaeology.md`
lines 207–208.

This package produces **no target architecture, no responsibility model, and no
repository layout**, per §5.3. It proposes no fix. Where the record cannot supply a
fact, the field says UNKNOWN and says why.

---

## 0. How this was read, and the limits that puts on it

**All three local checkouts are depth-1 shallow clones.** Verified:

| checkout | HEAD | `git rev-list --count HEAD` | `.git/shallow` |
|---|---|---|---|
| `/home/user/home-system` | `5e4256f9207674410f6f7f2046a6cb426c7495fb` | 1 | contains `5e4256f9…` |
| `/home/user/agent-rules-books` | `782a8860064ff113324582e4af6437893c2f7f84` | 1 | contains `782a8860…` |
| `/home/user/estimating-lab` | `be90aa28856440e7854d2466b95a852751cf9810` | 1 | contains `be90aa28…` |

`git cat-file -t 5ffc8bfb` in `/home/user/home-system` returns
`fatal: Not a valid object name 5ffc8bfb`. **No named anchor commit is present in
any local checkout.** Deepening a clone writes, and these repositories are read-only
for this ticket with two sibling agents live in the same container, so nothing was
fetched. Historical commits and blobs were read through the GitHub read APIs
(`get_commit`, `get_file_contents`, `list_commits`, `list_branches`) and current
state was read from the working trees with `cat`/`sed`/`grep`. No write of any kind
was made in any of the three repositories.

**Line numbers.** Numbers on *current* files are from the working tree at
`5e4256f`. Numbers on *pre-state* files are counted from the blob at
`f55bc3dda5ddf7c0f36a792d9d66b7b97ffad939`, and each one used below is
independently corroborated by a diff hunk header in the repair commit — stated at
the point of use. Nothing here is a line number I could not derive twice.

---

## 1. Anchor verification — the anchor is one of two SHAs for the same change

The report's anchor for this episode (spec 0003 §5.2 table; report line 140) is
Home-system `5ffc8bfb`. Reading it produced a fact the report does not carry.

**`9b7e1c3871b107c27e38b0aa355c6951b65ed519` and
`5ffc8bfb778700de4e0a8af1138a84c1fcea5b4d` are the same change, committed twice.**

| | `9b7e1c3` | `5ffc8bfb` |
|---|---|---|
| commit message | byte-identical | byte-identical |
| author date | `2026-08-31T20:07:44Z` | `2026-08-31T20:07:44Z` |
| committer date | `2026-08-31T20:07:44Z` | `2026-09-01T20:08:40Z` |

`5ffc8bfb` is the SHA that landed on `main`. `9b7e1c3` is the pre-rebase original.
This matters to replay rather than being trivia: the repository's own prose cites
the SHA that is **not** on `main`. The sibling commit
`61ddd1ce00f2e3237f4cc7281249075813d39515` says *"A format-only claim of 'end to
end' contradicts the fail-closed contract landed in 9b7e1c3"* — a pointer that
resolves to no commit reachable from `main`. Anyone replaying this episode from
that sentence lands nowhere.

This is SC-A10's territory (exact SHA versus patch equivalence), not SC-A05 or
SC-A06, and it is recorded as a fact rather than pursued.

## 1a. Two figures in the ticket and the report that the primary sources do not support

- The ticket and report line 90/140 both say **"a 549-line pricing review"**. Every
  primary source says a review **of a 549-line job**: `review/coverage.py:3`, `SKILL.md:44`,
  `tests/test_coverage.py:4`, and the commit message of `5ffc8bfb` all read *"a review
  of a 549-line job"*. 549 is the ConEst line count of the input export, not the
  length of the output. The longest committed review artifact in the repository is
  158 lines (`projects/VA UD OR AHU/reviews/2026-08-24-summary-pricing-review/review.md`).
- The ticket orders the two `agent-rules-books` commits as G-09 (`6a368a2d`) then
  "three checks **later** replaced" (`5001b49f`). The commit dates are the reverse:
  `5001b49f` is `2026-09-01T17:06:43Z`, `6a368a2d` is `2026-09-01T19:38:50Z`. The
  three-check commit came first; G-09's replacement came two and a half hours later.
  `5001b49f` also concerns G-10, G-12, G-13 and G-16 — not G-09.

---

# REGISTER 1 — FACTS

Each item is a thing the record states or a thing I read directly. Nothing here is
inference.

## F1 — What the failing run did

From the commit message of `5ffc8bfb`/`9b7e1c3`, and restated at three separate
addresses that survive at `5e4256f`
(`review/coverage.py:3-8`, `SKILL.md:43-47`, `tests/test_coverage.py:3-5`):

- Date of the failing run: **2026-08-31**.
- `summary_check.py` printed **`61 findings`** and **exited 0** on a **549-line job**
  in which **not one line carried a UPC**.
- Every one of the 61 findings was **structural** — "duplicates, zeroed packages, a
  unit-of-measure fossil" (`review/coverage.py:5`).
- **Not one price was compared, because no price could be** (`review/coverage.py:5-6`).
- `price_list.py` then **matched 19 rows** against a price table **built on a
  different job nine days earlier**, keyed by ConEst item number, and **told the
  estimator to type `+$3,045.11` into ConEst** (`review/coverage.py:6-8`).
- The reason the item-number join is unsafe is recorded concretely: a
  `FILLER TO KEEP MATERIAL AND LABOR SAME` row inserted on one job **shifted every
  hand-typed MISC number after it by one** (`SKILL.md:48-50`; commit message).

## F2 — The two code paths, at their pre-state bytes

Pre-state blob: `f55bc3dda5ddf7c0f36a792d9d66b7b97ffad939` (authored 2026-08-29,
"The grid the estimator actually sends is read, and nothing divides a price twice").
This is the last commit touching either file before the repair.

**F2a. `summary_check.py:174-176` — the bare headline.**

```python
    print('\n%d findings: %s\n' % (len(ranked), ', '.join(
        '%d %s' % (counts[s], s.lower())
        for s in ('Unsized', 'Critical', 'Major', 'Minor', 'Note') if counts.get(s))))
```

No qualifier, no axis name, no coverage figure. Corroborated by the repair's hunk
header `@@ -171,9 +172,29 @@` in `5ffc8bfb`, which removes exactly these three
lines at old 174–176.

**F2b. `summary_check.py:126-129` — the coverage report was conditional on coverage
existing.** This is the fact the commit message does not state and the one I consider
the mechanical centre of the failure:

```python
    with_upc = [r for r in rows if r.get('upc') and str(r['upc']).isdigit()]
    if with_upc:
        print('%d of %d lines carry a UPC -- the join key to a supplier catalogue.'
              % (len(with_upc), len(rows)))
```

The tool **did** know how many lines carried a UPC and **did** have a line of output
for it — but the print is guarded by `if with_upc:`. At zero UPCs the branch is
skipped and the tool says **nothing**. The one number that would have revealed the
review had not run was suppressed precisely in the case where it mattered. Zero
produced silence, and silence was then read as "no exceptions on that axis".

**F2c. `summary_check.py:202` — `return 0`.** `main()` has three `return 2` paths
(unparseable file, non-reconciling totals, wrong report type) and one terminal
`return 0`. Nothing between them consults coverage.

**F2d. `price_list.py:158` — the bare item-number join.**

```python
        entry = prices['items'].get(str(row.get('item')))
```

Corroborated by the repair's hunk header `@@ -154,10 +156,24 @@`, whose ten
unchanged old lines place this statement at 158. The ConEst item number is the whole
of the join; nothing checks that the stored price is for the same product.

Note a small prose/code divergence: the commit message quotes this as
`prices['items'].get(str(row['item']))`; the code is `.get(str(row.get('item')))`.
The described mechanism is unaffected.

## F3 — What the written contract said at the time

At `f55bc3d`, the operator-facing capability declaration
`.claude/skills/cowork-bridge/capabilities.json` listed under `outputs`:

> "A findings list ranked by dollars, each finding tied to a Summary line."

**It made no coverage promise.** There was no rule in the operator contract for the
tool to violate. (Compare F13 below: the coverage promise exists at `5e4256f`, so it
was added after the failure, not broken by it.)

`SKILL.md` at `f55bc3d` already forbade the unguarded description-style match under
Step 4 — *"Fail the gate and the line is reported as unresolved, not priced… Never
relax the floor to raise coverage"* (`SKILL.md:266-268` at `5e4256f`, text unchanged
by the repair). So Step 4's prohibition was **in force in prose and absent from the
code** at `price_list.py:158`.

## F4 — The pre-state commit cannot be pinned to a commit

`.scratch/commitment-moment/run-2026-08-31-bessemer-combined-diagnostic.md:366-369`
(present at `5e4256f`) records, for 2026-08-31:

> "The checkout is currently on `Merit/summary-pricing-review-tuning` with another
> session's uncommitted work, so per **M10** nothing here was committed."

`git ls-remote`-equivalent branch listing shows the tuning branch itself is gone from
`DWMerit/Home-system`, and in its place stand roughly **forty auto-snapshot branches**
named `archive/2026-09-01/rescue/2026-08-31-Merit-summary-pricing-review-tuning-0cae5cb`
through `-37`, plus `-2` … `-35`, plus two dated `2026-09-01`. The practice is
documented: commit `73130542007dc37ddc9fbd9a8ee73f7896f29a4a` (2026-08-28) says its
content was *"byte-identical to the rescue/…-0cae5cb-4 auto-snapshot, verified blob
by blob"*.

So the failing run executed a **dirty shared checkout on a branch that no longer
exists**, snapshotted into ~40 rescue refs. `f55bc3d` is the pre-state of the two
*files*, verified at their bytes; it is not established to be the pre-state of the
*process*.

## F5 — The failing run's own output is not in git, by construction

- `.gitignore:88` is `.prototypes/`, and `.prototypes/` is where `summary_check.py`
  writes `<job>-findings.json` (`summary_check.py:55` at `f55bc3d`:
  `DEFAULT_OUTPUT_DIR = '.prototypes'`). The rescue snapshots were taken with git,
  so they carry no ignored path: listing
  `.claude/skills/summary-pricing-review/` on
  `archive/2026-09-01/rescue/2026-08-31-Merit-summary-pricing-review-tuning-0cae5cb-37`
  returns eleven tracked entries and no `.prototypes`.
- `CORPUS.md` (tracked, at `5e4256f`) states the corpus root is
  `C:\HITL-MERIT\Bid Summary\`, that it is "not a git working tree, not a worktree,
  and not a checkout", and that it holds `validation/` (the real-corpus tests and the
  private job table — "**GONE. Not in any reachable commit.**"), `live_prices.json`,
  and `prior-reviews/` — "the review journal and the raw outputs of earlier runs".
- Commit `6311410b0645e992f7efec76109059ffa07bfa4f` (2026-08-31) records the standing
  rule that `.scratch/` run records are *"tuning and diagnostic evidence"* and are
  **deliberately not landed**.

The consequence is stated once here and referenced by the UNKNOWN fields below:
**the 549-line export, the 61 findings, the nine-day-old price table, the 19 matched
rows and the `+$3,045.11` instruction exist only outside every git tree, or only as
the repair commit's own summary of them.**

## F6 — No independent record of the episode exists

- `knowledge/experience/incidents/` holds `INC-0001` … `INC-0016` plus an example.
  Its `INDEX.md` frontmatter and rows show it is an **estimating-domain** register
  (takeoff, procurement, turnover, front end). **No incident was logged for the
  2026-08-31 pricing-review failure.** The nearest in subject is `INC-0015 —
  absent and zero are the same line in a takeoff` (2026-08-21), which is about a
  takeoff quantity column, not about this tool.
- No `.scratch/` folder for the pricing-review tuning session exists on
  `Merit/preserve-worktree-20260901-spr-tuning`; that branch's `.scratch/` listing
  has 41 entries and none of them is this work.
- A repository-wide grep for `3,045.11`, `549-line`, `549 line` and `61 findings`
  across `/home/user/home-system` returns hits at exactly five lines, all inside the
  repair itself: `SKILL.md:44`, `review/coverage.py:3,4,8`, `tests/test_coverage.py:4`.

**The repair is the sole surviving record of the failure it repairs.**

## F7 — The repair, as committed

`5ffc8bfb` (= `9b7e1c3`), authored 2026-08-31T20:07:44Z, +506 / −7 across six files:

| file | status | +/− |
|---|---|---|
| `review/coverage.py` | added | +192 |
| `tests/test_coverage.py` | added | +185 |
| `price_list.py` | modified | +67 |
| `SKILL.md` | modified | +31 |
| `summary_check.py` | modified | +24 / −3 |
| `tests/test_price_list.py` | modified | +7 / −4 |

Mechanism, at the bytes:

- **Four named verdicts, not a boolean** — `coverage.py:30-33`: `OK`, `NO_UPC`,
  `NO_TABLE`, `NO_COMPARISON`, each with its own remedy string in `REMEDY`
  (`coverage.py:35-49`) "because each one has a different remedy and they are not
  interchangeable".
- **The gate sets the exit code at the command boundary** —
  `price_list.py:266-287`: `cover = coverage.assess(...)`; `if not cover.ran:` print
  `cover.refusal()` to stderr and `return 3`. The comment states the property:
  *"Nothing below this point runs on a failed run — the refusal IS the output."*
  `coverage.py:15-18` states why it is not a flag: *"advice loses to a headline…
  a caller cannot print a completed review over a failed one without deleting this
  call — which is visible in a diff, where a missing warning is not."*
- **Identity before arithmetic** — `coverage.usable_reference()`
  (`coverage.py:52-76`), called at `price_list.py:171`. A stored price is usable only
  if its UPC equals the row's UPC. A stored entry with **no** UPC is refused as
  UNVERIFIED. Refusals are collected in `withheld` and printed per line
  (`price_list.py:278-286`), "reported per line, never silent".
- **Zero is defined, not inferred** — `coverage.normalise_upc()`
  (`coverage.py:78-91`) returns `None` for blank, non-digit, and all-same-digit
  codes, because "a UPC of all zeros is not a data-entry failure — it is how ConEst
  marks a labour line. Counting those as join keys is what turns a real coverage
  figure into a fake one."
- **The refusal carries its own evidence** — `Coverage.summary_lines()`
  (`coverage.py:138-169`) is printed on a failed run too: *"`0 of 549` is the evidence
  for the refusal, and a refusal with no numbers under it reads like a crash."*
- **The structural axis is demoted, not removed** — `summary_check.py:186-196`:
  at zero UPCs it prints `!! NO LINE ON THIS JOB CARRIES A UPC -- THE PRICE AXIS
  CANNOT RUN.` to stderr and labels stdout
  `%d INCIDENTAL structural findings (price axis did not run)`.
- **A negative control** — `tests/test_coverage.py:138-158`, class `NegativeControl`:
  `test_zero_upc_many_findings_still_cannot_run` builds 549 UPC-less rows and asserts
  `NO_UPC`, `not cover.ran`, `lines_with_upc == 0`, `dollars_compared == 0.0`, and a
  non-`None` refusal. `test_structural_findings_cannot_change_the_verdict` asserts,
  61 times in a loop, that *"there is no path from a finding count to `ran`"*.
- **A command-boundary test** — `tests/test_coverage.py:198-218`, class `EndToEnd`:
  runs `price_list.py` as a subprocess on a zero-UPC fixture and asserts
  `returncode == 3`, `'CANNOT RUN' in stderr`, and
  `'TYPE THESE INTO CONEST' not in stdout`.
- Stated verification in the commit message: the zero-UPC corpus job exits 3 and
  emits no ENTER instruction; a 954-line grid `.txt` reports 628 usable UPCs and
  routes on; **265 tests pass**.

## F8 — A secondary failure of the same shape, found ten minutes later

`61ddd1ce00f2e3237f4cc7281249075813d39515`, authored **2026-08-31T20:17:05Z** — ten
minutes after the repair. Title: *"The inventory called five jobs reviewable that the
gate refuses."*

- `corpus_manifest.py` decided `reviewable` from the **file format alone**
  (`'price check' in supports`) and headlined **"5 jobs known, 5 reviewable end to
  end"** for a corpus in which every job carries no join key and the new
  `coverage.py` refuses all five with `NO_UPC`.
- The inspect loop hit `if fmt == 'grid-copy': continue` **before reading the file**,
  so the one shape that does carry the UPC had its UPCs never counted at all.
- `_completeness()` printed *"identity only — a grid copy averages every phase"* as
  the blocker for **every** unreviewable job: the right reason for one of them and a
  wrong explanation for a narrow print with no UPC column.
- Fixed by splitting `readable` from `reviewable`, naming `pricing_reviewable()`
  (`corpus_manifest.py:91` at `5e4256f`) and having it count UPCs with
  `coverage.normalise_upc` — "the same definition the runtime gate uses, so the two
  cannot drift apart again". Headline moves from "5 reviewable" to
  **"5 PARSE; 1 can run the PRICE AXIS"** (`corpus_manifest.py:315-316`).
- +123 / −19 across `corpus_manifest.py`, `price_list.py`, `review/coverage.py`,
  `tests/test_coverage.py`. **270 tests pass.** Five new tests
  (`tests/test_coverage.py:160-195`, class `ManifestAgreesWithTheGate`) assert that
  for any UPC count the manifest and the gate give the same answer.

## F9 — The same mechanism, four days earlier, in another repository

`Estimating-Lab 020383dee21f9140939d559231177d6ebed32f82`, authored
**2026-08-27T14:03:30Z** — four days *before* the pricing episode, not after:

> "One of its eight checks exists only to assert that the note count is IDENTICAL
> across the fix, because note counts are what the rotation-independent rewrite was
> validated on, and swallowing a keyplan into a note body does not change one."

Also in that commit: a figure carried since 2026-08-25 — *"34 blocks / 34 clean cuts
is really 33 and 32"* — had been copied into a docstring, a backlog row and an
experiment, *"each copy reading as corroboration of the others"*. And
`test_notes_panel.py` replaced a single tuned band height with a sweep of 45,
because *"a tuned height proves a label appears somewhere; it cannot prove the
invariant holds wherever the break lands"*.

## F10 — The same mechanism in the checker layer

- **`agent-rules-books 6a368a2da916843526d84aa6e9daa079f67acc9f`**,
  2026-09-01T19:38:50Z. *"G-09's check was the defect G-09 is named after."* The
  entry titled *"A test can agree with the defect it was written against"* had as its
  check **a grep for the string `--path`**: *"It proved the file mentioned the pin. It
  could not have proved anything fails without it."* Replaced with a behavioural
  check that clones Home-system into a throwaway, drops the `* text=auto eol=lf` pin,
  forces `core.autocrlf` and **requires the suite to fail**, with both controls
  present. Measuring it **falsified the entry's own premise**: 46 passed / 0 failed as
  checked out; 45 passed / 1 failed and **628 CR bytes** with the pin dropped.
  Two further finds in the same commit: `test_register.py`'s default set path was
  stale by one directory segment so **the suite silently skipped every test and
  exited 0 — a zero-subject test suite**; and the first draft's CR detector used
  `grep`, which on MSYS strips the CR, so it *"reported no CR bytes while `od` showed
  1209"* and *"would have read `exit 2` forever"*.
- **`agent-rules-books 5001b49f8754fcb35cc4cc00ef068052be7c007f`**,
  2026-09-01T17:06:43Z. G-10, G-12, G-13 given behavioural replacements that
  *"read OPEN by running the thing rather than grepping for it"*. Two mechanical
  corrections, both squarely in this episode's shape: (i) `python3` reached the
  Microsoft Store shim, which returns 49 for every invocation, so **G-10's two probes
  failed identically, identical failure read as "both refused", and the check exited
  0 — "a false CLOSE, the one defect the register cannot carry, produced by the check
  written to prevent it"**; (ii) **G-10 had a positive control and no negative one**
  — *"A benign command must also be shown NOT refused, or a broken harness is
  indistinguishable from a working guard. Added."* And G-16's first draft *"sampled
  one pull request and passed… the fourth check today to pass for the wrong reason"*,
  widened to all 7 open PRs.
- **`agent-rules-books 8aa0b8523b34a291fd4aeb809588c0bdabfbd475`**,
  2026-08-31T12:12:11Z — the same-day contrast the report cites. Live acceptance was
  attempted and **did not run**; the record now says so **in its own section** rather
  than leaving a reader to infer it. The one thing measured is kept and explicitly
  scoped as *"not evidence about the reload path"*, and six outstanding live checks
  are listed.
- **`Merit-knowledge 77d812f3cac6e46162eaadb530c7c80304775a07`**,
  2026-08-28T19:08:50Z — completes the report's Episode C chain (report line 145) and
  is not named in the ticket. `./check.sh` had printed `boundary holds` and exited 0
  since it grew a success path, but `README.md` and the script's own header comment
  *"still told a reader to expect nothing on stdout"*. Wording only; both sites made
  to match `contracts/INDEX.md` L34, which already owned the rule.

## F11 — The enforcing boundary that exists

`.github/workflows/scripts.yml:168-170` (at `5e4256f`):

```yaml
      - name: Summary pricing review suite
        working-directory: .claude/skills/summary-pricing-review
        run: python -m unittest discover -s tests -p "test_*.py" -v
```

The surrounding comment (lines 154–167) records that the cwd is the skill directory
because `tests/test_audit.py` imports `review` at module scope, and that discovering
from the repository root *"loses one module and reports 225 of 264 tests as a pass"*.

## F12 — State of the repair at `5e4256f` (HEAD, authored 2026-09-04)

Read from the working tree, not inferred:

- `review/coverage.py` — **201 lines**, present. `OK`/`NO_UPC`/`NO_TABLE`/`NO_COMPARISON`
  at 30–33; `usable_reference` at 52; `normalise_upc` at 78; `verdict` at 123; `ran`
  at 135; `refusal` at 170; `assess` at 180.
- `price_list.py` — `from review import coverage` at 36; `usable_reference` call at
  171; the acceptance gate at 269–287 ending in `return 3` at 287.
- `summary_check.py` — the zero-UPC stderr banner at 186–191 and the `INCIDENTAL`
  label at 192.
- `tests/test_coverage.py` — **223 lines**; `NegativeControl` at 138;
  `ManifestAgreesWithTheGate` at 160; `EndToEnd` at 198 with
  `assertEqual(out.returncode, 3, …)` at 217.
- `SKILL.md:23-53` — the gate documented as a section of the skill, including the
  verdict/remedy table at 31–36, *"This is not a warning, it is the exit code"* at
  43, and the 2026-08-31 incident recorded in the prose at 44.
- `review/coverage.py` has exactly **two** commits in its history: `5ffc8bfb` and
  `61ddd1ce`. It has not been touched since 2026-08-31.

## F13 — `summary_check.py` still exits 0 on a zero-UPC job

`grep -n "return [0-9]" summary_check.py` at `5e4256f` returns `98: return 2`,
`107: return 2`, `138: return 2`, `223: return 0`. There is no `return 3` and no
coverage-dependent exit in `summary_check.py`. The repair changed **what that command
says** (stderr banner, `INCIDENTAL` label) and left **what it returns** unchanged.
The nonzero refusal lives only in `price_list.py`, the last command of a five-step
pipeline. `SKILL.md:39-41` states this arrangement deliberately:

> "Anything but `OK` and `price_list.py` prints `STOP — SUMMARY PRICING REVIEW CANNOT
> RUN`… and **exits 3**. `summary_check.py` labels its output `INCIDENTAL structural
> findings (price axis did not run)` rather than a bare finding count."

## F14 — The operator-facing contract changed after the failure

`.claude/skills/cowork-bridge/capabilities.json:25` at `5e4256f`, under `outputs`:

> "A stated coverage number. Until every identifiable line has been looked up,
> \"checked and fine\" is a silence that has not been earned."

At `f55bc3d` this line does not exist (see F3). **Which commit introduced it is
UNVERIFIED**: the path-filtered commit listing for that file returns only
`96c8cedf` (2026-08-26) and `3ae51434` (2026-08-28), neither of which contains the
line, while the file plainly differs between `f55bc3d` and `5e4256f`. The listing is
incomplete and I did not close the gap.

---

# REGISTER 2 — INTERPRETATIONS

Labelled as readings. Each one names the facts it rests on and is falsifiable by the
falsifier in field 13.

## I1 — The failure was a suppressed denominator, not a missing check

The tool already computed UPC coverage (F2b). It had a sentence for it. The defect
was that the sentence was printed **only when the number was non-zero**. On the
axis that matters — was there anything to price? — the tool was articulate about
every value except the one that meant "nothing". `61 findings` was then the only
quantity on screen, and a quantity reads as a result. I take this to be the precise
sense in which SC-A05's four terms collapsed: *zero* became *silence*, and *silence*
became *completed*.

## I2 — Two independent absences were rendered as one result

The commit message calls both halves *"the same mistake: an absence of evidence
rendered as a result"* (`coverage.py:10`). I read them as distinct and
independently sufficient:

- **Absence of a join key** rendered as a finding count (F2a, F2b).
- **Absence of a licensed identity** rendered as a dollar instruction (F2d): the
  item number was treated as sufficient identity, so a table from another job nine
  days earlier produced 19 matches and `+$3,045.11`.

Either alone would produce a review that priced nothing while reporting something.
Together the second made the first *actionable*, which is what turned a
reporting defect into a money instruction.

## I3 — The pipeline shape put the gate at the far end

`summary_check.py` is step 1 of five (F13; `capabilities.json` `invoke.pipeline`, five
commands). The nonzero refusal is at step 5. My reading: the exit-code semantics were
attached to the command that *produces the price report*, and the command that a
person actually runs first — and reads first — still returns 0. The repair's own
comment at `summary_check.py:179-183` says as much: *"THIS COMMAND IS STEP 1 OF FOUR
AND MUST NEVER READ LIKE THE REVIEW"* (note: "FOUR", where the declaration says
five). Whether a caller that runs only step 1 and branches on `$?` is a real caller
is not established by anything I read.

## I4 — The mechanism is not specific to pricing

F9 and F10 show four instances in three repositories inside six days of one
mechanism: **a measurement that could not have failed, accepted as validation.**
Note counts invariant across the fix being tested (F9). A grep for prose standing in
for a behavioural guard (F10, G-09). Two probes failing identically read as "both
refused" (F10, G-10). One PR sampled standing for all PRs (F10, G-16). A test suite
skipping every test and exiting 0 (F10). And, here, 61 structural findings standing
in for a price comparison. In each case the reported quantity was **orthogonal to
the property being asserted**. This is an observation about frequency and shape; it
is explicitly **not** a proposed responsibility boundary, which is Gate 2's question.

## I5 — Why the report's Episode C chain hangs together

The report pairs this episode with `8aa0b852` as a **contrast** (F10): the same
week, the same author, the same class of question — did the thing run? — and the
opposite outcome, because the record was written to say *attempted and did not run*
in its own section. I read the pair as the report's evidence that the capability to
report an honest nothing existed in the estate at the time, and was applied unevenly
across surfaces rather than absent.

## I6 — Why the repair reads as durable rather than as a patch

`coverage.py` has not been edited since the day it was written (F12), the gate is
load-bearing for a second component that was corrected to agree with it (F8), CI runs
its suite (F11), and the negative control encodes the original numbers — 549 rows, 61
iterations — so the specific historical case is asserted rather than described (F7).
This is a reading of the shape of the evidence, not a measurement of durability.

---

# REGISTER 3 — REPAIRS ATTEMPTED

Chronological. Each entry is what was *attempted*; whether it held is Register 4.

| # | when | what | where |
|---|---|---|---|
| R1 | 2026-08-31T20:07:44Z | **The acceptance gate.** `review/coverage.py` added: four named verdicts, per-verdict remedies, `usable_reference()`, `normalise_upc()`, `Coverage.summary_lines()`, `Coverage.refusal()`. Consulted at the command boundary in `price_list.py`, setting exit code 3. `summary_check.py` labels structural output `INCIDENTAL` at zero UPCs. `SKILL.md` gains the gate as doctrine with the incident recorded in it. `tests/test_coverage.py` added with the negative control and a subprocess end-to-end assertion. `tests/test_price_list.py` fixtures gain UPCs. | Home-system `5ffc8bfb` (= `9b7e1c3`) |
| R2 | 2026-08-31T20:17:05Z | **Making a second component agree with the gate.** `readable` and `reviewable` split; `pricing_reviewable()` named so it can be asserted, counting UPCs through `coverage.normalise_upc`; the `grid-copy` early-`continue` removed so the one format carrying UPCs is parsed for them; `_completeness()` made to name the actual blocker; every unqualified "net variance" label qualified. Five tests assert manifest and gate agree for any UPC count. | Home-system `61ddd1ce` |
| R3 | 2026-09-01T17:06:43Z | **Negative control added to a guard-check that had only a positive one** (G-10), interpreter resolved so two probes cannot fail identically, G-16's single-sample check widened to every open PR. | agent-rules-books `5001b49f` |
| R4 | 2026-09-01T19:38:50Z | **A presence-grep checker replaced with a behavioural one carrying both controls** (G-09): clone, drop the pin, force `core.autocrlf`, require failure; either control giving the wrong answer exits 2. Byte-counting CR detector replacing `grep`. | agent-rules-books `6a368a2d` |
| R5 | 2026-08-27T14:03:30Z (prior) | **A can't-fail count retired as validation**: regressions added that fail against copies with the fix removed (2 of 5, 3 of 8); a tuned band height replaced with a 45-height sweep; the miscarried 34/34 figure recounted to 33/32. | Estimating-Lab `020383de` |
| R6 | 2026-08-28T19:08:50Z (adjacent) | **"Empty output means success" prose corrected** to match a script that prints an explicit positive statement. Wording only; exit codes untouched. | Merit-knowledge `77d812f3` |

**Not attempted, on the evidence:** no incident record was filed (F6); no change was
made to `summary_check.py`'s exit code (F13); no migration of the legacy price table
was performed — the commit message states *"this needs no migration — only the legacy
table re-run"*, and whether that re-run happened is not in any tracked file.

---

# REGISTER 4 — EVIDENCE THE REPAIR HELD, FAILED, OR REMAINS UNKNOWN

## HELD — with evidence

| claim | evidence |
|---|---|
| The gate is still in force 4 days later, at `5e4256f` | `review/coverage.py` present, 201 lines, verdicts at 30–33; `price_list.py:269-287` still calls `coverage.assess` and `return 3`; `price_list.py:171` still calls `usable_reference` (F12) |
| The gate survived without erosion | `review/coverage.py` has **exactly two** commits in its history and none after 2026-08-31 (F12) |
| The negative control is still asserted, not merely described | `tests/test_coverage.py:138-158` — 549 UPC-less rows asserted `NO_UPC`; a 61-iteration loop asserting no path from a finding count to `ran` (F7, F12) |
| The gate is proved where a caller meets it, not only in a unit | `tests/test_coverage.py:198-218` runs `price_list.py` as a subprocess and asserts `returncode == 3`, `CANNOT RUN` on stderr, and **no** `TYPE THESE INTO CONEST` on stdout (F7) |
| Some layer can refuse | CI step `.github/workflows/scripts.yml:168-170` runs the suite on every push (F11) |
| The gate had enough force to correct a second component | `61ddd1ce` was written **because** `corpus_manifest.py` contradicted the gate, and the correction routes through `coverage.normalise_upc` so the two definitions cannot drift (F8) |
| Test counts moved in the direction claimed | 246 at `f55bc3d`-era (message of `b10745b5`), **265** at `5ffc8bfb`, **270** at `61ddd1ce`, CI comment referencing 264 (F7, F8, F11) |
| The doctrine layer was updated, not just the code | `SKILL.md:23-53` carries the gate, the verdict/remedy table and the dated incident (F12) |
| The operator-facing contract now requires a coverage number | `capabilities.json:25` at `5e4256f`, absent at `f55bc3d` (F14) |

## FAILED, or held only partly — with evidence

| claim | evidence |
|---|---|
| **The "exited 0" half is not closed at the command where it was observed.** `summary_check.py` — the command that printed `61 findings` and exited 0 — **still exits 0** on a zero-UPC job. Only its text changed. | `summary_check.py` return codes at `5e4256f`: `98`, `107`, `138` → 2; `223` → 0. No `return 3`. `SKILL.md:39-41` describes this as the design (F13) |
| **The same mechanism was still live elsewhere in the same tool ten minutes after the repair**, headlining "5 jobs known, 5 reviewable end to end" for five jobs the gate refuses. The gate did not prevent the adjacent claim; it made it *detectable*. | `61ddd1ce` commit message and stats (F8) |
| **The gate's own reachability was near-missed by the format shortcut it was written to kill**: `if fmt == 'grid-copy': continue` exempted the one format that carries the join key, "left in place for the one shape that actually carries the join key". | `61ddd1ce` commit message (F8) |
| **No incident was recorded**, so the episode is retrievable only from the code that fixes it. | `knowledge/experience/incidents/INDEX.md` + directory listing; five-line repository-wide grep (F6) |
| **The estate-wide prose pointer is broken**: `61ddd1ce` cites `9b7e1c3`, which is not reachable from `main`. | §1 |

## UNKNOWN — with the reason it is unavailable

| question | why unavailable |
|---|---|
| Did the estimator type `+$3,045.11` into ConEst? Was the bid submitted carrying it? | No incident record (F6); the review journal `prior-reviews/` lives outside every git tree (F5, `CORPUS.md`); no project `reviews/` folder for 2026-08-31 pricing exists (`projects/*/reviews/` listing shows 2026-08-24/28 pricing reviews and 2026-08-31 *commitment* passes only) |
| Which job the 549-line export was, and whether it was a live bid | The export is a business source document that "never was in git" (`CORPUS.md`); `.prototypes/` is gitignored (F5) |
| The prompt, session id, or transcript of the failing run | The checkout was shared and dirty on a branch since deleted (F4); `.scratch/` run records are deliberately not landed (F5, `6311410b`); no `.scratch/` folder for this session exists on the preserved worktree branch (F6) |
| Whether the legacy price table was re-recorded with UPCs, as the commit says is required | `live_prices.json` and the job tables live outside the tree (`CORPUS.md`); no tracked file records the re-run |
| Whether the gate has ever fired on a real job since 2026-08-31 | Real-corpus results are asserted inside `validation/`, which `CORPUS.md` states is "**GONE. Not in any reachable commit.**" Only the commit message's own statement ("the zero-UPC job now exits 3… a 954-line grid `.txt` reports 628 usable UPCs") attests it, and that is the repairer reporting on the repair |
| Which commit added the coverage promise to `capabilities.json` | Path-filtered commit listing returned two commits, neither containing the line; gap not closed (F14) |
| Whether `265`/`270` tests actually pass at `5e4256f` | Not measured. Running `python -m unittest` inside the checkout would create `__pycache__` and possibly `.prototypes/` **inside a read-only repository shared with two concurrent agents**, which this ticket forbids. The figures above are the commits' own claims plus CI's existence, not an observation |

---

# THE 13 FIELDS

## 1. Pre-state commits

**PARTIAL — evidenced at the file level, UNKNOWN at the process level.**

- **Files:** `f55bc3dda5ddf7c0f36a792d9d66b7b97ffad939` (authored 2026-08-29T16:17:01Z)
  is the last commit touching `summary_check.py` or `price_list.py` before the repair,
  and both defective code paths are present at its bytes: `summary_check.py:126-129`,
  `:174-176`, `:202`; `price_list.py:158` (F2). Corroborating the choice of this
  commit as the estate's own reference point: a branch named
  `Merit/reconcile-on-f55bc3d` exists in `DWMerit/Home-system`.
- **Process: UNKNOWN.** The run executed a **dirty shared checkout** on
  `Merit/summary-pricing-review-tuning`, which no longer exists, carrying another
  session's uncommitted work (F4). The bytes executed on 2026-08-31 are not
  established to be `f55bc3d`'s bytes. ~40 `rescue/2026-08-31-…-0cae5cb-*` snapshot
  branches exist and were not each read; identifying which snapshot (if any) matches
  the run would be a distinct piece of work.
- **Earlier chain, for context:** `5e335bb2` (2026-08-26, the skill moves into
  Home-system from the Lab), `73130542` (2026-08-28, the price-table writer that
  gave a live run somewhere to land — itself recovered from the shared checkout),
  `3ae51434` (2026-08-28, the capability becomes a five-step pipeline),
  `f55bc3d` (2026-08-29).

## 2. Prompting evidence

**UNKNOWN, with reason.** No prompt, session identifier, transcript, or user
instruction for the 2026-08-31 run survives in any reachable commit. Three
independent mechanisms account for it: `.scratch/` run records are by standing rule
*"tuning and diagnostic evidence"* that is deliberately not landed (`6311410b`, F5);
the session's checkout was shared and dirty so *"per M10 nothing here was
committed"* (F4); and `Merit/preserve-worktree-20260901-spr-tuning` carries no
`.scratch/` folder for this work (F6). The only prompting-adjacent fact recoverable
is the trigger surface itself: `SKILL.md`'s frontmatter lists the phrases that
activate it — *"review the summary", "check the summary pricing", "did you review
the summary", "update the commodities"* — and `ask-merit/SKILL.md:51` routes
*"review the summary" / "did you update the commodities"* to `/summary-pricing-review`
at Stage 6, after net pricer and recalculate.

## 3. Changed files, and the graph relationships around them

**EVIDENCED.**

Repair `5ffc8bfb` — six files (F7 table). Follow-on `61ddd1ce` — four files (F8).

Relationships, read from the code at `5e4256f`:

- `review/coverage.py` is imported by `price_list.py:36`, `summary_check.py:56`, and
  `corpus_manifest.py` (via `coverage.normalise_upc` at `:221`, `:235`, `:258`) —
  **one definition of "a usable UPC" consumed by three commands.**
- `price_list.py` consumes `summary_check.py`'s output file
  (`.prototypes/<job>-findings.json`) and `record_lookups.py`'s price table; the
  pipeline order is declared in `capabilities.json` `invoke.pipeline` (five steps).
- `tests/test_coverage.py` → `review/coverage.py` (unit) and → `price_list.py`
  (subprocess, `:198-218`).
- `.github/workflows/scripts.yml:168-170` → `tests/`.
- `SKILL.md:23-53` → `review/coverage.py` by name; `capabilities.json:6` →
  `SKILL.md` as its declared `source`.
- Doc-side readers: `knowledge/purchasing/remarcable.md:80`,
  `knowledge/purchasing/INDEX.md:28`, `projects/INDEX.md:25`,
  `docs/leadership-brief/INVENTORY.md:48,84`, `.claude/tools/INDEX.md:129`.
- **Known dangling edge:** `61ddd1ce`'s message → `9b7e1c3`, unreachable from `main` (§1).

## 4. Writer, reader, and enforcing boundary

**EVIDENCED.**

- **Writer of the defect:** commits `73130542` / `f55bc3d`, author
  `DWMerit <dw@megpgh.com>` / `<dylanawatkins@gmail.com>`, `Co-Authored-By: Claude
  Opus 5`. The bare headline at `summary_check.py:174` and the bare join at
  `price_list.py:158`.
- **Reader of the defect:** the estimator, via `summary_check.py` stdout and, at
  step 5, `price_list.py`'s "TYPE THESE INTO CONEST" total. The capability is
  additionally published to a Cowork operator through
  `cowork-bridge/capabilities.json`, whose `reachable_from_cowork` field records
  that the whole pipeline ran from Cowork exactly once, on 2026-08-28.
- **Enforcing boundary, pre-state: none.** `SKILL.md` Step 4 forbade the ungated
  description-style match in prose (F3) and no code consulted it. No exit code, no
  test, no CI assertion, no schema field bore on coverage.
- **Enforcing boundary, post-state:** `price_list.py:276-287` (process exit code 3)
  is the layer that can refuse. Below it, `tests/test_coverage.py` and
  `.github/workflows/scripts.yml:168-170` refuse the *removal* of the refusal.
  `coverage.py:15-18` states the design intent of putting it there rather than in
  a report field.
- **Still unenforced:** `summary_check.py` exit code (F13).

## 5. Authority and activation path

**EVIDENCED.**

1. **Session-open authority:** none. The skill is not loaded at session start; it is
   activated by trigger phrase from its own frontmatter `description`, which ends
   *"Load this before reading any summary, not after."*
2. **Routing authority:** `ask-merit/SKILL.md:51` maps two phrases to the skill at
   estimating Stage 6.
3. **Doctrine authority:** `SKILL.md` is the Code-side adapter. Post-repair it
   carries the gate at `:23-53`; pre-repair it carried Step 4's identity rule with
   no mechanism behind it (F3).
4. **External-publication authority:** `cowork-bridge/capabilities.json` is the
   *source* of the Cowork adapter — its `_comment` states *"publish.py renders it,
   nothing hand-edits the generated pack"* and *"Adding a capability means writing
   its entry here, not copying a skill"*. `.scratch/cowork-bridge/SCAIFE-PROOF.md:167`
   records `summary-pricing-review` as **the only published capability**, and that
   its adapter *"has not been read by an operator working a live summary"*.
5. **Runtime authority over the verdict, post-repair:** `coverage.Coverage.verdict`
   (`coverage.py:123-132`), consumed at `price_list.py:276`. One property decides,
   and it is a process exit code rather than a field in a document.

## 6. Lifecycle and supersession

**EVIDENCED.**

- Skill moves Lab → Home-system, 2026-08-26 (`5e335bb2`); Home-system declared the
  source and the Lab stripped.
- Price-table writer lands, 2026-08-28 (`73130542`), recovered from the shared
  checkout.
- Capability re-declared from one `executable` to a five-step `pipeline`,
  2026-08-28 (`3ae51434`).
- PR **#217** (branch `Merit/hempfield-pricing-summary-5ca23a`) **closed with an
  explicit ruling that it must not be merged, now or later** — recorded in
  `b10745b5` (2026-08-31T19:52:41Z). `f55bc3d` is its *"clean successor… built from
  current main"*. The branch still exists, unmerged.
- Failing run, 2026-08-31. Gate lands 20:07:44Z (`5ffc8bfb`/`9b7e1c3`). Manifest
  corrected 20:17:05Z (`61ddd1ce`).
- **No supersession of the gate.** `review/coverage.py` has two commits and none
  after 2026-08-31 (F12); it is intact at `5e4256f` four days later.
- Adjacent supersession in the same estate, for calibration: `f0b5ce03`
  (2026-09-01) retires `.githooks/pre-push` because *"it never once ran"* and *"a
  guard that reads as live while enforcing nothing is worse than no guard, because
  it gets cited."*

## 7. Secondary failures

**EVIDENCED — three, all in the record.**

1. **The inventory contradicted the gate** (`61ddd1ce`, ten minutes later):
   "5 jobs known, 5 reviewable end to end" against a corpus the gate refuses five
   times with `NO_UPC` (F8).
2. **The format shortcut inside the counting code** (`61ddd1ce`): `if fmt ==
   'grid-copy': continue` before reading the file, so the one export that carries
   the join key never had its UPCs counted — *"the same 'what a format can carry is
   not what this file does carry' mistake the discard was written to fix, left in
   place for the one shape that actually carries the join key"* (F8).
3. **A wrong reason attached to a right refusal** (`61ddd1ce`): `_completeness()`
   printed "identity only — a grid copy averages every phase" for **every**
   unreviewable job, *"the reason for one of them and a wrong explanation for a
   narrow print with no UPC column"* — and the two have different remedies (F8).

A fourth, adjacent and in the same class though not in this tool:
`61ddd1ce` cites a SHA unreachable from `main` (§1).

## 8. Repair attempted

**EVIDENCED.** See Register 3, R1–R6. R1 and R2 are this episode's repairs; R3–R6
are the same-mechanism repairs the report names as the rest of Episode C's chain,
one of which (R5, Estimating-Lab `020383de`) **precedes** this episode by four days.

## 9. Evidence that the repair held, failed, or remains unknown

**EVIDENCED, in all three directions.** See Register 4: nine held-claims with
addresses, five failed-or-partial claims with addresses, and six UNKNOWNs each with
the mechanism that makes it unavailable.

The one-line summary a replayer needs: **the headline half of the failure is closed
with a negative control and CI behind it; the exit-code half is closed at the last
command of the pipeline and not at the command where it was observed.**

## 10. Estimating effect

**PARTIAL.**

- **Evidenced:** the tool produced a specific, actionable, unlicensed money
  instruction — **19 rows matched against a table from a different job nine days
  earlier, totalling `+$3,045.11` presented for typing into ConEst**
  (`review/coverage.py:7-8`). The identity basis for those 19 matches was the ConEst
  item number, which the same source records as unstable across jobs by a concrete
  mechanism: a `FILLER TO KEEP MATERIAL AND LABOR SAME` row shifting every
  hand-typed MISC number after it by one (`SKILL.md:48-50`).
- **UNKNOWN:** whether the estimator typed it; whether the bid went out carrying it;
  what the job was; whether it was won or lost. Reasons in Register 4 — no incident
  record, the review journal and the export both live outside every git tree, and
  `.prototypes/` is gitignored. **No dollar figure of realised effect is available
  and none is estimated here.**
- **Also evidenced, on the other side of the ledger:** the review's structural axis
  did produce 61 findings, and the repair explicitly kept it running — *"The
  structural axis is untouched and still runs"* — relabelled `INCIDENTAL`. So the
  estimating effect of the repair was not the loss of the structural output but the
  loss of its ability to headline.

## 11. Sandcastle cross-reference, in the report's own four dispositions

**EVIDENCED.** The report's dispositions are: *a corroborated principle, a
Sandcastle-specific contrast, a test hypothesis, or an irrelevant operating
condition.* This episode appears in the report twice:

- **ADR-0010 — Structured output** (report line 90). Disposition as the report
  records it: **"Independently corroborated principle."** Sandcastle's ADR-0010 is
  *"Canonical and implemented; retry-ownership prose is stale."* The failure the
  report attaches to it: *"'The agent stopped,' 'the task completed,' and 'a valid
  artifact was produced' are collapsed into one success state. Invalid or empty
  output can pass."* This episode is cited as the Merit evidence for it, alongside
  `8aa0b852` as the correctly-recorded-blocked contrast.
- **Episode C — "empty, plausible, or mechanically passing output acquired success
  semantics"** (report lines 137–148). **Sandcastle corroboration: ADR-0010, 0019
  and 0020.** Responsibility under test: *tool implementation; workflow execution;
  acceptance.* Replay question as written: *"a producer processes no inputs, cannot
  parse the source, or returns prose instead of the requested artifact. What
  explicit coverage and artifact contract prevents `exit 0`, silence, or a plausible
  narrative from counting as success?"*

**No automatic authority is taken from any of this.** Sandcastle's ADR-0010 is a
structured-output decision in another codebase; what this episode corroborates is
the *principle* the report states, not the ADR's implementation. ADRs 0019 and 0020
were not read — they are not in `orbit/evidence/` and the report's own summary of
them is the only local source, which is not a primary source for their content.

### The probes, read at their exact bytes and applied

> **SC-A05** | **Explicit successful nothing:** zero, empty, silence, and no-diff
> each have named semantics and cannot masquerade as processed/accepted/completed. |
> Tool implementation; estimating workflows; checks | Positive outcome text plus
> coverage counts and nonzero refusal for required-but-unprocessed input; negative
> controls. | 61 findings with zero prices; empty-output success; no-fail count.
> — `orbit/evidence/sandcastle-adr-comparative-archaeology.md:207`

Applied to the **pre-state** (`f55bc3d`): **FAIL**, on every clause. Zero had no
named semantics — `summary_check.py:126-129` suppressed the coverage sentence
exactly at zero (F2b), so zero *was* silence. Coverage counts were absent from the
output on the run that needed them. There was no nonzero refusal:
`summary_check.py:202` returns 0 and `price_list.py` had no coverage-dependent exit.
There was no negative control anywhere in the suite. The probe's own replay seed —
*"61 findings with zero prices"* — is this episode.

Applied to the **post-state** (`5e4256f`): **PASS with one exception.** Zero, empty
and unavailable each have a name (`OK`, `NO_UPC`, `NO_TABLE`, `NO_COMPARISON`,
`coverage.py:30-33`) and a distinct remedy (`REMEDY`, `:35-49`), and all-zero UPCs
are explicitly defined as *not a join key* rather than as a bad one
(`normalise_upc`, `:78-91`). Positive outcome text plus coverage counts: the
nine-line coverage block prints on success *and* on refusal, deliberately —
*"`0 of 549` is the evidence for the refusal"* (`:141-142`). Nonzero refusal:
`price_list.py:287` returns 3. Negative control: `tests/test_coverage.py:138-158`.
**The exception is `summary_check.py`, which still returns 0 on a zero-UPC job
(F13)** — it satisfies the "positive outcome text plus coverage counts" clause and
not the "nonzero refusal for required-but-unprocessed input" clause.

> **SC-A06** | **Artifact contract:** execution status, source coverage, schema
> validity, artifact existence, and landing/reachability are separate fields. |
> Summary-pricing review; workflow execution; session evidence | Remove or corrupt
> each component in turn; the result identifies the missing component and never
> reports global success. | Parse failure stamped `is_error:false`; blocked live
> acceptance; chat-only verdicts.
> — `orbit/evidence/sandcastle-adr-comparative-archaeology.md:208`

Note that this probe names *"Summary-pricing review"* as its first primary
responsibility, so this episode is its named subject.

Applied field by field. **Pre-state (`f55bc3d`):**

| field | pre-state |
|---|---|
| execution status | present, and the only field: `return 0` / `return 2` |
| source coverage | **absent from the output at zero** (F2b) — computed, then suppressed |
| schema validity | **present and separate**, and it worked: `grid.ParseNotReconciled` → `return 2`; a `Bid Summary Report` with no line items → `return 2`; per-line arithmetic gated harder for a grid `.txt` |
| artifact existence | present: `wrote %s` after `json.dump` |
| landing / reachability | **conflated with existence** — the artifact was written to `.prototypes/`, which `.gitignore:88` ignores, so "written" and "landed anywhere durable" were one fact (F5) |

So **two of five fields were separate and working pre-state.** The parse gate — a
gate of exactly the same kind, on the same command, written earlier — was already
there and already fail-closed. What was missing was not the *idea* of a gate but a
**coverage** field beside the parse field.

**Post-state (`5e4256f`):** execution status and source coverage are now distinct
and the coverage field owns the exit code; schema validity unchanged; artifact
existence unchanged; **landing/reachability still conflated with existence** — the
`.prototypes/` boundary is acknowledged in `SKILL.md` and `.gitignore:83-88` as a
known exception, not resolved. The probe's requirement that *"the result identifies
the missing component and never reports global success"* is met for coverage
(`refusal()` names the verdict and prints the numbers), met for schema, and **not
met for landing.**

**Disposition of this episode against the report's four:** *independently
corroborated principle*, following the report's own reading at line 90, and
strengthened by F9/F10 — four further instances of the mechanism in three
repositories within six days, one of them four days *earlier* than this episode.

## 12. Replay scenario

**EVIDENCED and runnable by someone who was not there.** All addresses are
read-only; the two write-side steps use throwaway copies outside every checkout.

**Setup (read-only).**

```
GitHub read APIs, or a full clone made OUTSIDE the three read-only checkouts.
  pre-state blobs : f55bc3dda5ddf7c0f36a792d9d66b7b97ffad939
                    .claude/skills/summary-pricing-review/summary_check.py
                    .claude/skills/summary-pricing-review/price_list.py
  repair          : 5ffc8bfb778700de4e0a8af1138a84c1fcea5b4d  (= 9b7e1c3871b1…)
  follow-on       : 61ddd1ce00f2e3237f4cc7281249075813d39515
```

**Step 1 — reproduce the silence, without any job data.** Confirm at the pre-state
bytes that `summary_check.py`'s only UPC-coverage output is guarded by `if with_upc:`
(`:126-129`) and that `main()` ends in `return 0` (`:202`). The assertion to make is
not about the 549-line export: it is that **for `rows` where no element has a usable
`upc`, the coverage sentence is unreachable and the exit code is 0 regardless of
`len(ranked)`.** No confidential input is required to establish this.

**Step 2 — reproduce the unlicensed join.** At the pre-state bytes, confirm
`price_list.py:158` joins on `str(row.get('item'))` alone, with no comparison of
`entry['upc']` to `row['upc']`. Feed it a synthetic two-row job and a synthetic
table whose entries carry the same item numbers and **different** UPCs (the shape of
`tests/test_price_list.py`'s post-repair fixture, minus the UPCs that commit added).
Expected pre-state behaviour: a priced ENTER total. This is the 19-row / `+$3,045.11`
mechanism in miniature.

**Step 3 — run the repair's own negative control.** In a throwaway copy of the skill
at `5ffc8bfb` or later:

```
cd <throwaway>/.claude/skills/summary-pricing-review
python -m unittest tests.test_coverage.NegativeControl -v
python -m unittest tests.test_coverage.EndToEnd -v
```

`NegativeControl` builds 549 UPC-less rows and asserts `NO_UPC`, `not ran`,
`lines_with_upc == 0`, `dollars_compared == 0.0`, and a non-`None` refusal; then
asserts 61 times that a finding count cannot make `ran` true. `EndToEnd` runs
`price_list.py` as a subprocess on a 40-row zero-UPC fixture and asserts
`returncode == 3`, `CANNOT RUN` on stderr, and **no** `TYPE THESE INTO CONEST` on
stdout.

**Step 4 — remove each artifact-contract component in turn (SC-A06's stated method).**
In the throwaway, one at a time: delete the `coverage.assess` call at
`price_list.py:269`; blank `row['upc']` on every line; empty the price table;
give every table entry a UPC that matches no row; corrupt the input so
`grid.ParseNotReconciled` raises. Record for each what the result names and what it
exits. The two expected outcomes on the current code are `NO_UPC`/`NO_TABLE`/
`NO_COMPARISON` with exit 3, and `return 2` for the parse failure — and, for the
first mutation, **no refusal at all**, which is the property `coverage.py:15-18`
claims: deleting the call is visible in a diff.

**Step 5 — the boundary that is not closed.** Run `summary_check.py` alone on a
zero-UPC job and read `$?`. Expected: **0**, with the `INCIDENTAL` label on stdout
and the banner on stderr (F13). A caller that branches on the exit code of step 1
of the pipeline still gets success.

**Step 6 — the second component.** At `61ddd1ce`'s parent, run `corpus_manifest.py`
against a job table whose formats support a price check and whose files carry no
UPC. Expected: "5 jobs known, 5 reviewable end to end". At `61ddd1ce` and later:
"5 PARSE; 1 can run the PRICE AXIS", and
`python -m unittest tests.test_coverage.ManifestAgreesWithTheGate -v` passes.

**What cannot be replayed, and why:** the original run. The 549-line export, the 61
findings, the nine-day-old price table and the estimator's response are outside
every git tree (F5) and no session record survives (F2, F6). The replay above
reproduces the **mechanism** on synthetic inputs; it does not reproduce the
**event**.

## 13. Falsifier

**EVIDENCED.** Any one of these readings would show this reconstruction does not
hold:

1. **`f55bc3d` is not the code that ran.** If a `rescue/2026-08-31-…-0cae5cb-*`
   snapshot shows `summary_check.py` or `price_list.py` differing from `f55bc3d` in
   the coverage or join paths, then F2's line-level attribution is wrong even though
   the commit message's account stands. I did not read the ~40 snapshots. Field 1
   already marks this UNKNOWN at the process level; a positive finding here would
   move it from UNKNOWN to *contradicted*.
2. **The silence at zero was not the mechanism.** If `checks.run()` at `f55bc3d`
   emitted its own coverage statement, or if some other surface printed the UPC
   count unconditionally, then interpretation I1 is wrong and the failure was purely
   the missing exit code. I read `summary_check.py` end to end and found one UPC
   report, guarded; I did **not** read `conest/checks.py`.
3. **`9b7e1c3` and `5ffc8bfb` are not the same change.** If their trees differ, §1
   is wrong and `61ddd1ce`'s pointer is not dangling. Message, author date and
   patch description are identical; I compared metadata, not trees.
4. **The pre-state was never actually reachable as described.** If `summary_check.py`
   at `f55bc3d` could not in fact reach line 174 on a zero-UPC 549-line export —
   for example if `job['groups_reconciled']` or the grid per-line gate would have
   raised `ParseNotReconciled` first — then the episode as reconstructed could not
   have happened at these bytes and the run must have used different code. The
   commit message asserts it happened; I did not execute it.
5. **A second gate already covered `summary_check.py`'s exit code.** If any caller,
   hook, or wrapper between `summary_check.py` and the estimator converted its exit 0
   into a refusal, F13 and the SC-A05 exception are wrong.
6. **The estimating effect is recorded somewhere I did not look.** `prior-reviews/`,
   the ConEst estimate itself, or a non-git record (email, the bid file) would move
   field 10 from PARTIAL to evidenced, and could contradict the "no realised effect
   established" reading in either direction.
7. **The repair did not hold.** If a commit after `5e4256f` removes or weakens
   `coverage.assess`'s call at `price_list.py:269`, Register 4's held-claims are
   stale as of the date they were read (2026-09-12 against HEAD authored
   2026-09-04).
8. **`020383de` is not the same mechanism.** If the Lab's note-count assertion was a
   deliberate invariant test rather than a validation standing in for one, F9 and I4
   overstate the recurrence and the "four instances in six days" count drops.

---

# FIELD-FIT REPORT (feeds ticket #10)

## Which of the 13 fields fitted this episode

**Evidenced — 10 of 13:**

| field | how it fitted |
|---|---|
| 3. Changed files and graph relationships | Fitted cleanly. Both commits are small and fully readable; the import graph gives one definition consumed by three commands, plus a dangling prose edge |
| 4. Writer, reader, enforcing boundary | Fitted **unusually well** — and the field's real value here was that it forced the question "which layer could have refused?", whose pre-state answer is *none* while prose said otherwise |
| 5. Authority and activation path | Fitted, five layers deep, and surfaced that the skill has no session-open authority at all — it is trigger-phrase activated |
| 6. Lifecycle and supersession | Fitted. Includes a ruled-unmergeable predecessor (PR #217) and a clean-successor relationship |
| 7. Secondary failures | Fitted **strongly**. Three, one of them ten minutes after the repair. The field is what made the repair's real effect visible: it converted an undetectable claim into a detectable one |
| 8. Repair attempted | Fitted; six repairs across four repositories |
| 9. Evidence the repair held / failed / unknown | Fitted **best of all**, and only because it permits all three verdicts at once. A held/failed binary would have produced a false "held" |
| 11. Sandcastle cross-reference | Fitted. The report's own disposition for this episode exists and was used rather than re-derived. SC-A06 names this review as its first responsibility |
| 12. Replay scenario | Fitted, and is genuinely runnable — because the repair shipped its own negative control and a subprocess-level end-to-end test, the replay is mostly "run what is already there" |
| 13. Falsifier | Fitted; eight falsifiers, five of which name work I explicitly did not do |

**PARTIAL — 2 of 13:**

| field | what was evidenced / what was not |
|---|---|
| 1. Pre-state commits | Files: evidenced at the bytes (`f55bc3d`). **Process: UNKNOWN** — a dirty shared checkout on a deleted branch. The field assumes a commit identifies a pre-state; here it identifies the *code* but not the *run* |
| 10. Estimating effect | The instruction is evidenced to the cent (`+$3,045.11`, 19 rows). Whether it was acted on is UNKNOWN — no incident record, and the journal lives outside git |

**UNKNOWN — 1 of 13:**

| field | reason |
|---|---|
| 2. Prompting evidence | Three independent mechanisms, each documented in the repository: `.scratch/` run records are deliberately not landed; the checkout was shared and dirty so nothing was committed under M10; the preserved worktree branch carries no folder for this session |

So: **10 evidenced, 2 partial, 1 UNKNOWN.** Counting partials as not-fully-evidenced:
10 of 13 filled, 3 of 13 carrying a stated absence.

## Was any field the contract lacks needed?

**Yes — four.** Each is recorded as a need discovered while filling the 13, not as a
proposal.

**A. A field for *why the record is missing*, distinct from *what is missing*.**
Field 2 came out as "UNKNOWN", which reads as an accident of record-keeping. It is
not: `.scratch/` non-landing and M10 are **standing policies**, and `.prototypes/`
being gitignored and the corpus living outside every tree are **deliberate
confidentiality boundaries** (`CORPUS.md`, F5). A fixture that writes UNKNOWN in the
same shape for "nobody wrote it down" and for "the estate decided on purpose that
this must never be in git" has lost a distinction that a replayer needs, because the
second kind will be UNKNOWN for every future episode in this tool too. §5.1 requires
*"the reason it is unavailable"*, which I supplied in prose; it does not give the
reason a field, and the reasons here are load-bearing and recurring.

**B. A field for *the identity relation between the anchor and what landed*.**
The contract's field 1 is "pre-state commits" and its anchors table gives one SHA.
Neither has a place to record that the anchor SHA is one of **two** commits for the
same change (§1), that the repository's own prose cites the other, and that the
other is unreachable from `main`. I recorded it in §1 outside the 13 fields because
no field would take it. SC-A10 is the probe for this; the *fixture contract* has no
slot for it, so a replayer following the report's citation would silently fail.

**C. A field for *which of the failure's parts the repair did and did not close*.**
Field 9 accepts held / failed / unknown as verdicts on *the repair*. This episode's
repair closed the headline and left the exit code of the observing command open
(F13) — not a failure, not fully held, and not unknown: a **deliberate partial**,
documented as such in `SKILL.md:39-41`. I put it under "failed or held only partly",
which misfiles an intentional scope decision as a shortfall. The distinction matters
to replay, because step 5 of the replay scenario *passes* by returning 0.

**D. A field for *prior instances of the same mechanism*, separate from field 7.**
Field 7 is "secondary failures" — what the episode caused or exposed *after*.
`Estimating-Lab 020383de` is the same mechanism **four days earlier** in another
repository (F9), and `Merit-knowledge 77d812f3` is three days earlier (F10). They
are neither secondary failures of this episode nor part of its repair chain; they
are evidence that the mechanism predates the episode. I recorded them in Register 1
under F9/F10. Gate 2's own instruction is to *"derive responsibilities from
mechanisms that failed more than once"*, which is exactly the fact this missing
field would carry forward — and without it each fixture records only its own
downstream and the recurrence has to be reassembled later from nine separate
packages.

**Fields that did NOT need supplementing:** 3, 4, 5, 6, 8, 11, 12, 13 all took
everything the record offered without strain. Field 11's insistence on the report's
*own four dispositions* and on "never automatic authority" was actively useful: it
stopped me treating Sandcastle ADR-0019 and ADR-0020 as read when only the report's
summary of them is available locally.

## One further note for ticket #10

The four-register requirement earned its place on this episode, in a specific way
worth recording. The single most consequential fact in this package —
**`summary_check.py` still exits 0** (F13) — is a *fact*; that it is a deliberate
design scope rather than an oversight is an *interpretation* resting on
`SKILL.md:39-41`; the gate that does exist is a *repair*; and that the gate's
refusal is asserted by a subprocess test in CI is *evidence the repair held*. Four
registers, one sentence of prose if they were merged. Written as one narrative, the
sentence would have read "the pricing gate now exits non-zero" — which is true of
`price_list.py` and false of the command that failed.
