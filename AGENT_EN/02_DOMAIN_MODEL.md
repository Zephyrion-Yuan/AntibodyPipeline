
# 02_DOMAIN_MODEL.md (Antibody Experiment Domain Model)

## Core Principles

- No “mega sample” tables
- Each entity represents a real, referencable experimental object
- Downstream experiments must reference stable entities
- History is append‑only via versioning and lineage

## Core Entities

### Chain
- Heavy / Light / scFv sequence information only

### Construct
- DNA construct design combining one or more Chains
- Includes backbone and regulatory elements as attributes
- Does NOT represent a physical plasmid

### Clone
- A physical plasmid instance derived from a Construct
- Represents a single clone or plasmid preparation
- One Construct → many Clones

### Expression Sample
- One expression or transfection experiment setup
- Many-to-many with Clone

### Recombinant Antibody
- Purified antibody produced from an Expression Sample
- Stable physical entity
- Direct input to downstream functional assays

### Assay Result
- Functional assay outcome (ELISA / SPR / BLI / etc.)
- References one or more Recombinant Antibodies