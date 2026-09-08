# 04 — Pointer extraction and resolution

## Do

Extract pointers from surfaces and clauses, resolve them, write `gl_context_edge` and `gl_context_external_ref`.

Detectors, each recorded as an edge `subtype`:
`markdown-link`, `frontmatter-field`, `import-statement`, `config-value`, `bare-path-literal`, `supersedes-claim`

Resolution outcomes:
- resolves inside indexed roots → edge to the `gl_file` / `gl_context_surface` row
- resolves outside them → `ExternalRef` `outside-indexed-roots`
- parses but no target → `ExternalRef` `no-indexed-target-match`
- URL / scheme → `ExternalRef` `unresolvable-scheme`

Record whether a match sat inside a fenced code block. Label it; never drop it.

## Done when

The three `sub_kind` values are distinct in the table and never collapsed, and each edge carries `file:line`.

## Watch for — this bit has bitten already

**Token boundary handling is the dominant false-positive source.** A backtick in a negative lookbehind does not skip inline code; it shifts the match *start* into the middle of the token, so a valid path in backticks matches as a truncated fragment that cannot resolve. That produced **1,349 phantom findings out of 1,373** on one real repo.

Match from a real boundary — line start, whitespace, or one of `` ` `` `'` `"` `(` `<` `[` — never from a lookbehind that can slide the start. Exclude a leading `/` from the boundary class so URL paths are not re-matched as bare ones.

Sanity check before calling this done: unmatched count should be tens, not thousands.
