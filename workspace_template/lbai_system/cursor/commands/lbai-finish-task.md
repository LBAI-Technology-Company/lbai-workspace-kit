# /lbai-finish-task

Cursor command wrapper for the shared LBAI workflow contract.

Task folder:

{{input}}

## Required behavior

Read `lbai_system/runner_contracts/lbai_command_contract_v1.md` and execute the `/lbai-finish-task` section.

This is the **normal employee command**. It auto-runs retroactive intake when no task exists, and auto-runs delivery when `task_output.md` is not ready.

Flow:

1. Run `python3 lbai_system/tools/prepare_finish_task.py [task_folder]`.
2. **Auto-intake when needed** (`auto_intake_needed: true`):
   - Read current conversation, role context, and relevant prior artifacts.
   - Produce task intake enrichment JSON per `lbai_system/prompts/task_intake_enrichment_prompt_v1.md` and `lbai_system/schemas/task_intake_enrichment_schema_v1.json`. Use `conversation_context` for material already discussed in chat.
   - Run `python3 lbai_system/tools/new_task.py --enrichment <json_path>`.
   - If intake is `BLOCKED`, try `archive_input.py --resolves` from chat; otherwise stop with `auto_intake: BLOCKED`.
3. Archive chat clarifications with `archive_input.py --resolves "<exact missing input>"` when the employee provided decisions or context in this conversation.
4. Run `python3 lbai_system/tools/check_task_delivery.py <task_folder>`.
5. **Auto-execute when needed** (`auto_execute_needed: true`):
   - Run `python3 lbai_system/tools/prepare_execute_task.py <task_folder>`
   - Read `lbai_system/prompts/execute_task_plan_prompt_v1.md`
   - Write `execution_plan.md` and `task_output.md`
   - If still blocked, stop with `auto_execute: BLOCKED` and do not call `finish_task.py`
6. **Finish review:**
   - Read `task_scope.md`, `task_output.md`, `execution_plan.md` (if present), linked evidence, `missing_inputs.md`, and the current task conversation (employee/user messages only).
   - Read `lbai_system/prompts/finish_review_enrichment_prompt_v1.md` and produce finish review enrichment JSON per `lbai_system/schemas/finish_review_enrichment_schema_v1.json`, including `employee_conversation_turns`.
   - Run `python3 lbai_system/tools/finish_task.py <task_folder> --enrichment <json_path>`.

If AI enrichment is unavailable for intake or finish review, return blocked. Do not call `new_task.py` or `finish_task.py` without `--enrichment`.

Supported runtimes: Cursor and Codex desktop app only. No rule-based fallback.

## Response format

Use the `/lbai-finish-task` response format from `lbai_system/runner_contracts/lbai_command_contract_v1.md`.
