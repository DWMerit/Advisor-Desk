# 02 — Every governance object is a surface

**Blocked by:** 01
**Demo when done:** one query lists skills, agents, slash commands and hook definitions alongside instruction surfaces, each with its kind and size.

## Do

Extend detection beyond instruction surfaces. Each becomes a `surface_kind`:

- `skill-package` — a directory containing `SKILL.md` whose frontmatter carries `name` and `description`
- `agent-definition` — a file under `.claude/agents/` with `name` and `description` frontmatter
- `command-definition` — a file under `.claude/commands/`
- `hook-definition` — an entry inside a settings file's `hooks` block
- `mcp-config` — MCP server configuration

For skills and agents, record the **frontmatter bytes separately from the body bytes**. The description is what loads at boot for every session; the body only loads on invocation. Conflating them misstates the boot cost by an order of magnitude.

For hook definitions, resolve the command to a file where it resolves, and mark that file as a hook target.

## Acceptance

- [x] All six `surface_kind` values appear from a fixture containing one of each
- [x] Frontmatter bytes and body bytes are separately queryable for a skill
- [x] A hook definition row carries its matcher **quoted verbatim** with a `file:line` locator
- [x] A hook whose command resolves to a script in the tree is linked to that file
- [x] A hook whose command is a PATH lookup is recorded as unresolvable, not as missing

All five are pinned by test in `orbit/tests/test_governance.py`.

## Watch for

A file is often several things at once — a hook script is a tool *and* a hook target *and* possibly a generator. Rows are additive; do not force one categorisation.
