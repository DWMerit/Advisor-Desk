# 02 — Ontology YAML in GitLab's format

## Do

Write the context domain as ontology files mirroring `config/ontology/` in `gitlabhq/orbit-knowledge-graph`, so they could be overlaid or contributed upstream unchanged.

- `nodes/context/surface.yaml`, `clause.yaml`, `external_ref.yaml`
- `edges/references.yaml`, `invokes.yaml`, `produces.yaml`, `identical_bytes.yaml`

Follow their node schema exactly: `node_type`, `domain`, `description`, `label`, `destination_table`, `default_columns`, `sort_key`, `properties` (each with `type`, `source`, `nullable`, `description`), `storage.columns`.

Follow their edge schema: `description`, `table`, `variants` with `from_node`/`to_node`/`description`.

Reference copies: `config/ontology/nodes/source_code/file.yaml`, `definition.yaml`, `config/ontology/edges/contains.yaml`, `calls.yaml`.

Then make the indexer read table shapes **from these files** rather than hardcoding `CREATE TABLE`.

## Done when

- Files parse and validate against their schema shape.
- Adding a column means editing YAML, not Python.
- Slice 01's tables are created from the YAML and still query the same.

## Why it matters

This is what makes promoting a new node type cheap later, and what makes upstream contribution possible without a rewrite.
