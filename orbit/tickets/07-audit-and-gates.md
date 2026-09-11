# 07 — The estate, in two families, and both gates

**Blocked by:** 06, 14. Re-scoped by ticket 14 before it ran, as spec 0002 §8.4
requires.
**Demo when done:** two reports — the lineage comparison and the hand-built
audit — plus two recorded gate decisions.

Phase 1's exit run is **simultaneously** the estate audit and the input to both
gate decisions. Two passes, not three, and they are two because the estate is
two families with two different kinds of answer available.

## Why this ticket was rewritten

It used to be one pass over the whole estate. That conflates spec 0002 §4's two
families, and the difference between them is not presentational:

| family | repositories | shared origin? | what can be said |
|---|---|---|---|
| **clone lineage** | Advisor-Desk, agent-rules-books | yes — one upstream | a delta against a common base |
| **hand built** | Home-system, Estimating-Lab, Merit-knowledge | no | absolute figures, and whatever they are argued against |

A delta is only a measurement where the two states share a base. Run over a
hand-built repository it is a subtraction between two unrelated numbers, and
printing it beside a lineage delta would let one be read as the other.

## Part 1 — the clone lineage, as a controlled comparison

**Runs first, and it is already runnable.** Ticket 14 ran it for C0, C1 and C2:

```sh
orbit-context compare a7d7649 <head> /home/user/agent-rules-books@782a886 --repo .
```

What Part 1 owes beyond that run:

1. **Re-run it against the head this ticket is executed on**, and name that head
   by its commit. C1 moves with every session, so a table that does not name the
   commit it was taken at is not reproducible.
2. **Establish the base before reading any delta**, the way ticket 14 did: the
   fourteen `full.md` links per state from the rows, and the shared corpus by
   git blob id across the trees. Ticket 14's answer — 195 of C0's 201 paths
   identical in C2, no book or `_rule-workbench` file among the six that moved —
   holds for `782a886` and has to be retaken if C2 has moved on.
3. **Carry ticket 14's recognition finding forward.** Three files present and
   byte-identical in both C0 and C2 are recognised in one and not the other,
   because C2's additions took `_rule-workbench/` under the corpus rule's 0.75
   declared share. Any surface delta over a repository whose corpus directories
   changed shape has to say whether the same thing happened there. A count that
   moved because a share moved is not a count of files anyone added.

**agent-rules-books is read-only.** Index it. Never write to it, never push to
it, never open a pull request against it. `compare` materialises every state as
a clone for this reason, so running it is enough.

## Part 2 — the hand-built family, as an audit

**Runs second.** Home-system, Estimating-Lab, Merit-knowledge. No shared origin,
so `compare` is the wrong instrument and `orbit-context index` plus `repo-map`
is the right one.

Report, per repository: git state; surfaces by kind and recognition, with the
number folded beside the count; files and bytes walked; clauses by type; edges
by kind; pointers by detector; the three non-resolutions with the detector set
version; identical-byte pairs with their provenance counts; coverage notes.

**Conditions and evidence only.** Nothing is labelled broken, obsolete,
misplaced or safe to delete. Zero recognised inbound pointers is a statement
about the detector set, not about a file.

**Whatever a figure here is measured against is argued in writing, or it is not
measured against anything.** There is no baseline. An absolute figure is a
result on its own — "this repository holds N surfaces over M files" — and any
comparison to another repository, to a lineage state, or to an expectation is a
claim that has to carry its argument beside it.

## Part 3 — Gate A: does the load ledger earn its place?

Unchanged.

**Before looking at the data**, write down the three questions about loading you
actually want answered. Then attempt each in plain SQL over the phase-1 tables.

- **All three answer** → the ledger is not built. Filename convention plus
  `size_bytes` was enough. Record the result.
- **They do not, and the same column is missing each time** → build **only that
  column**.

Prior signal: phase 1 catches byte-identical `AGENTS.md`/`CLAUDE.md` pairs with a
hash, but cannot say a Claude session pays one and a Codex session the other. So
`client` is the likeliest — possibly the only — surviving column. The honest
first version may be one column, not fourteen.

## Part 4 — Gate B: do evidence columns earn their place?

Unchanged.

Take a **random sample of 50 findings** and hand-classify each as a real estate
condition or a detector artifact.

- **False-positive rate low and uniform across detectors** → not built. A single
  `detector` column suffices to trace a rule that reads wrongly; the four-way
  class is ceremony.
- **Rate high, or varying sharply between detectors** → built. A finding whose
  reliability depends on which rule produced it must carry that rule.

The 1,349-of-1,373 phantom rate is a strong argument, but it came from **one
fixed bug**. The question is the steady-state rate, and only the sample answers
it.

