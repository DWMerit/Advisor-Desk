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

**Phase 1 is complete**: tickets 01–07, with 09–15 closing the recognition gap
07 needed. Both gated additions were tested against the real estate in ticket
07 and **both gates opened, each for far less than was drawn**: of the load
ledger's fourteen columns only `client`, and of the evidence columns only
`evidence_class`, since `detector` is already on every row as `subtype`,
`recognition` and `direction_reason`. The figures, and the two first-pass
decisions the ticket had to correct, are in
`orbit/tickets/07-audit-and-gates.md`.

Five node types and four edge types. `Surface` covers
every governance object — instruction surfaces, skill packages, agent
definitions, slash commands, hook definitions and MCP servers. `Clause` is one
addressable fragment inside a surface, and `CONTAINS` holds the two together.
`REFERENCES` is one pointer a surface or clause writes down, and `ExternalRef` is
where a pointer lands when it lands outside the graph. `IDENTICAL_BYTES` is two
files that hash the same, and `PRODUCES` is the provenance that explains a match
when the estate wrote any down. `IndexRun` and `CoverageNote` carry no edges:
they record what the walk covered and what it could not read, so a count read
back out of the graph arrives with its denominator and the detector set that
produced it.

## Run it

```sh
# Index an estate. Walks the path, finds every git repository under it.
orbit/bin/orbit-context index /home/user

# Per-file skipped and errored detail as well as counts.
orbit/bin/orbit-context index /home/user --stats

# Somewhere other than ~/.orbit-context/context.duckdb.
orbit/bin/orbit-context index /home/user --db /tmp/scratch.duckdb

# Bring a store whose columns have parted from the ontology back to it.
orbit/bin/orbit-context migrate --db /tmp/scratch.duckdb
```

Then read one rule back, by name, out of the file it lives in:

```sh
cd /path/to/the/repository
orbit/bin/orbit-context show 'CLAUDE.md#Estimating rules#M6 anchors'
```

The bytes go to stdout and the locator to stderr, so redirecting stdout gives
that span of the file and nothing else. `--repo` names a path inside the
repository if you are not standing in it.

Or read the whole repository at once, before doing anything else:

```sh
orbit/bin/orbit-context repo-map --repo /path/to/the/repository
```

Or ask for every byte-identical pair, each with the direction its evidence
supports or an explicit UNKNOWN and the reason there is none:

```sh
orbit/bin/orbit-context pairs --repo /path/to/the/repository
```

Or difference two states — or three, one of them in another repository — by
indexing each, subtracting against the first, and printing every state's own
figures beside every delta:

```sh
orbit/bin/orbit-context compare main HEAD --repo /path/to/the/repository
orbit/bin/orbit-context compare a7d7649 HEAD ../agent-rules-books@782a886 --repo .
```

Or ask one book for its ladder — every rung it was written at, largest first:

```sh
orbit/bin/orbit-context ladder refactoring --repo /path/to/the/repository

# Every ladder in the repository.
orbit/bin/orbit-context ladder --repo /path/to/the/repository
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

# Every rule in an instruction surface, with its address and what it weighs.
orbit local sql "SELECT fqn, end_byte - start_byte AS bytes, start_line
                 FROM gl_context_clause
                 WHERE surface_path = 'CLAUDE.md' AND clause_type = 'list-rule'
                 ORDER BY bytes DESC"

# How deep the nesting goes, walked over CONTAINS.
orbit local sql "WITH RECURSIVE walk(id, depth) AS (
                   SELECT target_id, 1 FROM gl_context_edge
                    WHERE relationship_kind = 'CONTAINS' AND source_kind = 'Surface'
                   UNION ALL
                   SELECT e.target_id, walk.depth + 1
                     FROM gl_context_edge e JOIN walk ON e.source_id = walk.id
                    WHERE e.relationship_kind = 'CONTAINS' AND e.source_kind = 'Clause')
                 SELECT c.surface_path, max(walk.depth) AS deepest
                 FROM walk JOIN gl_context_clause c ON c.id = walk.id
                 GROUP BY 1 ORDER BY 2 DESC"

# The three negative findings, kept apart. One row per address, not per mention.
orbit local sql "SELECT sub_kind, count(*) AS addresses
                 FROM gl_context_external_ref GROUP BY 1 ORDER BY 2 DESC"

# Which rule points where, with the locator and whether it sat in a fenced block.
orbit local sql "SELECT source_path || ':' || source_line AS locator, subtype,
                        target_address, target_kind, target_path, in_code_fence
                 FROM gl_context_edge
                 WHERE relationship_kind = 'REFERENCES' ORDER BY locator"

# Every address named in the estate that no file here matches, and who names it.
orbit local sql "SELECT x.address, count(*) AS mentions,
                        min(e.source_path || ':' || e.source_line) AS first_written
                 FROM gl_context_external_ref x
                 JOIN gl_context_edge e ON e.target_id = x.id
                 WHERE x.sub_kind = 'no-indexed-target-match'
                 GROUP BY 1 ORDER BY 2 DESC"

# Byte-identical pairs, each with whatever provenance either end carries.
# The two are read together on purpose: the pair count alone over-reads.
orbit local sql "SELECT i.source_path, i.target_path, p.subtype AS evidence,
                        p.source_path AS producer,
                        p.evidence_path || ':' || p.evidence_line AS evidenced_at
                 FROM gl_context_edge i
                 LEFT JOIN gl_context_edge p
                   ON p.relationship_kind = 'PRODUCES'
                  AND p.project_id = i.project_id
                  AND p.target_path IN (i.source_path, i.target_path)
                 WHERE i.relationship_kind = 'IDENTICAL_BYTES'
                 ORDER BY i.source_path"

# How many identical-byte pairs carry any provenance evidence at all.
orbit local sql "SELECT count(*) AS pairs,
                        count(*) FILTER (WHERE producer IS NOT NULL) AS with_provenance
                 FROM (SELECT i.source_path, max(p.source_path) AS producer
                       FROM gl_context_edge i
                       LEFT JOIN gl_context_edge p
                         ON p.relationship_kind = 'PRODUCES'
                        AND p.project_id = i.project_id
                        AND p.target_path IN (i.source_path, i.target_path)
                       WHERE i.relationship_kind = 'IDENTICAL_BYTES'
                       GROUP BY i.source_path, i.target_path)"

# Every producer the estate names, on the rung of evidence it stands on.
orbit local sql "SELECT subtype AS evidence, source_path AS producer,
                        target_path AS artifact, source_address AS named_as,
                        evidence_path || ':' || evidence_line AS evidenced_at
                 FROM gl_context_edge
                 WHERE relationship_kind = 'PRODUCES' ORDER BY subtype, artifact"

# What the estate declares superseded, beside the surface that still loads.
orbit local sql "SELECT e.source_path || ':' || e.source_line AS claimed_at,
                        e.target_address, s.surface_kind, s.size_bytes
                 FROM gl_context_edge e
                 LEFT JOIN gl_context_surface s
                   ON s.path = e.target_path AND s.project_id = e.project_id
                 WHERE e.subtype = 'supersedes-claim'"
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

Seven files, in GitLab's own tree shape, each copied from the shape of one of
theirs, so any of them can be overlaid onto their ontology tree or contributed
upstream unchanged:

| File | Copied from | Table |
|---|---|---|
| `ontology/nodes/context/surface.yaml` | `nodes/source_code/file.yaml` | `gl_context_surface` |
| `ontology/nodes/context/clause.yaml` | `nodes/source_code/definition.yaml` | `gl_context_clause` |
| `ontology/nodes/context/external_ref.yaml` | their node format | `gl_context_external_ref` |
| `ontology/edges/context/contains.yaml` | their edge format, with `variants` | `gl_context_edge` |
| `ontology/edges/context/references.yaml` | their edge format, with `variants` | `gl_context_edge` |
| `ontology/edges/context/identical_bytes.yaml` | their edge format, with `variants` | `gl_context_edge` |
| `ontology/edges/context/produces.yaml` | their edge format, with `variants` | `gl_context_edge` |

Four edge types share `gl_context_edge`, which is what an edge table is for, and
they do not carry the same columns: `CONTAINS` holds only the endpoints,
`REFERENCES` also holds a detector, a locator and an address, `IDENTICAL_BYTES`
holds the digest two files share, and `PRODUCES` holds a rung of evidence and
the locator of the line that evidences it. The table is the **union** of all
four files' columns, and a column two files declare differently fails the index
rather than one of them silently winning. The columns one edge type does not
carry are NULL on its rows.

The indexer builds each DuckDB table from that file's `storage.columns`. Adding a
column to the YAML adds it to the table on the next index; no Python change.

Removing one from the YAML is the direction the YAML cannot describe, so it is
read off the store instead, and it **fails the run** — before a row is written,
naming the table, the column and the command that resolves it. Not a migration
the run performs on its own: removing a column cannot be undone, and a run that
prints `surfaces: 214` while having removed one is a run whose number cannot be
read afterwards. A count is exactly the thing that cannot show the difference
between the estate changing and the schema changing.

`orbit-context migrate` is that command. It removes a column the ontology does
not declare **where it holds no values**, and where one does hold values it names
it with the number of rows and alters nothing at all — not the columns that would
otherwise have gone, nor the declared columns it would have added, because a
store half at one schema and half at another is harder to read than the drift. `--remove-values` takes such a column and what
it holds, and is a decision made by hand on the command line rather than a
default: whether those values are a leftover or data is not something this tool
can tell. The report carries each table's row count either side, because removing
a column is the cheapest place to move a number without noticing, and the
declared columns it added as well as the ones it removed.

An edge type is declared once and carries the `from_node`/`to_node` pairs it is
allowed between, rather than being declared once per pair. Those `variants` are
load-bearing, not documentation: writing an edge the YAML declares no variant for
fails the index.
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

## A surface is cut into clauses

A 17 KB instruction surface is dozens of rules with different lifetimes.
Addressed as one file, *which rule* is unanswerable — so every whole-file text
surface is segmented, and each fragment becomes a `gl_context_clause` row.

Four kinds, by Markdown structure alone:

| `clause_type` | Is |
|---|---|
| `heading-section` | A heading and everything under it, to the next heading at the same level or above. |
| `list-rule` | One list item beneath a heading, and each item nested inside it. |
| `frontmatter-field` | One top-level key of the leading `---` block. |
| `code-block` | One fenced block. |

Structure only. Nothing here classifies what a clause *means*; that would be the
tool deciding, and an address is not for deciding.

Hook definitions and MCP servers are not segmented — they are entries inside
JSON, not Markdown — and neither is a `hook-target`, which is whatever file a
command happened to point at.

### `fqn` is the address

Their convention: the surface path, then one `#` per level of structure.

```
CLAUDE.md#Estimating rules#M6 anchors
CLAUDE.md#Estimating rules#M6 anchors#Cast-in channel#Edge distance is 75 mm
.claude/skills/anchor-schedule/SKILL.md#description
```

Every segment is the estate's own text — a heading, a list item's first line, a
frontmatter key, a fence's language. Nothing is invented to make it unique, so
two sibling headings with the same words share one address. `show` prints every
match rather than picking one; that is a fact about the file, not a collision to
resolve.

### The offsets are byte offsets

`start_byte` and `end_byte` are offsets into the file's UTF-8 bytes, and the span
is `[start_byte, end_byte)`. **Not character offsets.** One em dash above a
clause and a character offset lands the retrieved span short of its own text,
with nothing to say so. `start_line` and `end_line` are alongside them, 1-based
and inclusive, for a locator a person can read.

### No clause text is stored

`content` is declared `virtual` on `Clause` exactly as it is on `Surface`, and is
never written. The row carries a path and a span; `show` opens the file, seeks,
and reads.

What that guarantees is that the bytes are the file's own, not a copy the graph
kept — never that they are current. Edit the file and the offsets stand still
until the next index; re-index and they move.

### Depth is not a column

A clause nested inside another is a `CONTAINS` edge between them: `Surface →
Clause` for a clause nothing else encloses, `Clause → Clause` for the rest. So
"how deep does this nest" is a walk of the graph at query time, as in the
recursive query above, rather than a number frozen at index time.

Edges land in `gl_context_edge` in their column shape — `source_id`,
`source_kind`, `relationship_kind`, `target_id`, `target_kind`,
`traversal_path` — plus the `project_id`, `branch` and `commit_sha` that make an
edge part of one snapshot, and so replaceable by a re-index alongside the rows it
joins.

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

## Pointers, and the three ways one does not resolve

A surface names other things, and each naming is one `REFERENCES` row carrying a
`file:line` locator, the address **as the estate wrote it**, and where it landed.
Six detectors, each recorded as the edge's `subtype`:

| `subtype` | What it reads |
|---|---|
| `markdown-link` | `[text](target)`, an image, an autolink, a reference definition |
| `frontmatter-field` | a path written in the leading `---` block |
| `import-statement` | `@path` — what an import means in a prose estate |
| `config-value` | a path inside a hook or MCP entry in a settings file |
| `bare-path-literal` | a path written in prose, in backticks or not |
| `supersedes-claim` | a path on a line where the estate declares a supersession |

A pointer that lands on a governance surface points at that `Surface` row. One
that lands on any other file in the tree points at Orbit's own `File` — their
row, in their database — so the edge carries `target_path` and the join that
crosses graphs goes by path. Everything else becomes an `ExternalRef`:

| `sub_kind` | Means |
|---|---|
| `outside-indexed-roots` | The address resolved above the repository root. A sibling repository in the same estate is outside it: a different snapshot, with its own branch and commit. |
| `no-indexed-target-match` | The address stayed inside the root and no file was there. |
| `unresolvable-scheme` | The address named a URI scheme, so nothing on this filesystem is being pointed at. |

**Never merged.** Each is a statement about the detector set, not about the file,
and one total would say none of the three. One `ExternalRef` row per address,
however many edges enter it — an address named forty times is one finding.

A pointer is attributed to the **innermost clause** holding it, so "which rule
points at this" is answerable. Text above the first heading sits in no clause and
is attributed to the surface.

Three addresses are recorded as nothing at all, because each names something
other than a file: an anchor in the same document, a value still carrying an
unexpanded variable, and a directory that exists. They are stated limits of the
detector set rather than findings — phase 1 has no node for a directory, and a
place that is there is not a file that is not.

### `supersedes-claim` is a claim

It is DECLARED, permanently. A surface the estate says is superseded and that
still loads is reported as **that pair of facts** — the claim, with its locator,
and the surface row still standing. Nothing here derives a third fact from them.

### Boundary handling is the whole game

A backtick in a negative lookbehind does **not** skip inline code. It shifts the
match *start* into the middle of the token, so a valid path in backticks matches
as a truncated fragment that then cannot resolve. On one real repository that
produced **1,349 phantom findings out of 1,373** — ninety-six percent of the
report was the tool talking about itself.

So every prose detector starts from a **consumed** boundary: line start, or one
of whitespace `` ` `` `'` `"` `(` `<` `[`. A leading `/` is excluded, so the path
half of a URL is not re-matched as a bare path. A path is a pointer only if it
carries a file extension, and either a `/` or an extension the indexer
recognises, which is what keeps `0.118.1` and `SipHash-1-3` out of the report.
Sentence punctuation is trimmed off the end, or `../beta/AGENTS.md.` closing a
sentence would be captured with the full stop and then fail its own shape test.

Measured on this repository's 208 Markdown files: **2,094 pointers, 1,831
resolved, 52 distinct `no-indexed-target-match` addresses**, and every one of the
52 a path the estate actually wrote. If a run comes back with unmatched pointers
in the thousands, the detector is wrong, not the estate — which is what
`orbit/tests/test_pointers.py` asserts, over this repository, on every run.

## Identical bytes, never counted on their own

Every file in a repository is hashed — not only the surfaces — and each pair of
files whose bytes hash the same becomes one `IDENTICAL_BYTES` row carrying both
paths and the digest they share. Pure observation. Nothing in the row says why
they match, and spec §14 keeps *whether two identical files are intentionally
identical* as a permanent UNKNOWN.

**The count is never emitted alone.** A bare hash-match count over-reads badly,
so it is reported in one block with the count of pairs carrying provenance
evidence and the count carrying none:

```json
"identical_bytes": {
  "pairs": 28,
  "pairs_with_provenance": 0,
  "pairs_without_provenance": 28,
  "pairs_with_a_direction": 0,
  "pairs_by_direction_evidence": {"artifact-header": 0, "manifest-declaration": 0,
                                  "literal-write-path": 0},
  "pairs_with_no_direction": {"no-producer-named-at-either-end": 28,
                              "producer-named-outside-the-pair": 0,
                              "each-end-names-the-other-as-its-producer": 0},
  "produces_edges": 0,
  "produces_by_evidence": {"artifact-header": 0, "manifest-declaration": 0,
                           "literal-write-path": 0},
  "generation_declared_without_producer_named": 0,
  "producer_named_no_indexed_target_match": 0,
  "files_hashed": 254,
  "files_not_read": 14,
  "files_not_read_by_reason": {"non_regular_file": 14, "oversize": 0,
                               "read_error": 0},
  "zero_byte_files_not_paired": 1
}
```

That is this repository, and it is the ticket's own measurement: **28 pairs, 0
producers**. Every pair is a workbench file matching a published file — one
pipeline run 28 times — and the provenance explaining all 28 is invisible to the
tool, because nothing in the tree writes it down. The block is built in one
function (`provenance.summary`), which is what makes "never alone" a property of
the code rather than a habit.

### Which end came first

A pair is symmetric. `_rule-workbench/refactoring/nano.md` and
`refactoring/refactoring.nano.md` are the same bytes, and the row on its own
says nothing about which one the other came from — a second thing a reader will
fill in for themselves unless the row answers it.

So every `IDENTICAL_BYTES` row carries a `direction`, and it is derived from one
thing only: **a `PRODUCES` edge between the pair's own two ends.**

| `direction` | Means |
|---|---|
| `source-produces-target` | The evidence puts `source_path` first. `subtype` is the rung it stands on, `evidence_path:evidence_line` where it was read |
| `target-produces-source` | The same, the other way round. The row is written with the lexicographically first path as the source, so the direction is said against that ordering rather than by reordering the row |
| `UNKNOWN` | Nothing ordered the pair. `direction_reason` says which of three cases this is |

`UNKNOWN` rather than an empty column, because a blank reads as a column nobody
filled in and this is a measurement.

| `direction_reason` | Means |
|---|---|
| `no-producer-named-at-either-end` | No evidence reaches either file. These are exactly the pairs `pairs_without_provenance` counts |
| `producer-named-outside-the-pair` | Something produced one or both ends, and it was not the other end. The pair *has* provenance and still nothing that orders it |
| `each-end-names-the-other-as-its-producer` | Two claims that contradict each other. Choosing between them would be this tool deciding, and it has no basis to |

The middle one is why the reasons are never summed. A pair whose two files are
both artifacts of one script is a different finding from a pair nothing
evidences at all, and one number would say neither.

