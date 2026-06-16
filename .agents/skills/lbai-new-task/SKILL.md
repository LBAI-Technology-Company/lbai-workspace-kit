---
name: lbai-new-task
description: Create a formal LBAI task under tasks/. Use when the user types /lbai-new-task.
---

Read `AGENTS.md` and execute `/lbai-new-task` per `lbai_system/runner_contracts/lbai_command_contract_v1.md`. Tools: `lbai_system/tools/`.

Read `lbai_system/prompts/task_intake_enrichment_prompt_v1.md`.

1. Produce task intake enrichment JSON per `lbai_system/schemas/task_intake_enrichment_schema_v1.json`
2. Run `python3 lbai_system/tools/new_task.py --enrichment <json_path>`

No rule-based fallback.