**Sample across both families.** A rate taken only over the lineage is a rate
over one corpus shape, and the hand-built repositories are where the detectors
have seen least.

## Acceptance

- [ ] The lineage comparison is re-run and its head named by commit
- [ ] The base is established from the rows and the trees before any delta is read
- [ ] Every repository in the estate appears in one of the two parts, and which
      part it is in is stated
- [ ] No delta is reported for a repository with no shared base
- [ ] The three questions for Gate A were written down before the data was examined
- [ ] Each Gate A question is marked answerable or not, with the SQL attempted
- [ ] 50 findings sampled and hand-classified, with the rate broken down by
      detector and by family
- [ ] Both gate decisions recorded — including "not built", which is a result
- [ ] Any surface delta that moved because a corpus share moved says so
- [ ] Kill conditions checked against both parts before any phase 2 work starts
- [ ] Output contains no forbidden vocabulary word

## Either gate closing is a result, not a failure

Record it, so a future session sees the additions were tested rather than
re-proposing them from scratch.

---

# Gate A — the three questions, written before the data

**Committed on its own, before any query was run against the phase-1 tables**, so
that the order is in the history rather than asserted afterwards. Nothing below
was chosen for being answerable; the schema was not consulted while writing
them. Head at the time of writing: `38b9dce`.

**Q1 — When a session opens in this repository, which surfaces reach it, and
what do they weigh?** The cold-start bill, per client. Not "which surfaces
exist" — which ones arrive without anybody asking for them.

**Q2 — Of the bytes that reach a session, which are paid for twice?** The same
content arriving under two names, or a smaller rung of a ladder arriving
alongside a larger one that already contains it.

**Q3 — Which of those surfaces can a session stop paying for, and which are
unconditional?** A surface that loads on a trigger costs nothing until the
trigger fires. A surface that loads always is a floor.

Each is attempted below in plain SQL over the phase-1 tables, and marked
answerable or not answerable with the SQL that was attempted either way.

---

# What the run found

Two passes, in the order the ticket sets. The lineage comparison first, as a
controlled comparison. The hand-built family second, as an audit with no
baseline. Then the two gates, each against its own pre-registered rule.

**Every repository in the estate appears in exactly one part**, and which part
it is in is stated:

| repository | family | part | why |
|---|---|---|---|
| Advisor-Desk | clone lineage | 1 | shares an upstream with agent-rules-books |
| agent-rules-books | clone lineage | 1 | same upstream; read-only here |
| Home-system | hand built | 2 | no shared origin |
| Estimating-Lab | hand built | 2 | no shared origin |
| Merit-knowledge | hand built | 2 | no shared origin |

**No delta is reported for any repository in Part 2**, and none is computed. The
three hand-built repositories share no base with each other or with the
lineage, so a subtraction between any two of them would be a subtraction
between unrelated numbers.

**Nothing was written to any repository this ticket only reads.** Every state in
Part 1 is materialised as a clone. The four repositories indexed in place were
compared path for path, with size and mtime, before and after: unchanged, and
`git status` clean in all four.

## Part 1 — the clone lineage

```sh
orbit-context compare a7d7649 dc8d743 /home/user/agent-rules-books@782a886 --repo .
```

Detector set `1.8eabab386316` for every state, the set ticket 14 ran and the set
this ticket's two repairs leave unmoved.

**The head is `dc8d743`** — `Ticket 07: Gate A's three questions, written before
the data`, the commit that pre-registers Gate A. C1 moves with every session, so
the run is named by the commit it was taken at and can be retaken there.

| | C0 `a7d7649` | C1 `dc8d743` | C2 `782a886` | C1 − C0 | C2 − C0 |
|---|---|---|---|---|---|
| files walked | 201 | 323 | 515 | +122 | +314 |
| bytes walked | 2,172,106 | 3,260,876 | 10,432,071 | +1,088,770 | +8,259,965 |
| surfaces | 87 | 103 | 126 | +16 | +39 |
| names that resolve to another name | 14 | 14 | 14 | 0 | 0 |
| two names for one file, folded | 14 | 14 | 14 | 0 | 0 |
| clauses | 7,560 | 7,901 | 8,089 | +341 | +529 |
| pointers | 224 | 314 | 344 | +90 | +120 |
| surface bytes | 781,674 | 853,575 | 946,722 | +71,901 | +165,048 |

### What moved between ticket 14's head and this one, and what did not

C1 advanced from `dc16a3e` to `dc8d743`. **Bytes walked rose by 21,823 and every
other figure in the table is unchanged** — same 323 files, same 103 surfaces,
same 7,901 clauses, same 853,575 surface bytes. The commits in between are
ticket and README prose, which this detector set does not recognise, so they
weigh on the walk and nowhere else. C2 is at the same commit ticket 14 read and
every one of its figures is identical.

