# Spec 0001 (rev 3) — Orbit Context: emulating GitLab Orbit for the HITL estate

Status: draft, unimplemented. This document is being written, not consulted — nothing in it is settled by having been written down.
Baseline emulated: **GitLab Orbit**, `gitlabhq/orbit-knowledge-graph` @ `0fe19ac`, CLI `orbit 0.118.1`, installed and run.

## 1. Goal

Run an Orbit-shaped context graph over the HITL estate, covering the half of the estate GitLab Orbit does not parse: instruction surfaces, skills, agents, hooks, and the governance pointers between them.

**Emulate, do not reinvent.** Their architecture, their storage, their query surface, their ontology format, their command names. What changes is the *domain* — `source_code` becomes `context` — not the machinery.

## 2. The architecture decision, settled by test

Three routes were possible. A fourth was found and verified.

Their ontology is embedded at build time (`rust-embed`). An overlay merge exists — `Ontology::load_embedded_with_overlay`, maps merge, lists append, overlay-only files are added — but it is called **only from their integration test kit**. No CLI flag or env var reaches it. So extending their ontology in the installed binary is not possible; it needs a source build.

**But the local graph is a plain DuckDB file at `~/.orbit/graph.duckdb`, and nothing stops another process writing tables into it.**

Verified, working, this session:

```sql
orbit sql "SELECT c.path, c.client, c.activation, c.size_bytes, f.language
           FROM gl_context_surface c JOIN gl_file f ON f.path = c.path
           ORDER BY c.size_bytes DESC"
```

A context domain written by a separate indexer is queried by **their** CLI and **joins to their code graph**. That is the emulation path:

| Route | Cost | Chosen |
|---|---|---|
| Fork and build from source | Rust toolchain, upstream tracking, indexer work in Rust | No |
| Contribute the domain upstream | Longest path, not ours to schedule | Later, maybe (§12) |
| Parallel tool, own store | Loses their query surface, MCP, and all joins | No |
| **Co-resident tables in their DuckDB** | **A Python indexer that writes `gl_context_*`** | **Yes** |

Consequence: **`orbit sql` is the query engine, `orbit mcp` is the agent surface, and neither has to be built.**

## 3. Emulated wholesale

Adopted without argument. These are their calls.

| Adopted | Detail |
|---|---|
| **Persistent DuckDB** | `~/.orbit/graph.duckdb`, the same file. No live-derivation scheme, no cache of our own. Earlier revisions cut persistence on one small measurement; that is withdrawn. |
| **`gl_` table naming and column conventions** | `id`, `traversal_path`, `project_id`, `branch`, `commit_sha`, `path`, `name`, `size_bytes`, `reason`. |
| **`branch` + `commit_sha` on every row** | Snapshot semantics. Multiple repositories and branches coexist, scoped by `traversal_path`. |
| **`reason` column for skipped/errored files** | Coverage is a property of the record, not a footnote. |
| **Ontology as YAML, one file per type** | `node_type`, `domain`, `description`, `label`, `destination_table`, `default_columns`, `sort_key`, `properties`, `storage`. Written in their exact format, in a tree mirroring `config/ontology/`, so it can be overlaid or contributed upstream unchanged. |
| **Edges declared with `variants`** | One edge type, many `from_node`/`to_node` pairs, each described. |
| **`gl_edge` shape** | `source_id`, `source_kind`, `relationship_kind`, `target_id`, `target_kind`, `traversal_path`. Context edges go in `gl_context_edge`, mirroring how they route code edges to `gl_code_edge`. |
| **Sub-file granularity with byte offsets** | Their `Definition` carries `start_line`/`end_line`/`start_byte`/`end_byte`. `Clause` does the same (§4). Earlier revisions argued for file-level only; withdrawn. |
| **Virtual `content`** | Never stored, resolved from the file at query time. Same guarantee, cheaper: the row carries the path and offsets, the caller reads the bytes. |
| **Command shape** | `index`, `describe`, `repo-map`, `grep`, `list`, `sql`, `mcp`. Named questions above a general query. |
| **JSON statistics from `index`** | Counts of surfaces, clauses, edges, skipped, errored. |
| **`setup` pattern** | Managed section in the assistant's instruction file, `.orbit-backup` before first write, in-place update, clean `--remove`. See §8. |
| **Telemetry** | **Not** adopted. The one thing dropped from their runtime behaviour. |

