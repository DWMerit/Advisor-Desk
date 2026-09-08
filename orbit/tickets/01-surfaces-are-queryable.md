# 01 — Surfaces are queryable

**Blocked by:** nothing. This is the frontier.
**Demo when done:** `orbit sql` returns instruction surfaces from a real repository, joined to GitLab Orbit's own `gl_file` rows.

The tracer bullet. Deliberately the heaviest ticket, because it carries the full path once so every later ticket is an extension rather than a retrofit.

## Do

1. Ontology YAML for `Surface`, in GitLab's node format — `node_type`, `domain`, `description`, `label`, `destination_table`, `default_columns`, `sort_key`, `properties`, `storage.columns`. Copy the shape of their `source_code/file.yaml`.
2. `orbit-context index <path>`: walk the path, find git repositories, read branch and commit for each.
3. Detect instruction surfaces by filename convention: `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.cursorrules`, `.github/copilot-instructions.md`.
4. Create the table **from the YAML**, not from a hardcoded `CREATE TABLE`, and write rows.
5. Emit JSON statistics in their shape: surfaces, skipped, errored, each with a `reason`.
6. Fixture: a script that builds a throwaway two-repo estate in a temp dir, with root and nested surfaces.

## Acceptance

- [ ] `orbit sql "SELECT path, surface_kind, size_bytes FROM gl_context_surface"` returns rows
- [ ] `orbit sql` joining `gl_context_surface` to `gl_file` on `path` returns rows for a repo indexed by both tools
- [ ] Adding a column to the YAML changes the table without touching Python
- [ ] Re-running the index does not duplicate rows
- [ ] Statistics JSON reports a non-zero skipped or errored count on a fixture containing a binary file

## Watch for

`traversal_path` must match the convention their rows use. Get it wrong and the join returns **zero rows silently** rather than erroring — it will look like "no surfaces found".

Build the fixture with a script, not as a committed tree. Committing real repositories means nested `.git` directories that every clone and tool then has to special-case.
