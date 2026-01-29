
# 05_FRONTEND_RULES.md (Frontend Rules)

## Stack

- React 18+
- React Flow
- Zustand
- Tailwind CSS

## Page Structure

- Batch List Page
- Batch Workflow Page (one batch = one graph)

## React Flow Constraints

MUST:
- Visualize template structure & state
- Allow parameter editing & rollback triggers

MUST NOT:
- Add/remove/reorder steps
- Drive execution logic
- Represent plate movement

## Data Model (UI)

Nodes reflect template steps + latest node versions.
Edges reflect template structure only.
