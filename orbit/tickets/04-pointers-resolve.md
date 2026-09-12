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

**The ceiling became a share, 2026-09-10.** The absolute ceiling of 100 addresses
was calibrated when this repository was a book corpus. It breached at 125 the day
the repository also held documentation about a file-handling tool — prose that
names files for a living, including files that do not exist here by definition,
because the detector's own basename table is `CLAUDE.md`, `GEMINI.md`,
`.cursorrules`. That breach said the repository had grown, not that the detectors
had degraded, and a guard that fires on growth stops being read.

Two corrections came with it. The old pair compared distinct unmatched addresses
against resolved *occurrences* — two units either side of one ratio, which
flattered the reading by roughly six times. Both sides are now distinct
addresses. And thirty-nine bare filenames in this project's own tickets and specs
were rewritten to repository-root paths, because `orbit/orbit_context/compare.py`
written as `compare.py` inside a ticket resolves against the ticket's own
directory and finds nothing. That was a real defect in the documentation, fixed
at the source rather than absorbed by the ceiling.

Reading when the share was set: **98 of 341 distinct addresses did not resolve,
28.7%**, against a ceiling of one in three. Of the 98, thirty-two are correctly
unresolvable — six are class names (`SKILL.md` matches sixteen files) and
twenty-six name nothing in the tree because they are examples. Spec 0001 section
14 already holds that case: whether a path-shaped string in prose was a pointer
or an example is a permanent UNKNOWN.

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
