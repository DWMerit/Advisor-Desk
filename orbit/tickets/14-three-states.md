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

Then produce the comparison:

| state | what it is |
|---|---|
| **C0** | Advisor-Desk `main` @ `a7d7649` — untouched upstream |
| **C1** | Advisor-Desk branch head — built a tool, corpus untouched |
| **C2** | agent-rules-books — grew its own governance layer, stopped producing |

**agent-rules-books is read-only.** Index it. Never write to it, never push to
it, never open a pull request against it.

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
