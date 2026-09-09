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

Phase 1, tickets 01–06. Five node types and four edge types. `Surface` covers
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
  "produces_edges": 0,
  "produces_by_evidence": {"artifact-header": 0, "manifest-declaration": 0,
                           "literal-write-path": 0},
  "generation_declared_without_producer_named": 0,
  "producer_named_no_indexed_target_match": 0,
  "files_hashed": 231,
  "files_not_read": 0,
  "zero_byte_files_not_paired": 1
}
```

That is this repository, and it is the ticket's own measurement: **28 pairs, 0
producers**. Every pair is a workbench file matching a published file — one
pipeline run 28 times — and the provenance explaining all 28 is invisible to the
tool, because nothing in the tree writes it down. The block is built in one
function (`provenance.summary`), which is what makes "never alone" a property of
the code rather than a habit.

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

## Statistics

`index` prints JSON in Orbit's shape — `repository`, `path`, `time_seconds`,
`graph`, `coverage`, `processing`, `database_path`, `detector_set_version`, and
`detailed` under `--stats`. `coverage` carries `files_walked`,
`files_with_surface_kind` and `files_with_no_surface_kind`, at estate level and
per repository. `graph`
counts `repositories`, `surfaces`, `clauses`, `edges` and `pointers`, and reports
`external_refs` as the three `sub_kind` counts separately, always all three, even
at zero. `identical_bytes` is the byte-identity and provenance block above,
present at estate level and per repository, with every key including each rung
of the ladder reported even at zero. Skipped entries carry
`reason`, errored entries carry `kind`, matching their `SkippedFile` and
`ErroredFile`. A `repositories` array itemises each repository found under the
indexed root, and `schema` reports, per table, which columns the YAML added and
which the table carries that the YAML does not declare.

## Re-indexing

Re-indexing replaces the rows for the indexed
`(traversal_path, project_id, branch, commit_sha)` — in all six tables — rather
than adding a second copy. Once per *table*, not once per ontology shape: two
edge types share `gl_context_edge`, and a second replacement for the same
snapshot would delete what the first had just written. `project_id` is part of that key because every local row carries the same
empty `traversal_path`. Row ids are derived from the same tuple plus the path,
so they are stable across re-index.

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
  declare or write them. The indexer leaves them alone and names them on stderr.
  Dropping the table so it matches the ontology exactly is a decision for Dylan,
  not something the indexer does on its own.
- The indexed roots, and whether `~/.claude/` and other user-global surfaces are
  inside them, are spec §12 items and still Dylan's to set. `index` takes
  whatever path it is given.
