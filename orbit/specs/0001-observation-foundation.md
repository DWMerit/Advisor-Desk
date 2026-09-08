# Spec 0001 — Orbit: the observation foundation

Status: draft, unimplemented
Authored: 2026-09-08
Authored deliberately **before** inspecting any existing estate repository, so the model is derived from first principles rather than from current folder names.

## What this spec decides

The node model, relationship model, evidence model, load ledger, query surface and output contract for **Orbit**, the observation plane of the HITL context-and-governance operating system.

## What this spec explicitly does not decide

- The target repository set.
- Which capability belongs in which repository.
- Whether any existing file is canonical, obsolete, duplicated, misplaced, or safe to delete.
- Which workflow governs any task.
- The design of retrieval, context assembly, or execution beyond the **interface** each needs from Orbit.

---

## 1. The question this spec answers

> How does a session find out what the estate actually is — right now, mechanically, with evidence — without any part of that answer deciding what the estate *means*?

Everything else in the operating system depends on this being trustworthy. A governance layer built on a map that quietly editorialises is worse than no map, because its errors are invisible and inherited.

Estimating analogue: Orbit is the **quantity takeoff**, not the estimate. A takeoff says *there are 412 receptacles, here is the sheet and grid line for each*. It does not say which are in scope, which the GC will delete, or what they cost. The moment a takeoff starts pricing, you can no longer audit it. Orbit has the same rule.

---

## 1.1 Why this is not one more mechanism

> **Evidence class: DECLARED.** The failure modes below come from a prior session's analysis of the estate, supplied as input to this spec. Every figure in them is an unverified claim from that analysis, not something confirmed here — no estate repository was inspected while writing this document. They are recorded because a design argument is worth answering even when unverified; they are not promoted to fact, and the audit (§17) is where they get tested.

The strongest argument against building Orbit is claimed to come from the estate's own history:

- It adds a mechanism to a system whose diagnosed problem is too many mechanisms.
- It makes **collecting** cheaper, and cheap collecting is claimed to be what produced a 693-line `CONTEXT.md`.
- Hand-built indexes are claimed to already function as a context graph — 373 rows, zero measured drift. Automating something that is working is not obviously a gain.
- Every previous reset is claimed to have become a document explaining the reset. An observation tool is a machine for producing more of those.

This spec does not need those claims to be true. Four structural guards answer them either way, and each is mechanical rather than a promise — they cost nothing if the claims turn out to be wrong.

**G1 — Orbit exists to make subtraction safe, not collection cheap.**
You cannot delete confidently without knowing what points at the thing. (The prior analysis claims ~300 references a single deletion would strand; treat the figure as DECLARED and the shape of the problem as the point.) `inbound` and `unmatched` are the deletion-safety tools, and every other command is in service of them. A command that does not help you remove something, or verify that removing it is survivable, has to justify its own existence.

**G2 — Orbit has zero always-on footprint** (invariant I9).
Orbit appears in no instruction surface, no skill description, no hook, no session start. It is a command a human or a bounded session runs deliberately. Its cost to a cold session is zero bytes. A tool that measures the boot burden must never be part of it.

**G3 — Orbit writes no documents** (invariant I10).
Output goes to stdout and dies with the terminal. No report file, no generated index, no committed findings, no markdown artifact. This is the guard against reset number four: the observation must not become another document explaining the observation. If a finding matters, a human writes one line somewhere durable — a human act, not a tool output.

**G4 — Orbit's success is a number that goes down** (invariant I11).
Not graph richness. See §11a.

**On the indexes claimed to already work.** If the zero-drift claim holds, that is evidence the convention works, not evidence automation is needed. Orbit's honest role against a working index is a **cheap drift check**: run it, get the same 373 rows, learn nothing, cost nothing. The day it disagrees is the day it earned its place. Orbit never replaces, regenerates or improves an index — §18 forbids it outright.

**On matching the repo's habit.** A system whose rulebook is majority self-defence — claimed, in the prior analysis, at 9 of 17 rules about the machinery against 4 about estimating — teaches every session that arrives to produce more self-defence. Orbit cannot fix that, and must not participate in it: I10 means Orbit has no way to add to the pile even if a session wants it to.

---

## 2. The four planes

The operating system has four planes. Orbit is plane 1 and only plane 1.

| Plane | Name | Job | Decides meaning? |
|---|---|---|---|
| 1 | **Observation** (Orbit) | Reports what exists, how it connects, what can load, and the evidence for each claim. | No |
| 2 | **Retrieval** | Flat search across every boundary, for recall. | No |
| 3 | **Context assembly** | An explicit selection chooses which local instructions and sources to load. | Yes — by explicit human/workflow selection |
| 4 | **Execution** | A bounded session performs work under the activated context. | Yes — within its bounds |

**Flat retrieval, nested governance.** Search must ignore boundaries or recall collapses. Authority must respect boundaries or governance leaks. These are opposite requirements and they belong on different planes. Orbit serves both and obeys neither.

### Orbit must never

