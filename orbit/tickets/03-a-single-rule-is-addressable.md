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

- [x] A rule buried three headings deep is retrievable by `fqn`
- [x] Retrieved text is byte-identical to that span of the file on disk
- [x] Editing the file and re-indexing moves the offsets
- [x] No clause text is stored in any column
- [x] Nesting depth is queryable via `CONTAINS`

Three contracts were added after the first implementation, because ticket 04
resolves pointers **to** these addresses — at which point an ambiguous address
becomes a wrong edge, and a stale offset becomes a wrong edge that also looks
right. Each is now pinned by test:

- [x] An `fqn` matching more than one clause fails as `AMBIGUOUS` (exit 2),
      writes **nothing** to stdout, and lists candidates by `id`
- [x] A clause `id` resolves to exactly one clause; `fqn` is a lookup key, `id`
      is the address — the split GitLab makes between `Definition.fqn` and
      `Definition.id`
- [x] Reading a file that changed since indexing fails as `STALE` (exit 3), not
      a slice at offsets that no longer describe it — caught by SHA-256, so a
      same-length edit is caught too
- [x] A parent's span **includes** its descendants, documented and tested,
      matching GitLab where a class definition spans its methods
- [x] `show --own` returns a clause's own bytes with descendant spans removed,
      for a bounded load rather than a whole subtree

## Watch for

Offsets must be **byte** offsets, not character offsets, or any non-ASCII content silently shifts the retrieved span.

No semantic classification of what a clause means. Structure only.
