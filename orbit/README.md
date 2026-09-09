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

Phase 1, tickets 01–02. One node type — `Surface` — covering every governance
object: instruction surfaces, skill packages, agent definitions, slash commands,
hook definitions and MCP servers.

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
orbit local sql "SELECT surface_kind, name, path, size_bytes FROM gl_context_surface
                 ORDER BY size_bytes DESC"

# What a cold session pays for skills, against what the files weigh.
orbit local sql "SELECT sum(frontmatter_bytes) AS boot, sum(size_bytes) AS total
                 FROM gl_context_surface WHERE surface_kind = 'skill-package'"

# Every hook, where it is defined, and where its command goes.
orbit local sql "SELECT path || ':' || start_line AS locator, name, matcher,
                        target_resolution, target_path
                 FROM gl_context_surface
                 WHERE surface_kind = 'hook-definition' ORDER BY locator"

orbit local sql "SELECT c.path, c.surface_kind, c.size_bytes, f.language
                 FROM gl_context_surface c
                 JOIN gl_file f ON f.path = c.path AND f.project_id = c.project_id
                 ORDER BY c.size_bytes DESC"
```

Requires Python 3 and `duckdb`; `pyyaml` for reading the ontology and
Markdown frontmatter. JSON is read by `orbit_context/jsonloc.py`, which keeps
every value's position so a hook entry can carry a `file:line` locator.

## Tests

```sh
python3 -m unittest discover -s orbit/tests -t .
```

They build a throwaway three-repository estate in a temp directory
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

Six kinds, plus one that is additive. Not all of them are files.

| `surface_kind` | Detected by |
|---|---|
| `instruction-surface` | basename `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.cursorrules`; path `.github/copilot-instructions.md` |
| `skill-package` | a directory holding a `SKILL.md` whose frontmatter declares `name` and `description` |
| `agent-definition` | a `.md` file under `.claude/agents/` whose frontmatter declares `name` and `description` |
| `command-definition` | a `.md` file under `.claude/commands/` |
| `hook-definition` | one command entry inside a settings file's `hooks` block |
| `mcp-config` | one server inside `mcpServers` (or VS Code's `servers`), in `.mcp.json`, `.cursor/mcp.json`, `.vscode/mcp.json` or a settings file |
| `hook-target` | a file a hook command resolves to |

Settings files read: `.claude/settings.json` and `.claude/settings.local.json`.

`node_modules`, `target`, `vendor`, `.venv`, `venv`, `__pycache__` and `.git`
are not walked.

**Rows are additive.** A hook script is a hook target *and* whatever else it is.
`hook-target` is written as well as, never instead of, another kind for the same
file — a `SKILL.md` invoked by a hook is two rows, not one argument about which
it really is. Two hooks pointing at one script still make one `hook-target` row.

A `SKILL.md` or an agent file that declares no `name` and `description` is not
one. It is reported in the statistics as `frontmatter_declaration_absent`, so
that a file which is present but not a skill does not read as absent.

## Not every surface is a file

A hook definition and an MCP server are entries *inside* a file. Those rows
carry a line locator and the size of the entry:

| Column | Whole-file surface | Entry inside a file |
|---|---|---|
| `path` | the file | the file the entry sits in |
| `start_line` / `end_line` | NULL | the entry's span, 1-based |
| `size_bytes` | the file size | the entry's bytes |

So `path || ':' || start_line` is the locator for a hook, and
`WHERE start_line IS NULL` is how to ask for whole-file surfaces only.

## Frontmatter is measured apart from the body

`frontmatter_bytes` and `body_bytes` sum to `size_bytes` for anything read as
text. They are separate columns because they load at different times: a skill's
frontmatter description loads at boot for **every** session, and the body only
when the skill is invoked. Conflating them misstates the boot cost by an order
of magnitude — measured over 12 real skill packages:

```
sum(size_bytes)        214,398
sum(frontmatter_bytes)   8,341     <- what a cold session actually pays
```

Both are NULL, never 0, for a surface that was not read as text. 0 means
measured and absent; NULL means unknown.

## Where a hook command points

Each `hook-definition` row carries its `matcher` **quoted verbatim** from the
settings file, and where its command resolved:

| `target_resolution` | Means | `target_path` |
|---|---|---|
| `in-tree` | The command names a file in this repository. | that file, repository-relative |
| `path-lookup` | Nothing in the command looks like a path; the program is found on `PATH`. | empty |
| `no-indexed-target-match` | The command names a path, and no file is there. | empty |
| `unexpanded-variable` | The path holds a variable this indexer does not expand. | empty |
| `unparsable-command` | The command line could not be split into words. | empty |

`$CLAUDE_PROJECT_DIR` is expanded; nothing else is. The distinction the ticket
asks for is the first two rows of that table: *"we cannot see where this program
lives"* and *"the script is not here"* are different statements about the
estate, and are never merged.

`matcher` is NULL where the entry declares no matcher key, and empty where it
declares an empty one.

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

Three cases produce no row, and are reported in the statistics instead, so that
a surface which is present but unindexed does not read as a surface that is
absent:

| Reported | Why there is no row |
|---|---|
| `outside_indexed_repository` | A surface under the indexed root belonging to no git repository: no branch or commit to carry. |
| `frontmatter_declaration_absent` | A `SKILL.md` or agent file that declares no `name` and `description`. Calling it a skill would be the tool deciding. |
| `invalid_json` | A settings or `.mcp.json` file that would not parse. Its hooks and servers are entries inside it; with the file unread there is nothing to write a row about. |

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
