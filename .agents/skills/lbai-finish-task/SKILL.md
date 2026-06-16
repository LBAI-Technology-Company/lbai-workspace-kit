---
name: lbai-finish-task
description: Finish an LBAI task and sync safe artifacts. Use when the user types /lbai-finish-task.
---

Read `AGENTS.md` and execute `/lbai-finish-task` per `lbai_system/runner_contracts/lbai_command_contract_v1.md`. Tools: `lbai_system/tools/`.

Read `lbai_system/prompts/finish_review_enrichment_prompt_v1.md`.

1. Read task scope, task_output, execution_plan.md (if present), linked evidence
2. Produce finish review enrichment JSON per `lbai_system/schemas/finish_review_enrichment_schema_v1.json`
3. Run `python3 lbai_system/tools/finish_task.py <task_folder> --enrichment <json_path>`

No rule-based fallback.
