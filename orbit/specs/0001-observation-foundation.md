# Spec 0001 (rev 2) — a diff against GitLab Orbit

Status: draft, unimplemented
Baseline: **GitLab Orbit**, `gitlabhq/orbit-knowledge-graph` @ `0fe19ac`, CLI `orbit 0.118.1`, installed and run.

## 0. What this document is

**A diff, not an independent design.**

GitLab Orbit is a working, shipped, in-use context graph for AI agents. This document does not re-derive one. It takes GitLab Orbit as the default and records only:

- what is **inherited** unchanged,
- each **deviation**, with the reason, the reason's evidence class, what it costs if the reason is wrong, and how to revert,
- each **addition**, with the same,
- what is **undecided**.

Anything not named below is inherited. If a future session cannot find a deviation recorded here, the answer is *do what GitLab Orbit does.*

## 1. Why this was rewritten

Revision 1 was an independent design that discovered GitLab Orbit afterwards and then measured GitLab against itself. That inverted the evidence. Their system is built, shipped, and running against real repositories at scale; this document is a hypothesis written in one session that has never touched the estate it is for. Those are not peers, and treating them as peers let invented choices harden into "the spec says".

Under a diff, a departure is a **debt with a stated reason**, not a feature. Several of revision 1's positions do not survive that test and are demoted below.

## 2. Inherited from GitLab Orbit, unchanged

Taken as-is. No argument required; these are their calls and they are good.

| Inherited | What it means here |
|---|---|
| **Property graph over RDF** | Typed nodes, typed directed edges, properties on both. |
| **Ontology as one file per type** | `config/ontology/nodes/<domain>/<type>.yaml`, `config/ontology/edges/<type>.yaml`. Adding a type is adding a file. Rev 1 praised this pattern and then failed to adopt it; adopted now. |
| **Edge `variants`** | One edge type declares many `from_node`/`to_node` pairs, each with its own description. Their `contains.yaml` carries 8 variants. This is exactly how a small edge set stays honest about what it actually connects. |
| **`description` on every type and variant** | Machine-readable and human-readable in the same place. |
| **Local-first, offline, no account at query time** | `orbit index .` then query. Same posture. |
| **Read-only query surface** | Their `sql` is read-only by construction. |
| **Purpose-built commands over raw query** | `grep`, `show`, `describe`, `repo-map`, `list` sit above `sql`. The shape is right: a few named questions, with the general query underneath. |
| **`describe` semantics** | "Print every connection of X — callers, callees, supertypes, members, importers." This is `inbound` + `outbound` in one command, and their naming is better. **Adopted: `describe` replaces rev 1's separate `inbound`/`outbound`.** |
| **`repo-map` as the orientation command** | A high-level, LLM-oriented map. **Adopted, name included**, replacing rev 1's invented `orient`. |
| **MCP as a delivery surface** | They serve the graph over MCP. Same, when there is anything worth serving. |
| **Skipped/errored file accounting** | Their `gl_file.reason` column records *why* a file was skipped (`oversize`, `timeout_parse`, `invalid_utf8`). Coverage is a first-class property of the record, not a footnote. Adopted. |
| **Indexing emits statistics as JSON** | Counts of directories, files, definitions, relationships, skipped, errored. Adopted. |

## 3. The gap that motivates a diff at all

GitLab Orbit indexes **code**. It parses 20 languages — Rust, Python, Go, TypeScript, Ruby, Bash, YAML, and others — and **not Markdown**.

Measured on two real repositories with the installed binary:

| | GitLab's own repo (Rust) | A Markdown estate |
|---|---|---|
| Files | 1,775 | 202 |
| Definitions | 17,669 | **0** |
| Edges | 57,278 | 249, all structural |
| Index time | 15.5 s | 1.1 s |

And on their own repository, every one of the **357 edges touching a `.md` file is `CONTAINS`** — "this directory holds this file". It records that `CLAUDE.md` exists and is 17,294 bytes. It does not record that the file is an instruction surface, that it loads at repository entry, or that `AGENTS.md` beside it is byte-identical.