**A sentence does not order a pair.** `_rule-workbench/refactoring/traceability.md`
says `full.md` *"should resolve to `../../refactoring/refactoring.md`"* — a
producer relationship a human reads in ten seconds. Spec §14 lists prose
provenance as a permanent UNKNOWN, and it stays UNKNOWN: a direction read out of
a sentence would be indistinguishable in this table from one something observed,
which is what makes it worse than no direction at all. The honest route to the
direction is a machine-readable declaration in the corpus, which is a change to
the corpus.

`orbit-context pairs` prints every pair with what is known about it:

```
IDENTICAL BYTES  28 pairs  [1.8516f0a599c4]
  carrying provenance evidence     0
  carrying no provenance evidence  28
  carrying a direction             0
  ...
  pair by pair
    _rule-workbench/refactoring/nano.md = refactoring/refactoring.nano.md  UNKNOWN: no-producer-named-at-either-end
```

`repo-map` prints the same block from the same reading — `pairs.from_graph` —
capped to a few example rows, so the map and the command cannot disagree about a
number they both print.

Two files are only ever paired **within one repository**: two repositories are
two snapshots with their own branch and commit, and an edge across them would
join two things this indexer has not established are the same.

Zero-byte files are counted and left out of the pairing. An empty file matches
every other empty file, so twenty of them would report 190 pairs that say
nothing about any of them.

### `PRODUCES` is a ladder, strongest first

| `subtype` | Evidence | Where the locator points |
|---|---|---|
| `artifact-header` | The artifact's own header names its producer — `Generated by X`, `@generated`, `DO NOT EDIT` | the artifact |
| `manifest-declaration` | A config or manifest declares input → output, both resolving in the tree | the manifest |
| `literal-write-path` | A script contains a literal path it writes to | the script |

One artifact keeps only its **strongest** rung. A file whose header names the
script that also writes it by literal path is one fact evidenced twice, not two
producers.

`evidence_path` and `evidence_line` are their own columns because the evidence
is not always at either end of the edge: a header sits in the artifact, a
manifest declaration in a third file. `source_address` holds the producer
exactly as the estate wrote it, beside the `source_path` it resolved to.

Three near-misses are counted rather than turned into edges, because each says
something different:

- **A producer named that the tree does not hold** — an edge needs both ends, so
  none is written, and `producer_named_no_indexed_target_match` records that a
  producer *was* named.
- **A file that says it was generated without saying by what** —
  `generation_declared_without_producer_named`. Evidence of something; not
  evidence of what.
- **A header written in prose** — not evidence at all. A generation header is
  read only from a comment or the leading frontmatter block. Without that rule
  the detector reads the sentence in `orbit/tickets/05` warning about trailing
  comment syntax as a header, and reports the ticket as an artifact of the
  script that sentence names. That is the tool talking about itself, which this
  project has already paid for once at 1,349 findings out of 1,373, and
  `orbit/tests/test_provenance.py` pins it using the ticket's own text.