- Choose which workflow governs a task.
- Treat proximity, linkage or frequency as relevance.
- Load a workflow because it discovered one.
- Rank authority, resolve conflicts, or prescribe repository changes.
- Store a second, summarised copy of repository content.

The last one is the failure mode that kills this kind of system. It is prevented structurally in §12, not by discipline.

---

## 3. Non-negotiable invariants

These are the spec. Everything below is an implementation of them.

- **I1 — Report, never decide.** Every Orbit output is a fact plus its evidence. No output ranks, prioritises, or recommends.
- **I2 — Certainty is never promoted.** OBSERVED / DECLARED / INFERRED / UNKNOWN travel with every claim and never merge. A query may filter by class; nothing may collapse classes.
- **I3 — A declaration stays a declaration.** Repository prose asserting ownership, canonicity or supersession is recorded as *"file X, line N, claims Y"* — permanently, no matter how plausible.
- **I4 — Absence of evidence is reported as absence of evidence.** Never as absence of the thing. See §9.
- **I5 — Orbit stores structure, never prose.** Paths, hashes, counts, git state, byte sizes: yes. Extracted or summarised file content: no. One narrow exception in §12.
- **I6 — Observation does not activate.** Describing what a workflow would load must not load it, run it, or check it out.
- **I7 — Live derivation by default.** No persistent graph. Cache is disposable and content-addressed, never a source of truth.
- **I8 — Orbit's boundary is always stated.** Every report says what was indexed and what was not.
- **I9 — Zero always-on footprint.** Orbit is never auto-loaded, never referenced from an instruction surface, never registered as a hook. Cost to a cold session: zero bytes.
- **I10 — No durable artifacts.** Output is ephemeral. Orbit writes no report, no index, no findings file, anywhere, ever — outside its disposable cache.
- **I11 — Success is the cold-start burden falling**, not the graph growing.

---

## 4. The observed estate boundary

Orbit resolves the estate from filesystem and git evidence at run time, from a set of **indexed roots**.

For every repository found under an indexed root, Orbit records:

| Fact | Source | Class |
|---|---|---|
| Repository root path | filesystem: `.git` present | OBSERVED |
| Whether `.git` is a directory or a worktree pointer file | filesystem | OBSERVED |
| Remotes and their URLs | `git remote -v` | OBSERVED |
| Current ref, or detached HEAD + sha | `git symbolic-ref` / `git rev-parse` | OBSERVED |
| Local branches | `git for-each-ref refs/heads` | OBSERVED |
| Remote-tracking branches last known locally | `git for-each-ref refs/remotes` | OBSERVED |
| Ahead/behind vs upstream | `git rev-list --left-right --count` | OBSERVED **as of last fetch** |
| Time of last fetch | mtime of `.git/FETCH_HEAD` | OBSERVED |
| Dirty / staged / untracked counts | `git status --porcelain` | OBSERVED |
| Linked worktrees and their paths and refs | `git worktree list --porcelain` | OBSERVED |
| Submodules declared | `.gitmodules` | DECLARED |
| Submodules actually populated | filesystem | OBSERVED |
| Paths referenced that fall outside all indexed roots | pointer resolution | OBSERVED (as *outside boundary*) |

### Hard boundary: Orbit observes the checked-out tree only

Orbit **names** every branch it can see in the ref database. It **does not read content from any branch that is not checked out**, in any worktree, because doing so would require a checkout or an object walk whose cost and side effects break I6 and I7.

Consequence, stated plainly in every report: *a rule, hook or skill that exists only on an unchecked-out branch is invisible to Orbit.* That is a coverage gap, not a claim of nonexistence.

Ahead/behind is truthful only about local knowledge. Orbit never fetches. If `FETCH_HEAD` is three weeks old, the report says so and classes the ahead/behind figure as OBSERVED-as-of-that-time.

---

## 5. Node model

The smallest model that preserves the useful distinctions is **three node kinds**.

### 5.1 `Scope`

A bounded region with an identity. Kinds: `repository`, `worktree`, `directory`.

Branches are **not** nodes. A branch is state of a repository, recorded as an attribute (§4). Making branches nodes implies Orbit can see into them, which it cannot.

### 5.2 `File`

Every regular file under an indexed root, addressed by repo-relative path. A file is one node regardless of how many things it is. Attributes: size in bytes, content hash, executable bit, mtime, tracked/untracked.

### 5.3 `ExternalRef`

A pointer target Orbit cannot resolve to a `File` inside its indexed roots. It has an address and no content. Three sub-kinds, and they must never be merged (§9): `no-indexed-target-match`, `outside-indexed-roots`, `unresolvable-scheme` (URLs, MCP server names, runtime identifiers).

### 5.4 Why not more node types

The brief lists eighteen candidate types — rule surface, skill package, hook, tool, test, generator, artifact, agent definition, and so on. Making each a node kind forces a decision at index time: *is this file a rule or a skill?* That decision is exactly what Orbit is forbidden to make, and it is frequently wrong (a hook script is a tool **and** a hook target **and** possibly a generator).

