# /lbai-execute-task

Cursor command wrapper for the shared LBAI workflow contract.

Task folder:

{{input}}

## Required behavior

Read `lbai_system/runner_contracts/lbai_command_contract_v1.md` and execute the `/lbai-execute-task` section.

Execution flow:

1. Resolve task folder if omitted (`resolve_current_task.py execute`).
2. Run `python3 lbai_system/tools/prepare_execute_task.py <task_folder>` to validate inputs and create `execution_plan.md` if missing.
3. Read `lbai_system/prompts/execute_task_plan_prompt_v1.md`.
4. Write `tasks/<task_folder>/task_output.md` aligned with `execution_plan.md` and `task_slot.md`.
5. If chat input is a direct clarification, decision, preference, or lightweight context, save it as task-local input with `archive_input.py --resolves "<exact missing input>"`; use `/lbai-add-evidence` only for reusable/source material that should become independent evidence.

No enrichment JSON tool for execute-task. Deliverables: `execution_plan.md` and `task_output.md`.

Supported runtimes: Cursor and Codex desktop app only.

## Response format

Use the `/lbai-execute-task` response format from `lbai_system/runner_contracts/lbai_command_contract_v1.md`.
