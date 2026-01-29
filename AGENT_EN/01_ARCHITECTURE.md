
# 01_ARCHITECTURE.md (System Architecture)

## Logical Components

Frontend (React + React Flow)
- Batch List Page
- Batch Workflow Page
- Plate Viewer (optional)

Backend API (FastAPI)
- Auth & permissions
- Batch / template / node version APIs
- Artifact indexing & download
- Run / rollback signaling

Temporal
- One Workflow per Batch
- One Activity per step_index

Storage
- PostgreSQL: metadata, versions, lineage
- Object storage: immutable artifacts

## Source of Truth

- Execution order & runtime state: Temporal
- Experimental facts & lineage: PostgreSQL
- File contents: Artifact storage
- Visualization: React Flow

## Boundary Rules

- React Flow: visualization only
- Temporal Workflow: orchestration only (deterministic)
- Activities: all IO & computation
- DB never stores large files