**That is the whole gap, and it is one addition (§5, A1), not a different system.**

## 4. Deviations

Each carries: **their choice → this choice**, the reason, the **evidence class of the reason**, the cost of the reason being wrong, and how to revert.

---

### D1 — Domain: source code → context and governance surface

**GitLab:** indexes definitions, imports and call sites across 20 languages.
**Here:** indexes instruction surfaces, skill packages, agent definitions, hook definitions, and the pointers between Markdown and config files.

**Reason:** the estate's stated problem is which rules load into a session and at what cost, which their parser set cannot see (§3).
**Evidence class: OBSERVED.** Measured, twice, with their binary.
**Cost if wrong:** none — it is additive. The code layer is not removed, it is delegated (§6).
**Revert:** not applicable; without this there is no project.

---

### D2 — Storage: persistent DuckDB → **undecided**

**GitLab:** persistent DuckDB at `~/.orbit/graph.duckdb`, shared across repositories, scoped by repository and branch.
**Rev 1:** no persistence, live derivation, cache cut on evidence.
**Rev 2: undecided. The rev-1 position is withdrawn.**

**Why withdrawn.** Rev 1 cut persistence citing 0.24 s over 190 files. That measurement does not carry: the same code took 1.6 s over 1,775 files, and a multi-repository estate is untested. Their persistence is not a design flourish — parsing 17,669 definitions is genuinely expensive and worth keeping. This document generalised one small number into a principle.

**Evidence class of the reason for deviating: INFERRED, and weakly.** Not sufficient to overturn a shipped design.
**Resolution:** measure the real estate in step 3 (§9). Live derivation is the *provisional default* only because it is the cheaper thing to try first and trivially reversible — not because it is established.
**Note:** if persistence is adopted, the anti-staleness guarantee must come from somewhere else, and their model (index explicitly, record `commit_sha`, re-index on demand) is the thing to copy.

---

### D3 — Node set: 6 source-code node types → 3 kinds plus roles. **Provisional.**

**GitLab (`source_code` domain):** `Branch`, `Commit`, `Directory`, `File`, `Definition`, `ImportedSymbol`. Across the whole ontology, 32 node files.
**Here:** `Scope` (repository / worktree / directory), `File`, `ExternalRef` — plus additive, evidence-bearing **roles** on a `File` (`instruction-surface`, `skill-package`, `agent-definition`, `hook-definition`, `hook-target`, `executable`, `config`, `test`, `generated-artifact`, `generator`, `decision-surface`).

**Reason:** a governance file is often several things at once — a hook script is a tool *and* a hook target *and* possibly a generator. Making each a node type forces a single categorisation at index time.
**Evidence class: INFERRED.** This is an argument from principle. It has been exercised on two repositories and did not break, which is not the same as being right.
**Cost if wrong:** roles are unindexed labels, so role-heavy queries degrade to scans. GitLab's typed tables with per-column codecs and bloom filters exist because that mattered to them at scale.
**Revert:** promote any role to a node type by adding one ontology file. The inherited file-per-type pattern (§2) makes this cheap **by design** — which is the main reason to adopt their pattern rather than a table in code.
**Status: provisional until the audit.** Rev 1 stated this as settled. It is not.

---

### D4 — Edge set: their code edges → six kinds

**GitLab (code graph):** `CONTAINS`, `DEFINES`, `IMPORTS`, `CALLS`, `EXTENDS`, `ON_BRANCH`. 59 edge files across the full ontology.
**Here:** `contains`, `references`, `loads`, `invokes`, `produces`, `identical-bytes`, each declared with **variants** in their format.

Mapping, so the relationship is legible:

| GitLab | Here | Note |
|---|---|---|
| `CONTAINS` | `contains` | Same. Inherited outright. |
| `IMPORTS` | `references` (variant `import-statement`) | Demoted to a variant: in a Markdown estate an import is one pointer kind among many. |
| `CALLS` | — | Not represented. Delegated (§6). |
| `DEFINES`, `EXTENDS` | — | Sub-file structure. Delegated (§6). |
| `ON_BRANCH` | — | See D7. |
| — | `references` | New: Markdown links, frontmatter fields, config values, bare paths. |
| — | `loads` | New. The point of the exercise (A1). |
| — | `invokes` | New: hook commands, script calls. |
| — | `produces` | New: generator → artifact. |
| — | `identical-bytes` | New: hash equality. |

**Reason:** these are the relationships that exist mechanically in a governance surface.
**Evidence class: OBSERVED** for the existence of each (all were detected on real repositories); **INFERRED** for the claim that six is the right number.
**Cost if wrong:** too few edge kinds means semantics hide inside `subtype` strings and become hard to query.
**Revert:** add an edge file.

---

### D5 — Granularity: sub-file → file-level. **Provisional.**

**GitLab:** `Definition` carries `start_line`, `end_line`, `start_byte`, `end_byte`, `start_char`, `end_char`, and a virtual `content` resolved on demand.
**Here:** file-level, with `file:line` locators on evidence records only.

**Reason:** a rule inside a `CLAUDE.md` has no addressable boundary the way a function does; Markdown has no equivalent of a definition.
**Evidence class: INFERRED.** Plausible, unproven.
**Cost if wrong — and this may well be wrong:** the estate's real question is often *which rule*, not *which file*. A 17 KB instruction surface is not one thing; it is dozens of rules with different lifetimes. Their byte-offset model exists precisely so a caller can address a fragment without copying it, and that is the same problem.
**Revert:** add a `Clause` node type with byte offsets into an instruction surface, following `definition.yaml` exactly.
**Status: the most likely deviation to be reversed by the audit.**

---

### D6 — Always-on footprint: they install one → this forbids one

**GitLab:** `orbit setup <assistant>` writes a **managed section into the assistant's instruction file** (user-global by default, `--project` for the repository) and installs **nudge hooks** where the platform supports them, for Claude Code and OpenCode. It takes a one-time `.orbit-backup` before first modification, updates the section in place on re-run, and uninstalls with `--remove`. They also ship two skill packages, whose descriptions load at boot.
**Here:** zero always-on footprint. Never in an instruction surface, never a hook, never a skill description. Invoked deliberately or not at all.

**Reason:** the tool that measures cold-start burden must not be part of it, and an estate diagnosed with too many auto-loading mechanisms should not gain another.
**Evidence class: DECLARED** — it follows from a claim about the estate, not from a measurement.

**The counter-argument, stated fairly because it is strong.** GitLab made the opposite call deliberately and engineered it properly: backup before write, managed section with stable boundaries, in-place update, clean uninstall. Their reasoning is visible in the command's own help text — *"telling the assistant to prefer graph queries over grepping raw files"* — a tool nobody remembers to run is a tool that does not get used, and a graph that goes unqueried while the agent greps is worse than no graph.

**Cost if wrong:** the tool is built, is correct, and nobody runs it.
**Revert:** adopt `orbit setup`'s pattern wholesale — managed section, backup, `--remove`. It is a good design and it exists.
**Status: a genuine open disagreement with the baseline, not a settled principle.**

---

### D7 — Branches: `ON_BRANCH` edges and `branch` on every node → checked-out tree only

**GitLab:** every code node carries `branch` and `commit_sha`; `ON_BRANCH` snapshots a node to a branch and commit; the local DB holds multiple repositories and branches side by side.
**Here:** only the checked-out tree is read. Branches are named from the ref database; nothing is read from them.

**Reason:** reading another branch requires a checkout or an object walk, with cost and side effects.
**Evidence class: INFERRED.** Git can read another branch's blobs without checkout (`git cat-file`), so "requires a checkout" is **not true as stated** — this is a scoping choice, not a constraint. Recorded honestly.
**Cost if wrong:** a rule, hook or skill that exists only on an unchecked-out branch is invisible. On an estate with active branches this could be a large blind spot.
**Revert:** copy their model — carry `commit_sha` on every record and read via `git cat-file`.