### The base, established before any delta was read

**Fourteen names that resolve to another name in each of the three states, 812
bytes, all fourteen folded** — read off the rows, not counted by hand. The same
fourteen `_rule-workbench/<book>/full.md` paths naming the same fourteen
targets. C2 inherited them as links and still holds them as links; had anything
resolved them, the rows would carry fourteen regular files weighing what the
books weigh.

**The rest of the base was retaken by git blob id across the two trees**, because
byte identity is measured inside one snapshot and "is this the same file in
another repository" is not a question the graph answers. C0's 201 paths land in
C2 as:

| | paths |
|---|---|
| identical in bytes and mode | 195 |
| present and edited | 5 — `.gitignore`, `CHANGELOG.md`, `README.md`, `docs/CRITICISM.md`, `docs/USAGE.md` |
| absent | 1 — `docs/ADDING_THE_BOOK.md` |

**No book file and no `_rule-workbench` file is among the six.** Ticket 14's
answer holds at `782a886` unchanged, retaken rather than assumed. The shared
corpus is byte-identical at both ends, so `C1 − C0` and `C2 − C0` are the same
kind of measurement.

**The coverage gap ticket 14 recorded still stands.** The C2 clone is shallow —
one commit, no history — so whether `a7d7649` is an ancestor of `782a886` was
answered from content and not from lineage. A repository that reproduced C0's
bytes without descending from C0 would be indistinguishable here.

### The recognition finding, carried forward and asked of both states

Ticket 14 found three files present and byte-identical in C0 and C2, recognised
in one and not the other, because C2's additions took `_rule-workbench/` under
the corpus rule's 0.75 declared share. The ticket requires any surface delta
over a repository whose corpus directories changed shape to say whether the same
happened there. Asked of both states, from the rows:

| | read Markdown under `_rule-workbench/` | declared | share | a corpus at 0.75? |
|---|---|---|---|---|
| C0 | 45 | 42 | 0.933 | yes |
| C1 | 45 | 42 | 0.933 | yes |
| C2 | 59 | 42 | 0.712 | no |

**C1's corpus directories did not change shape, and the rows say so directly:
zero paths recognised in C0 are unrecognised in C1.** So none of `C1 − C0`'s +16
moved because a share moved. All sixteen are `skill-package` rows, one per
`.claude/skills/<name>/SKILL.md`.

**C2's did**, and the three files are named: `_rule-workbench/CHECK_COMPATIBILITY.md`,
`PROCESS.md` and `RELEASE.md`. Nothing happened to those files — they are
byte-identical to C0's. C2 added one undeclared `skill.frontmatter.md` per book
to that subtree, which took the directory under the share. It is the same
detector set at both ends, and **a reader taking C2's −3 as three files removed
would be reading something false out of a correct number.**

## Part 2 — the hand-built family

`orbit-context index` and `repo-map`. No comparison instrument, because there is
nothing to compare against.

| | Home-system | Estimating-Lab | Merit-knowledge |
|---|---|---|---|
| git state | `main` @ `5e4256f92076` | `main` @ `be90aa288564` | `main` @ `f1c14a955a9e` |
| files walked | 1,348 | 601 | 11 |
| bytes walked | 40,849,304 | 23,716,125 | 106,314 |
| surface rows | 36 | 25 | 0 |
| files carrying a surface kind | 35 | 24 | 0 |
| surface bytes | 499,428 | 247,487 | 0 |
| names that resolve to another name, folded | 0 | 0 | 0 |
| clauses | 920 | 578 | 0 |
| edges | 1,552 | 810 | 0 |
| pointers | 622 | 229 | 0 |
| identical-byte pairs | 9 | 1 | 0 |
| ladders | 0 | 0 | 0 |
| read in part | 1 | 0 | 0 |

**Surfaces by kind**, rows / bytes:

| kind | Home-system | Estimating-Lab | Merit-knowledge |
|---|---|---|---|
| instruction-surface | 1 / 7,286 | 1 / 7,487 | 0 / 0 |
| skill-package | 27 / 460,839 | 20 / 214,450 | 0 / 0 |
| agent-definition | 4 / 15,114 | 1 / 5,919 | 0 / 0 |
| hook-definition | 2 / 419 | 2 / 463 | 0 / 0 |
| hook-target | 1 / 15,604 | 1 / 19,168 | 0 / 0 |
| mcp-config | 1 / 166 | 0 / 0 | 0 / 0 |
| command-definition | 0 / 0 | 0 / 0 | 0 / 0 |

