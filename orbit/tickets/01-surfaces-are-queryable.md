# 01 — Surfaces are queryable

**Blocked by:** nothing. This is the frontier.
**Demo when done:** instruction surfaces from a real repository, queried from our own DuckDB file and joined to GitLab Orbit's `gl_file` rows via a read-only attach.

The tracer bullet. Deliberately the heaviest ticket, because it carries the full path once so every later ticket is an extension rather than a retrofit.

## Do

1. Ontology YAML for `Surface`, in GitLab's node format — `node_type`, `domain`, `description`, `label`, `destination_table`, `default_columns`, `sort_key`, `properties`, `storage.columns`. Copy the shape of their `source_code/file.yaml`.
2. `orbit-context index <path>`: walk the path, find git repositories, read branch and commit for each.
3. Detect instruction surfaces by filename convention: `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.cursorrules`, `.github/copilot-instructions.md`.
4. Create `~/.orbit-context/context.duckdb` if absent. Create the table **from the YAML**, not from a hardcoded `CREATE TABLE`, and write rows. Never open their file for writing.
5. Emit JSON statistics in their shape: surfaces, skipped, errored, each with a `reason`.
6. Fixture: a script that builds a throwaway two-repo estate in a temp dir, with root and nested surfaces.

## Acceptance

- [x] `orbit local sql --db ~/.orbit-context/context.duckdb "SELECT path, surface_kind, size_bytes FROM gl_context_surface"` returns rows
- [x] With `ATTACH '<their file>' AS orbit (READ_ONLY)`, a join from `gl_context_surface` to `orbit.gl_file` on `path` returns rows for a repo indexed by both tools
- [x] `orbit sql` and `orbit index` keep working **while** our indexer holds its write lock
- [x] Adding a column to the YAML changes the table without touching Python
- [x] Re-running the index does not duplicate rows
- [x] Statistics JSON reports a non-zero skipped or errored count on a fixture containing a binary file

Each is pinned by test in `orbit/tests/`: `orbit/tests/test_index.py` for the query, the
re-index and the statistics, `orbit/tests/test_ontology.py` for the YAML-driven column,
`orbit/tests/test_join.py` for the attach and the lock. The join runs against a `gl_file`
table built from the DDL of a graph written by `orbit 0.118.1`, in its own
file, attached read-only — so it holds without a live Orbit install, and it is
their column shape being joined, not an approximation of it.

## Watch for

**Never open their file read-write.** DuckDB's lock is exclusive across processes — a write lock on their file locks out `orbit sql`, `orbit index` and `orbit mcp` entirely, not just for writing. Attach read-only, join, detach.

The attach does not persist for a fresh connection. Anything needing the join must do the ATTACH itself.

`traversal_path` must match the convention their rows use. Get it wrong and the join returns **zero rows silently** rather than erroring — it will look like "no surfaces found".

Build the fixture with a script, not as a committed tree. Committing real repositories means nested `.git` directories that every clone and tool then has to special-case.
