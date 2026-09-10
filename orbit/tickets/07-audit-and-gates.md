# 07 — Audit the estate, and both gates

**Blocked by:** 06, and **14** — see `08-recognition-and-comparison.md`.
This ticket is rewritten by 14 before it runs: the clone lineage first as a
controlled comparison, the hand-built repositories second as an audit. Both gates
below keep their rules unchanged.
**Demo when done:** the estate audit report, plus two recorded gate decisions.

Phase 1's exit run is **simultaneously** the estate audit and the input to both gate decisions. One pass, not three.

## Part 1 — the audit

Index every repository in the estate. Report, per repository: git state; surfaces by kind and size; clauses; edges by kind; the three negative findings with detector version; identical-byte pairs with provenance counts; coverage gaps.

**Conditions and evidence only.** Nothing is labelled broken, obsolete, misplaced or safe to delete. Zero recognized inbound pointers is a statement about the detector set, not about a file.

## Part 2 — Gate A: does the load ledger earn its place?

**Before looking at the data**, write down the three questions about loading you actually want answered. Then attempt each in plain SQL over the phase-1 tables.

- **All three answer** → the ledger is not built. Filename convention plus `size_bytes` was enough. Record the result.
- **They do not, and the same column is missing each time** → build **only that column**.

Prior signal: phase 1 catches byte-identical `AGENTS.md`/`CLAUDE.md` pairs with a hash, but cannot say a Claude session pays one and a Codex session the other. So `client` is the likeliest — possibly the only — surviving column. The honest first version may be one column, not fourteen.

## Part 3 — Gate B: do evidence columns earn their place?

Take a **random sample of 50 findings** and hand-classify each as a real estate condition or a detector artifact.

- **False-positive rate low and uniform across detectors** → not built. A single `detector` column suffices to trace a bad rule; the four-way class is ceremony.
- **Rate high, or varying sharply between detectors** → built. A finding whose reliability depends on which rule produced it must carry that rule.

The 1,349-of-1,373 phantom rate is a strong argument, but it came from **one fixed bug**. The question is the steady-state rate, and only the sample answers it.

## Acceptance

- [ ] Every repository in the estate appears in the audit
- [ ] The three questions for Gate A were written down before the data was examined
- [ ] Each Gate A question is marked answerable or not, with the SQL attempted
- [ ] 50 findings sampled and hand-classified, with the rate broken down by detector
- [ ] Both gate decisions recorded — including "not built", which is a result
- [ ] Kill conditions checked against the audit before any phase 2 work starts

## Either gate closing is a result, not a failure

Record it, so a future session sees the additions were tested rather than re-proposing them from scratch.