## 4. The context domain — node types

New ontology files under `nodes/context/`. Their `source_code` nodes (`File`, `Directory`, `Branch`, `Commit`) are **reused, not duplicated** — the indexer joins to `gl_file` by path.

### `Surface` → `gl_context_surface`
A file that can place text into a session.

`id` · `traversal_path` · `project_id` · `branch` · `commit_sha` · `path` · `surface_kind` · `client` · `activation` · `size_bytes` · `est_tokens` · `revocable` · `evidence_class` · `detector` · `reason`

- `surface_kind`: `instruction-surface` | `skill-package` | `agent-definition` | `command-definition` | `hook-definition` | `mcp-config`
- `client`: `claude` | `codex` | `cursor` | `opencode` | `any` — **not optional.** `AGENTS.md` and `CLAUDE.md` in GitLab's own repo are byte-identical at 17,294 bytes each; a client-blind sum reports 39,975 for a session that pays ~22,700.
- `activation`: `boot` | `repo-entry` | `path-scoped` | `explicit-invocation` | `event` | `agent-scoped` | `retrieval` | `runtime`

### `Clause` → `gl_context_clause`
An addressable fragment within a surface — the governance analogue of `Definition`, and the reason granularity is sub-file.

`id` · `traversal_path` · `branch` · `commit_sha` · `surface_path` · `fqn` · `heading` · `clause_type` · `start_line` · `end_line` · `start_byte` · `end_byte` · `evidence_class` · `detector`

- `fqn` mirrors theirs: `CLAUDE.md#Estimating rules#M6 anchors`.
- `clause_type`: `heading-section` | `list-rule` | `frontmatter-field` | `code-block`
- Segmentation is by Markdown structure. A 17 KB instruction surface is dozens of rules with different lifetimes; addressing it as one file makes "which rule" unanswerable.

### `Mechanism` → `gl_context_mechanism`
The load ledger as a table. One row per way text reaches a session.

`id` · `traversal_path` · `mechanism` · `client` · `source_path` · `activation` · `trigger` (verbatim, with locator) · `scope` · `inheritance` · `bytes` · `est_tokens` · `lifetime` · `revocable` · `consumer_evidence` · `evidence_class` · `detector`

**Not reducible to edges.** A `LOADS` edge needs a file at the *from* end, and the loads that matter have none — the client loads a root instruction surface, not another file. Modelled as edges alone they vanish and their targets report as pointerless.

`bytes` is `NULL`, never `0`, where the payload is produced at runtime.

### `ExternalRef` → `gl_context_external_ref`
A pointer target not resolvable inside the indexed roots.

`id` · `address` · `sub_kind` · `evidence_class` · `detector`

`sub_kind`: `no-indexed-target-match` | `outside-indexed-roots` | `unresolvable-scheme`. **Never merged**, and each is a statement about the detector set, not the file.

## 5. The context domain — edge types

Written as `edges/*.yaml` with variants, routed to `gl_context_edge`.

| Edge | Variants | Evidence |
|---|---|---|
| `LOADS` | Mechanism → Surface; Surface → Clause | mechanism registry + config |
| `REFERENCES` | Surface → File · Surface → Surface · Clause → Surface · Surface → ExternalRef | markdown-link, frontmatter-field, config-value, bare-path, import-statement, supersedes-claim |
| `INVOKES` | Surface → File · Surface → ExternalRef | hook command, script call |
| `PRODUCES` | File → File | artifact header, manifest, literal write path |
| `IDENTICAL_BYTES` | File ↔ File | sha256 equality |
| `CONTAINS` | Surface → Clause · Clause → Clause | inherited semantics, nested headings |

`CONTAINS`, `IMPORTS` and `DEFINES` already exist in their ontology; the first is reused as-is, `REFERENCES`'s `import-statement` variant subsumes the second for prose estates.