Producer parsing takes only the **first token** after `by`, then trims the
comment's own closing syntax off it: `Generated by scripts/build.py -- DO NOT
EDIT -->` names `scripts/build.py`. Without the trim the name resolves to
nothing and a producer the estate did name is reported as one it did not.

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
| `non_regular_file` | A symlink. Listed as a node, never read. |

### A symlink is a node, never read

GitLab Orbit's rule, adopted in their vocabulary rather than answered our own
way. Their walk accepts an entry that is a file **or** a symlink and skips only
what is neither (`crates/utils/src/walk.rs:37-41`); a symlink is then routed
away from the reader rather than out of the walk (`:53-57`), where the default
is `Decision::ListOnly` — "record the file as a node without loading its bytes"
(`crates/utils/src/fs_stream.rs:22`). Its size is `symlink_metadata()`
(`walk.rs:47`), the link's own. The reason is `FilterSkip::NonRegularFile`
(`crates/code-graph/src/v2/config/filter.rs:51`), documented at
`crates/orbit-observability/src/indexer/code.rs:152` as "a symlink — a node,
never parsed".

So, here:

- The walk lists it, and does not descend into a link to a directory: that would
  walk one tree twice and count one file as two. A link wearing a pruned name is
  refused by the name, before anything asks what it is.
- **No bytes are loaded** — not for a first heading, not for a clause, not for a
  hash. It follows that a link is in no byte-identical pair and on no ladder.
- Its `size_bytes` is the link's own. On this repository
  `_rule-workbench/<book>/full.md` is 32 bytes, not the 17,866 of the book it
  names.
- Two of the three recognition rules still reach it. A **vendor name** is
  readable without opening the file, and so is the **corpus** a directory's read
  files made; only "the file says so" needs the bytes, and a node nobody opened
  declared nothing. Where one of the two reaches it, the link becomes a row
  carrying `non_regular_file`, the way an oversize surface carries `oversize`.
- **The corpus share counts only files that were read** — a narrower statement
  than the set that share is then applied to. A node the walk listed without
  loading cannot declare itself, so it must not count against the files that
  did. Without that rule, counting this repository's fourteen `full.md` links
  takes `_rule-workbench` from 42 of 45 declared to 42 of 59 — under the 75%
  share — and the three files that only the share recognises stop being
  surfaces, with nothing in the output saying a symlink rule caused it.
- **`repo-map`'s recognition split counts rows that were read.** The split
  separates what the estate stated about a file from what this tool read off the
  directory around it, and a file nobody opened is evidence of neither. So it
  sums to `surfaces read in full`, not to `files carrying a surface kind`.

Two names for one file still count as two nodes here, and the row carries
`link_target`: where the link's own name resolves, repository-relative, read
from the link and never through it. Folding them to one entry labelled by the
target (`crates/orbit-local/src/commands/setup.rs:265-271`) is a stronger
statement than byte identity, and it is applied by `compare` — where two states
can disagree about it — rather than by the walk. So the graph holds both names
and the comparison counts one file, which is the arrangement that lets the
number folded be reported per state instead of vanishing into a total.

Every one of these also lands in `gl_context_coverage`, keyed to the snapshot,
so `repo-map` can report what was reached and not read without re-walking the
tree. A reason printed once to stdout and thrown away reads afterwards as a
surface that was never there.

Three cases produce no surface row, and are reported in the statistics instead, so that
a surface which is present but unindexed does not read as a surface that is
absent:

| Reported | Why there is no row |
|---|---|
| `outside_indexed_repository` | A surface under the indexed root belonging to no git repository: no branch or commit to carry. Alone among these it is not written to `gl_context_coverage` either — with no branch and no commit it keys to no snapshot. |
| `frontmatter_declaration_absent` | A `SKILL.md` or agent file that declares no `name` and `description`. Calling it a skill would be the tool deciding. |
| `invalid_json` | A settings or `.mcp.json` file that would not parse. Its hooks and servers are entries inside it; with the file unread there is nothing to write a row about. |

## Orientation in one command

`repo-map` prints one repository's governance surface: the boundary the walk
covered, coverage, surfaces by kind, clauses and how deep they nest, edges and
pointers by kind, the three non-resolutions, the identical-byte pairs with their
provenance counts, and the branch's own git state. It is orientation, not a
report — the question is "what governance does this repository carry, and how
much of it did these detectors see", answered in one screen.

**It re-walks nothing.** Every number comes out of the graph, from one
`(project_id, branch, commit_sha)`. A second walk at map time would be a second
answer to "what is in this repository", taken against a working tree that has
moved on since indexing, and the map would print a denominator its own
numerators were never measured against. So the walk records itself:
`gl_context_run` holds one row per snapshot with the indexed root, the excluded
directories, the files walked and the files carrying a surface kind;
`gl_context_coverage` holds one row per file reached and not fully indexed, with
its reason. Both are declared in ontology YAML like every other table, and
neither carries edges — a node type is how this ontology declares a table shape,
and the record of a walk is not a participant in the graph it produced.

The consequence is that a map can be older than the tree, and that is stated
rather than hidden: the snapshot's commit is in the header, and where the
detector set that wrote the graph differs from the one in the running build, the
map says so instead of presenting the counts as current.

### Every zero is printed

All seven surface kinds, all four clause types, all six pointer detectors, all
three non-resolutions, all three evidence rungs — listed whether or not they
found anything. A map printing only its non-zero rows reads as a description of
the estate. Printed in full, a column of zeroes reads as what it is: the
inventory of what these detectors look for, and how little of it is here.

Coverage carries its denominator for the same reason. Four surfaces out of
fifteen files and four out of 1,775 are the same numerator about two very
different repositories.

`SURFACES` reports rows and, of those, how many were read through. A candidate
that could not be read still becomes a row carrying its reason, so the row count
and the surface count `index` prints are two different numbers; the map
reconciles them rather than leaving them to disagree quietly.

### The budget

GitLab Orbit's own `repo-map` emits **12,874 bytes (~3,200 tokens)** for a
1,775-file repository. That measurement is the budget. The map holds to it by
construction — every varying section is a fixed inventory of detectors, and the
two sections that list rows are capped and say how many they did not list — and
the last line reports what the map actually cost, counting itself. If a
repository ever finds a way past the caps, the listings are dropped and the map
says they were dropped rather than quietly exceeding the figure it just printed.

The fixture estate maps in about 2.5 KB, and this repository in about 3 KB.

### The detector set version

Every count in the graph is a count of what these detectors recognise, and two
counts taken a month apart are only comparable if the same detectors produced
them. Ticket 04's boundary fix moved one detector's match start by one character
and took a finding count from 1,373 to 24; read without a version beside them,
those two numbers describe an estate that changed. It did not.

So the version is **derived, not declared** — `orbit_context/detectors.py`
digests the module-level constants and compiled patterns of the five modules
that decide what is recognised, so editing a basename table, a pruned directory,
a regex or an evidence rung moves it whether or not anyone remembers to. A
constant somebody has to remember to bump is the class of mechanism this project
has already decided it has too many of. `RECIPE` versions the digest itself, so
`1.4e7b…` and `2.4e7b…` read as "computed differently" rather than as "detects
differently", and `detectors.manifest()` lists every hashed input so a version
that moved can be explained rather than merely noticed.

It is recorded on each snapshot's run row and printed on every counted section,
so a count quoted out of a map into a ticket arrives with the detector set that
produced it.

### Git state, and what absence means

The map ends with the branch: its base, how many commits are ahead of it, how
many of those carry a `Claude-Session` trailer, and how many carry this
session's.

That block exists because of a specific failure. Twice in this project a session
read commits it had made itself, saw an unfamiliar subject line, and attributed
them to a different session — with the disproof, a trailer carrying its own id,
sitting in the commit body it had just printed. It then wrote that invention
into a scheduled prompt, which fed it back as an established fact every hour.
The rule it encodes: **absence from a transcript is a fact about the transcript,
not about the world.**

Two things about how it reads that are the whole point:

- **A session identifier comes from the environment, never from the commits.**
  Where the environment supplies none, the count is reported as *not measured* —
  never as zero. Zero and unknown are different findings, and printing the first
  for the second is the error the block exists to stop.
- **Every distinct trailer is reported whatever matched.** The id a client
  exports and the id written into the trailer are not always spelled the same
  way — one environment exports `cse_01ABC` for a trailer reading
  `.../session_01ABC` — so matching is on the id's tail, the variable that
  actually matched is named, and the full distribution is printed beside it. A
  reader who can see "seven commits carry session_01ABC" can settle the question
  themselves when the match comes up empty.

The base is resolved by a stated ladder — `--base`, then `$CLAUDE_CODE_BASE_REF`,
then `origin/HEAD`, then the first of `origin/main`, `origin/master`, `main`,
`master` that resolves — and the rung that answered is printed, because ahead of
what is half the number. Where none resolves, the count is stated as not
measured rather than guessed. The block is labelled as git state, not a detector
finding: it is the one part of the map that is not an observation of the estate's
governance surface.

## The ladder

Progressive disclosure of rules, built here by hand before Orbit existed: one
book written three times at three sizes, so a session loads the rung its
workflow can afford.

```
refactoring/refactoring.md       17866
refactoring/refactoring.mini.md   5167
refactoring/refactoring.nano.md   1986
```

`RUNG_OF` is the edge between them, from the rung to the **base rung** — the
file in the same directory named by the stem alone. Every rung of one ladder
carries that path in `target_path`, so the base rung is the ladder's address and
a ladder is one walk of these edges. The rung word the filename carried is on
the row as `subtype`.

The base rung is never a `RUNG_OF` *source* — the edges leave the other rungs
and enter it — so it is unioned in rather than joined to, or a book comes back
one rung short of itself:

```sh
orbit local sql "SELECT r.ladder, s.path, s.size_bytes, r.rung
                 FROM (SELECT target_path AS ladder, source_path AS path, subtype AS rung,
                              project_id, branch, commit_sha
                         FROM gl_context_edge WHERE relationship_kind = 'RUNG_OF'
                       UNION
                       SELECT target_path, target_path, 'base',
                              project_id, branch, commit_sha
                         FROM gl_context_edge WHERE relationship_kind = 'RUNG_OF') r
                 JOIN gl_context_surface s
                   ON s.path = r.path AND s.project_id = r.project_id
                  AND s.branch = r.branch AND s.commit_sha = r.commit_sha
                 ORDER BY r.ladder, s.size_bytes DESC"