**Surfaces by recognition.** Every recognised surface in all three repositories
is `vendor-name`: 35, 24 and 0. `declared-marker` and `corpus-adjacent` are zero
everywhere in this family. Of the figures above, **none was read off a directory
rather than stated by the estate** — the one recognition rule that reads rather
than quotes contributed nothing here.

**Clauses by type:**

| | Home-system | Estimating-Lab | Merit-knowledge |
|---|---|---|---|
| heading-section | 345 | 224 | 0 |
| list-rule | 428 | 266 | 0 |
| frontmatter-field | 86 | 60 | 0 |
| code-block | 61 | 28 | 0 |

**Edges by kind:**

| | Home-system | Estimating-Lab | Merit-knowledge |
|---|---|---|---|
| CONTAINS | 920 | 578 | 0 |
| REFERENCES | 622 | 229 | 0 |
| IDENTICAL_BYTES | 9 | 1 | 0 |
| PRODUCES | 1 | 2 | 0 |
| RUNG_OF | 0 | 0 | 0 |

**Pointers by detector:**

| | Home-system | Estimating-Lab | Merit-knowledge |
|---|---|---|---|
| bare-path-literal | 498 | 216 | 0 |
| markdown-link | 121 | 3 | 0 |
| config-value | 3 | 2 | 0 |
| frontmatter-field | 0 | 8 | 0 |
| import-statement | 0 | 0 | 0 |
| supersedes-claim | 0 | 0 | 0 |
| written inside a fenced block | 30 | 22 | 0 |

**The three non-resolutions, never merged**, detector set `1.8eabab386316`:

| | Home-system | Estimating-Lab | Merit-knowledge |
|---|---|---|---|
| no-indexed-target-match | 141 | 49 | 0 |
| unresolvable-scheme | 1 | 1 | 0 |
| outside-indexed-roots | 0 | 2 | 0 |

**Identical-byte pairs and their provenance counts.** Home-system 9 pairs,
Estimating-Lab 1, Merit-knowledge 0. **Every pair in this family carries no
provenance evidence and no direction**, all under
`no-producer-named-at-either-end`. Whether two files holding identical bytes are
intentionally so stays a permanent UNKNOWN (spec 0001 §14).

Home-system's sharpest pair is `CLAUDE.md` = `_workbench/boot/mini.md`: one end
is the repository's instruction surface, the other is not a recognised surface
at all. Estimating-Lab's single pair is two capture directories of one
transcript holding the same image — and it is the pair that exposed a reporting
defect, recorded below.

`PRODUCES` edges: Home-system 1, Estimating-Lab 2. Home-system additionally
carries one producer named that matched nothing indexed, and one declaration
naming a file as both its own input and its own output. Estimating-Lab carries
eight declarations of generation that name no producer.

### Merit-knowledge returns zero, and the zero is tied back to named files

Eleven files, 106,314 bytes, no surface rows. Spec 0002 §9 says a number that
cannot be tied back to named files is not a result, so the eleven:

```
README.md                       check.sh
contracts/ANCHOR-FORMAT.md      contracts/DECISION-FORMAT.md
contracts/INDEX-FORMAT.md       contracts/INDEX.md
contracts/LEDGER.md             contracts/MODEL-FORMAT.md
contracts/PACKET-FORMAT.md      contracts/TURNOVER-SUMMARY.md
knowledge/standing-figures.md
```

**The zero is a statement about this detector set, and the reason is exact.**
Three recognition rules exist. No file here carries a name or location any
vendor defined. No file opens with a directive heading: `DIRECTIVE_HEADING_WORDS`
is the single word `OBEY`, and these files open `# Anchor Format`,
`# merit-knowledge`, `# Standing figures` — noun phrases. And with nothing
declared, no directory reaches the 0.75 share, so the corpus rule finds none.

**Nothing here is labelled.** A repository of format contracts that this
detector set does not recognise is a condition of the detector set meeting a
naming convention it was not built from. It is not a statement about those
files.

### The two families are shaped differently, and the figure is argued

The ticket requires any comparison to carry its argument beside it. This one is
between two figures taken the same way, by the same query, over the same graph,
and it is offered as an observation and nothing more.

**How much of each repository's governance is reachable from a surface a vendor
filename names**, by walking `REFERENCES` edges from `CLAUDE.md`, `AGENTS.md` and
`.claude/` until nothing new is reached:

| repository | family | surface rows | reachable from a client-named root |
|---|---|---|---|
| Advisor-Desk | lineage | 117 | 16 |
| agent-rules-books | lineage | 140 | 9 |
| Home-system | hand built | 36 | 33 |
| Estimating-Lab | hand built | 25 | 24 |

