# 03 — Clause segmentation with byte offsets

The governance analogue of their `Definition`. This is why granularity is sub-file: a 17 KB instruction surface is dozens of rules with different lifetimes, and *which rule* is the real question.

## Do

Segment each surface into `gl_context_clause`:
`id`, `traversal_path`, `branch`, `commit_sha`, `surface_path`, `fqn`, `heading`, `clause_type`, `start_line`, `end_line`, `start_byte`, `end_byte`

- `fqn` mirrors theirs: `CLAUDE.md#Estimating rules#M6 anchors`
- `clause_type`: `heading-section` | `list-rule` | `frontmatter-field` | `code-block`
- Segment by Markdown structure — heading tree, then list items under a heading
- Emit `CONTAINS` edges: Surface → Clause, Clause → Clause for nesting

## Done when

A single rule is addressable by `fqn`, and its text is retrieved **by reading the file at the recorded byte offsets** — never from a column.

## Not in this slice

No semantic classification of what a clause means. Structure only.