```

The join carries the whole snapshot — `project_id`, `branch` and `commit_sha` —
because the graph holds every snapshot ever indexed. Joined on the path alone,
a store holding two commits of one repository returns each rung twice, once at
a size taken from the other commit.

### What the edge says, and what it does not

It relates **two filenames**, in one directory, and nothing else. It does not
say the nano rung was derived from the full one: spec 0001 §14 keeps "whether
two identical files are intentionally identical" a permanent UNKNOWN, and a
derivation nothing observed would be the same over-read. Where the estate
evidences one, the `PRODUCES` edges beside these rows carry it.

**Which rung a session actually loaded is not here.** That needs the load
ledger, which is Candidate A and still gated. Every command that prints a ladder
prints it as UNKNOWN with the reason named, never as zero — spec 0001 §9's rule
that an unobservable quantity must not improve a number by being unobservable.

### What the rule keys on

A file named `<stem>.md` beside `<stem>.mini.md` or `<stem>.nano.md`, in one
directory. `RUNG_WORDS` in `surfaces.py` is the table, and adding a word to it
moves the detector set version on its own.

That convention is **this repository's, not a standard** — nobody defined
`.mini.md` the way Anthropic defined `CLAUDE.md`. So a repository naming its
rungs otherwise has no ladders **found** here, which is not the same statement
as no ladders, and the rule is printed beside every count including zero.

This repository already carries a second shape it is deliberately not keyed on:
`_rule-workbench/<book>/` holds `mini.md` and `nano.md` with no stem in front,
so the directory is the book and the filename is the rung alone. Reaching that
means a rule that reads a directory rather than a name, which is the corpus
rule's kind of inference rather than this one's.

### A rung with no base rung

A filename can carry a rung word with nothing beside it named by the stem alone.
No edge is written — an edge needs both ends, and inventing the missing one
would put a file in the graph the repository does not hold — so it is counted
and named instead, as `rungs_with_no_base_rung`. A rung the estate wrote and
this tool could not attach is not the same as a rung never written.

How many rungs a book carries is an observation, not a defect. A book at two is
reported at two, beside the books at three.

## Two states, or three, differenced

`compare` takes two or more states, indexes each, and prints every state's own
figures beside its difference from the first.

```sh
orbit/bin/orbit-context compare main HEAD --repo /path/to/the/repository
```

A state is a git ref in `--repo`, or `path@ref` for a state of **another
repository** — which is what makes a three-state comparison of one lineage
possible:

```sh
orbit/bin/orbit-context compare a7d7649 HEAD ../agent-rules-books@782a886 --repo .
```

The `@` is read from the right, and only where the text before it names a
directory that is there. A git ref is allowed to hold one — `main@{yesterday}`
is a ref — so a rule that split on the character alone would take a ref apart
and then report the repository it invented as one that could not be read.

A comparison is N indexes plus subtraction, and it is built as exactly that.
It has **no store of its own, no index path of its own and no query language of
its own** — spec 0002 §12 lists each of those as a kill condition, because each
would mean the figures in this table were taken differently from the figures
every other command prints.

### Every delta is against the first state

Not a chain. Three states of one lineage are an untouched base and two
descendants of it, and `C2 − C1` is a subtraction between two repositories that
never shared anything but that base — printed as a delta it would read as one
session having done what a whole second repository did. The baseline is the
only state they all share, so it is the only one they are all differenced
against, and each delta column is named for the state it was taken from.

Where the states are not all from one repository the header says so. What a
delta between two repositories measures is only what their shared base makes
it, and whether that base is still shared is a question about the rows — see
*what the fold would otherwise hide*, below.

### Every state is read from a commit, and nothing is written to its repository

Each state is materialised as a **clone**, checked out detached at its own
commit, and indexed there. Three consequences, and each is the point:

- The working tree is never checked out over. The comparison runs from the
  branch you are standing on.
- No reading carries anything its commit does not. A working tree holds
  whatever is lying around in it, and differencing a clean checkout against a
  working tree reports somebody's scratch file as something the second state
  added.
- **The repository a state comes from is not written to.** `git worktree add`
  writes to the repository it is run in; a clone does not. A state can come
  from a repository this project is allowed to read and not to touch, and a
  materialisation that wrote to one repository and not to another would also be
  two kinds of reading.

The clone is removed afterwards, including when the index run raises.

### Every absolute figure, beside every delta

Subtraction hides which side moved. `+40` cannot distinguish *the second state
added forty* from *the first state was miscounted by forty*, and the second is
the failure mode this project has already had twice. With three states it
cannot even say which pair moved. So every row carries every state's own figure,
and the sections that list rows by name carry one more thing: a total over every
name at delta 0, computed over all of them rather than over the ones that fit
under the cap.

### Bytes walked, beside files walked

`bytes walked` is the walk's own weight for the same files `files walked`
counts, each entry taken by `lstat` so a symlink weighs its own name and never
the file it names. Two states holding the same number of files can hold ten
times the bytes, and a count of files says which of those a repository is about
as well as a count of pages says how long a book is.

It is printed beside `surface bytes` and nothing divides them. Spec 0002 §11
refuses a metric built for a hypothesis before the hypothesis was measured, so
a share of one by the other is a reading somebody takes off the table, not a
number this tool computes, ranks or raises anything on.

### Two names for one file are one file

GitLab Orbit's rule, at `crates/orbit-local/src/commands/setup.rs:265-271`: the
paths are canonicalised and one entry is kept, labelled by the **target**. Their
test at `:292` writes `AGENTS.md`, symlinks `CLAUDE.md` to it, and asserts one
entry named `AGENTS.md`.

It matters here because the row this comparison turns on is a zero. Fourteen
symlinked `full.md` files sit in both states of this repository; counted as
governance in one state and not the other, the zero moves and the comparison
reports a session adding rules it did not write.

The fold happens at compare time, off the `link_target` column, and **the number
folded is reported per state** — beside the counts, never inside them. A fold
that happens in one state and not in another is exactly what moves a zero, and
one summed figure would hide which state it happened in.

### What the fold would otherwise hide

Printed beside the fold: how many names in each state resolve to another name,
and what those names weigh. Fourteen 32-byte links and fourteen full-sized
copies of the files those links used to name are different repositories, and
after the fold both read as fourteen names counted once — which is the right
answer to *how many files is this* and no answer at all to *is this still the
same base*. A copy that no longer tracks its source is a rewritten base whatever
a diff says, so the figure that tells the two apart is printed rather than left
to be worked out by hand.

**Only a link folds.** Rows here are additive on purpose and several of them
legitimately stand at one path: a settings file holds a row per hook and a row
per MCP server. A fold keyed on the path alone takes four hooks down to one and
reports a file folded into itself — a dedupe quietly changing a count, which is
the failure mode this whole batch exists to catch. So the rows standing at a
name of their own and the rows whose name resolves to another are separated
first, and only the second kind can fold away.

What the fold is not: same-inode is a stronger statement than the byte identity
`IDENTICAL_BYTES` carries. Byte-identical says *same content, cause unknown*;
same-inode says *same file*. So the target being the surviving name is observed,
and it reopens nothing — two files that merely hash the same are still
unordered.

### Where the walk's own tally comes from

`files walked` breaks down by suffix and by top-level directory because the run
row carries those two tallies — `files_walked_by_suffix` and
`files_walked_by_directory`, JSON objects written by the walk that produced the
count. Recorded rather than recomputed, on `repo-map`'s rule: a second walk at
compare time would be a second answer to "what is in this repository", taken
against a tree that has moved on, and the difference between two states is
exactly where that would show.

### Every zero is printed here too

The sections that break the counts down — surfaces by kind, clauses by type,
pointers by detector, edges by kind, the three non-resolutions — print their
whole inventory in every state, at zero as well as at count, for the reason
`repo-map` does. Only the two sections whose names come from the estate
(suffixes, top-level directories) are capped, they never cap a row that moved,
and what they leave out is totalled into their own "did not move" row rather
than dropped.

Byte identity is printed as the block `pairs.PairCounts` divides it into —
pairs, carrying provenance evidence, carrying none, carrying a direction —
because a bare hash-match count over-reads and the rule that it is never emitted
alone belongs to that function rather than to each command that prints it.

### The exit code is a finding as well as a status

| exit | means |
|---|---|
| 0 | The comparison ran and its readings are comparable. |
| 1 | A state could not be materialised, indexed or read, or fewer than two states were named. Nothing is printed to stdout: half a table is the one output shape this command must not produce. |
| 4 | The comparison ran and its states were **not all read by one detector set**. The table is printed and every figure in it was measured; what is not established is that subtracting them means anything. |

### What it does not do

Nothing is characterised. The deltas are counts and bytes, and no row says what
a difference means, which state is the better one, or what to do about either.
Spec 0002 §12's last kill condition is reaching for the comparison to decide
something rather than to check something.

### The acceptance run

Advisor-Desk against its own history, hand-checked against the shape ticket 13
pinned **before** the run:

```
orbit-context compare a7d7649 e6a6d74 --repo .

