# Gate A re-run, with the `client` column in the graph

**What this is.** The benefit test spec 0004 names, run. Gate A's three
questions were committed on their own in `dc8d743`, before any query was run
against the phase-1 tables, and they are re-run here **unchanged**. Each is
marked answerable or not, with the SQL attempted either way — the same form
ticket 07 used, so the two readings sit side by side.

**What this is not.** It does not decide Gate A. Spec 0003 §3.1 records the gate
as undecided until a benefit test shows the column earns its place, and
`orbit/specs/0004-the-client-column.md` says in its own last line that Dylan
decides. This record builds no case either way; it reports what the SQL returned.

**No new rule is pre-registered here.** Writing one now would be writing a rule
after seeing the data it runs on, which is the move both gates exist to stop.

---

## The run

| | |
|---|---|
| detector set version | `1.8eabab386316` — the figure spec 0004 requires, unmoved |
| repositories | the four ticket 07 audited |
| surface rows | 319 |
| surface bytes | 2,552,315 |

Ticket 07 measured 318 rows and 2,548,836 bytes. One row and 3,479 bytes
separate the two readings, so the estate is close enough to the one those
figures came off that the comparison below is a comparison of derivations
rather than of estates. Two further repositories were in the index run and are
left out of every figure here, because they were not in ticket 07's population.

### The split the column produces

```sql
SELECT s.client, count(*), sum(s.size_bytes)
FROM current_surface s
JOIN current_run r USING (traversal_path, project_id, branch, commit_sha)
GROUP BY 1 ORDER BY 2 DESC;
```

| `client` | rows | surface bytes |
|---|---|---|
| UNKNOWN | 213 | 1,534,274 |
| claude | 104 | 1,015,454 |
| codex | 2 | 2,587 |

**66.8% of rows and 60.1% of surface bytes are UNKNOWN.** Ticket 07's reading
was 237 of 318 rows and 1,707,616 of 2,548,836 bytes — 74.5% and 67.0%.

### Where the two readings differ, row by row

The honesty check spec 0004 sets is that a derivation producing materially
fewer UNKNOWNs has begun inferring. It produces 24 fewer, and none of the 24 is
an inference: every one is a filename or a path a vendor defined, which ticket
07's query did not have a branch for. Its query had three — `CLAUDE.md`,
`AGENTS.md`, and anything under `.claude/` — and is re-run here on this same
snapshot to separate the estate having changed from the derivation being wider:

```sql
SELECT CASE
         WHEN s.path = 'CLAUDE.md'  THEN 'named'
         WHEN s.path = 'AGENTS.md'  THEN 'named'
         WHEN s.path LIKE '.claude/%' THEN 'named'
         ELSE 'not named by that query'
       END, count(*), sum(s.size_bytes)
FROM current_surface s
JOIN current_run r USING (traversal_path, project_id, branch, commit_sha)
GROUP BY 1;
-- named                     82   844,699
-- not named by that query  237 1,707,616
```

**82 and 237, against the 81 and 237 ticket 07 recorded.** The estate moved by
one row. The whole of the remaining difference is the derivation, and it is 24
rows and 173,342 bytes:

| how the column names it | rows | bytes | what they are |
|---|---|---|---|
| a filename this vendor defined | 22 | 172,012 | 22 `SKILL.md` files outside any `.claude/` directory — 16 published skills and 3 eval outputs in agent-rules-books, 1 tool skill in Estimating-Lab, 2 under a retired directory in Home-system |
| a filename this vendor defined | 1 | 1,164 | an `AGENTS.md` below the repository root, in agent-rules-books' `evals/` |
| a path this vendor defined | 1 | 166 | Home-system's root `.mcp.json` |

Every one is a name a vendor defined, read where the estate wrote it. The
question of whether a `SKILL.md` outside `.claude/` should count is a question
about the derivation, not about the data, and it is visible here rather than
folded into a total.

### The identity that holds exactly

```sql
SELECT s.recognition, s.client, count(*) FROM current_surface s
JOIN current_run r USING (traversal_path, project_id, branch, commit_sha)
GROUP BY 1, 2;
-- vendor-name      claude   104
-- vendor-name      codex      2
-- declared-marker  UNKNOWN  168
-- corpus-adjacent  UNKNOWN   45
```

**Every row a vendor named carries a client, and every row no vendor named
carries UNKNOWN. There is no third case.** That is the derivation's whole
claim, and it is checkable in one query rather than trusted.

---

## Q1 — which surfaces reach a session when it opens, and what do they weigh?

*"The cold-start bill, per client. Not 'which surfaces exist' — which ones
arrive without anybody asking for them."*

**The per-client half is now answerable, for 106 of 319 rows. The
"without anybody asking" half is not answerable, for any row.**

Ticket 07 attempted three routes and marked all three short. Route three was:

```sql
SELECT client FROM gl_context_surface LIMIT 1;
-- Binder Error: Referenced column "client" not found in FROM clause!
```

