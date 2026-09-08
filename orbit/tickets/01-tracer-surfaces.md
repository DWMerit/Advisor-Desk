# 01 — Tracer: surfaces into DuckDB, queryable by their CLI

**Tracer bullet. Thin end to end, nothing wide.**

## Do

`orbit-context index <path>`:
- walk the given path, find git repos, read `branch` and `commit_sha` per repo
- detect instruction surfaces by filename convention: `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.cursorrules`, `.github/copilot-instructions.md`
- write `gl_context_surface`: `id`, `traversal_path`, `project_id`, `branch`, `commit_sha`, `path`, `surface_kind`, `size_bytes`, `reason`
- emit JSON statistics like theirs: surfaces, skipped, errored

## Done when

```
orbit sql "SELECT path, surface_kind, size_bytes FROM gl_context_surface ORDER BY size_bytes DESC"
orbit sql "SELECT c.path, c.surface_kind, f.language FROM gl_context_surface c JOIN gl_file f ON f.path = c.path"
```
both return rows on a repo indexed by both tools.

## Not in this slice

Skills, agents, hooks, clauses, pointers, hashes. Only instruction surfaces.

## Watch for

`traversal_path` must match the convention their rows use, or the join fails silently and returns zero rows rather than erroring.