Instead those distinctions become **roles** (§6): additive, evidence-bearing, non-exclusive labels on a `File`. Nothing is forced into one box, and every label carries the detector that produced it.

---

## 6. Role model

A role is an observation: *"this file matched detector D, whose evidence is E."* A file may carry any number of roles, or none. Roles are data, not schema — the detector registry is a list Orbit ships and you extend.

| Role | Detector evidence | Class |
|---|---|---|
| `instruction-surface` | Filename matches a known always-on convention (`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `.github/copilot-instructions.md`, `GEMINI.md`) | OBSERVED |
| `skill-package` | Directory containing `SKILL.md` with parseable frontmatter carrying `name` + `description` | OBSERVED |
| `agent-definition` | File under `.claude/agents/` with frontmatter carrying `name` + `description` | OBSERVED |
| `command-definition` | File under `.claude/commands/` | OBSERVED |
| `hook-definition` | An entry inside a settings file's `hooks` block | OBSERVED |
| `hook-target` | A file named as the command of a hook definition | OBSERVED |
| `executable` | Executable mode bit, or a shebang on line 1 | OBSERVED |
| `config` | Filename matches a known tool's config convention | OBSERVED |
| `test` | Path or filename matches a framework convention **and** a matching framework config exists in the same repo | INFERRED |
| `generated-artifact` | File contains a generation marker in its first N lines (`DO NOT EDIT`, `@generated`, `Generated by`) | DECLARED |
| `generator` | File appears as the producer end of a `produces` edge (§7) | varies with that edge |
| `decision-surface` | Path matches an ADR/decision-record convention, or is `CHANGELOG.md` | INFERRED |
| `data-record` | Under a path declared in config as project/job evidence | DECLARED |

Notes that matter:

- `test` is INFERRED, not OBSERVED. Naming convention is a convention, not a fact. Orbit says *"matched the pytest convention"* and stops.
- `generated-artifact` is DECLARED because the file is asserting something about itself. A file with no marker is not thereby hand-written — it is unmarked.
- Absence of every role is not a finding. Most files have no role. That is normal.

---

## 7. Relationship model

**Six edge kinds.** Each carries a `subtype` naming the detector, which is evidence, not meaning.

### 7.1 `contains`

Scope → Scope, Scope → File. Source: filesystem walk plus `git worktree list`. Class: OBSERVED. No blind spots beyond permissions and symlink loops, both of which are reported rather than followed.

**Cannot conclude:** containment is not ownership, authority, or scope of application.

### 7.2 `references`

File → File | ExternalRef. A path-like or URL-like token found in a file's bytes that Orbit attempted to resolve.

Subtypes and their evidence: `markdown-link`, `markdown-image`, `frontmatter-field`, `import-statement`, `require-call`, `config-value`, `shell-path`, `bare-path-literal`, `supersedes-claim`.

Class: OBSERVED that *the token exists at file:line*. The **resolution** is OBSERVED when the target is a real file; otherwise it becomes an `ExternalRef` of the appropriate sub-kind.

**False-positive risks, which the report must state:** a path-shaped string inside a code sample, a fenced block, a commented-out line, or a string that coincidentally looks like a path. Orbit records whether the token was inside a fenced code block, and never removes such matches — it labels them.

**Measured after the prototype (§17), and the single largest risk in the whole model.** Token-boundary handling in the bare-path detector dominated the finding count. A backtick placed in a negative lookbehind did not skip inline code — it shifted the match *start* into the middle of the token, so `` `patterns-of-enterprise-application-architecture/…mini.md` `` matched as `of-enterprise-application-architecture`, a target that cannot exist. Over one real repository that produced **1,349 phantom `no-indexed-target-match` findings out of 1,373**. Correct boundary handling: **59**.

Two rules follow, and they are not optional:

- A reference detector must match from a real token boundary (line start, whitespace, or one of `` ` `` `'` `"` `(` `<` `[`), never from a negative lookbehind that can slide the start.
- Every negative finding is reported **with its detector version**, because a detector bug is indistinguishable from an estate condition when you are only shown the count. Ninety-six percent of that first count was Orbit talking about itself.

**Cannot conclude:** that the reference is used, current, intended, or authoritative. A reference is a string, not a dependency.

### 7.3 `loads`

File → File. A `references` edge where a **known loading mechanism** will place the target's bytes into a session's context.

Source: the mechanism registry (§10) plus the config that activates it. Class: OBSERVED where the mechanism is file-driven and its rule is deterministic; UNKNOWN where the mechanism is a runtime decision.

This edge is the reason Orbit exists. It is the only mechanical way to see the governance surface.

**Cannot conclude:** that what loads *should* load, that it was consumed, or that it influenced anything.

**Amended after the prototype (§17).** The load ledger is **not reducible to edges.** A `loads` edge requires an in-repo file at the *from* end, and the most important loads have none: a root instruction surface, a skill description and an agent description are loaded by the client, not by anything in the repository. Modelled as edges alone they vanish. So the ledger (§10) is a first-class output, not a rendering of the graph, and §9's `zero-recognized-inbound-pointers` must be read against it — see the two buckets below.

