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

- [x] The three `sub_kind` values are distinct rows and never collapsed
- [x] Every edge carries a `file:line` locator
- [x] A path in backticks resolves correctly
- [x] A path inside a fenced block is recorded and flagged, not dropped
- [x] On a real repository, `no-indexed-target-match` is under 100
- [x] Output contains no forbidden vocabulary word

Pinned by test in `orbit/tests/test_pointers.py`, with the vocabulary lint
extended to the detector names and the three `sub_kind` values in
`orbit/tests/test_vocabulary.py`.

**The measurement.** Run over this repository's 208 Markdown files: **2,094
pointers, 1,831 resolved, 52 distinct `no-indexed-target-match` addresses.**
Counted over addresses because that is what the graph holds — one `ExternalRef`
per address, however many edges enter it, so an address named forty times is one
finding rather than forty. Every one of the 52 was a path the estate had actually
written; none was a fragment. That test runs on every suite run, against whatever
repository the code is sitting in, so the boundary rules cannot silently rot.

**Three decisions worth stating, because none was forced by the ticket:**

- *An address is only a pointer if it carries a file extension, and either a `/`
  or an extension the detector set recognises.* Without it `0.118.1` and
  `SipHash-1-3` are findings. The cost is that a directory named in prose is not
  reported at all — stated as a limit rather than counted as unmatched.
- *An anchor, an unexpanded variable, and a directory that exists are recorded as
  nothing*, not as a non-resolution. Each names something other than a file, and
  reporting one as an unmatched file says something untrue about the estate.
- *`REFERENCES` and `CONTAINS` share `gl_context_edge` and do not carry the same
  columns.* The table is now the **union** of both YAML files, and a column two
  files declare differently fails the index. Before this, the second file's
  columns were never created — a schema decided by which filename sorted first.

## Watch for — this has already bitten

**Token boundary handling is the dominant false-positive source.** A backtick in a negative lookbehind does *not* skip inline code — it shifts the match **start** into the middle of the token, so a valid path in backticks matches as a truncated fragment that cannot resolve. That produced **1,349 phantom findings out of 1,373** on one real repository. Ninety-six percent of the report was the tool talking about itself.

Match from a real boundary — line start, whitespace, or one of `` ` `` `'` `"` `(` `<` `[` — never from a lookbehind that can slide the start. Exclude a leading `/` so URL paths are not re-matched as bare ones.

If the unmatched count comes back in the thousands, the detector is wrong, not the estate.
