# /lbai-finish-task

Cursor command wrapper for the shared LBAI workflow contract.

Task folder:

{{input}}

## Required behavior

Read `lbai_system/runner_contracts/lbai_command_contract_v1.md` and execute the `/lbai-finish-task` section.

Before calling `finish_task.py`:

1. Read `task_scope.md`, `task_output.md`, `execution_plan.md` (if present), linked evidence, and `missing_inputs.md`.
2. Read `lbai_system/prompts/finish_review_enrichment_prompt_v1.md` and produce finish review enrichment JSON per `lbai_system/schemas/finish_review_enrichment_schema_v1.json`.
3. Run `python3 lbai_system/tools/finish_task.py <task_folder> --enrichment <json_path>`.

If AI enrichment is unavailable, return blocked finish. Do not call the tool without `--enrichment`.

Supported runtimes: Cursor and Codex desktop app only. No rule-based fallback.

## Response format

Use the `/lbai-finish-task` response format from `lbai_system/runner_contracts/lbai_command_contract_v1.md`.