### 7.4 `invokes`

File → File | ExternalRef. A pointer a known mechanism will **execute** — a hook command, a script called by another script, a generator entry point named in config.

Class: OBSERVED when the command string resolves to a file in the tree; `ExternalRef` with sub-kind `unresolvable-scheme` when it resolves to a system binary or a PATH lookup.

**Blind spot, stated:** dynamically constructed commands, anything behind a shell variable, and anything invoked by a process Orbit did not read. Reported as a coverage gap on that file.

### 7.5 `produces`

File → File. A generator wrote an artifact.

Evidence ladder, and the class follows the rung:
- Artifact header names its producer → **DECLARED** (the artifact says so).
- Config or manifest declares input → output → **DECLARED**.
- A generator script contains a literal write path → **INFERRED** (Orbit read a string; it did not watch a write).
- Observed by running the generator → **OBSERVED**, and only available if Orbit is explicitly asked to run it, which it is not by default (I6).

**Cannot conclude:** that the artifact is current, that the generator is the only producer, or that regenerating is safe.

### 7.6 `identical-bytes`

File ↔ File, hash equality. Pure observation, zero interpretation. Class: OBSERVED.

**Cannot conclude:** duplication in the sense that matters. Two identical files may be a deliberate vendored copy, a build output, or an accident. Orbit reports the hash match and the two paths. The word "duplicate" does not appear in output.

### 7.7 Relationships deliberately not modelled as edges

- `tests` — expressed as a query: *files carrying role `test` that `reference` this file*. Making it an edge would assert a semantic relationship the evidence doesn't carry.
- `consumes` — the inverse traversal of `references`/`loads`. A direction, not a kind.
- `configures` — `references` with subtype `config-value`.
- `imports` — `references` with subtype `import-statement`.
- `declares supersession` — `references` with subtype `supersedes-claim`, class **DECLARED**, permanently. A superseded file that is still loaded is reported as exactly that pair of facts, never as an error.
- `owns`, `canonical`, `production`, `obsolete`, `should merge` — decisions. Orbit has no vocabulary for them.

---

## 8. Evidence and certainty model

Every node, role and edge carries one evidence record:

```
evidence:
  class:     OBSERVED | DECLARED | INFERRED | UNKNOWN
  source:    filesystem | git | config | hook-definition | frontmatter
             | file-content | file-header | hash | prose | runtime
  locator:   "<repo-relative path>:<line>"  or  "git <exact command run>"
  detector:  "<detector-name>@<version>"
```

Definitions, applied strictly:

- **OBSERVED** — the result of a mechanical read that does not depend on interpretation. The file exists. Git reports this sha. These two hashes match. This settings file contains this hook entry at this line.
- **DECLARED** — a claim made *by repository content*. Recorded with who said it and where. Never independently true because it is written confidently.
- **INFERRED** — produced by an Orbit heuristic. The heuristic is named in `detector` so you can disagree with it specifically.
- **UNKNOWN** — Orbit knows the question and knows it cannot answer it mechanically. This is a first-class result, not a gap in the report.

**Promotion is a defect.** If a later detector confirms a DECLARED claim by observation, the result is two records — the declaration and the observation — not one upgraded record. This is what keeps Orbit auditable after it has been running for a year.

---

## 9. The three negative findings, and forbidden vocabulary

These three must never be collapsed. Each is a statement about **Orbit's detectors and boundary**, not about the file.

| Finding | Means exactly | Does not mean |
|---|---|---|
| `no-indexed-target-match` | A pointer parsed cleanly; no file at that address inside the indexed roots. | The target does not exist. It may be on another branch, outside the roots, generated at runtime, or the pointer may be prose. |
| `outside-indexed-roots` | The pointer resolves to a real path Orbit was not asked to index. | Anything is wrong. This is usually correct and expected. |
| `zero-recognized-inbound-pointers` | No edge produced by Orbit's current detector set points at this file. | The file is unused, orphaned, or valueless. Orbit's detectors are incomplete by construction. |

`zero-recognized-inbound-pointers` splits into **two buckets**, and reporting them as one is a defect:

- **zero pointers, and no ledger row** — nothing Orbit recognises points at it *and* no mechanism loads it.
- **zero pointers, but auto-loaded** — nothing points at it because nothing needs to: the client loads it. In the prototype run this was every `CLAUDE.md`, every `SKILL.md`, every agent definition and `settings.json` — 5 of the 8 files in the single bucket. Merging them would have flagged the estate's entire governance surface as pointerless.

### Output vocabulary is constrained, and the constraint is tested

The following words must not appear in Orbit's generated output: **broken, dangling, orphaned, obsolete, stale, dead, unused, duplicate, redundant, misplaced, wrong, should, safe to delete.**