COUNTS  both figures beside every delta  [1.8eabab386316]
  state                                  a7d7649  e6a6d74  delta
  files walked                               201      253    +52
  files carrying a surface kind, folded       87       87      0
  governance surfaces                         87       87      0
  of those, read in full                      87       87      0
  two names for one file, folded              14       14      0
  clauses                                   7560     7560      0
  pointers                                   224      224      0
  governance surface bytes                781674   781674      0

FILES BY SUFFIX
  .md                             198      209    +11
  .py                               0       31    +31
  .yaml                             0        9     +9

FILES BY TOP-LEVEL DIRECTORY
  orbit                              0       52    +52
  every directory that did not move  201      201      0

IDENTICAL BYTES
  pairs                             28       28      0
  carrying provenance evidence       0        0      0
  carrying no provenance evidence   28       28      0
```

Every row the ticket pinned by hand is reproduced: 201 files against 253, 198
Markdown against 209, 201 non-`orbit/` files either side, and **governance
surfaces at 87 in both states**. That last row is the finding. C1 built a tool
and added no governance, and the comparison says so — with the fourteen `full.md`
links folded in both states rather than in one, which is what keeps the zero a
measurement instead of an artefact of when the fold happened.

`a7d7649` is `main`: 50 commits, every one authored upstream. `e6a6d74` is the
state ticket 13 was written against. **The branch has moved since**, and running
the same comparison against today's head is a different measurement — the
sessions after `e6a6d74` installed skill packages under `.claude/`, which is
governance, added outside `orbit/`. Both runs are correct and they answer
different questions; the pinned one is the falsifier, because its expected
values were written down before it was run.

### The three-state run

Ticket 14, the same detector set, one of the three states in another repository:

```
orbit-context compare a7d7649 dc16a3e /home/user/agent-rules-books@782a886 --repo .

COUNTS  every state's own figures beside every delta  [1.8eabab386316]
  state                                  a7d7649  dc16a3e  agent-r…@782a886  dc16a3e-a7d7649  agen…2a886-a7d7649
  files walked                               201      323               515             +122                +314
  bytes walked                           2172106  3239053          10432071         +1066947            +8259965
  files carrying a surface kind, folded       87      103               126              +16                 +39
  surfaces                                    87      103               126              +16                 +39
  of those, read in full                      87      103               126              +16                 +39
  names that resolve to another name          14       14                14                0                   0
  two names for one file, folded              14       14                14                0                   0
  clauses                                   7560     7901              8089             +341                +529
  pointers                                   224      314               344              +90                +120
  surface bytes                           781674   853575            946722           +71901             +165048
