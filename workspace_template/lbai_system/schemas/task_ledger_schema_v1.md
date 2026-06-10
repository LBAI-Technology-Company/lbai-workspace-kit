# task_ledger_schema_v1

Task ledgers are markdown artifacts with stable fields.

## Required Fields

- `task_id`: stable folder-based task id
- `task_goal`: the work goal
- `source_artifacts`: task inputs and evidence artifacts
- `agents_or_tools_used`: company agents, Cursor commands, or local tools used
- `outputs_created`: output artifacts created or updated
- `status`: `OPEN`, `BLOCKED`, `READY_TO_EXECUTE`, or `COMPLETED`; `WAITING_REVIEW` may appear only in legacy artifacts
- `blocked_reason`: reason if blocked, otherwise `None`
- `review_needed`: `true` or `false`
- `leader_review_reminder`: reminder text or `None`
- `commit_readiness`: `READY`, `BLOCKED`, `NEEDS_MANUAL_CHECK`, or `UNKNOWN`; `READY` means task hygiene and Git sync preconditions are satisfied
- `git_status`: `NOT_SYNCED`, `COMMITTED`, `PUSHED`, `PUSH_FAILED`, or `BLOCKED`
- `next_dependency`: the next human, source, review, or system dependency

## Admission Rule

A task can be admitted to the private GitHub artifact ledger when hygiene checks pass, even if `review_needed: true`.

Review-sensitive work may finish as `COMPLETED` while `review_needed: true` and `leader_review_reminder` are set. External release still requires responsible reviewer approval outside this workflow.