This is enforced by a test over Orbit's own output (§15), and the test runs over **Orbit-authored fields only** — never over node addresses, file paths, locators or `verbatim_quote`. Those carry text the estate wrote. The prototype's lint fired on the node address `ext:no-indexed-target-match:repo-one/orphan-note.md`: a forbidden word, echoed from a filename, in a data field. Linting echoed data would force Orbit to launder the estate's own vocabulary, which is the opposite of the rule's purpose. It is a cheap, mechanical guarantee against the exact failure the whole design is built to avoid: the map quietly becoming a judge. Words a user types are their own business; words Orbit emits are the spec's business.

---

## 10. The load ledger — automatic and conditional context

Orbit maintains a **mechanism registry**: every known way repository-authored text can enter a session. For each mechanism instance found in the estate, Orbit emits a ledger row.

### Ledger row

| Field | Meaning |
|---|---|
| `mechanism` | Registry id |
| `source` | The file supplying the text |
| `activation` | `boot` \| `repo-entry` \| `path-scoped` \| `explicit-invocation` \| `event` \| `agent-scoped` \| `retrieval` \| `runtime` |
| `trigger` | The literal condition, quoted verbatim from config with a locator |
| `scope` | Which paths or sessions it applies to |
| `inheritance` | Does a nested instance **add to** or **replace** its parent? |
| `bytes` | Measured payload, OBSERVED |
| `est_tokens` | `bytes / 4`, class **INFERRED**, heuristic named |
| `lifetime` | How long it persists once loaded |
| `revocable` | Whether any mechanism exists to stop its influence before the session ends |
| `consumer_evidence` | Any mechanical evidence that something consumed it |

### Registry (initial)

| Mechanism | Activation | Payload known? | Revocable? |
|---|---|---|---|
| Root instruction surface (`CLAUDE.md`, `AGENTS.md`) | repo-entry, automatic | Yes | No |
| Nested instruction surface in a subdirectory | path-scoped, automatic on touching that path | Yes | No |
| User-global instruction surface (`~/.claude/CLAUDE.md`) | boot, automatic | Yes, **but outside indexed roots** | No |
| Skill *descriptions* (name + description of every installed skill) | boot, automatic | Yes — **and this is the cost of having skills at all** | No |
| Skill *body* (`SKILL.md` contents + bundled files) | explicit-invocation | Yes | No |
| Agent *description* | boot, automatic | Yes | No |
| Agent *body* | agent-scoped, on spawn | Yes | **Yes — see below** |
| Slash command body | explicit-invocation | Yes | No |
| `SessionStart` hook output | boot, automatic | **UNKNOWN** — output is produced at runtime | No |
| `UserPromptSubmit` hook output | event, automatic per turn | **UNKNOWN** | No |
| `PreToolUse` / `PostToolUse` hook output | event | **UNKNOWN** | No |
| MCP server instructions | boot, automatic | **UNKNOWN**, and **outside the estate entirely** | No |
| Files read during the session | retrieval / task-selected | Yes, per read | No |

### The finding that shapes the whole operating system

**`revocable` is `No` for almost everything.** Once bytes are in a context window they stay for the life of that window. There is no unload.

Class: OBSERVED, source: mechanism definition.

Two consequences follow mechanically, and they belong in the spec because they constrain plane 3 and 4 design rather than expressing a preference:

1. **Progressive disclosure can only be achieved by not loading.** Any design that plans to "unload the workflow rules afterwards" is building on something that does not exist.
2. **The one real revocation boundary is a bounded sub-session.** An agent or subagent context ends, and everything in it ends with it. That makes "run this workflow in its own bounded context" the only mechanism that genuinely scopes governance in time rather than merely in intent.

Orbit reports these. It does not act on them.

### What Orbit must not infer here

That automatically loaded material deserves to be loaded. A 40 KB always-on instruction surface with no `consumer_evidence` is reported as *40 KB, always-on, no recognized consumer*. Whether that is waste or load-bearing is not Orbit's call — a rule can be doing its job precisely by preventing something from ever appearing in a diff.

---

## 11. Query surface

Twelve commands. Each answers one of the questions the estate must be able to ask.

| Command | Answers |
|---|---|
| `orbit estate` | What repositories and worktrees exist right now, and what is their git state? |
| `orbit orient [--budget N]` | Compact orientation: counts, roots, boundary, coverage gaps. Fits a stated token budget. |
| `orbit boot [--from PATH]` | What loads automatically before a task is known, and at what measured cost? |
| `orbit would-load <selector>` | If this workflow / event / path were selected, what *would* load? **Describes; does not load.** |
| `orbit inbound <path>` | What points at this? |
| `orbit outbound <path>` | What does this point at? |
| `orbit trace <path>` | What produces, consumes or tests this artifact? |
| `orbit links` | How do the repositories reference one another? |
| `orbit unmatched` | Pointers with no indexed target match. |
| `orbit outside` | References resolving outside the indexed roots. |
| `orbit unpointed` | Files with zero recognized inbound pointers. |
| `orbit cold-start` | **The falsifier.** How many bytes must a fresh session load before it can start one real task? See §11a. |
| `orbit blindspots` | What cannot presently be known mechanically, and why. |

