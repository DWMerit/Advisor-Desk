# 14 — Three states, and ticket 07 re-scoped

**Blocked by:** 13
**Demo when done:** the three-state table, and ticket 07 rewritten so it can be
run.

## Do

**First, attach agent-rules-books and establish whether C2 rewrote its base.**
C1 did not — outside `orbit/`, `main..HEAD` is two lines of `.gitignore`, so
`C1 − C0` measures what a session *added*. Whether the same holds for C2 is not
known. If C2 rewrote its base, the two deltas are not the same kind of
measurement, and the report says so rather than tabling them side by side.

**The fourteen `full.md` symlinks are a cheap first test of exactly that.** C0
carries them as symlinks (`10f71b9`, git mode `120000`, authored upstream on
2026-04-26 and never touched since), so C2 inherited them. Ticket 15 makes a
symlink a node with its own size, which means the question can be asked of the
rows rather than by hand: if C2 holds fourteen 32-byte links, its base is intact
in this respect; if it holds fourteen full-sized regular files, something
resolved them, and a copy that no longer tracks its source is a base rewrite
whatever else the diff says. Either answer is a result. Report it before any
delta is read as comparable, and report which of the two it is rather than only
that they differ.

Then produce the comparison:

| state | what it is |
|---|---|
| **C0** | Advisor-Desk `main` @ `a7d7649` — untouched upstream |
| **C1** | Advisor-Desk branch head — built a tool, corpus untouched |
| **C2** | agent-rules-books — grew its own governance layer, stopped producing |

**agent-rules-books is read-only.** Index it. Never write to it, never push to
it, never open a pull request against it.

**Ticket 13's dedupe applies to all three states, and C2 is where it can bite.**
Two names for one file count once, labelled by the target — GitLab's rule at
`crates/orbit-local/src/commands/setup.rs:265-271`. A repository that grew its own
governance layer is exactly the shape that acquires a `CLAUDE.md` symlinked to an
`AGENTS.md`, or a rule file exposed under two names, and counting those twice
would report governance growth that is one file wearing two hats. Report the
number folded per state beside the counts, never inside them.

**One question is asked here, not built.** The collapse in C2 plausibly shows up
as governance bytes rising against product bytes. Report the ratio for all three
states as an observation. Do **not** build a metric, a threshold or an alert for
it — spec 0002 §11 refuses that explicitly, because building a measure for a
hypothesis before measuring it is the same failure this whole batch is aimed at.

**Then re-scope ticket 07.** It is currently written as one pass over the whole
estate, which conflates the estate's two families:

- **clone lineage** — Advisor-Desk, agent-rules-books. Shared upstream, so a
  controlled comparison is possible. Runs first.
- **hand built** — Home-system, Estimating-Lab, Merit-knowledge. No shared
  origin, no baseline, so it is an audit and whatever it is measured against has
  to be argued. Runs second.

Gate A and Gate B keep their rules unchanged, including that the three Gate A
questions are written down **before** the data is examined, and that "not built"
is a recorded result.

## Measured before this ticket ran — vocabulary, 2026-09-10

C2 is cloned at `/home/user/agent-rules-books` (`782a886`, 515 tracked files:
386 Markdown, 51 JSON, 35 Python). It holds no Orbit implementation. Our
vocabulary was measured against it before the comparison, so a term appearing in
both is a reading taken on purpose rather than a surprise mid-run.

**Every compound identifier we use appears in zero of its files.** All of
`instruction-surface`, `skill-package`, `agent-definition`,
`command-definition`, `hook-definition`, `hook-target`, `mcp-config`,
`no-indexed-target-match`, `outside-indexed-roots`, `unresolvable-scheme`,
`bare-path-literal`, `frontmatter-field`, `import-statement`, `config-value`,
`supersedes-claim`, `markdown-link`, `artifact-header`,
`manifest-declaration`, `literal-write-path`, `rung_of`, `external_ref`,
`index_run`, `coverage_note`, `gl_context`, `surface_kind`. The compound shape
of the names is what makes them unambiguous; nothing else was needed.

**Our single English words appear throughout, as English.** `surface` in 66 of
515 files — "reliably surface defects", "a large surface with minor helpers" —
and `contains` 47, `references` 41, `produces` 36, `clause` 15. These were never
identifiers. A count of them says nothing about either graph.

**One term is shared with a different meaning.**
`.claude/skills/video-harvest/SKILL.md` runs its own provenance scheme:
`SOURCE: SCREEN-READ` or `SOURCE: INFERRED`, with a named failure,
`source_out_of_contract`, for a model that "graded its own evidence instead of
saying whether it read the frame". `INFERRED` appears in 7 files and `UNKNOWN`
in 4 under that scheme. `OBSERVED` and `DECLARED` appear in none.

**Recorded, not designed against.** Two repositories reaching for the same word
for the same idea is an observation about the estate, and plausibly a symptom of
the layer this project exists to decompose rather than a naming fault to
engineer around. Candidate B is still gated, and whatever ticket 07 decides
about evidence columns it now decides knowing this. Nothing here changes a
detector, a name, or a gate.

## The pass mark, set before any data

**If Orbit cannot show a measurable difference between C0, C1 and C2, it does not
work.** Not "needs more detectors" — spec 0001 §13's kill conditions apply and
the project stops. This was agreed before the run for exactly the reason that it
would be negotiable afterwards.

Also binding: no finding may assert something false. A single false assertion is
a stop, not a bug. Any question the run cannot address is recorded as a coverage
gap, which is a result.

## Acceptance

- [ ] agent-rules-books attached, indexed, and never written to
- [ ] Whether C2 still carries the fourteen `full.md` symlinks is established
      from the rows and stated, either way, as part of the base-rewrite question
- [ ] Two names for one file count once in every state, with the number folded
      reported per state
- [ ] Whether C2 rewrote its base is established and stated before any delta is
      read as comparable
- [ ] The three-state table is produced, with absolute figures beside every delta
- [ ] The governance-to-product byte ratio appears as an observation for all
      three states, with no metric, threshold or alert built
- [ ] The pass mark is applied and the result recorded — including a stop
- [ ] Ticket 07 rewritten: lineage first as a controlled comparison, hand-built
      family second as an audit, both gates unchanged
- [ ] Output contains no forbidden vocabulary word

## Watch for

**C2 is somebody's failed work, and the vocabulary constraint is at its most
load-bearing here.** A repository whose governance grew until work stopped is a
condition, reported as counts and bytes. It is not broken, obsolete or wrong, and
the tool does not say which parts to remove — that is the recomposition decision,
which spec 0002 §11 keeps out of scope until after the audit.

**The pass mark cuts both ways.** A difference that only appears after the fourth
attempt at a new detector is not a difference Orbit found — it is one that was
built to be found. Record what the comparison showed on the detector set that
existed when the run started.
