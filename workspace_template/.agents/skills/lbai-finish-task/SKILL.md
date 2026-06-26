---
name: lbai-finish-task
description: Finish an LBAI task and sync safe artifacts. Use when the user types /lbai-finish-task. Auto-runs delivery when task_output.md is not ready.
---

Read `AGENTS.md` and execute `/lbai-finish-task` per `lbai_system/runner_contracts/lbai_command_contract_v1.md`. Tools: `lbai_system/tools/`.

This is the normal employee end command. It auto-runs delivery (same as `/lbai-execute-task`) when needed.

1. Resolve task folder if needed
2. Archive chat clarifications with `archive_input.py --resolves` when applicable
3. Run `check_task_delivery.py`; if `auto_execute_needed: true`, run `prepare_execute_task.py`, read `execute_task_plan_prompt_v1.md`, write `execution_plan.md` + `task_output.md`
4. Read `finish_review_enrichment_prompt_v1.md`, produce finish JSON, run `finish_task.py --enrichment`

No rule-based fallback.