## 6. The one genuine addition — evidence columns

`evidence_class` and `detector` on every row: `OBSERVED` | `DECLARED` | `INFERRED` | `UNKNOWN`, plus the name and version of the rule that produced it.

**Why add what the baseline does without.** Their inputs are parse trees — deterministic. These inputs are prose, filename conventions and heuristics, where a wrong guess is indistinguishable from a fact. Demonstrated on this project's own prototype: one detector bug produced **1,349 phantom findings out of 1,373**, every one authoritative-looking. Ninety-six percent of that report was the tool talking about itself.

**Promotion between classes is a defect.** A confirmed declaration yields two rows, not one upgraded row.

Two derived constraints:

- **Constrained output vocabulary.** Tool-authored output must not contain: *broken, dangling, orphaned, obsolete, stale, dead, unused, duplicate, redundant, misplaced, wrong, should, safe to delete.* Enforced by a test over tool-authored fields only — never over paths, addresses or quotes, which carry the estate's own words.
- **No prose columns.** No `summary`, no `purpose`. One exception: `verbatim_quote`, on DECLARED rows only, capped at 200 characters, always with a locator.

## 7. The indexer

`orbit-context index <path>` — Python 3, stdlib plus `duckdb`.

1. Walk indexed roots; find git repositories; read git state per repository.
2. Join to `gl_file` where present; index independently where not.
3. Detect surfaces by filename and frontmatter convention → `gl_context_surface`.
4. Segment surfaces into clauses by Markdown structure → `gl_context_clause`.
5. Build the mechanism registry from settings files, skill and agent directories, and known client conventions → `gl_context_mechanism`.
6. Extract and resolve pointers → `gl_context_edge`, `gl_context_external_ref`.
7. Hash every file; emit `IDENTICAL_BYTES`.
8. Emit JSON statistics, including skipped and errored counts with reasons.

Writes only `gl_context_*` tables. **Never writes to their tables.** Re-index replaces rows for the indexed `(traversal_path, branch, commit_sha)`.

Reads the checked-out tree. Other branches are reachable via `git cat-file` without checkout — deferred to a later slice, and recorded as a coverage gap until then, not as absence.

## 8. Query surface

Their CLI answers most of it. New commands only where there is no counterpart.

| Command | Origin |
|---|---|
| `orbit sql` | **Theirs.** The general query surface, across both domains. |
| `orbit describe` | **Theirs.** Extended by the context edges, since they land in a table it already reads. |
| `orbit mcp` | **Theirs.** The agent surface. |
| `orbit-context index` | New |
| `orbit-context boot --client C [--from PATH]` | New — the ledger for a cold session |
| `orbit-context cold-start --client C [--from PATH]` | New — the falsifier (§9) |
| `orbit-context would-load <selector>` | New — describes; never loads, never runs a hook. States the count of boot/repo-entry mechanisms it excluded. |
| `orbit-context repo-map` | New — governance orientation, budgeted against their measured 12,874 bytes for a 1,775-file repo |

**Footprint.** GitLab's `orbit setup` deliberately writes a managed section into instruction files and installs nudge hooks, because a tool nobody remembers to run does not get used. Their engineering is sound — backup, in-place update, clean uninstall — and their argument is correct.

The awkwardness is specific and worth stating: a tool that measures cold-start burden adds to the number it measures. The resolution is not to refuse the footprint but to **make it self-accounting** — `orbit-context setup` writes a managed section using their pattern, and `cold-start` reports that section as its own line item, by name. If the tool cannot justify its own bytes, that is a finding.

## 9. Cold-start burden — the falsifier

Bytes a fresh session loads, **per client, per entry point**, before it can begin one real task.

- Counts OBSERVED bytes only.
- Runtime payloads (hooks, MCP servers) appear as a named UNKNOWN line, **never zero** — otherwise the number improves by becoming less observable.
- Path-scoped surfaces count, keyed to entry point. Measured on GitLab's own repository: root entry ≈ 22,700 bytes for one client; opening a file under `crates/indexer/` adds **15,133** more, a 66% jump invisible in any single estate-wide figure.
- The tool's own managed section is a line item.

