# 04 — Pointers resolve; non-resolution is classified

**Blocked by:** 02
**Demo when done:** the three negative findings, distinct, on a real repository — with counts in the tens, not the thousands.

## Do

Extract pointers from surfaces and clauses; resolve them; write `gl_context_edge` and `gl_context_external_ref`.

Detectors, each recorded as an edge `subtype`: `markdown-link`, `frontmatter-field`, `import-statement`, `config-value`, `bare-path-literal`, `supersedes-claim`.

Resolution outcomes:
- resolves inside indexed roots → edge to the `gl_file` or `gl_context_surface` row
- resolves outside them → `ExternalRef` `outside-indexed-roots`
- parses but no target → `ExternalRef` `no-indexed-target-match`
- URL or scheme → `ExternalRef` `unresolvable-scheme`

Record whether a match sat inside a fenced code block. Label it; never drop it.

`supersedes-claim` is **DECLARED**, permanently. A superseded file still being loaded is reported as that pair of facts, never as an error.

## Acceptance

- [ ] The three `sub_kind` values are distinct rows and never collapsed
- [ ] Every edge carries a `file:line` locator
- [ ] A path in backticks resolves correctly
- [ ] A path inside a fenced block is recorded and flagged, not dropped
- [ ] On a real repository, `no-indexed-target-match` is under 100
- [ ] Output contains no forbidden vocabulary word

## Watch for — this has already bitten

**Token boundary handling is the dominant false-positive source.** A backtick in a negative lookbehind does *not* skip inline code — it shifts the match **start** into the middle of the token, so a valid path in backticks matches as a truncated fragment that cannot resolve. That produced **1,349 phantom findings out of 1,373** on one real repository. Ninety-six percent of the report was the tool talking about itself.

Match from a real boundary — line start, whitespace, or one of `` ` `` `'` `"` `(` `<` `[` — never from a lookbehind that can slide the start. Exclude a leading `/` so URL paths are not re-matched as bare ones.

If the unmatched count comes back in the thousands, the detector is wrong, not the estate.