Cross-cutting flags: `--json` (default for machine use), `--class OBSERVED|DECLARED|INFERRED|UNKNOWN` (filter, never collapse), `--budget N`, `--no-cache`, `--roots PATH...`.

`orbit would-load` is deliberately named for what it does. It never checks out, never runs a hook, never reads a skill body it is only measuring. Naming it `activate` would have been an invitation to violate I6.

---

## 11a. The falsifier: cold-start burden

`orbit cold-start [--from PATH]`

One number and its itemisation: **the total bytes a fresh session must load before it can begin one real estimating task**, summing every mechanism in the §10 registry that fires at or before repository entry.

That number is the falsifier for the entire operating system, and the discipline it enforces is: **count, cut, count again.** It is the only figure Orbit produces that is meant to be tracked over time, and the only one whose direction has a right answer.

Rules that keep it honest:

- It counts bytes **actually loaded**, class OBSERVED. Not an estimate of what ought to load.
- Runtime-payload mechanisms — hooks, MCP server instructions — appear as a named **UNKNOWN line, never as zero**. Otherwise the number improves by becoming less observable, which is the worst possible failure for a falsifier.
- It is reported per entry point, because entering repo A costs differently from repo B.
- Orbit contributes zero to it, by I9.
- It is printed to stdout and not written anywhere, by I10. Tracking it over time is a human act — one line in whatever durable record you already keep.

A design change that reduces this number while moving the same governance behind explicit activation is a win. A design change that reduces it by deleting a rule that was doing work is a loss, and **Orbit cannot tell the difference**. That judgment is §20's, permanently.

---

## 12. Output contract, and the structural guard against becoming a second copy

Every record is JSON with a stable shape: `{ id, kind, attrs, evidence }` for nodes; `{ from, to, kind, subtype, evidence }` for edges. Every response carries a `boundary` block naming the indexed roots, the excluded paths, and the detector set version.

**The structural guard for I5:** the output schema has **no field capable of carrying prose extracted from a file**, with exactly one exception:

- `verbatim_quote` — permitted only on records of class DECLARED, capped at 200 characters, always accompanied by a `locator`, and always rendered with its source. It exists so a supersession claim or an ownership claim can be shown as *what someone wrote*, not paraphrased into a fact.

No summary field. No description field. No "purpose" field. If a consumer wants to know what a file says, the contract is: **Orbit gives you the path, you read the file.** This is what stops Orbit becoming a stale semantic mirror of the estate, and it is enforced by the schema rather than by good behaviour.

---

## 13. State, configuration, caching

- **No persistent graph.** Every command derives from live filesystem and git state.
- **Cache** is optional, content-addressed by file hash, stored under a single disposable directory, invalidated by hash mismatch, and bypassable with `--no-cache`. Deleting it must never change an answer, only the time to get it. If it ever does, that is a defect.
- **Configuration is one file**, `orbit.toml`, and it may contain only: indexed roots, excluded globs, detector toggles, and paths declared as project/job evidence. Anything else must be justified by evidence that live derivation cannot supply it.
- **Zero-config default:** given a starting path, index every git repository at or beneath it. Config exists to widen or narrow that, not to describe the estate.

Every added config key is a place the map can drift from the territory. The bar for adding one is high and stated here so a future session has to argue past it.

---

## 14. Boundary with retrieval, context assembly and execution

### What plane 3 (context assembly) may ask Orbit for

Assembly proceeds from **explicit selection**, never from inferred relevance:

| Selection | Orbit returns |
|---|---|
| Selected repository | Its root, git state, and its `orbit boot` ledger |
| Selected project/job | Paths declared as that job's evidence, and their sizes |
| Selected workflow | The workflow package path, and its `would-load` ledger with measured costs |
| Selected task | Nothing by itself — task-to-workflow mapping is a plane-3 decision |
| Applicable event or hook | The hook definitions matching that event, and their targets |
| Requested reasoning lens | Files carrying the matching role, as paths |

### The hard rule at this boundary

**The assembler loads the source file. It never loads an Orbit summary in place of the source.** Orbit hands over addresses and costs. The bytes that enter the session come from the file itself, at the moment of assembly, so they cannot be stale.

### Explicitly not designed here

An LLM-based relevance authority. Selection is explicit — a human, a workflow definition, or an event. If relevance ranking is ever wanted, it is a separate plane with its own spec, and it must sit *above* Orbit, never inside it.

---

## 15. Testing decisions

### One seam: fixture estate → JSON

A small synthetic estate is checked into the repository under `orbit/fixtures/`. It contains **real** git repositories (created by a setup script, committed as a tarball or built on demand), real settings files with real hooks, a real skill package, a real generated artifact with a real header, a real pointer that resolves nowhere, and a real file nobody points at.

Tests run the whole observer over a fixture and compare emitted JSON against a committed expectation. No mocks. No internal test doubles. Collectors, git reads, loader tracing and evidence tagging are all exercised through this one boundary, which leaves internals free to be restructured without rewriting tests.

The fixtures for the real build are **harvested from the audit** (§17 step 3) — real conditions found in the real estate, shrunk to minimum size — not invented in advance.

