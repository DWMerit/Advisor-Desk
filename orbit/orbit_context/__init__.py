"""Orbit Context — a context domain co-resident in GitLab Orbit's local DuckDB.

Writes only ``gl_context_*`` tables. Never writes to Orbit's own tables.
"""

__all__ = [
    "ontology", "workspace", "surfaces", "clauses", "store", "indexer",
    "retrieve", "cli",
]
