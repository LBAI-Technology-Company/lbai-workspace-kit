---
name: lbai-finish-task
description: Finish an LBAI task and sync safe artifacts. Use when the user types /lbai-finish-task. Auto-runs retroactive intake when no task exists, and delivery when task_output.md is not ready.
---

Read `AGENTS.md` and execute `/lbai-finish-task` per `lbai_system/runner_contracts/lbai_command_contract_v1.md`. Tools: `lbai_system/tools/`.

This is the normal employee command. `/lbai-new-task` is optional.

1. `prepare_finish_task.py` — resolve task or signal `auto_intake_needed`
2. If auto-intake: task intake JSON → `new_task.py --enrichment`
3. Archive chat clarifications with `archive_input.py --resolves` when applicable
4. Run `check_task_delivery.py`; if `auto_execute_needed: true`, run `prepare_execute_task.py`, read `execute_task_plan_prompt_v1.md`, write `execution_plan.md` + `task_output.md`
5. Read `finish_review_enrichment_prompt_v1.md`, produce finish JSON, run `finish_task.py --enrichment`

No rule-based fallback.
