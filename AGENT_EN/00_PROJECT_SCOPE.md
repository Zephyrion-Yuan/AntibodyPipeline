
# 00_PROJECT_SCOPE.md (Scope & Non‑Goals)

## In Scope

- Batch‑centric experimental record system (LIMS‑like)
- Fixed / semi‑fixed workflow templates (≤20 steps)
- Full reproducibility, rollback, and lineage tracking
- Antibody expression & functional validation workflows
- Plate/Well‑level spatial audit (separate from workflow)

## Out of Scope

- Generic low‑code workflow builders
- Undo/Redo as experiment history
- Inventory, procurement, or cost accounting
- Instrument/robot control
- Storing large binary data in PostgreSQL

## Design Philosophy

Priority order:
1. Traceability
2. Reproducibility
3. Auditability
4. Evolvability
5. UI polish
