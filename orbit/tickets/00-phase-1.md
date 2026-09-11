# Phase 1 — Orbit Context

Spec: `orbit/specs/0001-observation-foundation.md`

Seven tickets. **All seven are done. Phase 1 is finished.**

**07 ran, and both gates closed.** The estate was read in its two families:
the clone lineage as a controlled comparison at head `dc8d743`, the hand-built
family — Home-system, Estimating-Lab, Merit-knowledge — as an audit with no
baseline. Gate A: the load ledger is **not built**; `client` is the only
candidate column that survived the three questions, and where a vendor filename
names a client `path` already carries it, while for the 237 of 318 surface rows
no filename names, the estate states nothing to observe. Gate B: the four-way
`evidence_class` is **not built**, and the `detector` column the gate would have
opened for is already on every row as `subtype`, `recognition` and
`direction_reason`. The steady-state artifact rate is **8% over a 50-finding
sample**, against the 96% that came from one fixed bug.

**Both gates closing means phase 2 is empty rather than blocked**, and spec
0001 §9's cold-start work — which depended on Candidate A — has no route
through it. The full evidence is in `07-audit-and-gates.md`.

**07 originally did not run**, and the reason was closed before it did. Running
the indexer against this repository returned **0 surfaces from 238 files
walked** — recognition was by vendor filename, so a repository that is entirely
governance matched none of it. An estate audit on that indexer returns honest
zeros and teaches nothing. Spec 0002 and tickets 09–14
(`08-recognition-and-comparison.md`) closed the gap; ticket 14 re-scoped 07 and
handed it back runnable.

**Tickets 09 to 12 are done.** The same repository now returns **87 surfaces
from 254 files walked**, reconciled file by file against the hand count in `08`,
and its fourteen three-rung ladders are a first-class edge that can be asked for
by book. Its 28 byte-identical pairs each carry a direction or an explicit
UNKNOWN with the reason, and on this corpus all 28 are UNKNOWN — the relationship
is stated only in prose, and prose provenance stays a permanent UNKNOWN.
Recognition is no longer what blocks 07; tickets 13 and 14 are.
**Tickets 13 and 14 are done, and so is 07. There is no frontier** — the
sequence tracked in `08-recognition-and-comparison.md` is complete. Ticket
15 — a divergence from GitLab Orbit found while closing 12, which had to be
closed before the comparison ran or the comparison would have measured it — is
done: a symlink is now a node the walk lists and never reads, which took
`files_walked` up by the fourteen `full.md` links and left surfaces, pairs and
ladders where they were.

| # | Ticket | Blocked by |
|---|---|---|
| 01 | Surfaces are queryable | — |
| 02 | Every governance object is a surface | 01 |
| 03 | A single rule is addressable | 01 |
| 04 | Pointers resolve; non-resolution is classified | 02 |
| 05 | Identical bytes, reported with provenance | 02 |
| 06 | Governance orientation in one command | 03, 04, 05 |
| 07 | Audit the estate, and both gates | 06, 14 — **done, both gates closed** |

**Prefactoring: none.** Greenfield — there is nothing to make easy first.

## What phase 1 is

A faithful small **Orbit over the estate's governance surface** — the half GitLab Orbit does not parse. Their architecture, storage, query surface, ontology format, command names. Only the domain changes: `source_code` → `context`.

**Not in phase 1:** the load ledger, evidence columns, `would-load`, `setup`, cross-branch reading. Both additions were gated behind tests that could only run after phase 1 had been used (ticket 07). **Both gates have now run and both closed**, so neither addition is in any phase: they were tested against the estate and did not earn a place. `07-audit-and-gates.md` carries the evidence, so that a later session sees they were measured rather than merely considered.

## Architecture, already verified

Context tables live in **our own DuckDB file** at `~/.orbit-context/context.duckdb`. GitLab Orbit's graph is attached **read-only** when a cross-domain join is wanted:

```
ATTACH '~/.orbit/graph.duckdb' AS orbit (READ_ONLY);
SELECT c.path, c.surface_kind, f.language
FROM gl_context_surface c JOIN orbit.gl_file f ON f.path = c.path
```

**Why a separate file, not theirs.** DuckDB's file lock is exclusive across processes: while one process holds a file for writing, no other process can open it at all — not even read-only. Writing into their file means our indexer locks out `orbit sql` and `orbit mcp`, and an open MCP session locks out our indexer. Tested and confirmed. With a separate file, their CLI kept answering while we held our own write lock.

`orbit local sql --db ~/.orbit-context/context.duckdb` still works against our file, so their query surface serves our tables.

## Rules for every ticket

- **Never open their file for writing.** Read-only ATTACH only, and only when joining.
- Their column conventions: `id`, `traversal_path`, `project_id`, `branch`, `commit_sha`, `path`, `name`, `size_bytes`, `reason`.
- **No prose columns.** No `summary`, no `purpose`. Rows carry paths and offsets; callers read bytes.
- **Vocabulary constraint** on tool-authored fields: never *broken, dangling, orphaned, obsolete, stale, dead, unused, duplicate, redundant, misplaced, wrong, should, safe to delete*. Paths and quotes are exempt — they carry the estate's own words.
- Every node and edge type is declared in **ontology YAML in GitLab's format** before the indexer writes it. Adding a column means editing YAML, not Python.
- **Tests ship with the ticket that needs them.** No test ticket at the end.
- Python 3 + `duckdb`. Parsing is Markdown/JSON/TOML, not tree-sitter.
- Re-index replaces rows for the indexed `(traversal_path, branch, commit_sha)`.
