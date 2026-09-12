# Advisor-Desk

Two things live here: **Orbit Context**, a tool under `orbit/` that indexes the
governance surfaces of a repository into a DuckDB graph, and the **rule corpus**
under `_rule-workbench/`, which is a product of this repository rather than
instructions to you.

## Read state before describing it

This repository's own history is the argument for this rule. Sessions have
reported work as missing that was committed minutes earlier, and reported a
ticket unrun that was finished, because the context window reads like a record
and is not one.

```sh
orbit/bin/orbit-context index .        # ~60s; writes ~/.orbit-context/context.duckdb
orbit/bin/orbit-context repo-map       # this repository's surfaces, at this commit
```

`repo-map` selects the snapshot from the working tree's git state, and declines
when no index run matches it. **Let it decline.** A declining command is the
signal; re-index rather than answering from memory.

Tickets carry a `## Acceptance` block. A ticket that has been run carries a
**second** one with its boxes checked — read the last one, not the first.

## Querying the graph

```sh
orbit local sql --db ~/.orbit-context/context.duckdb "SELECT ..."
```

**`--db` is not optional.** Without it, `orbit local sql` reads GitLab Orbit's
own graph, finds a table of the same name, and returns a small plausible number
instead of an error.

The store keeps every run ever indexed. Scope to one snapshot on
`(project_id, branch, commit_sha)` before reading any figure as current, or the
answer is several runs added together. `orbit/README.md` shows the clause.

## Tests

```sh
python3 -m pytest orbit/tests        # 500 tests, ~4 minutes
```

`orbit/tests/test_pointers.py` guards against detector drift by measuring how
many addresses written in this repository's prose resolve to nothing here,
against a ceiling of 0.33. Prose that names files spends that headroom. If it
breaches, the answer is never to raise the ceiling.

## Where things are

| | |
|---|---|
| `orbit/specs/` | what is being built and why; 0001 is the foundation |
| `orbit/tickets/` | one unit of work each, in order |
| `orbit/README.md` | the tool's reference, including every query idiom |
| `orbit/evidence/` | records quoted by specs, held at their exact bytes |

Specs and tickets are not loaded by any session. A rule that matters at session
open belongs in this file; a rule written only in a ticket is read by nobody.
