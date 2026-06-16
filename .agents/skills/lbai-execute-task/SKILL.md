---
name: lbai-execute-task
description: Execute the current LBAI task contract; write execution_plan.md and task_output.md. Use when the user types /lbai-execute-task.
---

Read `AGENTS.md` and execute `/lbai-execute-task` per `lbai_system/runner_contracts/lbai_command_contract_v1.md`. Tools: `lbai_system/tools/`.

Read `lbai_system/prompts/execute_task_plan_prompt_v1.md`.

1. Resolve task folder if needed
2. Run `python3 lbai_system/tools/prepare_execute_task.py <task_folder>`
3. Read linked evidence briefs and write `task_output.md`

No separate enrichment JSON tool; deliverables are `execution_plan.md` and `task_output.md`.