---

### D8 — Language coverage: 20 tree-sitter parsers → Markdown, JSON, TOML, YAML, shell

**GitLab:** Bash, C#, C++, Elixir, Go, HCL, Java, JavaScript, Kotlin, Lua, PHP, Python, Ruby, Rust, Scala, Swift, TSX, TypeScript, YAML, Zig.
**Here:** the file types a governance surface is written in.

**Reason:** complementary coverage, not competing (§6).
**Evidence class: OBSERVED.** Their parser list was read from `languages.rs`; the absence of Markdown was verified.
**Cost if wrong:** none. Both can be run.
**Revert:** n/a.

---

### D9 — Runtime: Rust → Python 3, stdlib only

**GitLab:** Rust, tree-sitter, DuckDB/ClickHouse, ~150 MB binary.
**Here:** Python 3, standard library.

**Reason:** the work is walking directories, running `git`, reading text, emitting JSON. A codebase its owner can read is a codebase its owner can trust.
**Evidence class: INFERRED.** A preference with a rationale, not a measurement. Their choice is justified by tree-sitter and by scale; neither applies here yet.
**Cost if wrong:** slow on a large estate. Unmeasured beyond 1,775 files / 1.6 s.
**Revert:** cheap while the surface is small; expensive later.

---

### D10 — Telemetry: present → absent

**GitLab:** the released binary attempts telemetry to a GitLab-operated collector; `config/default.yaml` exposes `collector_url`. Observed: index runs emitted `batch send failed … snowplowprd.trx.gitlab.net` when the network blocked it.
**Here:** no network access at all.

**Reason:** a private estate.
**Evidence class: OBSERVED** for their behaviour; **DECLARED** for the requirement.
**Cost if wrong:** none.
**Note:** this also bears on adopting Orbit Local itself (§6, §10).

---

## 5. Additions

Things with no counterpart in the baseline.

### A1 — The load ledger

The one thing GitLab Orbit does not do and this exists for.

An inventory of every mechanism that can place repository-authored text into a session. One row each:

`mechanism` · `client` · `source` · `activation` (`boot` | `repo-entry` | `path-scoped` | `explicit-invocation` | `event` | `agent-scoped` | `retrieval` | `runtime`) · `trigger` (quoted verbatim, with locator) · `scope` · `inheritance` · `bytes` · `est_tokens` · `lifetime` · `revocable` · `consumer_evidence`

**The `client` field is not optional.** Mechanisms are client-specific: Claude Code reads `CLAUDE.md`, Codex reads `AGENTS.md`. On GitLab's own repository those two files are **byte-identical at 17,294 bytes each**, so a naive repo-entry sum of 39,975 bytes describes a client that does not exist; a real session pays ~22,700. Every figure is reported **per client and per entry point**. A cross-client total may appear only as an explicitly labelled upper bound.

**The ledger is not reducible to edges.** A `loads` edge needs a file at the *from* end, and the loads that matter have none — the client loads a root instruction surface, not another file. Modelled as edges alone they vanish, and the files then report as pointerless. On a fixture that was 5 of 8 files in the bucket: the entire governance surface.

**Revocability, observed:** for almost every mechanism, `revocable` is *no*. Once bytes are in a context window they stay for its life. Two consequences, reported not acted on: progressive disclosure is achievable only by **not loading**; and the only real revocation boundary is a **bounded sub-session that ends**.

### A2 — Evidence classes

**GitLab has none.** In their ontology a fact is a fact. Here every node, role and edge carries:

`class` (OBSERVED | DECLARED | INFERRED | UNKNOWN) · `source` · `locator` · `detector` name and version