**What is being compared and why it is comparable:** both columns are counts of
rows in one graph, written by one detector set in one run, and the traversal is
the same query for every repository. What is *not* established is that the two
numbers mean the same thing about the two families — the lineage repositories
hold a published rule corpus that is a product of the repository, and the
hand-built ones hold working skills. A corpus nothing points at and a skill
nothing points at are not the same condition, and this table does not
distinguish them.

**No metric was built and nothing in the tool divides these columns.** The
traversal was written to answer Gate A's first question and is reported here
because it was run.

## Part 3 — Gate A: does the load ledger earn its place?

The three questions were written down and committed in `dc8d743`, before any
query was run against the phase-1 tables. Each is attempted below in plain SQL,
and marked answerable or not answerable **with the SQL that was attempted either
way**.

### Q1 — which surfaces reach a session when it opens, and what do they weigh?

**Not answerable.** Two routes were attempted.

*Route one — filename convention plus `size_bytes`, which is what the gate
names:*

```sql
SELECT CASE
         WHEN path = 'CLAUDE.md'  THEN 'Claude, by a filename Anthropic defined'
         WHEN path = 'AGENTS.md'  THEN 'Codex, by a filename OpenAI defined'
         WHEN path LIKE '.claude/%' THEN 'Claude, by a directory Anthropic defined'
         ELSE 'no filename in this query names a client for it'
       END AS client_from_the_filename,
       surface_kind, count(*), sum(size_bytes)
FROM gl_context_surface GROUP BY 1, 2;
```

Estate-wide: **81 of 318 surface rows, 841,220 of 2,548,836 surface bytes, carry
a filename that names a client. 237 rows and 1,707,616 bytes do not.** The whole
of Advisor-Desk's rule corpus — 101 rows, 782,486 bytes — is in the second
group, and so are agent-rules-books' 19 skill packages under `skills/` and
`evals/`.

*Route two — walk the pointer graph, in case reachability supplies what the
filename does not:* the recursive query in Part 2 above. It adds **one row in
Home-system and one in Estimating-Lab beyond the filename-named roots, and none
in either lineage repository.** Reachability does not carry load attribution.

*Route three — is there a column?*

```sql
SELECT client FROM gl_context_surface LIMIT 1;
-- Binder Error: Referenced column "client" not found in FROM clause!
```

There is none, in any of the six tables.

### Q2 — of the bytes that reach a session, which are paid for twice?

**Half answerable.** Which content exists twice is fully answerable and every
instance is named:

```sql
SELECT r.path, count(*) FROM gl_context_edge e
JOIN gl_context_run r ON r.project_id = e.project_id
WHERE e.relationship_kind = 'IDENTICAL_BYTES' GROUP BY 1;
-- Advisor-Desk 28, agent-rules-books 55, home-system 9, estimating-lab 1
```

and the ladder rungs beside them, 28 `RUNG_OF` edges in each lineage state.
Ninety-three pairs and fifty-six rung edges, all with both ends named.

**Which of them a session pays for twice is not answerable**, and the missing
thing is the same one Q1 is missing. `home-system/CLAUDE.md` and
`_workbench/boot/mini.md` hold identical bytes; the first reaches a session when
it opens and the second is not a recognised surface at all. Whether the same
content arrives twice depends on whether anything loads the second, which no row
says.

### Q3 — which surfaces can a session stop paying for, and which are unconditional?

**Not answerable, and the missing thing is not the same one.**

No column carries it — `activation`, `trigger`, `lifetime`, `revocable`, `scope`
and `inheritance` all return a binder error. What phase 1 does carry is the
frontmatter field names, in the clause address:

```sql
SELECT split_part(fqn, '#', 2) AS field, count(*) FROM gl_context_clause
WHERE clause_type = 'frontmatter-field' GROUP BY 1 ORDER BY 2 DESC;
-- name 93, description 93, disable-model-invocation 27, model 5, tools 5, allowed-tools 1
```

So SQL can name the **27 surfaces that declare `disable-model-invocation`**, a
field that governs exactly this question. Two things stop that being an answer:

- **The value is not in the row, by a decision already taken.** Spec 0001 §3
  adopts virtual content: the row carries the path and the offsets, and the
  caller reads the bytes. `disable-model-invocation: true` and `: false` are one
  row shape. This is not a gap — it is the design, and it is addressable.
- **Sixty-one of 88 skill packages and all 218 instruction surfaces declare
  nothing about activation at all.** For those, no column could carry an
  observation, because the estate makes no statement to observe. A column filled
  for them would be filled by inference, and spec 0002 §5 forbids recording
  inference as fact.

### The decision: not built