```

The whole section, as it printed. An evidence block is the last place an
abridged table belongs: a row left out for width is a row a reader cannot check,
and two of the rows above stand at zero.

Three readings of that table, and each is in the ticket with the figures it
rests on:

- **C2 still holds the fourteen links.** The same fourteen paths naming the same
  fourteen targets, 812 bytes, in every state — so nothing resolved them, and
  the base is intact in the respect that would have made the two deltas
  different kinds of measurement. The fold reports fourteen either way; the link
  count is what says which fourteen they are.
- **The deltas tie back to named files.** C1's +16 is sixteen
  `.claude/skills/<name>/SKILL.md`. C2's +39 is 42 rows C0 does not carry, less
  three of C0's that C2 does not.
- **Those three did not go anywhere.** `_rule-workbench/CHECK_COMPATIBILITY.md`,
  `PROCESS.md` and `RELEASE.md` are present in C2 and byte-identical to C0's.
  C2 added one undeclared file per book to that subtree, which took it from 42
  declared of 45 to 42 of 59 — under the corpus rule's 0.75 — so the directory
  is a corpus in one state and not in the other. A count that moved because a
  share moved is not a count of files anyone removed, and the ticket says so
  beside the number.

This is evidence, not a test. `orbit/tests/test_compare.py` asserts against
`build_states`, a fixture repository committed at three states — and against a
second copy of it standing for a clone that went its own way, in both the shape
that kept its links and the shape whose links were resolved — because a test
that reads live repository content fails whenever that content changes,
including from this work.

### The estate, in two families

Ticket 07, the same detector set again. The estate splits in two, and the two
halves support different statements: Advisor-Desk and agent-rules-books share an
upstream, so they can be differenced; Home-system, Estimating-Lab and
Merit-knowledge share nothing, so they are read as absolute figures and no delta
is computed between any of them.

```
                        Home-system   Estimating-Lab   Merit-knowledge
files walked                   1348              601                11
bytes walked               40849304         23716125            106314
surface rows                     36               25                 0
surface bytes                499428           247487                 0
clauses                         920              578                 0
pointers                        622              229                 0
identical-byte pairs              9                1                 0
```

**Merit-knowledge returns zero from eleven files, and the zero is exact rather
than empty.** No file there carries a name a vendor defined, none opens with the
one directive heading word this set reads, and with nothing declared no
directory reaches the corpus share. It is a repository of format contracts that
this detector set does not recognise, which is a statement about the detector
set and not about those files.

Two defects in the tool's own output were found by running it over repositories
it had not seen, and both are repaired: a pair of two files differing only in
the middle of their paths printed as one file beside itself, and `produces_edges`
counted one production the edge writer had declined. Both are rendering and
accounting, so the detector set is unmoved at `1.8eabab386316` and every figure
above is comparable with the ones before it.

A third was found and recorded rather than repaired — 157 of 1,306
`bare-path-literal` rows restate a markdown link sitting on the same line, one
pointer reported twice. Repairing it moves the detector set version, which would
make ticket 07's figures incomparable with ticket 14's, so it is left to a
ticket of its own. It is also the measurement that opened Gate B.

## Statistics

`index` prints JSON in Orbit's shape — `repository`, `path`, `time_seconds`,
`graph`, `coverage`, `processing`, `database_path`, `detector_set_version`, and
`detailed` under `--stats`. `coverage` carries `files_walked`,
`files_with_surface_kind` and `files_with_no_surface_kind`, at estate level and
per repository. `graph`
counts `repositories`, `surfaces`, `clauses`, `edges` and `pointers`, and reports
`external_refs` as the three `sub_kind` counts separately, always all three, even
at zero. `identical_bytes` is the byte-identity, provenance and direction block above,
present at estate level and per repository, with every key reported even at
zero — each rung of the ladder, and each of the three reasons a pair carries no
direction. `produces_edges` counts `PRODUCES` rows and nothing else; each
production the edge rule declines is named in a key of its own, so that a
declaration the estate wrote and the tool could not turn into an edge does not
read as a declaration never written —
`producer_named_no_indexed_target_match` for a producer that matched nothing
indexed, `producer_and_artifact_are_one_file` for a declaration naming one file
as both its own input and its own output. Skipped entries carry
`reason`, errored entries carry `kind`, matching their `SkippedFile` and
`ErroredFile`. A `repositories` array itemises each repository found under the
indexed root, and `schema` reports, per table, which columns the YAML added and
which the table carries that the YAML does not declare.

`replaced` says how many rows the run took out of the store to put its own in,
per table, at estate level and per repository. Zero everywhere on a first index.
Without it a total that did not move reads the same whether the run replaced its
own snapshot or wrote nothing at all.

`store` is what else is in there. One store holds many repositories and many
snapshots of each — that is the design — so a count read out of it is only
interpretable beside the rest of its contents. The block lists every snapshot the
store holds with its `branch`, `commit_sha`, `indexed_at`, `detector_set_version`
and the rows it holds per table, marks each `indexed_by_this_run` or not, and
counts `repositories_from_other_detector_sets`. That last one is the reason the
detector version exists: a change in the detectors and a change in the estate
move the same numbers, and the version beside each snapshot is what separates
them. `rows_outside_a_recorded_run` names rows whose snapshot no run row accounts
for — normally empty, and never folded into a total that would read as if they
carried a version and a time.

## Re-indexing

Re-indexing replaces the rows for the indexed
`(traversal_path, project_id, branch, commit_sha)` — in all six tables — rather
than adding a second copy. Once per *table*, not once per ontology shape: two
edge types share `gl_context_edge`, and a second replacement for the same
snapshot would delete what the first had just written. `project_id` is part of that key because every local row carries the same
empty `traversal_path`. Row ids are derived from the same tuple plus the path,
so they are stable across re-index.

Every clause of that key is also what keeps one repository's re-index off
another's rows: the store holds many repositories, and a replacement that
dropped any clause of the key would take rows the run never looked at. What it
did take is reported as `replaced`.

Snapshots on different commits coexist, which is Orbit's own semantics. A commit
that moves leaves the previous snapshot's rows in place.

## Constraints held here

- **Never writes to Orbit's tables.** `store.assert_context_table` refuses any
  table not prefixed `gl_context_`.
- **No prose columns.** No `summary`, no `purpose`, and no clause text.
- **Constrained vocabulary** on tool-authored fields — reasons, surface kinds,
  column names, statistics keys. Enforced by `orbit/tests/test_vocabulary.py`,
  never over paths or quoted system messages.

## Open, not decided

- `gl_context_surface` in the live graph carries four columns from an earlier
  prototype — `client`, `activation`, `evidence_class`, `detector`. All four are
  phase 2/3 candidates gated behind the tests in spec §6, so phase 1 does not
  declare or write them. **Decided by ticket 09:** the run no longer leaves them
  alone. It refuses, names them, and names `orbit-context migrate`. Where the
  prototype rows still hold values in those columns, `migrate` refuses in turn
  and names them, and `--remove-values` is the decision Dylan takes by hand.
- The indexed roots, and whether `~/.claude/` and other user-global surfaces are
  inside them, are spec §12 items and still Dylan's to set. `index` takes
  whatever path it is given.
