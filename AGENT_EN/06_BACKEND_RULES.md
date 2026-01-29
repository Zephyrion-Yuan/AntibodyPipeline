
# 06_BACKEND_RULES.md (Backend Rules)

## API Responsibilities

- Auth & permission checks
- Batch & graph projection APIs
- Parameter updates (new versions)
- Run & rollback signaling
- Artifact download

## Worker Structure

- workflows/: orchestration only
- activities/: IO & computation
- steps/: pure step logic

## Storage Rules

- Artifacts written before DB commit
- No direct user access to storage
- No artifact mutation
