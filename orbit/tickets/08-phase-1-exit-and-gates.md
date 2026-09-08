# 08 — Phase 1 exit: the estate audit, and both gates

Run phase 1 over the real estate. **This single run is the audit and the input to both gate decisions.**

## Part 1 — the audit

Index every repository in the estate. Report, per repository: git state, surfaces by kind and size, clauses, edges by kind, the three negative findings with detector version, identical-byte pairs with provenance counts, and coverage gaps.

Report conditions and evidence only. Nothing is labelled broken, obsolete, misplaced or safe to delete.

## Part 2 — Gate A: does the load ledger earn its place?

Before looking at the data, **write down the three questions about loading you actually want answered.** Then attempt each in plain SQL over the phase-1 tables.

- **All three answer** → the ledger is not built. Filename convention plus `size_bytes` was enough. Record the result.
- **They don't, and the same column is missing each time** → build **only that column**.

Prior signal: phase 1 will catch byte-identical `AGENTS.md`/`CLAUDE.md` pairs with a hash, but cannot say a Claude session pays one and a Codex session the other. So `client` is the likeliest — possibly only — surviving column. The honest first version may be one column, not fourteen.

## Part 3 — Gate B: do evidence columns earn their place?

Take a **random sample of 50 findings** and hand-classify each as a real estate condition or a detector artifact.

- **False-positive rate low and uniform across detectors** → not built. A single `detector` column suffices to trace a bad rule; the four-way class is ceremony.
- **Rate high, or varying sharply between detectors** → built. A finding whose reliability depends on which rule produced it must carry that rule.

The 1,349-of-1,373 phantom rate is a strong argument but came from **one fixed bug**. The question is the steady-state rate, and only the sample answers it.

## Either gate closing is a result, not a failure

Record it, so a future session sees the additions were tested rather than re-proposing them from scratch.

## Then

Kill conditions (spec §13) get checked against the audit before any phase 2 work starts.
