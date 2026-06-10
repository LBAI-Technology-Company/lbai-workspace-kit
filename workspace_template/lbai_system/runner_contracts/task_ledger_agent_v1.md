# task_ledger_agent_v1

## Purpose

Convert task state into structured task and global ledger artifacts.

## Inputs

- `task_scope.md`
- `task_slot.md`
- `task_output.md` when present
- linked evidence under `role_workspace/knowledge/evidence/`
- `role_workspace/ledgers/EVIDENCE_LEDGER_v1.md`
- legacy task-local `input_*.md` when present
- Review files when required
- Git hygiene and push status

## Outputs

- Updated task-level `task_ledger.md`
- Updated `role_workspace/ledgers/TASK_LEDGER_v1.md`

## Hard Blocks

- Missing task contract
- Missing required output
- Sensitive data detected
- Unsafe non-task changes
