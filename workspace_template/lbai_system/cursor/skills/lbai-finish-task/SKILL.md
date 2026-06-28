# LBAI Finish Task Skill

Read `lbai_system/runner_contracts/lbai_command_contract_v1.md`, `lbai_system/prompts/task_intake_enrichment_prompt_v1.md`, `lbai_system/prompts/execute_task_plan_prompt_v1.md`, and `lbai_system/prompts/finish_review_enrichment_prompt_v1.md`.

Normal employee command. Auto-runs retroactive intake when no task exists; auto-runs delivery when `task_output.md` is not ready:

`prepare_finish_task.py` → optional auto-intake (`new_task.py`) → `archive_input` (if needed) → `check_task_delivery.py` → optional auto-execute → finish review JSON → `finish_task.py --enrichment`.

No fallback.