**Count, cut, count again.** The only figure meant to be tracked over time, and the only one whose direction has a right answer.

## 10. Verification

Against a script-built fixture estate, plus the two real repositories already used.

1. Boot path from repository entry, per client, with the hook payload reported UNKNOWN.
2. An explicitly invoked skill: body separated from its always-on description.
3. A hook definition resolved to its target script.
4. A generated artifact traced to producer (DECLARED) and consumer (OBSERVED).
5. A cross-repository reference.
6. A pointer with no indexed match.
7. A file with zero recognized inbound pointers, split into *no ledger row* versus *auto-loaded*.
8. A clause addressed by `fqn`, its bytes read from the file, not from the graph.
9. `orbit sql` joining `gl_context_surface` to `gl_file` — **already verified working**.
10. The vocabulary lint over every command's output.

## 11. Build slices

Each sized for one session. Slice 1 is a tracer bullet: end to end, thin.

| # | Slice | Done when |
|---|---|---|
| 1 | **Tracer:** walk one repo, detect instruction surfaces, write `gl_context_surface`, query via `orbit sql` | `orbit sql` returns surfaces joined to `gl_file` |
| 2 | Ontology YAML for the context domain, in their format | Files parse against their schema; `orbit-context index` reads table shapes from them |
| 3 | Mechanism registry → `gl_context_mechanism`; `boot` command | Ledger rows per client for a fixture estate |
| 4 | `cold-start`, per client and entry point, with UNKNOWN lines | A number, and its itemisation, for both real repositories |
| 5 | Clause segmentation → `gl_context_clause` with byte offsets | A rule addressable by `fqn`, bytes read from the file |
| 6 | Pointer extraction and resolution → `gl_context_edge`, `gl_context_external_ref` | The three negative findings, distinct, with detector versions |
| 7 | `PRODUCES` and `IDENTICAL_BYTES` | Byte-identical pairs reported with provenance-evidence count |
| 8 | `would-load`, `repo-map` | Governance orientation inside a stated budget |
| 9 | Fixture estate builder + vocabulary lint + acceptance scenarios | §10 passes |
| 10 | `setup`, following their pattern, self-accounting in `cold-start` | Managed section installs, uninstalls, and reports its own bytes |

## 12. Reserved for Dylan

1. **The indexed roots.** The estate boundary is a decision, not an observation.
2. **Whether `~/.claude/` and other user-global surfaces are inside it.** They load automatically and sit outside every repository.
3. **Which clients count.** The set changes every number in §9.
4. **Whether to adopt Orbit Local for the code half**, given its persistent index and its telemetry to a GitLab-operated collector.
5. **§8 footprint.** The self-accounting resolution is proposed, not settled.
6. **Whether the context domain is eventually contributed upstream** as a GitLab ontology domain rather than maintained co-resident. Their README explicitly invites ontology contributions.
7. **What "one real estimating task" means** for the cold-start count.
8. **Whether a rule removed to lower that number was doing work.** The tool measures the number; it cannot measure the loss.
9. **Whether this is built at all.** §13 stands.

## 13. Kill conditions

Stated in advance, so stopping is a planned outcome rather than a failure.

- It agrees with the hand-built indexes and surfaces nothing they did not already show.
- Its output starts being pasted into documents, or anyone asks it to write one.
- The cold-start number rises during its existence.
- It needs its own store, its own query language, or a second implementation — at which point the honest move is to contribute the ontology upstream instead of maintaining a parallel system.
- Someone reaches for it to decide something rather than to check something.

## 14. Permanent UNKNOWNs

- What any hook emits, without running it.
- What an MCP server injects at boot.
- Content on branches not checked out, until §7's `git cat-file` slice lands.
- Whether a loaded instruction influenced any output.
- Whether a path-shaped string in prose was a pointer or an example.
- Whether two identical files are intentionally identical.
- Whether an artifact is current relative to its declared producer.
- Anything constructed at runtime.
- True ahead/behind without fetching.
- Whether a file with zero inbound pointers matters.
