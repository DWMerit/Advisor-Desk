# Sandcastle ADR comparative archaeology

**Review date:** 2026-09-11  
**Verdict:** **READY WITH FOLLOW-UPS** — this is sufficiently grounded to use as an audit-hypothesis catalogue and as input to historical failure replay. It does **not** authorize an architecture, a migration, or adoption of any Sandcastle mechanism.

## Executive judgment

Sandcastle's ADRs corroborate a real subset of the failures visible in the Merit estate, but they do not supply the estate's target architecture.

The current Sandcastle `main` contains **20 ADR files representing 19 numbers**: there are two ADR-0005 files, no ADR-0013 file, and an ADR-0021 exists only on an unmerged issue branch. Of the 21 decisions reviewed here:

| Disposition | Count | Meaning |
|---|---:|---|
| Independently corroborated principle | 12 | The same underlying failure is visible in Merit Git evidence. Sandcastle's mechanism is not automatically the answer. |
| Sandcastle-specific decision | 2 | The decision follows from Sandcastle's packaging or runtime model; Merit evidence does not justify importing it. |
| Worth testing | 5 | The failure is plausible or adjacent, but the estate history examined here does not establish the proposed response. |
| Irrelevant to our architecture | 2 | The dependency or operating condition is absent from the current estate. |

The twelve corroborated decisions collapse into eight reusable audit families:

1. Re-read state and identity at the point of use.
2. Keep task, session, process, workspace, branch, artifact, and cleanup lifecycles separate.
3. State every dimension of isolation; never infer filesystem or branch isolation from session isolation.
4. Do not treat empty output, zero, silence, or exit code 0 as evidence of success.
5. Keep payload, template, and instruction boundaries explicit.
6. Put provenance and mutable state in the representation that owns them.
7. Test the enforcing mechanism, not the prose that says a guard exists.
8. Do not infer percentages or failure classes from signals the platform does not actually expose.

These are candidate **replay requirements**, not a new governance layer. Orbit should observe whether the relevant surfaces and relationships exist; Git and session evidence establish what happened; a replay test establishes whether a proposed boundary would contain it; estimating work decides whether the result is worth keeping.

## Scope, identity, and limitations

### Repositories examined