The gate's two branches are "all three answer → not built" and "they do not, and
the same column is missing each time → build only that column". Neither fires
cleanly, so the reasoning is set out rather than asserted.

Q1 and Q2 miss the same thing: which client pays for a surface. Q3 misses
something else, and most of what Q3 misses cannot be observed at all.

**So the one surviving candidate is `client`, and it does not earn a column.**
Where a vendor filename names the client, `path` already carries it — that is
how the query above answered for 81 rows, and it is the same evidence
`recognition = 'vendor-name'` already records. Where no filename names it, for
the 237 rows that are two-thirds of the estate's surface bytes, there is no
static evidence to read: which client pays for `_rule-workbench/refactoring/mini.md`
is not written in that file, in any file pointing at it, or anywhere in the
tree. A `client` column would hold values derivable from a column already
present, or UNKNOWN.

**A column whose every non-UNKNOWN value is derivable from a column already on
the row is not a column.** Gate A closes.

**What would reopen it:** evidence of an actual session load — a transcript, or
a hook that records what was read. That is runtime observation, not static
indexing, and it is not what Candidate A specifies. Spec 0002 §13's permanent
UNKNOWN — *whether a rule file is loaded by any session, absent Candidate A* —
is sharpened by this run: Candidate A as written would not have answered it
either, because it would have had to read the same static evidence phase 1
already reads.

## Part 4 — Gate B: do evidence columns earn their place?

**Population: 2,167 findings** — every row that makes a claim about the estate.
Surfaces (this file is a surface of this kind), external refs (this address
matched nothing indexed), pointers (this text names that file), and
identical-byte pairs.

**Sample: 50, stratified 25 per family so a rate can be read per family, random
within each, seed 20260911.** Each was hand-classified against its own evidence,
reading the source line where there is one.

### The rate

**Four of 50 are detector artifacts. 8.0%.**

| family | sampled | artifacts | rate |
|---|---|---|---|
| clone lineage | 25 | 2 | 8.0% |
| hand built | 25 | 2 | 8.0% |

| detector | sampled | artifacts | rate |
|---|---|---|---|
| pointer/bare-path-literal | 37 | 4 | 10.8% |
| pointer/markdown-link | 2 | 0 | 0% |
| external_ref/no-indexed-target-match | 4 | 0 | 0% |
| surface/declared-marker | 3 | 0 | 0% |
| surface/corpus-adjacent | 2 | 0 | 0% |
| surface/vendor-name | 1 | 0 | 0% |
| identical_bytes | 1 | 0 | 0% |

**The rate is uniform across families and is not uniform across detectors. All
four artifacts came from one detector, and the other six produced none.**

### The four, named

1. **`.claude/skills/bid-day-review/SKILL.md:55`** — the line is
   `[DOSSIER-FORMAT.md](../project-knowledge/DOSSIER-FORMAT.md)`. The tool wrote
   two rows for it: a `markdown-link` row resolving correctly to
   `.claude/skills/project-knowledge/DOSSIER-FORMAT.md`, and a
   `bare-path-literal` row that read the link's *display text* and reported no
   resolution. One pointer, reported twice, once as a non-resolution that is not
   one.
2. **`.claude/skills/merit-proposal/SKILL.md:122`** — `payload.json` in
   `python .../render.py payload.json "…"`. A placeholder argument inside a
   fenced block, not a file of the repository.
3. **`.claude/skills/video-harvest/SKILL.md:280`** — `INTEGRITY.md` inside a
   fenced directory diagram (`└── INTEGRITY.md`), describing output the skill
   writes rather than a file it points at.
4. **`_rule-workbench/designing-data-intensive-applications/traceability.md:9`**
   — a pointer from a file to itself, from a sentence about the file's own
   previous version. True, and not a relation: it inflates any inbound count.

### The population confirms the detector split, beyond the sample

The sample is 50 rows; two of its four artifacts belong to classes that can be
counted over the whole population, and both are confined to one detector.

**157 of 1,306 `bare-path-literal` rows — 12.0% — restate a markdown link
that sits on the same line**, where the link's own address ends with the bare
row's:

| repository | such rows | of those, reported as not resolving |
|---|---|---|
| Advisor-Desk | 32 | 0 |
| agent-rules-books | 23 | 0 |
| Home-system | 100 | 37 |
| Estimating-Lab | 2 | 0 |

**Twenty pointer rows run from a file to itself**: Advisor-Desk 9,
agent-rules-books 5, Estimating-Lab 3, Home-system 3.

Neither class is reachable by `markdown-link`, `frontmatter-field`,
`config-value`, or any of the three surface rules. **The reliability of a
finding here depends on which rule produced it**, and the population figure is
the measurement rather than the 37-row sample.

