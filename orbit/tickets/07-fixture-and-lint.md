# 07 — Fixture estate, vocabulary lint, acceptance scenarios

Closes phase 1.

## Do

**Fixture builder** — a script that constructs a throwaway multi-repo estate in a temp dir at test time. Not a committed tree: committing real repositories means nested `.git` directories that every clone and tool has to special-case. A ~90-line builder covered every scenario in the prototype and reads in one screen.

Must contain: real git repos, real instruction surfaces (root and nested), a real skill package, a real agent definition, a real settings file with hooks, a real generated artifact with a header, a real cross-repo link, a real pointer resolving nowhere, a real byte-identical pair.

**Vocabulary lint** — run every command over every fixture; assert no forbidden word appears in **tool-authored fields**. Scope it to those fields only: it must not fire on a node address echoing a filename that happens to contain one. That is data, not the tool's voice.

**Acceptance scenarios** — spec §10, items 1–10.

## Done when

All scenarios pass and the lint is green on both the fixture and the two real repositories.