That route now returns rows, and the per-client bill is the query at the top of
this record. What it gives is 1,015,454 bytes claimed by Claude and 2,587 by
Codex across four repositories, against 1,534,274 bytes that no vendor's naming
claims at all.

What it does not give is the word *reach*. A row saying Claude's naming claims a
surface is not a row saying a Claude session loads it at open. The two come
apart on the estate's largest single group:

```sql
SELECT s.client, count(*), sum(s.frontmatter_bytes), sum(s.body_bytes)
FROM current_surface s
JOIN current_run r USING (traversal_path, project_id, branch, commit_sha)
WHERE s.surface_kind = 'skill-package' GROUP BY 1;
-- claude  88  49,819 frontmatter  890,446 body
```

Eighty-eight skill packages, 940,265 bytes, all of them Claude's by name. 49,819
bytes of that are frontmatter, which a session pays for at open; 890,446 are
body, which it pays for only when the skill is invoked. **Which figure is the
cold-start bill is not in the row**, and telling them apart is `activation`,
which spec 0004 puts out of scope and which is not built. The measurement above
is a ceiling on the bill, not the bill.

So: the column moved Q1 from *no route at all* to *a per-client total with an
unmeasured multiplier on it*. Whether that is an answer is the reading, and the
reading is not this record's to make.

## Q2 — of the bytes that reach a session, which are paid for twice?

**Not answerable. The column made no difference to it at all, and the figure is
zero.**

Ticket 07 found the first half fully answerable — which content exists twice is
in the graph, every pair named — and the second half blocked on not knowing
whether anything loads the second end. With `client` on both ends, that is now
one join:

```sql
SELECT coalesce(a.client, 'not a surface'), coalesce(b.client, 'not a surface'),
       count(*)
FROM current_edge e
JOIN current_run r USING (traversal_path, project_id, branch, commit_sha)
LEFT JOIN current_surface a ON a.project_id = e.project_id AND a.branch = e.branch
  AND a.commit_sha = e.commit_sha AND a.path = e.source_path
LEFT JOIN current_surface b ON b.project_id = e.project_id AND b.branch = e.branch
  AND b.commit_sha = e.commit_sha AND b.path = e.target_path
WHERE e.relationship_kind = 'IDENTICAL_BYTES'
GROUP BY 1, 2 ORDER BY 3 DESC;
```

| one end | other end | pairs |
|---|---|---|
| UNKNOWN | UNKNOWN | 56 |
| not a surface | not a surface | 40 |
| claude | not a surface | 1 |

**Ninety-seven byte-identical pairs, and not one of them carries a client at
both ends.** Fifty-six are workbench-to-published rung pairs in the two lineage
repositories, where neither end carries a vendor name. Forty are pairs between
files that are not surfaces at all. The single remaining pair is the one spec
0004 and ticket 07 both named in advance: Home-system's root `CLAUDE.md` against
a workbench rung, Claude at one end and nothing at the other.

A column that answers a question needs both ends of the thing it is asked
about. Here it has one end of one pair.

## Q3 — which surfaces can a session stop paying for, and which are unconditional?

**Not answerable, exactly as predicted.**

```sql
SELECT activation FROM current_surface LIMIT 1;
-- Binder Error: Referenced column "activation" not found in FROM clause!
```

Ticket 07's reading was that Q3 misses `client` *and* `activation`, and that
`client` is "necessary for Q3 as well, and not sufficient". That reading is
confirmed by the Q1 figures above rather than merely repeated: 88 skill packages
now carry a client, and the 49,819/890,446 split between frontmatter and body is
in the graph, and the rows still cannot say which of the 890,446 a given session
pays for — because nothing observes a trigger.

Spec 0004 says a run in which all three questions suddenly answer should be
disbelieved before it is believed. This is not that run.

---

## The marks, in one table

| | ticket 07 | this run |
|---|---|---|
| Q1 | not answerable, no route | the per-client total is a query for 106 of 319 rows; "at open" is not answerable for any row |
| Q2 | not answerable, second half blocked | not answerable, and measured at 0 of 97 pairs attributable at both ends |
| Q3 | not answerable | not answerable, unchanged |

**One of three moved, and it moved partly.** Spec 0004's stated honest
expectation was "Q1 should answer for the 81 rows. Q2's answerable half already
answers and its other half will not. Q3 will not." Q2 and Q3 came out as
written. Q1 came out narrower than written: the column supplies the *per client*
half of Q1 and supplies nothing toward the *arrives without being asked for*
half, which the question states in its own second sentence.

**What it cost.** Two `LowCardinality(String)` columns on one table, 319 rows
here; one 150-line module with no branching beyond three table lookups; one test
file. No detector was edited and the detector set version is the same string
before and after, so every figure in tickets 07 and 14 remains comparable with
every figure above. Removing it is deleting a module, two YAML blocks, four
lines of the indexer and a test file — which is what spec 0004 means by calling
it reversible.

**What it did not cost.** Nothing was inferred. The 213 UNKNOWN rows are the
same 213 rows no vendor named, and they say so.

Reading this is Dylan's.
