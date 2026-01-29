
# AGENT.md (Entry Point / Source of Truth)

> **Read this first.** This directory is the operational manual for Codex/Agents to
> continuously develop this project until testing is complete.
> If conflicts exist with any other documents, this directory takes precedence.
> If conflicts exist *within* this directory, the file with the **larger index number wins**
> (e.g. `09_...` > `04_...`).

---

## 0) Your Role

You are the primary software engineer (Codex Agent) for this project.

You MUST:
- Strictly follow all MUST / MUST NOT constraints defined here.
- Never invent core domain entities not defined in the Domain Model.
- Never change database schema, workflow semantics, or rollback semantics
  without updating the corresponding documents.
- Always prioritize a **minimal end-to-end working loop** before adding features.

---

## 1) One‑Sentence Project Description

This is a **Batch‑first antibody experiment tracking and computation system**:

- **React Flow** visualizes a fixed workflow template and execution state
- **Temporal** is the single source of truth for execution order and state
- **PostgreSQL** is the factual ledger for metadata, versions, and lineage
- **Artifacts (files)** are immutable and stored in object storage (S3 / MinIO)

---

## 2) Non‑Negotiable Rules

### Execution & Authority
- **Temporal is the only authority** on execution order and runtime state.
- **React Flow is visualization only**; it must never drive execution logic.

### Immutability & Traceability
- Artifacts are **immutable** once created.
- **Rollback ≠ Undo**: rollback means recomputation from a step with new parameters,
  producing new versions and lineage while preserving all history.

### Workflow Template
- Semi‑fixed template, ≤ 20 steps.
- Each step has an immutable `step_index`.
- `step_index` rules:
  - Starts at 1
  - Never reused
  - New steps are append‑only
  - Deleted steps are deprecated, never removed

### Data Modeling
- PostgreSQL never stores large files.
- **No “universal sample table”** — use explicit entities + relation tables.
- Plate/Well (spatial) modeling is strictly separated from workflow/lineage (causal).

---

## 3) Reading Order

1. 00_PROJECT_SCOPE.md
2. 01_ARCHITECTURE.md
3. 04_WORKFLOW_ENGINE.md
4. 02_DOMAIN_MODEL.md
5. 03_DATABASE_SCHEMA.md
6. 05_FRONTEND_RULES.md
7. 06_BACKEND_RULES.md
8. 09_DEVELOPMENT_PLAN.md
9. 10_TESTING_STRATEGY.md

---

## 4) Definition of Done

A release is considered test‑ready when:

- A Batch can be created and visualized
- A workflow run executes ≥2 steps and produces artifacts
- Node execution status is visible in the UI
- Parameters can be changed and rollback triggered
- New versions and lineage are generated correctly
- Automated tests cover core semantics

---
