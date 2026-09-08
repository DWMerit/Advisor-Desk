# Phase 1 — Orbit Context (parent)

Spec: `orbit/specs/0001-observation-foundation.md`

## What phase 1 is

A faithful small **Orbit over the estate's governance surface** — the half GitLab Orbit does not parse. Their architecture, storage, query surface, ontology format and command names. Only the domain changes: `source_code` → `context`.

**Not in phase 1:** the load ledger, evidence columns, `would-load`, `setup`, cross-branch reading. Both additions are gated behind tests that can only run after phase 1 has been used (spec §6).

## Architecture, already verified

Context tables live **inside GitLab Orbit's own DuckDB** at `~/.orbit/graph.duckdb`. A separate Python indexer writes `gl_context_*`; their CLI queries it and joins it to their code graph:

```sql
orbit sql "SELECT c.path, c.surface_kind, f.language
           FROM gl_context_surface c JOIN gl_file f ON f.path = c.path"
```

`orbit sql` is the query engine and `orbit mcp` is the agent surface. Neither gets built.

## Rules for every slice

- **Never write to their tables.** Only `gl_context_*`.
- Their column conventions: `id`, `traversal_path`, `project_id`, `branch`, `commit_sha`, `path`, `name`, `size_bytes`, `reason`.
- **No prose columns.** No `summary`, no `purpose`. Rows carry paths and offsets; callers read bytes.
- **Vocabulary constraint** on tool-authored fields: never *broken, dangling, orphaned, obsolete, stale, dead, unused, duplicate, redundant, misplaced, wrong, should, safe to delete*. Paths and quotes are exempt — they carry the estate's own words.
- The three negative findings stay distinct: `no-indexed-target-match`, `outside-indexed-roots`, `unresolvable-scheme`.
- Python 3 + `duckdb`. Parsing is Markdown/JSON/TOML, not tree-sitter.
- Re-index replaces rows for the indexed `(traversal_path, branch, commit_sha)`.

## Exit

Slice 7 done → run over the real estate. **That run is the estate audit and the input to both gates.**