### The decision: `detector` is already on the row, and `evidence_class` is not built

The pre-registered rule fires on its second branch: the rate varies sharply
between detectors. What that branch requires is stated in the ticket — *a
finding whose reliability depends on which rule produced it must carry that
rule.*

**It already does.** `gl_context_edge.subtype` holds `bare-path-literal` and
`markdown-link`. `gl_context_surface.recognition` holds `vendor-name`,
`declared-marker` and `corpus-adjacent`. `gl_context_edge.direction_reason`
holds why a pair carries no direction. Every rate in this section was read by
detector using columns already present; without them the sample could not have
been classified at all. The column Gate B would have opened for is built.

**`evidence_class` is not built.** Neither branch of the pre-registered rule
asks for it — the first calls the four-way class ceremony, and the second asks
only that the finding carry its rule. Measured against this sample it would also
be a function of the detector name: `vendor-name` and `declared-marker` are
DECLARED, `corpus-adjacent` is the reading rather than the estate's statement,
`markdown-link` is DECLARED and `bare-path-literal` is INFERRED. The codebase
already keeps exactly that table — `INFERRED_RECOGNITIONS`, *"the values that are
this tool's reading rather than the estate's statement"* — as a table over the
recognition name rather than as a column. A column derivable from a column
already on the row is not a column, which is the same test that closed Gate A.

**The steady-state rate is 8%, against the 96% that came from one fixed bug.**
That was the question the sample existed to answer, and it is answered: the
phantom rate was the bug, not the tool.

**What this leaves as work, and deliberately not done here:** the
link-display-text class is a detector change, and changing a detector moves the
detector set version, which would make every figure in this ticket
incomparable with the one it was taken against. Ticket 14's rule holds —
record what the run showed on the detector set that existed when it started.
Recorded, and left for a ticket of its own.

## What the audit found in the tool itself

Three things, all found by running the tool over repositories it had not seen.
Two are repaired here because each one puts something false or unaccountable in
front of a reader, and neither touches a detector: the set is unmoved at
`1.8eabab386316` and every figure above stands either side of both.

**Two different files printed as one.** Estimating-Lab's only identical-byte
pair is

```
work/sparx-academy-new-ken.transcript/2026-08-20-8bbf42cf/images/4856501b5adc.webp
work/sparx-academy-new-ken.transcript/2026-08-20-ea6aa9c3/images/4856501b5adc.webp
```

— one directory of captures, one file name reused inside each. The two agree at
both ends and differ only in the middle, which is where the elision cuts, so the
line read `X = X`: a true finding arriving as a file identical to itself. Spec
0002 §9 makes a single false assertion a stop. `pairs.tell_apart` now makes
distinct paths print distinctly a guarantee rather than a tendency, and the fold
listing in `compare` is cut through it for the same reason — a link sits beside
what it names, so its two paths share both ends by construction.

**A count that did not tie back to rows.** `index` reported
`produces_edges: 2` for Home-system and the graph held one `PRODUCES` row.
`.claude/tools/skill-sync/skills.json:80` declares
`.claude/tools/skill-sync/NOTES.md` as both an input and an output; the edge
writer refuses it, correctly, and the tally did not. Counted now by the same
rule, with the declined production named in
`producer_and_artifact_are_one_file`, beside the field that already does this
for a producer named and not found.

**One class of pointer artifact, recorded and not repaired** — the 157
link-display-text rows above, for the detector-version reason given there.

**And one the audit tripped in this repository by being written down.**
`test_pointers.py` guards against detector drift by asserting that fewer than
one in three of the distinct addresses named across this repository's prose
resolve to nothing here. Recording this ticket took that reading from 29.6% to
34.0% — 24 addresses, all of them paths in the four repositories audited above:
`contracts/ANCHOR-FORMAT.md` in Merit-knowledge,
`.claude/tools/skill-sync/skills.json` in Home-system, two capture directories
in Estimating-Lab, and so on. Every one was read correctly and resolved
correctly. None of them can resolve here, by definition.

**The ceiling was not moved.** Its own comment sets it as a rule rather than a
figure fitted to a reading, and it already describes this exact failure one step
earlier — a breach that "said the repository had grown, not that the detectors
had degraded, which is not what a guard is for". What grew this time is that the
repository now contains an audit of four repositories that are not it. So the
guard's population is narrowed to prose about this repository and the rule stays
at one in three, which is also what spec 0002 §6 asks for: the acceptance run's
report is evidence, and evidence is never asserted in a test. Both readings are
recorded in the test beside the exclusion, so neither is hidden by it.

## Kill conditions, checked against both parts