- **OBSERVED** — a mechanical read that does not depend on interpretation.
- **DECLARED** — a claim made by repository content, recorded with who said it and where.
- **INFERRED** — an Orbit heuristic, named so it can be disagreed with specifically.
- **UNKNOWN** — the question is known and cannot be answered mechanically. A first-class result.

**Promotion between classes is a defect.** A confirmed declaration yields two records, not one upgraded record.

**Why add this when the baseline does without.** Their inputs are parse trees and a database — deterministic. These inputs are prose, filename conventions and heuristics, where a wrong guess is indistinguishable from a fact. Demonstrated on this very tool: a detector bug produced **1,349 phantom findings out of 1,373**, and every one looked authoritative. Ninety-six percent of that report was the tool talking about itself.

*Evidence class of this addition's reason: OBSERVED.* It is the best-supported thing in the document.

### A3 — Cold-start burden

`cold-start` — bytes a fresh session must load, **per client, per entry point**, before it can begin one real task. Counts OBSERVED bytes. Runtime-payload mechanisms (hooks, MCP) appear as a named **UNKNOWN line, never zero**, or the number improves by becoming less observable.

Path-scoped surfaces count, keyed to entry point. Measured on GitLab's repository: entering the root costs ~22,700 bytes for one client; opening a file under `crates/indexer/` adds a further **15,133** — a 66% increase invisible in any single estate-wide figure.

This is the falsifier: **count, cut, count again.** It is the only figure meant to be tracked over time and the only one whose direction has a right answer.

### A4 — Constrained output vocabulary

These words must not appear in tool-authored output: **broken, dangling, orphaned, obsolete, stale, dead, unused, duplicate, redundant, misplaced, wrong, should, safe to delete.** Enforced by a test over **tool-authored fields only** — never over addresses, paths, locators or quotes, which carry text the estate wrote.

Three negative findings stay distinct and are never merged: `no-indexed-target-match`, `outside-indexed-roots`, `zero-recognized-inbound-pointers`. Each is a statement about the **detector set**, not about the file, and each is reported with its detector version.

`zero-recognized-inbound-pointers` splits in two: *no pointers and no ledger row*, versus *no pointers but auto-loaded*. Merging them flags an estate's entire governance surface as pointerless.

### A5 — No prose in the output schema

The schema has **no field able to carry prose extracted from a file**, with one exception: `verbatim_quote`, permitted only on DECLARED records, capped at 200 characters, always with a locator.

**This is a real divergence from the baseline.** GitLab's `File` and `Definition` both carry a virtual `content` property resolved from Gitaly at query time. That is the right call for them — resolved live, never stored, never stale. The same guarantee is available here more cheaply: hand over the path, let the caller read the file.

### A6 — No durable artifacts

Output goes to stdout. No report file, no generated index, no committed findings. The observation must not become another document explaining the observation.

*Evidence class: DECLARED.* It follows from a claim about the estate's history, not a measurement.

## 6. What is delegated rather than built

**The code layer is GitLab Orbit's, off the shelf.** `orbit index .`, then `grep` / `show` / `describe` / `sql` / `repo-map` / `mcp`. Verified working: 17,669 definitions and 20,104 `CALLS` edges from 1,775 Rust files in 15.5 s, offline after install.

| Question | Answered by |
|---|---|
| What calls this function? What breaks if I change it? | **GitLab Orbit Local** |
| What loads into a session, from where, at what cost, on what evidence? | **This diff** |
| Which of these governs the task? | **Neither.** Explicit activation, by a human, a workflow definition, or an event. |

No integration is proposed. Separate commands, separate questions, same files.

## 7. Corrections to revision 1

Recorded so the same mistakes are not re-derived.

