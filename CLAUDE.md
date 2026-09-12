# Advisor-Desk

Two things live here. **Orbit Context**, under `orbit/`, indexes the governance
surfaces of a repository — instruction surfaces, skill packages, agent
definitions, hooks, and the pointers between them — into a DuckDB graph. The
**rule corpus** under `_rule-workbench/` is a product of this repository rather
than instructions to you.

**This file holds no state.** It says how to ask, not what the answer is, so
there is nothing here to go stale and nothing here to answer from.

## What is in the repository — ask Orbit

```sh
orbit/bin/orbit-context index .     # writes ~/.orbit-context/context.duckdb
orbit/bin/orbit-context repo-map    # surfaces at this commit
```

`repo-map` takes its snapshot from the working tree's git state and declines
when no index run matches it. The decline is the answer: index, then ask again.

Reading the graph directly:

```sh
orbit local sql --db ~/.orbit-context/context.duckdb "SELECT ..."
```

Two things about that command, both measured rather than assumed:

- **`--db` is not optional.** Without it, `orbit local sql` opens GitLab Orbit's
  own graph, finds a table of the same name, and answers from it — returning a
  small plausible number rather than an error. A query written against a
  `current_` view cannot: no such view exists there, so it fails and names the
  table it could not find.
- **The store keeps every run ever indexed.** Ask a `current_` view —
  `current_surface`, `current_clause`, `current_edge`, and `current_run` for
  which snapshot that was — or the answer is several runs added together. The
  `gl_context_*` tables underneath are every run at once, which is the right
  question only when comparing snapshots. `orbit/README.md` carries the views
  and every other query idiom.

## What work exists, and its state — ask the tracker

Work lives as GitHub issues on `DWMerit/Advisor-Desk`. The roadmap is a
wayfinder map — the issue labelled `wayfinder:map` — and its child issues are
the open questions and build tickets.

**An issue's state is open or closed, and that is the only place work state
lives.** No file in this repository records whether something is done. A
`## Acceptance` block, a status line, a table of tickets and an index of phases
are all prose, and prose here has been superseded three and four times over
while reading exactly as though it were current.

`docs/agents/issue-tracker.md` says how to reach the tracker from a local
machine and from a remote session, and which operations need the REST API
directly.

`orbit/tickets/` is a **legacy record**, written before there was a tracker. It
is preserved as historical evidence. No new ticket is created there, and nothing
in it describes current state.

## Whether it works — run it

```sh
python3 -m pytest orbit/tests
```

The run reports its own count. `orbit/tests/test_pointers.py` measures how many
addresses written in this repository's prose resolve to nothing here, against a
ceiling declared in the test; prose that names files spends that headroom, and
the test's own comment says what to do when it breaches.

## Where things are

| | |
|---|---|
| `orbit/specs/` | numbered in sequence; each states its own status and what it rests on |
| `orbit/evidence/` | records quoted by specs, held at their exact bytes |
| `orbit/README.md` | the tool's reference |
| `orbit/tickets/` | legacy, historical |
| `docs/agents/` | how the tracker, its labels, and domain docs are reached |