Spec 0001 §13 and spec 0002 §12, checked before any phase 2 work starts.

| condition | checked against | result |
|---|---|---|
| It agrees with the hand-built indexes and surfaces nothing they did not already show | both parts | **Not met.** Three files losing recognition to a share rule, Merit-knowledge's exact zero, the 157 link-display-text rows and two repaired output defects were none of them known before this run. |
| Its output starts being pasted into documents, or anyone asks it to write one | both parts | **Not met.** Every figure here is quoted into a ticket by hand with its detector version attached, which is the citation rule, not the tool authoring prose. |
| The cold-start number rises during its existence | — | **Not measurable, recorded as a coverage gap.** The cold-start burden is spec 0001 §9, phase 2, behind Candidate A — which Gate A has now closed. This condition has no reading and will not acquire one on the current plan. |
| It needs its own store, its own query language, or a second implementation | both parts | **Not met.** One DuckDB file, plain SQL, one implementation. Every query in Part 3 and Part 4 is SQL a reader can rerun. |
| Someone reaches for it to decide something rather than to check something | both gates | **Not met, and tested.** Both gate decisions rest on figures the tool produced, and both decisions are *not built* — the tool was used to check two proposals and neither survived. |
| Recognition is widened until it matches everything | Part 1 | **Not met.** 87 of 201 files in C0; 35 of 1,348 in Home-system; 0 of 11 in Merit-knowledge. No detector was added during this ticket. |
| The three states come back indistinguishable | Part 1 | **Not met.** 87, 103 and 126 surfaces; 201, 323 and 515 files; 781,674, 853,575 and 946,722 surface bytes. |
| The comparison needs a new store, a second index, or a query language of its own | Part 1 | **Not met.** One `compare` invocation, one store. |
| Anyone reaches for the comparison to decide something rather than to check something | Part 1 | **Not met.** The comparison established the base and was read for no decision. |

**No kill condition is met. Phase 2 is not entered regardless**, because both
gates closed, which is the outcome that makes phase 2's contents empty rather
than blocked.

## The pass marks, applied

Spec 0002 §9, set before any data and applied here unchanged.

- **A measurable difference between C0, C1 and C2** — shown above, on the
  detector set that existed when the run started.
- **Recognition on Advisor-Desk reconciles against the hand count** — 87
  surfaces in C0, unchanged from ticket 12's file-by-file reconciliation; the
  +16 in C1 is sixteen named `SKILL.md` files and nothing else.
- **No finding asserts something false.** Two output defects that would have put
  a false reading in front of a reader were found and repaired, and are recorded
  above rather than quietly fixed.
- **Every question the run could not address is recorded as a coverage gap** —
  C2's shallow clone, the cold-start condition having no reading, and the three
  hand-built repositories being read from shallow clones with no history, so
  nothing here rests on their lineage.

## Vocabulary

Checked with the project's own `offending_words` over every tool-authored output
this ticket produced — the three-state comparison and all three repository maps.
**Clean: no forbidden word in any of them.**

The rule is over tool-authored output, which is what was checked. This ticket's
own prose carries some of the words on purpose, in the two places prose has to:
where the ticket states the rule, and in the acceptance line that asks for a
rate read out per detector. Neither is the tool describing a file.

## Acceptance

- [x] The lineage comparison is re-run and its head named by commit — `dc8d743`
- [x] The base is established from the rows and the trees before any delta is read
- [x] Every repository in the estate appears in one of the two parts, and which
      part it is in is stated
- [x] No delta is reported for a repository with no shared base
- [x] The three questions for Gate A were written down before the data was examined
      — committed in `dc8d743`, on its own, before the first query
- [x] Each Gate A question is marked answerable or not, with the SQL attempted
- [x] 50 findings sampled and hand-classified, with the rate broken down by
      detector and by family
- [x] Both gate decisions recorded — both are *not built*, which is a result
- [x] Any surface delta that moved because a corpus share moved says so — C2's
      −3, and C1's zero stated as well
- [x] Kill conditions checked against both parts before any phase 2 work starts
- [x] Output contains no forbidden vocabulary word

## Either gate closing is a result, not a failure

Both closed. Recorded here with the evidence, so a future session sees that the
load ledger and the evidence columns were tested against the estate rather than
argued about, and does not propose either from scratch.

**What closing them settles:** phase 1 is the tool. There is no phase 2 on the
current plan, and spec 0001 §9's cold-start work — which depended on Candidate
A — has no route through it.

**What it does not settle:** the estate has now been indexed once, and the two
families read very differently. Whether that difference is worth acting on is a
recomposition question, which spec 0002 §11 keeps out of scope until after the
audit. The audit is this ticket. The question is open, and it is Dylan's.
