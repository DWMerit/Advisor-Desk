# Phase 1 — Orbit Context

Spec: `orbit/specs/0001-observation-foundation.md`

Seven tickets. Frontier is **01** alone. Work top to bottom, or take any ticket whose blockers are done.

| # | Ticket | Blocked by |
|---|---|---|
| 01 | Surfaces are queryable | — |
| 02 | Every governance object is a surface | 01 |
| 03 | A single rule is addressable | 01 |
| 04 | Pointers resolve; non-resolution is classified | 02 |
| 05 | Identical bytes, reported with provenance | 02 |
| 06 | Governance orientation in one command | 03, 04, 05 |
| 07 | Audit the estate, and both gates | 06 |

**Prefactoring: none.** Greenfield — there is nothing to make easy first.

## What phase 1 is

A faithful small **Orbit over the estate's governance surface** — the half GitLab Orbit does not parse. Their architecture, storage, query surface, ontology format, command names. Only the domain changes: `source_code` → `context`.

**Not in phase 1:** the load ledger, evidence columns, `would-load`, `setup`, cross-branch reading. Both additions are gated behind tests that can only run after phase 1 has been used (ticket 07).

## Architecture, already verified

Context tables live **inside GitLab Orbit's own DuckDB** at `~/.orbit/graph.duckdb`. A separate Python indexer writes `gl_context_*`; their CLI queries it and joins it to their code graph:

```
orbit sql "SELECT c.path, c.surface_kind, f.language
           FROM gl_context_surface c JOIN gl_file f ON f.path = c.path"
```

`orbit sql` is the query engine, `orbit mcp` is the agent surface. Neither gets built.

## Rules for every ticket

- **Never write to their tables.** Only `gl_context_*`.
- Their column conventions: `id`, `traversal_path`, `project_id`, `branch`, `commit_sha`, `path`, `name`, `size_bytes`, `reason`.
- **No prose columns.** No `summary`, no `purpose`. Rows carry paths and offsets; callers read bytes.
- **Vocabulary constraint** on tool-authored fields: never *broken, dangling, orphaned, obsolete, stale, dead, unused, duplicate, redundant, misplaced, wrong, should, safe to delete*. Paths and quotes are exempt — they carry the estate's own words.
- Every node and edge type is declared in **ontology YAML in GitLab's format** before the indexer writes it. Adding a column means editing YAML, not Python.
- **Tests ship with the ticket that needs them.** No test ticket at the end.
- Python 3 + `duckdb`. Parsing is Markdown/JSON/TOML, not tree-sitter.
- Re-index replaces rows for the indexed `(traversal_path, branch, commit_sha)`.
