
# 03_DATABASE_SCHEMA.md (PostgreSQL Schema Rules)

## Global Rules

- PostgreSQL 15+
- UUID primary keys
- UTC timestamps
- Artifacts stored externally
- Versions are append‑only

## Core Tables

- batch
- workflow_template_step
- workflow_node_version
- artifact
- lineage_edge

## Domain Tables

- chain
- construct
- construct_chain
- clone
- plasmid
- expression_sample
- recombinant_antibody
- assay_result

## Plate Tables

- plate
- well
- sample_well

## Hard Constraints

- No artifact overwrite
- No step_index reuse
- No history deletion