### Second, tiny seam: output vocabulary lint

A test that runs every command over every fixture and asserts none of the forbidden words in §9 appears in any output string. Cheap, and it makes I1 mechanically enforced rather than aspirational.

### Deliberately not tested

Per-collector unit tests, at least initially. They freeze internals at exactly the stage the internals are least settled.

---

## 16. Acceptance scenarios

The fixture estate must contain one of each. For each, the spec states where Orbit's claim stops.

**A. Session boot path from repository entry.**
`orbit boot --from fixtures/estate-a/repo-one` enumerates every automatic source with measured bytes: root instruction surface, one nested surface, skill descriptions, agent descriptions, one `SessionStart` hook.
*Claim stops at:* the hook's **output**. Orbit reports the hook exists, will fire at boot, and points at this script. Its payload is UNKNOWN, because it is produced at runtime.

**B. Explicitly invoked workflow.**
`orbit would-load skill:set-breakout` lists the skill body, its bundled reference files, and total measured bytes.
*Claim stops at:* whether that skill should govern anything. Orbit describes the package; it does not load it, rank it, or connect it to a task.

**C. Hook or event-triggered context.**
A `PreToolUse` hook in `.claude/settings.json`. Orbit reports: definition at `settings.json:14`, matcher quoted verbatim, target script resolved to a file, `invokes` edge recorded.
*Claim stops at:* what the script emits and whether it ever fires. Both UNKNOWN without running it.

**D. Generated artifact traced to producer and consumer.**
The fixture's `README.md` carries a `Generated by scripts/build-matrix.py` header and is referenced by two other files.
*Claim stops at:* the producer link is **DECLARED** — the artifact says so. Whether the script is the only producer, and whether the artifact is current, are both UNKNOWN. The two references are OBSERVED as references, not as consumption.

**E. Cross-repository relationship.**
`repo-one/docs/index.md` contains a relative link resolving into `repo-two`.
*Claim stops at:* a link is not a dependency, an import, or a coupling. Orbit reports one `references` edge with subtype `markdown-link`, crossing a repository boundary.

**F. Recognized pointer with no indexed match.**
A link to `../shared/policy.md` where nothing exists at that path.
*Claim stops at:* `no-indexed-target-match`. Orbit must not say broken. The target may live on an unchecked-out branch, outside the roots, or be generated at runtime — and Orbit reads none of those.

**G. File with zero recognized inbound pointers.**
A skill file nothing links to.
*Claim stops at:* `zero-recognized-inbound-pointers`, qualified by the detector set version that produced the zero. It is a statement about Orbit's detectors, not about the file's value. A file can be load-bearing precisely because it is auto-loaded rather than linked.

### Orientation budget check

`orbit orient --budget 2000` must produce a usable estate orientation inside that budget while every deeper query remains available on demand. If orientation cannot be compact, the model is too large and §5 needs to shrink, not the budget grow.

---

## 17. Implementation decisions

- **Runtime: Python 3, standard library only.** Orbit does four things — walk directories, run `git`, read text, emit JSON — all of which the stdlib covers. Zero dependencies means nothing to install, nothing to break, and a codebase small enough for its owner to read. Orbit's value is that it is trusted; unreadable code is untrusted code.
- Git is reached by `subprocess` with explicit argument lists, never a shell string, never a library that might fetch.
- Detectors are registered in one table with `name`, `version`, `evidence class`, and a pure function. Adding a detector must not require touching the graph or the CLI.
- Output is JSON to stdout; the human rendering is a separate formatter over the same records, so the two cannot diverge.
- Layout: `orbit/collectors/` (git, filesystem), `orbit/detectors/` (roles, references, loaders), `orbit/model.py` (nodes, edges, evidence), `orbit/queries/`, `orbit/cli.py`, `orbit/fixtures/`, `orbit/tests/`.

### How this spec gets tested against reality

1. Spec (this document) — written before seeing any estate repository.
2. **Prototype** — a throwaway observer on a `prototype/orbit-observer` branch, no tests, answering one question: *is this model small enough to build and rich enough to describe a real estate without deciding what anything means?*
3. **Audit** — run the prototype over the real estate. Its output is the diagnostic report, and simultaneously the falsification test of this spec.
4. **Build** — corrected spec, fixtures harvested from step 3, one seam.

If the prototype cannot describe the real estate using only §5–§10, this spec is wrong and gets amended before anything is built properly.

### Prototype result (step 2 complete)

Branch `prototype/orbit-observer`, not for merge. Driven over a synthetic two-repo estate covering all seven §16 scenarios, and over one real repository (190 files, 1,800 references, 0.24 s, Python 3 stdlib only, ~560 lines).

**Answer to the question: yes.** Three node kinds, six edge kinds and four certainty classes were sufficient to describe both estates, and no case appeared that required a new node kind, a new edge kind, or a semantic judgement. Roles-on-files absorbed every object the brief listed without a categorisation decision at index time.

