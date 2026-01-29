
# 02_DOMAIN_MODEL.md (Antibody Experiment Domain Model)

## Core Principles

- No “mega sample” tables
- Each entity represents a real, referencable experimental object
- Downstream experiments must reference stable entities
- History is append‑only via versioning and lineage

## Core Entities

### Chain
- Heavy / Light / scFv sequences

### Construct
- Combination of one or more chains
- Many‑to‑many with Chain

### Clone
- Physical instantiation of a Construct

### Expression Sample
- One expression/transfection setup
- Many‑to‑many with Clone

### Recombinant Antibody (Required)
- Purified product of expression
- Direct input to all functional assays

### Assay Result
- ELISA / SPR / BLI / Neutralization etc.
- References Recombinant Antibody

## Plate / Well Model

- Plate: physical plate
- Well: fixed coordinate (A1, B2…)
- SampleWell: occupancy event at a step/time
- Spatial tracking is **not** expressed via workflow edges

## Lineage

- All outputs record derivation relationships
- Rollback creates new lineage, never deletes history
