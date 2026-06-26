# LBAI Finish Task Skill

Read `lbai_system/runner_contracts/lbai_command_contract_v1.md`, `lbai_system/prompts/execute_task_plan_prompt_v1.md`, and `lbai_system/prompts/finish_review_enrichment_prompt_v1.md`.

Normal employee end command. Auto-runs delivery when `task_output.md` is not ready:

`archive_input` (if needed) → `check_task_delivery.py` → optional auto-execute (`prepare_execute_task` + write plan/output) → finish review JSON → `finish_task.py --enrichment`.

No fallback.
