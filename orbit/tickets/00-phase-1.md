# Phase 1 — Orbit Context

Spec: `orbit/specs/0001-observation-foundation.md`

Seven tickets. Tickets 01–06 are done.

**07 did not run**, and the reason has since been closed. Running the indexer
against this repository returned **0 surfaces from 238 files walked** —
recognition was by vendor filename, so a repository that is entirely governance
matched none of it. An estate audit on that indexer returns honest zeros and
teaches nothing. Spec 0002 and tickets 09–14 (`08-recognition-and-comparison.md`)
close the gap; ticket 14 re-scopes 07 and hands it back runnable.

**Tickets 09 to 12 are done.** The same repository now returns **87 surfaces
from 254 files walked**, reconciled file by file against the hand count in `08`,
and its fourteen three-rung ladders are a first-class edge that can be asked for
by book. Its 28 byte-identical pairs each carry a direction or an explicit
UNKNOWN with the reason, and on this corpus all 28 are UNKNOWN — the relationship
is stated only in prose, and prose provenance stays a permanent UNKNOWN.
Recognition is no longer what blocks 07; tickets 15, 13 and 14 are.
**The frontier is 15**, tracked in `08-recognition-and-comparison.md` — a
divergence from GitLab Orbit found while closing 12, which has to be closed
before the comparison runs or the comparison measures it.

| # | Ticket | Blocked by |
|---|---|---|
| 01 | Surfaces are queryable | — |
| 02 | Every governance object is a surface | 01 |
| 03 | A single rule is addressable | 01 |
| 04 | Pointers resolve; non-resolution is classified | 02 |
| 05 | Identical bytes, reported with provenance | 02 |
| 06 | Governance orientation in one command | 03, 04, 05 |
| 07 | Audit the estate, and both gates | 06, **14** |

**Prefactoring: none.** Greenfield — there is nothing to make easy first.

## What phase 1 is

A faithful small **Orbit over the estate's governance surface** — the half GitLab Orbit does not parse. Their architecture, storage, query surface, ontology format, command names. Only the domain changes: `source_code` → `context`.

**Not in phase 1:** the load ledger, evidence columns, `would-load`, `setup`, cross-branch reading. Both additions are gated behind tests that can only run after phase 1 has been used (ticket 07).

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
