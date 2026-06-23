# LBAI Finish Task Skill

Read `lbai_system/runner_contracts/lbai_command_contract_v1.md` and `lbai_system/prompts/finish_review_enrichment_prompt_v1.md`.

Flow: read scope/output/plan + task conversation → AI finish review JSON (with employee_conversation_turns) → `finish_task.py --enrichment`. Writes `task_conversation.md` and syncs with the task folder. No fallback.
