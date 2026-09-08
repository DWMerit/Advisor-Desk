# 06 — repo-map for the context domain

Governance orientation, mirroring their `repo-map`.

## Do

`orbit-context repo-map --repo <path>` — a compact, LLM-oriented map of the governance surface: surfaces by kind and size, clause counts, edge counts by kind, coverage (files carrying no surface role), the three negative-finding counts, and the indexed boundary.

## Done when

Output fits a **stated** budget and the budget is justified by measurement, not invented.

## Calibration

Their `repo-map` emits **12,874 bytes (~3,200 tokens)** for a 1,775-file repo. That is the real reference point. An earlier draft of this project asserted a 2,000-token budget with no basis; do not re-derive it.

## Rule

Every count is reported with the **detector set version** that produced it. A negative finding is a statement about the detectors, not about the estate.
