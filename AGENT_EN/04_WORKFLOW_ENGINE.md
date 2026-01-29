
# 04_WORKFLOW_ENGINE.md (Temporal & Rollback Model)

## Mapping

Batch → Workflow Instance  
Step (step_index) → Activity  
Rollback → Signal + recomputation

## Workflow Rules

- Deterministic only
- No IO, DB access, or computation
- Handles sequencing, branching, signals

## Activity Rules

- One activity per step_index
- Performs computation & IO
- Produces immutable artifacts
- Writes versions & lineage

## Rollback Semantics

Rollback means:
- Recompute from a given step_index
- Create new versions downstream
- Preserve all historical data

Undo‑style rollback is forbidden.