1. **"GitLab Orbit does not touch the governance surface" — wrong.** It does not *index* it, but `orbit setup` **writes into instruction files and installs hooks**, and it ships skill packages whose descriptions load at boot. Revision 1's zero-footprint rule is therefore a **deviation from the baseline** (D6), not a neutral principle.
2. **The orientation budget was invented.** Rev 1 asserted a 2,000-token budget with no basis. Their `repo-map` on a 1,775-file repository emits **12,874 bytes (~3,200 tokens)**. That is a real number from a working tool; the invented one is dropped.
3. **Cutting persistence was overreach.** One measurement on one small repository was generalised into a principle (D2).
4. **The ontology-as-YAML pattern was praised and then not adopted.** Fixed (§2).
5. **`inbound` / `outbound` / `orient` were invented names** for things GitLab already names `describe` and `repo-map`. Their names are adopted.
6. **"Reading another branch requires a checkout" is false** (D7). It is a scoping choice.
7. **The three-node model and file-level granularity were stated as settled.** Both are provisional (D3, D5).

## 8. Query surface

Inherited names first; new commands only where there is no counterpart.

| Command | Origin |
|---|---|
| `index` | Inherited |
| `describe <path>` | Inherited name and semantics — every connection of a thing |
| `repo-map` | Inherited — orientation |
| `list` | Inherited — indexed repositories |
| `sql` / general query | Inherited — read-only |
| `mcp` | Inherited |
| `estate` | New — repositories, worktrees, git state |
| `boot [--client C] [--from PATH]` | New — the ledger (A1) |
| `cold-start [--client C] [--from PATH]` | New — the falsifier (A3) |
| `would-load <selector>` | New — describes; never loads, never runs a hook. Reports the count of boot/repo-entry mechanisms it excluded, and points at `boot` for them. |
| `trace <path>` | New — producers, consumers, tests |
| `unmatched` / `outside` / `unpointed` / `dupes` | New — the negative findings (A4) |
| `blindspots` | New — what cannot be known mechanically |

## 9. How this gets tested

1. Rev 2 (this document).
2. **Prototype** — throwaway, on `prototype/orbit-observer`, already run: all seven acceptance scenarios on a synthetic estate, plus two real repositories.
3. **Audit** — run over the real estate. Settles D2 (persistence), D3 (node set), D5 (granularity), D7 (branches), and whether the cold-start metric holds.
4. **Build** — corrected diff, fixtures harvested from step 3, one seam: a script-built fixture estate to JSON, plus the vocabulary lint.

## 10. Reserved for Dylan

1. **The indexed roots.** The boundary is a decision, not an observation.
2. **Whether user-global surfaces (`~/.claude/`) are inside it.** They load automatically and sit outside every repository.
3. **D6 — always-on footprint.** GitLab installs one deliberately and engineered it well. A tool nobody runs is worth nothing. This is the sharpest open disagreement with the baseline.
4. **D2 — persistence**, once the audit gives a real number.
5. **D5 — granularity.** If the real question is *which rule* rather than *which file*, their byte-offset model is the answer and this deviation reverses.
6. **Whether to adopt Orbit Local**, given its persistent index and its telemetry.
7. **Which clients count** for cold-start. The set changes every number.
8. **Whether this should be built at all.** §11 stands.
9. **What "one real estimating task" means** for the cold-start count.
10. **Whether a rule removed to lower that number was doing work.** Measurable: no.

## 11. Kill conditions

Stated in advance, so stopping is a planned outcome.

- It agrees with the hand-built indexes and surfaces nothing they did not already show.
- Its output starts being pasted into documents, or anyone asks it to write one.
- The cold-start number rises during its existence.
- It needs a persistent graph **and** a query DSL **and** a second implementation to stay accurate — at which point the honest move is to file the governance ontology upstream with GitLab rather than maintain a parallel system.
- Someone reaches for it to decide something rather than to check something.

## 12. Permanent UNKNOWNs

- What any hook emits, without running it.
- What an MCP server injects at boot.
- Content on any branch not checked out (until D7 reverses).
- Whether a loaded instruction influenced any output.
- Whether a path-shaped string in prose was a pointer or an example.
- Whether two identical files are intentionally identical.
- Whether an artifact is current relative to its declared producer.
- Anything constructed at runtime.
- True ahead/behind without fetching.
- Whether a file with zero inbound pointers matters.
