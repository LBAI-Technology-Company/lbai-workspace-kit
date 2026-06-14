# /lbai-new-task

Cursor command wrapper for the shared LBAI workflow contract.

User input:

{{input}}

## Required behavior

Read `lbai_system/runner_contracts/lbai_command_contract_v1.md` and execute the `/lbai-new-task` section.

Before calling `new_task.py`:

1. Read role context, current conversation context, and optional prior artifacts. Search existing artifacts first when the task may depend on company knowledge.
2. Read `lbai_system/prompts/task_intake_enrichment_prompt_v1.md` and produce task intake enrichment JSON per `lbai_system/schemas/task_intake_enrichment_schema_v1.json`.
3. Run `python3 lbai_system/tools/new_task.py --enrichment <json_path>`.

The enrichment must separate known information by source, blocking gaps, and recommended non-blocking context. Direct employee clarifications belong in task-local context; use `/lbai-add-evidence` only for source material that should be archived as reusable evidence.

If AI enrichment is unavailable, return blocked intake. Do not call the tool without `--enrichment`.

Supported runtimes: Cursor and Codex desktop app only. No rule-based fallback.

## Response format

Use the `/lbai-new-task` response format from `lbai_system/runner_contracts/lbai_command_contract_v1.md`.
