# 03 — A single rule is addressable

**Blocked by:** 01
**Demo when done:** name a rule by `fqn`, and its text prints — read from the file at recorded byte offsets, not from any column.

This is the whole reason for emulating their `Definition` model. A 17 KB instruction surface is dozens of rules with different lifetimes; addressed as one file, *which rule* is unanswerable.

## Do

1. Ontology YAML for `Clause`, mirroring their `source_code/definition.yaml` — including `start_line`, `end_line`, `start_byte`, `end_byte`.
2. Segment each surface by Markdown structure: heading tree first, then list items beneath a heading.
3. `fqn` follows their convention: `CLAUDE.md#Estimating rules#M6 anchors`.
4. `clause_type`: `heading-section` | `list-rule` | `frontmatter-field` | `code-block`.
5. Emit `CONTAINS` edges — Surface → Clause, and Clause → Clause for nesting.
6. A retrieval path that takes an `fqn`, reads the file at the offsets, and prints the bytes.

## Acceptance

- [ ] A rule buried three headings deep is retrievable by `fqn`
- [ ] Retrieved text is byte-identical to that span of the file on disk
- [ ] Editing the file and re-indexing moves the offsets
- [ ] No clause text is stored in any column
- [ ] Nesting depth is queryable via `CONTAINS`

## Watch for

Offsets must be **byte** offsets, not character offsets, or any non-ASCII content silently shifts the retrieved span.

No semantic classification of what a clause means. Structure only.
