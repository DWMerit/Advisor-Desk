# Issue tracker: GitHub

Issues and specs for this repo live as GitHub issues, on `DWMerit/Advisor-Desk`.

## Which command actually works, and where

**`gh` is not installed in Claude Code remote sessions.** Verified 2026-09-12:
`which gh` finds nothing there. The conventions below are written against `gh`
because that is what works on Dylan's own machine, and they are correct there.

In a remote session, use the **GitHub MCP tools** (`mcp__github__*`) instead.
Same repository, same issues, same labels -- a different way of reaching them.
`issue_write` creates and edits, `issue_read` reads, `list_issues` and
`search_issues` list.

### What the MCP tools do not cover

Some operations have no MCP tool. **Do not conclude they are unreachable.**
`GH_TOKEN` and `GITHUB_TOKEN` are both present in the remote session's
environment, so the REST API can be called directly with `curl` using the
session's own credential -- the same one `git push` uses. Verified 2026-09-12 by
wiring three issue dependencies and creating eight labels this way, after first
reporting both as impossible.

Two that need this route:

- **Issue dependencies** (the `blocked_by` relationship that renders the
  `Blocked` badge): `POST /repos/{owner}/{repo}/issues/{n}/dependencies/blocked_by`
  with `{"issue_id": <blocker's numeric database id>}`. The database id is not
  the `#number`: read it from `GET /repos/{owner}/{repo}/issues/{n}` as `.id`.
- **Creating labels**: `POST /repos/{owner}/{repo}/labels`. A label that does
  not exist cannot be applied, and issue creation fails rather than creating it.

Two things that cost time when they were learned the hard way:

- Every POST needs `Content-Type: application/json` explicitly, or the API
  returns **415** with no other clue.
- `issue_dependencies_summary.blocked_by` is **eventually consistent**. Straight
  after wiring three edges it read 1, and settled to 3 seconds later. Re-read
  before treating a zero as unblocked.

**And check the feature is switched on.** `list_issues` returning
`totalCount: 0` reads identically whether the tracker is empty or disabled;
creating an issue is what distinguishes them, and a disabled tracker answers
`410 Issues has been disabled in this repository`.

This is all written down because a file that says "use the `gh` CLI for all
operations" reads perfectly and then fails with command-not-found, and a file
that stops at "use the MCP tools" leads the next session to conclude that
anything without a tool cannot be done here. Both are the kind of rule that
costs a session rather than helping it.

## Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> --comments`, filtering comments by `jq` and also fetching labels.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..."`

Infer the repo from `git remote -v`; `gh` does this automatically when run inside a clone.

## Pull requests as a triage surface

**PRs as a request surface: no.** _(Set to `yes` if this repo treats external PRs as feature requests; `/triage` reads this flag.)_

When set to `yes`, PRs run through the same labels and states as issues, using the `gh pr` equivalents:

- **Read a PR**: `gh pr view <number> --comments` and `gh pr diff <number>` for the diff.
- **List external PRs for triage**: `gh pr list --state open --json number,title,body,labels,author,authorAssociation,comments` then keep only `authorAssociation` of `CONTRIBUTOR`, `FIRST_TIME_CONTRIBUTOR`, or `NONE` (drop `OWNER`/`MEMBER`/`COLLABORATOR`).
- **Comment / label / close**: `gh pr comment`, `gh pr edit --add-label`/`--remove-label`, `gh pr close`.

GitHub shares one number space across issues and PRs, so a bare `#42` may be either: resolve with `gh pr view 42` and fall back to `gh issue view 42`.

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments`.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a single issue with **child** issues as tickets.

- **Map**: a single issue labelled `wayfinder:map`, holding the Notes / Decisions-so-far / Fog body. `gh issue create --label wayfinder:map`.
- **Child ticket**: an issue linked to the map as a GitHub sub-issue (`gh api` on the sub-issues endpoint). Where sub-issues aren't enabled, add the child to a task list in the map body and put `Part of #<map>` at the top of the child body. Labels: `wayfinder:<type>` (`research`/`prototype`/`grilling`/`task`). Once claimed, the ticket is assigned to the driving dev.
- **Blocking**: GitHub's **native issue dependencies**, the canonical, UI-visible representation. Add an edge with `gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`, where `<blocker-db-id>` is the blocker's numeric **database id** (`gh api repos/<owner>/<repo>/issues/<n> --jq .id`, _not_ the `#number` or `node_id`). GitHub reports `issue_dependencies_summary.blocked_by` (open blockers only, the live gate). Where dependencies aren't available, fall back to a `Blocked by: #<n>, #<n>` line at the top of the child body. A ticket is unblocked when every blocker is closed.
- **Frontier query**: list the map's open children (`gh issue list --state open`, scoped to the map's sub-issues / task list), drop any with an open blocker (`issue_dependencies_summary.blocked_by > 0`, or an open issue in the `Blocked by` line) or an assignee; first in map order wins.
- **Claim**: `gh issue edit <n> --add-assignee @me`, the session's first write.
- **Resolve**: `gh issue comment <n> --body "<answer>"`, then `gh issue close <n>`, then append a context pointer (gist + link) to the map's Decisions-so-far.