| Repository | Identity examined | Role in this review |
|---|---|---|
| [`mattpocock/sandcastle`](https://github.com/mattpocock/sandcastle/tree/e99f832f26dc9d245c019a9ddd19fa5dee792427) | `main` at `e99f832f26dc9d245c019a9ddd19fa5dee792427`, plus relevant remote branches | Source ADR corpus and implementation-status check |
| [`DWMerit/Home-system`](https://github.com/DWMerit/Home-system/tree/5e4256f9207674410f6f7f2046a6cb426c7495fb) | `main` at `5e4256f9207674410f6f7f2046a6cb426c7495fb`; 500 recent commits examined back to 2026-08-11 | Accepted product behavior and repairs |
| [`DWMerit/Estimating-Lab`](https://github.com/DWMerit/Estimating-Lab/tree/be90aa28856440e7854d2466b95a852751cf9810) | `main` at `be90aa28856440e7854d2466b95a852751cf9810`; 373 commits examined back to 2026-08-19 | Observations, experiments, and falsification discipline |
| [`DWMerit/agent-rules-books`](https://github.com/DWMerit/agent-rules-books/tree/782a8860064ff113324582e4af6437893c2f7f84) | `main` at `782a8860064ff113324582e4af6437893c2f7f84`; 302 commits examined back to 2026-04-16 | Work design, authority history, and governance failure episodes |
| [`DWMerit/Merit-knowledge`](https://github.com/DWMerit/Merit-knowledge/tree/f1c14a955a9e49c4dc2633319cae2fa2d3a59ab8) | `main` at `f1c14a955a9e49c4dc2633319cae2fa2d3a59ab8`; all 19 commits examined | Shared contracts, source/target discipline, and generated-state repairs |
| [`DWMerit/Advisor-Desk`](https://github.com/DWMerit/Advisor-Desk/tree/a7d7649044505b9c377c8dca28d2d6a543bc7f8c) | `main` at `a7d7649044505b9c377c8dca28d2d6a543bc7f8c`; all 50 commits examined | Inspected, but excluded as an active estate authority: its history ends in May and later Desk failures live in `agent-rules-books` |

The Sandcastle repository was cloned with its refs and inspected locally. Private Merit repositories were inspected through the connected GitHub account. That means this review can establish committed Git state and current default-branch content; it cannot see uncommitted files, reflog-only recovery, unpushed local commits, transient worktrees, or runtime behavior that was never recorded.

An earlier Sandcastle review was already present in the conversation context. This is therefore **not a blind review**. Prior conclusions were treated as contamination and used only as a completeness check after retained claims had been re-established from current Git objects.

No candidate change was executed. No runtime benchmark was run. The Git episodes below are evidence that failures occurred, not evidence that any proposed intervention works.

### Disposition rules

- **Independently corroborated principle:** a materially similar failure appears in Merit history. Only the principle transfers; implementation remains open.
- **Sandcastle-specific decision:** the decision depends on Sandcastle's container, template, or provider abstraction. It may illustrate a concern but is not an estate requirement.
- **Worth testing:** preserve as a hypothesis with a falsifier. Do not turn it into a rule until a replay or live experiment earns it.
- **Irrelevant to our architecture:** the operating condition is absent. Revisit only if the estate acquires that dependency.

## Finding 1 — the ADR directory is evidence, not authority

**Severity:** High for comparative archaeology.  
**Why it matters:** copying the ADR prose would import decisions that are unimplemented, stale, or not canonical even inside Sandcastle.

Four provenance defects were confirmed:

1. **ADR numbering is not a stable key.** `main` contains two ADR-0005 files and no ADR-0013. ADR-0014 refers to “ADR-0013's principle,” leaving a dangling decision reference.
2. **Written does not mean implemented.** [ADR-0007 was added to `main`](https://github.com/mattpocock/sandcastle/commit/ce476e1927c8d874f3986f0054682c8cf58b84bf), but the worktree-lock implementation at [`9891de2c`](https://github.com/mattpocock/sandcastle/commit/9891de2c8f1beab57b59392e8925db533f6a047d) remains outside `main` on `implement/worktree-locking`.
3. **Implemented behavior can supersede unamended prose.** ADR-0010 says structured-output recovery belongs outside Sandcastle, while current `main` implements same-session `output.maxRetries`, introduced at [`9f3f6d5c`](https://github.com/mattpocock/sandcastle/commit/9f3f6d5c5f2527d5e1d8349f80eec2d36e797540).
4. **Proposed is not canonical.** ADR-0021 exists on `agent/issue-850-fallback-when-the-implementation-agents-run-out-of`, not on `main`.

**Audit consequence:** every external decision record used in the recomposition program needs four separate fields: document identity, canonical-branch status, implementation evidence, and supersession/drift status. Orbit can help report these relationships; it cannot decide that a document has authority merely because it is named `ADR`.

**Acceptance condition for later tooling:** given an ADR, the observer can distinguish `canonical document`, `implemented on canonical branch`, `documented but unimplemented`, `behavior superseded`, and `candidate branch only` without collapsing them into a single “decision exists” state.

## Complete ADR inventory and comparison

The “agent failure” column describes the failure pattern inferred from the decision, not a claim that Sandcastle published a validated taxonomy. “Merit comparison” names committed evidence; it does not claim the corresponding repair held unless the history demonstrates that separately.

| ADR and Sandcastle status | Agent failure addressed | Merit comparison | Disposition | Repository audit probe |
|---|---|---|---|---|
| **0001 — Per-step timeouts.** Canonical and implemented; some API details have expanded beyond the prose. | A hook or provider phase hangs, while one coarse timeout cannot say which lifecycle stalled or preserve a typed diagnosis. | Adjacent evidence exists for operations becoming indistinguishable from hung, but this review found no controlled Merit episode establishing per-step timeouts as the missing intervention. | **Worth testing** | Can every long-running hook, capture, import, and provider call distinguish `slow`, `stuck`, `cancelled`, and `complete`? Does timeout preserve partial work and identify the exact phase? |
| **0002 — `cwd` option and prompt-file resolution.** Canonical and implemented. | A relative path is interpreted against ambient process state rather than the caller's declared working context. | Machine-specific work-order paths were repaired in [`e6a90adf`](https://github.com/DWMerit/agent-rules-books/commit/e6a90adf59c23350270e4af940d0d86cd3fc61ac); Lab sibling paths were made checkout-relative in [`08dd7b55`](https://github.com/DWMerit/Estimating-Lab/commit/08dd7b5535a99776a044b7ff9704c4b8c7a287f3). | **Independently corroborated principle** | For every durable path or locator, what root owns resolution? Would it still resolve on another machine, checkout, provider, or working directory? |
| **0003 — Reuse worktree by default.** Canonical and implemented, including safe fast-forward checks. | A rerun assumes a fresh workspace, creates duplicate state, or destroys dirty/unpushed work during preparation. | Seven worktrees contained one unique untracked tool about to be lost in [`70da3eb3`](https://github.com/DWMerit/Home-system/commit/70da3eb31e3647d0c2bd25b0f0537157cb433e8b). Current Home and Lab deliberately removed worktree-per-session machinery, so Sandcastle's reuse mechanism conflicts with the present local choice. | **Independently corroborated principle**; mechanism differs | Before reusing, replacing, or cleaning a workspace, can the system prove base/ref freshness, dirty state, untracked state, and unpushed reachability? Does it avoid treating “clean” as “safe”? |
| **0004 — AbortSignal on `run` and interactive operations.** Canonical and implemented. | Cancellation of an operation is conflated with destruction of the durable workspace/resource that may contain recoverable work. | The estate recorded that archiving a session is not permission to delete its workspace. A SessionEnd archive ran after the last commit and was swept to rescue in [`51ba99e0`](https://github.com/DWMerit/Estimating-Lab/commit/51ba99e0efc362306deab53babf54c20b0d10904). | **Independently corroborated principle** | Are operation cancellation, session close, workspace retirement, branch deletion, and artifact cleanup separately authorized and separately observable? |
| **0005a — Remove runtime `chown` UID alignment.** Canonical and implemented. | Container startup recursively mutates ownership, increasing latency, privilege, and failure surface. | The active estate reviewed here does not own a Docker/Podman sandbox image or a recursive UID-alignment lifecycle. | **Irrelevant to our architecture** | None until container ownership becomes an estate-owned runtime concern. |
| **0005b — Raw usage tokens, no percentage.** Canonical and implemented. | The agent fabricates a precise utilization percentage when the denominator or provider accounting is unavailable. | Home recorded a gauge pinned at 100% CRIT and under-reporting/observability gaps; the broader Lab pattern is that an unmeasured “cannot” or platform claim becomes inherited fact. | **Independently corroborated principle** | Does every percentage name a measured numerator, denominator, model, method, and date? If the denominator is unavailable, does the surface expose raw counts and uncertainty instead? |
| **0006 — Patch Git worktree mounts on Windows.** Canonical and implemented. | A worktree's `.git` pointer contains a host path that is meaningless inside the sandbox. | The estate has Windows/cloud path portability failures, but current Home and Lab instructions prohibit the worktree model this patch serves. | **Sandcastle-specific decision** | Retain only the portable root-ownership probe from ADR-0002. Do not add a worktree mount patch to an architecture that intentionally has no worktrees. |
| **0007 — Worktree locking.** Canonical document, **not implemented on canonical `main`**. | Two agents believe they own the same filesystem and Git `HEAD`; writes, branch movement, or amend operations collide. | Lab records 17 concurrent-session cases. [`077776de`](https://github.com/DWMerit/Estimating-Lab/commit/077776de9b6105d5f3298237a4678e0dac704cb4) documents an amend decided in one session landing on another session's commit because `HEAD` belonged to the folder, not the session. | **Independently corroborated principle**; Sandcastle implementation unproven | Can two sessions enter the same checkout or mutate the same ref? What mechanism actually refuses the second writer? Test the refusal; do not infer it from an ownership file or instruction. |
| **0008 — Inline prompts skip template processing.** Canonical and implemented. | Data supplied as payload is interpreted as template syntax and silently rewritten. | Lab recorded skill-body substitution corrupting `$<digits>` prices three times in one session; other observations distinguish descriptions and reload/context text from executable instruction. | **Independently corroborated principle** | For every user/job/transcript/vendor payload, can `$`, braces, code fences, paths, and imperative prose pass byte-for-byte unless the caller explicitly selects template interpretation? |
| **0009 — Templates share no code.** Canonical and implemented as a packaging rule. | Shared helpers couple templates that must remain independently copyable and modifiable. | Merit history points the other direction for generated or distributed governance: duplicate source/target copies repeatedly drifted. The boot source fell behind its generated layer three commits after repair in [`c83589f5`](https://github.com/DWMerit/Home-system/commit/c83589f59c755342908bd47b7d5d5c50b5b1d280). Shared contracts were extracted to stop repeated reconstruction. | **Sandcastle-specific decision**, with local counter-evidence | Classify each duplicate: independently authored product, generated target, cache, or accidental copy. If it is a target, require one named source and a behavioral parity check; if independently authored, prove that shared evolution is not required. |
| **0010 — Structured output.** Canonical and implemented; retry-ownership prose is stale. | “The agent stopped,” “the task completed,” and “a valid artifact was produced” are collapsed into one success state. Invalid or empty output can pass. | A 549-line pricing review printed 61 findings and exited 0 while pricing zero UPCs in [`5ffc8bfb`](https://github.com/DWMerit/Home-system/commit/5ffc8bfb778700de4e0a8af1138a84c1fcea5b4d). Advisor Desk repeatedly described the artifact rather than producing it; live acceptance that did not run was correctly recorded as blocked in [`8aa0b852`](https://github.com/DWMerit/agent-rules-books/commit/8aa0b8523b34a291fd4aeb809588c0bdabfbd475). | **Independently corroborated principle** | Does every producer report execution state, coverage, schema validity, and artifact existence separately? Can zero processed inputs, a parse error, or a missing deliverable ever return success? |
| **0011 — Resume is one iteration.** Canonical and implemented. | A “resume” call silently chains multiple agent iterations, obscuring which prompt, state transition, or failure belongs to which step. | The estate uses long sessions, compaction, and continuation, but this review found no stable cross-provider runner contract against which to call this a demonstrated failure. | **Worth testing** | In a workflow replay, define whether continuation resumes the original session once or consumes a remaining plan. Can each iteration be attributed and independently stopped? |
| **0012 — Provider-owned session storage.** Canonical and implemented; interface examples have drifted. | A generic orchestrator hardcodes one provider's private cache paths and mistakes that storage layout for a universal session model. | Claude, Codex, Cowork, local hooks, and transcript captures expose different evidence paths. Current history shows platform-specific capture failures, but not a validated common storage abstraction. | **Worth testing** | Build a capability inventory: which provider owns the session identifier, durable transcript/export, rewrite semantics, and retention? Can core workflow code consume capabilities without embedding provider paths? |
| **0014 — Docker UID alignment via build arg.** Canonical and implemented; it contains the dangling ADR-0013 reference. | Runtime ownership repair is replaced with image-build ownership alignment. | No estate-owned container image or UID-alignment layer is in the reviewed architecture. | **Irrelevant to our architecture** | None unless container image construction becomes a responsibility of the estate. Retain the dangling-reference lesson under Finding 1. |
| **0015 — `noSandbox` on run/create boundary.** Canonical and implemented. | Safety intent is represented by an extra wrapper flag that cannot enforce a different boundary, creating ceremonial or contradictory protection. | A ref-preservation rule existed only as prose and could not refuse deletion in [`61385432`](https://github.com/DWMerit/Home-system/commit/6138543242e54ebb76ca578269181130fd805a34). A G-09 checker proved mention rather than behavior in [`6a368a2d`](https://github.com/DWMerit/agent-rules-books/commit/6a368a2da916843526d84aa6e9daa079f67acc9f), then behavioral checks replaced presence checks in [`5001b49f`](https://github.com/DWMerit/agent-rules-books/commit/5001b49f8754fcb35cc4cc00ef068052be7c007f). | **Independently corroborated principle** | For every claimed guard, what exact boundary can refuse the action? Is safety delegated, duplicated, or merely described? Do negative controls show a forbidden action actually fails? |
| **0016 — Resume requires filesystem-backed sessions.** Canonical and implemented. | The orchestrator promises resume by depending on undocumented or ephemeral provider state it cannot address reliably. | A transcript written after the final commit became uncommitted rescue material in [`51ba99e0`](https://github.com/DWMerit/Estimating-Lab/commit/51ba99e0efc362306deab53babf54c20b0d10904); another session's transcript had to be landed before its container vanished in [`aaa74571`](https://github.com/DWMerit/Estimating-Lab/commit/aaa74571940001c9ba8310a69728c86c23b850f3). Those show durability risk, not that filesystem-only resume is the correct universal gate. | **Worth testing** | Per provider, can a session be durably addressed and resumed after process/container loss? If not, does the workflow decline the capability explicitly rather than simulating it from partial evidence? |
| **0017 — Sandbox-owned sync-base ref.** Canonical and implemented. | A host commit SHA is treated as stable identity after the sandbox re-authors or rewrites the same change; sync progress and provenance become false. | The estate records that merge methods rewrite SHAs, branch lists mislead, patch equivalence is not reachability, and a PR object's ref can be stale. Home fixed provenance that hashed working-copy bytes rather than the blob Git stored in [`3d27048f`](https://github.com/DWMerit/Home-system/commit/3d27048f4b5144faad7f2f729c13b45c0b2bc651). | **Independently corroborated principle** | For each comparison, is identity an exact commit, reachable ref, tree equality, patch equivalence, or rendered artifact? Is the state recorded in the namespace that owns the transformation? |
| **0018 — Fork is session-only.** Canonical and implemented. | A new model session is mistaken for a new filesystem, branch, tool state, or ownership boundary. | The amend collision in [`077776de`](https://github.com/DWMerit/Estimating-Lab/commit/077776de9b6105d5f3298237a4678e0dac704cb4) is exact counter-evidence: separate sessions shared one folder and one `HEAD`. A commit-reading detector also could not see the session that had not committed in [`a1819b86`](https://github.com/DWMerit/agent-rules-books/commit/a1819b86844759fe6848cbaf264293991d456dc1). | **Independently corroborated principle** | Every fork/fan-out contract must state separately whether context, provider session, process, filesystem, branch/ref, credentials, and tool state are shared. Which claimed boundary is tested? |
| **0019 — Completion timeout for hanging process.** Canonical and implemented. | A completion signal is observed, but the child process remains alive; an idle timeout cannot distinguish successful completion from post-completion hang. | The estate separately observed that `isRunning:false` is not “no process,” and SessionEnd capture can occur after the last project commit. The structured-output episode also shows that output existence is not task completion. | **Independently corroborated principle** | Does the workflow distinguish completion signal, process exit, artifact validation, landing, and cleanup? What happens when any earlier state is true and a later state never arrives? |
| **0020 — Prompt expansion fails fast.** Canonical and implemented. | Required prompt/template expansion fails and silently becomes empty, partial, or corrupted input; downstream output then looks plausible. | `$<digits>` substitution corrupted estimating prices; malformed keys silently dropped warnings; checks have exited 0 after processing nothing. | **Independently corroborated principle**, with local choice still open | For every required transformation, is the resulting byte stream validated before dispatch? Can missing files, empty expansion, or unresolved placeholders continue silently? Who owns retry versus refusal? |
| **0021 — No token-exhaustion fallback.** **Candidate branch only; not canonical.** | The orchestrator parses unstable stderr strings to infer token/quota exhaustion and automatically substitutes a fallback that may change semantics or hide the real failure. | Usage signals and context percentages have already proved unreliable, but this review found no committed incident where an automatic provider fallback caused estate damage. | **Worth testing** | Inventory every failure classifier. Is it backed by a stable structured signal? Replay quota/token/network/model-access failures and confirm they remain distinguishable; do not preregister a string match as truth. |

## Historical failure crosswalk

The ADR inventory becomes useful only after it is collapsed into estate failure episodes. The following are the strongest cross-repository matches.

### Episode A — ambient state was mistaken for current state

**Observed chain**

- A Lab session decided to amend, another session committed inside the decision window, and the amend changed the other session's commit: [`077776de`](https://github.com/DWMerit/Estimating-Lab/commit/077776de9b6105d5f3298237a4678e0dac704cb4).
- A generated boot target outran its source again only three commits after a repair: [`c83589f5`](https://github.com/DWMerit/Home-system/commit/c83589f59c755342908bd47b7d5d5c50b5b1d280).
- A shared contract was lifted from a stale point and had to be lifted again: [`638411f1`](https://github.com/DWMerit/Merit-knowledge/commit/638411f1a24fea4490254b6ce3bc79173070453d).
- A static Lab report described the working tree rather than the repository and was changed to derive state from tracked files: [`c2174f66`](https://github.com/DWMerit/Estimating-Lab/commit/c2174f66206b1fe2c2a8a4ec12e56827cbbd91f7).

**Sandcastle corroboration:** ADR-0002, 0003, 0007, and 0017.

**Responsibility under test:** context discovery and observation; workspace/ref ownership; generated-source provenance.

**Replay question:** an agent reads a branch, path, generated index, or source/target relation and pauses before acting. If another session changes it, what is re-read immediately before mutation, and what refuses or records the mismatch?

### Episode B — one lifecycle was allowed to impersonate another

**Observed chain**

- Tool confidence was confused with promotion and production adoption until the Lab separated the lifecycles.
- Six review verdicts existed only in conversation and then seeded five more drafts: [`b080c9ac`](https://github.com/DWMerit/agent-rules-books/commit/b080c9acafea1c1099ec898802b355ee93a5e244).
- A SessionEnd archive ran after the session's last commit, so “session closed” did not mean “evidence landed”: [`51ba99e0`](https://github.com/DWMerit/Estimating-Lab/commit/51ba99e0efc362306deab53babf54c20b0d10904).
- Desk machinery repeatedly described work products instead of producing them and was later deleted while its load-bearing decisions were retained: [`e7940598`](https://github.com/DWMerit/agent-rules-books/commit/e7940598b245c7bfb93f9c4ff9cc50f6e37a5efb), [`b60d20f8`](https://github.com/DWMerit/agent-rules-books/commit/b60d20f8679b35f945bc748a67a572fe613794e0).

**Sandcastle corroboration:** ADR-0004, 0010, 0011, 0018, and 0019.

**Responsibility under test:** session evidence and workflow capture; promotion/disposition; work design and authorization.

**Replay question:** a tool becomes PROVEN, an agent emits a completion marker, or a session closes. Which state changed? Which states did not? Can any transition accidentally authorize promotion, claim a delivered artifact, or permit workspace deletion?

### Episode C — empty, plausible, or mechanically passing output acquired success semantics

**Observed chain**

- A pricing review processed zero UPC prices, printed 61 findings, and exited 0: [`5ffc8bfb`](https://github.com/DWMerit/Home-system/commit/5ffc8bfb778700de4e0a8af1138a84c1fcea5b4d).
- G-09's checker proved that prose existed rather than that the guarded behavior worked: [`6a368a2d`](https://github.com/DWMerit/agent-rules-books/commit/6a368a2da916843526d84aa6e9daa079f67acc9f).
- Three checks were replaced with behavioral tests, including a negative control: [`5001b49f`](https://github.com/DWMerit/agent-rules-books/commit/5001b49f8754fcb35cc4cc00ef068052be7c007f).
- A count used to clear a rewrite could not fail and the ratio was never recalculated: [`020383de`](https://github.com/DWMerit/Estimating-Lab/commit/020383dee21f9140939d559231177d6ebed32f82).
- Merit-knowledge replaced “empty output means success” prose with an explicit positive success statement: [`77d812f3`](https://github.com/DWMerit/Merit-knowledge/commit/77d812f3cac6e46162eaadb530c7c80304775a07).

**Sandcastle corroboration:** ADR-0010, 0019, and 0020.

**Responsibility under test:** tool implementation; workflow execution; acceptance.

**Replay question:** a producer processes no inputs, cannot parse the source, or returns prose instead of the requested artifact. What explicit coverage and artifact contract prevents `exit 0`, silence, or a plausible narrative from counting as success?

### Episode D — the represented boundary was broader than the real boundary

**Observed chain**

- Separate sessions shared a worktree and `HEAD`: [`077776de`](https://github.com/DWMerit/Estimating-Lab/commit/077776de9b6105d5f3298237a4678e0dac704cb4).
- A detector that observed commits could not see an active session that had not committed: [`a1819b86`](https://github.com/DWMerit/agent-rules-books/commit/a1819b86844759fe6848cbaf264293991d456dc1).
- A local prose rule could not refuse a destructive ref operation: [`61385432`](https://github.com/DWMerit/Home-system/commit/6138543242e54ebb76ca578269181130fd805a34).
- Seven skills fired at apparent low and recorded nothing, leaving execution and observability disconnected: [`571a3886`](https://github.com/DWMerit/Home-system/commit/571a38868ba25eb613c97d08f1829ef122016a3c).

**Sandcastle corroboration:** ADR-0007, 0015, and 0018.

**Responsibility under test:** workflow execution; context observation; enforcement.

**Replay question:** a system claims isolation, protection, or execution. What exact resource is isolated, what layer can refuse the action, and what independent evidence shows the mechanism ran?

### Episode E — representation ownership and copied state drifted apart

**Observed chain**

- Home stamped working-copy bytes instead of the blob Git actually stored: [`3d27048f`](https://github.com/DWMerit/Home-system/commit/3d27048f4b5144faad7f2f729c13b45c0b2bc651).
- A stored knowledge map was a snapshot and its checker could not see the target paths: [`d8d85cba`](https://github.com/DWMerit/Merit-knowledge/commit/d8d85cba93c49de01facdaf218f542fa7b5cfcd0).
- Boot source/target copies drifted almost immediately after repair: [`c83589f5`](https://github.com/DWMerit/Home-system/commit/c83589f59c755342908bd47b7d5d5c50b5b1d280).
- An experiment's independent variable was not frozen until a digest was added: [`f9c0bfce`](https://github.com/DWMerit/Estimating-Lab/commit/f9c0bfce077f7ff6ea880b5dd36ef01954bca83d).

**Sandcastle corroboration or contrast:** ADR-0009, 0012, 0016, and 0017.

**Responsibility under test:** accepted knowledge; experiment evidence; session capture; context discovery.

**Replay question:** a file is copied, generated, cached, rendered, imported, or re-authored. Which representation owns truth? Which relations are provenance rather than authority? Can a stale target or provider-private cache become canonical by being easier to read?

### Episode F — payload or observation text acquired powers it did not have

**Observed chain**

- Lab observations accumulated authority despite being evidence that a problem occurred, not evidence that a repair worked.
- Skill-body substitution interpreted `$<digits>` as syntax and corrupted prices.
- Imported vocabulary changed local meaning; current Orbit work has already shown why identical names cannot be assumed to carry identical semantics.
- Current `agent-rules-books` deliberately says that `DECISIONS`, `OPEN-WORK`, projects, and stored rule sets are history or product text unless a separate activation path gives them authority.

**Sandcastle corroboration:** ADR-0008 and 0020. ADR-0009 is a packaging contrast, not a transferable answer.

**Responsibility under test:** experimental findings; accepted knowledge; context loading; instruction activation.

**Replay question:** an odd observation, external ADR, imported term, transcript, or user-supplied job string enters the estate. Can any loader, template processor, or naming collision turn it into instruction or accepted truth without a distinct human-authorized transition?

## Audit catalogue for the repositories

This is the actionable output of the review. Each item is a question to ask of frozen historical states and candidate recompositions. A `PASS` requires evidence from the named boundary; prose presence alone is insufficient.

| ID | Decision to audit against | Primary repositories/responsibilities | Evidence required for `PASS` | Replay seed |
|---|---|---|---|---|
| **SC-A01** | **Point-of-use state:** mutable branch, path, source/target, provider, and generated-state claims are re-read immediately before an action that depends on them. | Orbit/context observation; workflow execution; all repos | A negative-control replay where state changes after initial discovery is detected or refused before mutation. | The cross-session `--amend`; stale LEDGER lift; boot source/target drift. |
| **SC-A02** | **Declared path roots:** durable locators declare an owning root and survive another machine, checkout, provider, and working directory. | Work design; session evidence; Merit-knowledge contracts | Resolution tests from at least two roots/machines; no durable absolute workstation path as identity. | Machine-addressed work order; Lab sibling-path repair. |
| **SC-A03** | **Isolation vector:** context, provider session, process, filesystem, branch/ref, credentials, and tool state are each marked shared or isolated. | Workflow repo candidate; session capture; Home/Lab execution | A two-session collision test; observed refusal or containment at the actual shared resource. | Two sessions sharing one `HEAD`; commit-only detector missing uncommitted work. |
| **SC-A04** | **Lifecycle separation:** tool confidence, adoption, task completion, artifact production, landing, session close, workspace retirement, and cleanup cannot authorize one another implicitly. | Lab; Home; work design/authorization; workflow capture | State transitions are independently observable; replay of one transition leaves all others unchanged unless an explicit authorized transition runs. | PROVEN versus promotion; SessionEnd after last commit; Desk describing rather than producing. |
| **SC-A05** | **Explicit successful nothing:** zero, empty, silence, and no-diff each have named semantics and cannot masquerade as processed/accepted/completed. | Tool implementation; estimating workflows; checks | Positive outcome text plus coverage counts and nonzero refusal for required-but-unprocessed input; negative controls. | 61 findings with zero prices; empty-output success; no-fail count. |
| **SC-A06** | **Artifact contract:** execution status, source coverage, schema validity, artifact existence, and landing/reachability are separate fields. | Summary-pricing review; workflow execution; session evidence | Remove or corrupt each component in turn; the result identifies the missing component and never reports global success. | Parse failure stamped `is_error:false`; blocked live acceptance; chat-only verdicts. |
| **SC-A07** | **Payload boundary:** data is literal by default; template or instruction interpretation is selected explicitly and validates its result before dispatch. | Estimating inputs; skills; transcript ingestion; imported ADR/Orbit material | Round-trip adversarial payloads containing `$0.0114`, braces, fences, paths, and imperative sentences byte-for-byte. | Price substitution; observations acquiring authority; description interpreted as instruction. |
| **SC-A08** | **Real enforcement:** every safety claim names the layer that can refuse the action and includes a failing negative control. | Git protections; hooks; checkers; workflow permissions | Demonstration that the forbidden operation fails at the claimed boundary; a presence-only checker must fail review. | Ref-preservation prose; G-09 presence check; hook disabled in worktrees. |
| **SC-A09** | **Representation ownership:** source, generated target, cache, copy, provider-private state, and transformed artifact are distinct roles with one stated owner and provenance edge. | Merit-knowledge; Home boot/context surfaces; session storage | Modify source and target independently; drift is either allowed by declared independence or detected without declaring either side authoritative by convenience. | Stored knowledge-map snapshot; boot drift; provider session files. |
| **SC-A10** | **Git identity semantics:** exact SHA, reachability, tree equality, patch equivalence, PR ref, and rendered bytes are not interchangeable. | Work design/landing; provenance; Orbit Git model | Tests for merge/rebase/re-authored changes state which relation is being proven. | Blob-versus-working-copy stamp; stale PR ref; rewritten merge SHA. |
| **SC-A11** | **Signal honesty:** percentages and classified provider failures exist only when their numerator, denominator, or structured error signal exists. | Usage/cost observation; provider adapters | Missing-denominator and changed-error-message tests produce `unknown`, not a fabricated percentage or confident class. | Pinned 100% gauge; candidate token-exhaustion fallback. |
| **SC-A12** | **Capability-gated resume:** resume/capture promises are made per provider only when durable, addressable evidence survives process/container loss. | Workflow execution; session evidence repository candidate | Kill process/container, then demonstrate addressable resume or an explicit unsupported result without partial reconstruction being called resume. | Transcript after final commit; transcript landed before container vanished. |
| **SC-A13** | **Bounded timeout phases:** timeouts identify the stalled phase and do not convert cancellation into cleanup authority. | Workflow execution; provider adapters | Inject hangs separately into hook, agent, artifact validation, and post-completion exit; each yields a distinct state and preserves recoverable work. | Worth-testing synthesis of ADR-0001, 0004, and 0019. |
| **SC-A14** | **External-decision provenance:** an ADR, observation, or named framework records document status, implementation status, local semantic mapping, and adoption status separately. | Orbit/context graph; Lab; accepted knowledge | The observer reports Sandcastle ADR-0007 as documented/unimplemented and ADR-0010 as prose/behavior drift without calling either a local rule. | Sandcastle's own ADR provenance defects; Orbit vocabulary drift. |

## How this feeds the three-benchmark program

### Gate 0 — Orbit golden benchmark

Use the current calibrated estate to prove that Orbit reports files, relationships, exact bytes, unresolved references, and historical-state differences correctly. SC-A14 is the direct Sandcastle-derived golden case: duplicate ADR numbers, a dangling ADR reference, a documented-but-unmerged implementation, and stale prose beside changed behavior.

Orbit passes only if it reports those facts without deciding that the ADR is authoritative, that the code is correct, or that Merit should adopt it.

### Benchmark 1 — historical failure replay

For each selected failure episode, freeze:

- the pre-change commit;
- the prompting session/observation evidence;
- the files, pointers, roles, authority surfaces, and graph edges added;
- the first consumers of those additions;
- secondary failures and repairs;
- product/estimating effect, if any;
- what survived, with evidence of a reader or product dependency.

Then replay the episode against a candidate responsibility boundary using the relevant SC-A items. A pass means the proposed design prevents, contains, or makes the failure explicitly diagnosable with fewer surfaces and no new implicit authority. A replay that merely adds a checker, registry, pointer, or state field has not passed until a real consumer and negative control are shown.

Recommended first replay set:

1. **Lab observation becomes accepted truth** — SC-A04, A07, A14.
2. **Cross-session amend in a shared checkout** — SC-A01, A03, A08.
3. **Pricing review reports findings after pricing nothing** — SC-A05, A06.
4. **Generated boot/source layer drifts again** — SC-A01, A09.
5. **Tool reaches PROVEN and is mistaken for promoted/adopted** — SC-A04, A06.
6. **Convenience index becomes authority and maintenance work** — SC-A01, A09, A14.
7. **Imported Orbit term changes local meaning** — SC-A07, A14.
8. **Session closes before evidence is landed** — SC-A04, A06, A12.

### Benchmark 2 — estimating-work benchmark

Sandcastle provides no evidence for this gate. The recomposed design must be tested on real estimating work and compared on at least:

- time to a usable estimating decision;
- source coverage and plausible-wrong-result rate;
- human clarification/repair turns;
- context loaded and reconstruction cost;
- number of non-product files or maintenance obligations created;
- durability and later retrievability of accepted decisions;
- whether the estimator can tell what requires judgment without reading governance machinery.

A design that passes Orbit and failure replay but does not improve estimating work has failed the program.

## Failure-episode ledger fields

The Sandcastle audit should be attached to, not substituted for, the failure-episode ledger. A minimal episode record needs:

| Field | Purpose |
|---|---|
| Episode ID and concise failure claim | Stable address without importing external vocabulary as local meaning |
| Pre-state commit(s) | What existed before the change |
| Prompting evidence | Session, observation, error, or user decision that caused the change |
| Changed files and graph edges | What new surface or relationship appeared |
| Writer, reader, and enforcing boundary | Who created it, who consumed it, and whether anything could refuse behavior |
| Authority and activation path | Descriptive, experimental, accepted, executable, or generated; how it changed state |
| Lifecycle and supersession | How it was accepted, replaced, retired, or left stale |
| Secondary failures | Maintenance, drift, contradiction, duplicate work, or optimization churn caused later |
| Repair attempted | The actual intervention, separate from the failure observation |
| Held or failed | Git/session evidence that the repair survived; `unknown` if not measured |
| Estimating effect | Concrete decision, saved time, coverage, reliability, or `none observed` |
| Sandcastle cross-reference | Corroborated principle, specific contrast, or test hypothesis; never automatic authority |
| Replay and falsifier | Scenario a candidate recomposition must survive and evidence that would disprove the proposed boundary |

This preserves the program's central separation: **Orbit supplies observations; Git supplies history; failure episodes supply requirements; estimating work supplies the final test.**

## Recommended next action

Do not create a Sandcastle-derived ruleset. Freeze this catalogue as a source document for the archaeology program, then instantiate the first eight failure episodes above against selected historical commits. Each episode should begin descriptive and end with a replay requirement; architecture proposals should wait until repeated episodes reveal a smaller responsibility boundary.

The first high-value episode is the cross-session amend because it is unusually complete: precondition, exact race, destroyed history, recovery cost, rejected alternative guards, attempted repair, and a later architectural change away from worktrees are all recorded. The first product-facing episode should run in parallel conceptually—not as another agent session—with the pricing review that exited 0 after pricing nothing, because it tests whether the redesign improves estimating reliability rather than merely Git hygiene.

