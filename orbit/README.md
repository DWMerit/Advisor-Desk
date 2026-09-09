# Orbit Context

A context domain in its own DuckDB file (`~/.orbit-context/context.duckdb`),
beside GitLab Orbit's. A Python indexer writes `gl_context_*` tables; Orbit's
graph is ATTACHed **read-only** when a cross-domain join is wanted.

**Why a separate file.** DuckDB takes an exclusive lock across processes, and
it covers reads too: while one process holds a file for writing, no other
process can open it at all. Writing into `~/.orbit/graph.duckdb` would shut
`orbit sql`, `orbit index` and `orbit mcp` out for the length of every index
run, and an open MCP session would shut the indexer out. Tested both ways;
`tests/test_join.py` pins the behaviour.

The cost, since it is a real one: the attach does not persist to a fresh
connection, so a query spanning both graphs runs only from a connection that
attaches. Orbit's CLI reads one file or the other.

Spec: `orbit/specs/0001-observation-foundation.md`. Tickets: `orbit/tickets/`.

Phase 1, ticket 01. One node type — `Surface` — detected by filename convention.

## Run it

```sh
# Index an estate. Walks the path, finds every git repository under it.
orbit/bin/orbit-context index /home/user

# Per-file skipped and errored detail as well as counts.
orbit/bin/orbit-context index /home/user --stats

# Somewhere other than ~/.orbit-context/context.duckdb.
orbit/bin/orbit-context index /home/user --db /tmp/scratch.duckdb
```

Then query it with Orbit's own CLI, pointed at our file:

```sh
orbit local sql "SELECT path, surface_kind, size_bytes FROM gl_context_surface
                 ORDER BY size_bytes DESC"

orbit local sql "SELECT c.path, c.surface_kind, c.size_bytes, f.language
                 FROM gl_context_surface c
                 JOIN gl_file f ON f.path = c.path AND f.project_id = c.project_id
                 ORDER BY c.size_bytes DESC"
```

Requires Python 3 and `duckdb`; `pyyaml` for reading the ontology.

## Tests

```sh
python3 -m unittest discover -s orbit/tests -t .
```

They build a throwaway two-repository estate in a temp directory
(`orbit/fixtures/build_estate.py`) and index it into a temp DuckDB. Nothing
touches `~/.orbit/graph.duckdb` or `~/.orbit-context/context.duckdb`. The fixture is built by script, never
committed: a committed fixture would mean nested `.git` directories that every
clone and tool then has to special-case.

## The two conventions that must match Orbit exactly

Both are silent when wrong — the join returns zero rows rather than erroring,
and it reads as "no surfaces found".

**`traversal_path` is the empty string.** Orbit's local linker pushes `""` for
every row (`crates/code-graph/src/v2/linker/graph.rs`). Repositories are told
apart by `project_id`, not by traversal path.

**`project_id` is Rust's `DefaultHasher` over the canonical repository path**,
sign bit cleared (`crates/orbit-local/src/workspace.rs::project_id_from_path`).
That is SipHash-1-3 with zero keys, over the UTF-8 bytes plus Rust's `0xff`
string terminator. Reimplemented in `orbit_context/workspace.py` so a repository
Orbit has not indexed still gets the id Orbit would give it, and pinned by test
vectors read out of a real `graph.duckdb` in `orbit/tests/test_workspace.py`.

**Paths are repository-relative.** Because both facts hold, `JOIN ... ON path`
alone will match a same-named file in a different repository. Join on
`path AND project_id`.

## The table comes from the YAML

`orbit/ontology/nodes/context/surface.yaml` is written in GitLab's node format,
copied from their `config/ontology/nodes/source_code/file.yaml`, so it can be
overlaid onto their ontology tree or contributed upstream unchanged.

The indexer builds the DuckDB table from that file's `storage.columns`. Adding a
column to the YAML adds it to the table on the next index; no Python change.
ClickHouse storage types are mapped to DuckDB types (`Int64` → `BIGINT`,
`String` and `LowCardinality(String)` → `VARCHAR`); an unmapped type fails the
index rather than guessing.

`content` is declared `virtual` and is never stored. The row carries a path; the
caller reads the bytes.

## What counts as a surface

Phase 1 detects `instruction-surface` only, by filename:

| Matched on | Names |
|---|---|
| basename | `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.cursorrules` |
| repository-relative path | `.github/copilot-instructions.md` |

`node_modules`, `target`, `vendor`, `.venv`, `venv`, `__pycache__` and `.git`
are not walked.

## Coverage is a record, not a footnote

Every candidate becomes a row, including ones that could not be read. The
`reason` column is empty for a surface that indexed, and otherwise carries why:

| `reason` | Means |
|---|---|
| *(empty)* | Indexed. |
| `invalid_utf8` | Named like a surface, not decodable as UTF-8. |
| `oversize` | Larger than 5 MiB. |
| `read_error` | The filesystem refused the read. |
| `not_a_file` | The path is not a regular file. |

One case produces no row, because it has no branch or commit to carry:
`outside_indexed_repository`, a surface under the indexed root that belongs to
no git repository. It is reported in the statistics so that a surface which is
present but unindexed does not read as a surface that is absent.

## Statistics

`index` prints JSON in Orbit's shape — `repository`, `path`, `time_seconds`,
`graph`, `processing`, `database_path`, and `detailed` under `--stats`. Skipped
entries carry `reason`, errored entries carry `kind`, matching their
`SkippedFile` and `ErroredFile`. A `repositories` array itemises each repository
found under the indexed root, and a `schema` block reports which columns the
YAML added to the table.

## Re-indexing

Re-indexing replaces the rows for the indexed
`(traversal_path, project_id, branch, commit_sha)` rather than adding a second
copy. `project_id` is part of that key because every local row carries the same
empty `traversal_path`. Row ids are derived from the same tuple plus the path,
so they are stable across re-index.

Snapshots on different commits coexist, which is Orbit's own semantics. A commit
that moves leaves the previous snapshot's rows in place.

## Constraints held here

- **Never writes to Orbit's tables.** `store.assert_context_table` refuses any
  table not prefixed `gl_context_`.
- **No prose columns.** No `summary`, no `purpose`.
- **Constrained vocabulary** on tool-authored fields — reasons, surface kinds,
  column names, statistics keys. Enforced by `orbit/tests/test_vocabulary.py`,
  never over paths or quoted system messages.

## Open, not decided

- `gl_context_surface` in the live graph carries four columns from an earlier
  prototype — `client`, `activation`, `evidence_class`, `detector`. All four are
  phase 2/3 candidates gated behind the tests in spec §6, so phase 1 does not
  declare or write them. The indexer leaves them alone and names them on stderr.
  Dropping the table so it matches the ontology exactly is a decision for Dylan,
  not something the indexer does on its own.
- The indexed roots, and whether `~/.claude/` and other user-global surfaces are
  inside them, are spec §12 items and still Dylan's to set. `index` takes
  whatever path it is given.