Three corrections were required and are folded in above: the ledger is not reducible to edges (§7.3, §9); the vocabulary lint must be scoped to Orbit-authored fields (§9); reference-detector boundary handling is the dominant false-positive source and must carry its detector version (§7.2).

Two things the prototype did **not** settle, and step 3 must: whether the ~59 remaining negative findings are estate conditions or further detector gaps, and whether the cold-start number is meaningful on an estate that actually has one — the repository used carries no instruction surface, no skills and no hooks, so its cold-start burden measured **0 bytes with 0 unmeasurable mechanisms**. That is a true reading of an unusual repository, not a validation of the metric.

---

## 18. Out of scope

Refusals, recorded because they are the most useful lines here:

- **No relevance ranking**, LLM-based or heuristic. Explicit selection only.
- **No repository restructuring proposals.** Orbit produces the substrate for that decision and stops.
- **No persistent graph database.** Live derivation until evidence proves it too slow, and slow means measured, not felt.
- **No semantic summaries, embeddings, or extracted descriptions.** §12 makes this structural.
- **No writes of any kind** outside the disposable cache. Orbit never repairs, moves, renames, deletes or generates.
- **No fetching.** Orbit never touches the network, so it can never be slow, non-deterministic, or dependent on credentials.
- **No branch checkout or object-walking** to see other branches. Reported as a coverage gap instead.
- **No conflict resolution.** Two files claiming to be canonical is reported as two DECLARED claims.
- **No rule enforcement.** Orbit is not a linter and has no opinion about compliance.
- **No generated indexes or committed reports.** Orbit never writes a findings file, never regenerates an index, never "improves" an index convention that is working.
- **No auto-invocation.** Orbit is not wired into any hook, session start, instruction surface or skill description. If it ever becomes convenient to auto-run it, I9 has been broken.
- **No capability ownership assignment.** Candidate clusters, when they appear, are labelled candidate interpretations and given no owner or target repository.

---

## 19. Smallest next implementation slice

**`orbit estate` + `orbit boot`, over one fixture, emitting JSON with full evidence records.**

Rationale: these two answer the highest-value questions — *what exists right now* and *what loads before a task is known* — and together they force the evidence model, the boundary block, the git collector and the mechanism registry into existence. Every later command is a traversal over structures this slice has to build anyway.

Not in the slice: `trace`, `produces` detection, `identical-bytes`, the cache, the human formatter.

---

## 20. Decisions reserved for Dylan

1. **The indexed roots.** Which paths constitute the estate is a decision, not an observation. Orbit cannot choose its own boundary.
2. **Whether `~/.claude/` and other user-global surfaces are inside the boundary.** They load automatically and they sit outside every repository. Both answers are defensible; the choice changes what "the estate" means.
3. **Whether the audit runs before or after the prototype is cleaned up.**
4. **Which mechanisms belong in the registry beyond the initial list** — particularly any tool in use that this spec, written blind, does not know about.
5. **Whether project/job evidence paths are declared in `orbit.toml` or detected.** Declared is honest; detected is convenient.
6. **Whether Orbit ships inside an existing repository or gets its own.** Deliberately unanswered: this spec refuses to propose the target repository set.
7. **Whether the forbidden-vocabulary list in §9 is complete.** It is a judgement call about your own reading habits.
8. **Whether Orbit should be built at all**, if the hand-built indexes do show zero drift when checked. The cheapest honest test is the prototype: run it once against the real estate. If it agrees with the indexes and tells you nothing you did not already know, that is a real answer and the correct response is to stop.
9. **What "one real estimating task" means** for the cold-start count. The definition fixes the number, and it is a judgment call no tool can make.
10. **Whether a rule removed to lower the cold-start number was doing work.** Orbit measures the number; it cannot measure the loss.

---

## 20a. Kill conditions

Stated in advance, so abandoning Orbit is a planned outcome rather than an admission.

Delete Orbit if any of these hold after the audit:

- It agrees with the hand-built indexes and surfaces nothing they did not already show. (This is the claim in §1.1 turning out to be true, and it is a legitimate result, not a disappointment.)
- Its output starts being pasted into documents, or anyone asks it to write one.
- It acquires an always-on footprint of any size.
- The cold-start burden number goes up in the period Orbit exists.
- It needs a persistent graph, a config file longer than the roots list, or a second implementation to stay accurate.
- Someone reaches for it to decide something rather than to check something.

Any one of those means the tool has turned into the failure it was built to observe.

---

## 21. Mechanically unknowable — permanent UNKNOWNs

Reported by `orbit blindspots`, so their absence from a report is never mistaken for their absence from reality:

- What any hook actually emits, without running it.
- What an MCP server injects at boot.
- Content on any branch that is not checked out.
- Whether a loaded instruction influenced any output.
- Whether a reference inside prose was meant as a pointer or as an example.
- Whether two identical files are intentionally identical.
- Whether an artifact is current relative to its declared producer.
- Anything constructed at runtime: dynamic paths, computed commands, environment-dependent behaviour.
- True ahead/behind state without fetching.
- Whether a file with zero inbound pointers matters.
