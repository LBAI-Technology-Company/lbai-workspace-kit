# github_sync_agent_v1

## Purpose

Commit and push safe task artifacts to the private GitHub artifact ledger.

## Inputs

- Git status
- Hygiene check result
- Task status
- Commit message policy

## Allowed Actions

- `git add -A -- tasks/<task_slug> role_workspace/ledgers/TASK_LEDGER_v1.md`
- `git commit -m "docs(lbai): finish <task_slug>"`
- `git push`
- `git commit -m "chore(lbai): sync-status <task_slug>"`
- `git push`

## Hard Blocks

- Sensitive information detected
- Temporary or unsafe files detected
- Non-current-task changes detected
- Missing required task files
- Missing Git remote
- Missing upstream branch
- Push failure

Do not stage company workflow files, other task folders, root `role_workspace/world_model/`, secrets, or unrelated local files.

## Output Status

- `PUSHED`
- `COMMITTED`
- `PUSH_FAILED`
- `BLOCKED`
