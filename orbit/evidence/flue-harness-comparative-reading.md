# Flue harness comparative reading

**Reading date:** 2026-09-12
**Standing:** **ADMITTED AS COMPARATIVE EVIDENCE.** This is a reading of how a
different estate assembles a session's context. It authorizes no architecture,
no mechanism and no migration here, and nothing in Flue becomes a dependency of
this estate by having been read.

## Why this is filed at all

Flue is an agent harness: the layer that decides what text a model sees at the
start of a turn and what it can do during one. That is the same subject Orbit
Context observes, approached from the other end. Orbit derives a session's
context surface from files nobody arranged as a system; Flue states it in one
function, at build time, because it owns both ends.

So the comparison is not between two tools that do the same job. It is between
**a context surface that has to be discovered** and **a context surface that is
declared**, on the same underlying question: *what is actually loaded, and who
asked for it?*

That question is `client` (issue #12) and it is Gate A's Q1.

### What this reading does not license

Spec 0003 §10 excludes an agent-facing hot-context system — retrieval or
hydration that assembles context for an agent — on the ground that it is a
one-way door with respect to measurement: a mechanism that delivers context
changes the cold-start cost before the cost has been read.

**Flue is exactly such a mechanism.** Reading it is inside §10; building
anything shaped like it is outside, until the cold-start figure exists. The
findings below are therefore recorded as replay lenses and audit probes, in the
standing spec 0003 §4 gives the Sandcastle material, and not as a design input.

## Scope, identity and limitations

| Repository | Identity examined | Role |
|---|---|---|
| [`withastro/flue`](https://github.com/withastro/flue/tree/1ae1c85dae55e7b1215a6dc233796d36ec7d7c25) | `main` at `1ae1c85dae55e7b1215a6dc233796d36ec7d7c25`, shallow clone, working tree read | The harness read |

**What was read.** The runtime package's context-assembly and skill-mounting
path, at the files cited inline below. Every quotation is from that commit.

**What was not read.** The provider transport, the sandbox implementations, the
durability and compaction machinery, the twenty-four service integration
packages, and the published documentation site — the last because it is not
reachable from the session that made this reading. No Flue agent was built, run
or measured. **No figure in this file is a measurement**; the numeric limits
quoted are declared constants read out of source, not observed behaviour.

**Contamination.** An earlier reading of this repository's published summary was
present in the conversation before the source was read, and it reached a
conclusion — that Flue is a pure declaration model with no ambient discovery —
that the source contradicts (F2). The prior conclusion is recorded here as
having been corrected rather than quietly dropped, because the correction is
itself the most useful finding.

## Findings

### F1 — The composed context surface is one function with five inputs

`composeSystemPrompt`
([`context.ts:132`](https://github.com/withastro/flue/blob/1ae1c85dae55e7b1215a6dc233796d36ec7d7c25/packages/runtime/src/context.ts#L132))
assembles everything ambient a session begins with, and its own comment
enumerates the inputs: the agent's instructions, discovered workspace context,
the skill catalog, the task roster, and environment facts.

The comment also records a removal: *"Flue adds no behavioral stance of its own
(an autonomy preamble used to live here)"*
([`context.ts:128`](https://github.com/withastro/flue/blob/1ae1c85dae55e7b1215a6dc233796d36ec7d7c25/packages/runtime/src/context.ts#L128)).
A governance surface existed at this layer and was taken out, with the reason
kept beside the place it occupied.

**Comparison.** In this estate the same question — what is ambient at turn one —
is answerable only by indexing five repositories, and two-thirds of the surface
rows come back with no client attributable to them. That asymmetry is not a
defect finding about either estate. It is the difference between a surface
someone composed and a surface that accumulated.

**Disposition:** Independently corroborated principle — *the ambient surface is
worth being enumerable in one place.* The mechanism does not transfer; Flue owns
its own loader and this estate does not.

### F2 — Flue is a hybrid, and the discovery half is the half worth reading

The naive reading is that a declared harness has nothing to discover. The source
says otherwise. Two discovery paths run at session initialisation:

- `readAgentsMd`
  ([`context.ts:20`](https://github.com/withastro/flue/blob/1ae1c85dae55e7b1215a6dc233796d36ec7d7c25/packages/runtime/src/context.ts#L20))
  reads `AGENTS.md` **and** `CLAUDE.md` from the working directory and
  concatenates both.
- `discoverLocalSkills`
  ([`context.ts:54`](https://github.com/withastro/flue/blob/1ae1c85dae55e7b1215a6dc233796d36ec7d7c25/packages/runtime/src/context.ts#L54))
  walks a conventional skills directory and registers what it finds.

So a Flue session's catalog has **two provenances**: what the agent function
mounted, and what the workspace happened to contain. This is the same split this
estate has. What differs is that Flue keeps the two distinguishable at the type
level — a discovered skill carries a marker field that a mounted one does not —
so the question *who asked for this* is answerable by construction rather than
by derivation.

**Disposition:** Independently corroborated principle — *provenance of a loaded
surface is worth carrying on the surface itself.* This is `client` (issue #12),
and it is evidence that the column is answerable in an estate that decided to
answer it, not evidence that this estate's derivation of it will succeed.

### F3 — The two provenances carry different failure policies, and the rule is written down

A malformed discovered skill is skipped with a warning; a malformed mounted one
is a hard build-time failure. The stated reason
([`context.ts:49`](https://github.com/withastro/flue/blob/1ae1c85dae55e7b1215a6dc233796d36ec7d7c25/packages/runtime/src/context.ts#L49)):

> Discovered skills the user didn't opt into must not be able to brick the
> session: a malformed `SKILL.md` is skipped with a warning instead of failing
> `init()`. Explicitly imported/packaged skills stay strict — they are validated
> at build time where a hard error is actionable.

One artifact, two trust classes, keyed on **who opted in** and on **where a
failure is actionable**.

**Disposition:** Worth testing. The falsifier it needs before it is used here:
an episode in which a governance surface nobody opted into changed a session's
behaviour, and in which a skip-with-warning would have contained it. Episode 2's
mechanism — a pipeline that exits successfully after refusing at step five — is
adjacent but is not the same shape, because nothing there was skipped.

### F4 — Two enforcing boundaries that refuse at the point of use

Spec 0003 §7 sets the bar: a real enforcing boundary is one that refuses, at the
point of use. Flue has two, both throwing rather than reporting:

1. Mounting one skill name twice in a single render
   ([`use-skill.ts:44`](https://github.com/withastro/flue/blob/1ae1c85dae55e7b1215a6dc233796d36ec7d7c25/packages/runtime/src/hooks/use-skill.ts#L44)).
2. One name arriving from both provenances at once — *"Skill name X appears in
   both agent definition and workspace discovery"*
   ([`context.ts:111`](https://github.com/withastro/flue/blob/1ae1c85dae55e7b1215a6dc233796d36ec7d7c25/packages/runtime/src/context.ts#L111)).

The second is the interesting one. It is the collision this estate's 28
identical-byte pairs describe, caught at the moment the catalog is built rather
than reported afterwards by an observer.

**The negative control is available and cheap**, which is what makes this a
usable replay lens rather than an admired feature: remove either throw and the
later entry silently wins, because the catalog is a plain object keyed by name.

**Disposition:** Replay lens for Gate 3. A candidate arrangement that claims to
handle name collision is replayed against both these boundaries and against
their negative control.

### F5 — Progressive disclosure with a stated per-surface cost

`useSkill`'s contract
([`use-skill.ts:7`](https://github.com/withastro/flue/blob/1ae1c85dae55e7b1215a6dc233796d36ec7d7c25/packages/runtime/src/hooks/use-skill.ts#L7)):

> every mounted skill costs one always-present catalog line (name +
> description) in the system prompt, and the model pulls the full instructions
> on demand with the framework's `activate_skill` tool — the briefing arrives as
> the tool result, so the prompt prefix never changes. Supporting files stay
> lazy until explicitly read.

The budget is declared, not emergent: a name is at most 64 characters
([`skill-definition.ts:95`](https://github.com/withastro/flue/blob/1ae1c85dae55e7b1215a6dc233796d36ec7d7c25/packages/runtime/src/skill-definition.ts#L95))
and a description at most 1,024
([`skill-definition.ts:104`](https://github.com/withastro/flue/blob/1ae1c85dae55e7b1215a6dc233796d36ec7d7c25/packages/runtime/src/skill-definition.ts#L104)).
So the always-on cost of mounting a skill is bounded by construction, and the
body is never part of the prefix.

This is the always-on description separated from the on-demand body — the
condition the observer prototype's scenario 2 was built to detect. Flue treats
that separation as the unit it charges for.

**Disposition:** Independently corroborated principle — *the always-on cost of a
governance surface is worth being bounded and known per surface.* This is a
cold-start observation, and §10 puts acting on it behind the measurement.

### F6 — Skill bodies are re-read rather than retained

([`context.ts:42`](https://github.com/withastro/flue/blob/1ae1c85dae55e7b1215a6dc233796d36ec7d7c25/packages/runtime/src/context.ts#L42))
Bodies are deliberately not held in memory: activation re-reads the file, which
keeps relative references resolvable and picks up mid-session edits without
re-initialising.

**Comparison.** The condition this avoids is the one this estate measures as 28
identical-byte pairs: a body copied to a second location, after which the two
diverge and nothing says which was read.

**Disposition:** Worth testing. Its falsifier: an episode in which a session
acted on a body that had been superseded on disk. Episode 3 is close — four
readings of one unchanged body of measurements, with a router sending a reader
to the superseded one — but that is prose superseded in place, not a retained
copy, so it does not establish this.

### F7 — Where text goes is decided by how often it changes

The subagent roster is placed in the system prompt rather than in the tool
description, and the comment gives the reason
([`context.ts:162`](https://github.com/withastro/flue/blob/1ae1c85dae55e7b1215a6dc233796d36ec7d7c25/packages/runtime/src/context.ts#L162)):
the tool specification is kept fully static so that roster changes never touch
the serialized tools block, which providers cache as its own prefix segment.

Placement of governance text is a **cache decision**, taken on the text's change
frequency.

**Disposition:** Worth testing, and the most transferable item here — it is a
rule about arranging text that needs no Flue mechanism to apply. Its falsifier
is a measurement this estate has not taken: whether any of its ambient surfaces
change often enough for placement to cost anything.

## Dispositions, collected

| Finding | Disposition |
|---|---|
| F1 — ambient surface enumerable in one function | Independently corroborated principle |
| F2 — two provenances, distinguishable by construction | Independently corroborated principle |
| F3 — trust class follows who opted in | Worth testing |
| F4 — two boundaries that refuse at the point of use | **Replay lens for Gate 3**, negative control available |
| F5 — bounded always-on cost per surface | Independently corroborated principle |
| F6 — bodies re-read rather than retained | Worth testing |
| F7 — placement decided by change frequency | Worth testing |

No finding here is Flue-specific-and-irrelevant, which is itself worth noting
against the Sandcastle report's four irrelevant decisions: this reading was
scoped to the context-assembly path, so the parts of Flue that would have landed
in that column were not read.

## What this reading did not settle

- **Whether any of it survives contact with an episode.** Every corroborated
  principle above is corroborated against this estate's *recorded conditions*,
  not against a reconstruction. F3 and F6 name the falsifiers they still need.
- **Whether a declared harness is reachable from here at all.** Flue owns its
  loader, its runtime and its build step. This estate's surfaces are read by
  assistants it does not control, and nothing in this reading establishes that
  the declaration half is available without that ownership.
- **The cold-start figure.** F5 and F7 are both arguments about a cost this
  estate has not measured. Spec 0003 §1.1 wants it read before anything is built
  that would change it.
- **Whether Flue's own estate pays for these choices elsewhere.** A harness that
  refuses at the point of use fails builds that a lenient one completes. Nothing
  here counts that cost, and the repository's own history was not read.
