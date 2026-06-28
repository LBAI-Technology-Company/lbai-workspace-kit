---
name: lbai-finish-task
description: Deliver (when needed), review, finish, and safely synchronize an LBAI task. Normal employee command; auto-runs retroactive intake when no task exists and delivery when task_output.md is not ready.
---

# LBAI Finish Task

Route reads and writes through the registered active workspace (`lbai workspace show`). Commands work from any Codex project once `lbai init-workspace` or `lbai workspace set` has run.

1. Run `lbai doctor --json --plugin-version 1.5.6 --min-workspace-version 1.4.1`. Stop on an invalid or incompatible workspace.
2. Read the workspace `AGENTS.md`, `lbai_system/runner_contracts/lbai_command_contract_v1.md`, `lbai_system/prompts/task_intake_enrichment_prompt_v1.md`, `lbai_system/prompts/execute_task_plan_prompt_v1.md`, `lbai_system/prompts/finish_review_enrichment_prompt_v1.md`, and related schemas.
3. Run `prepare_finish_task.py`. If `auto_intake_needed: true`, produce task intake JSON and run `new_task.py --enrichment` before continuing.
4. Archive chat clarifications with `archive_input.py --resolves` when applicable.
5. Run `check_task_delivery.py`. If `auto_execute_needed: true`, run `prepare_execute_task.py` and write `execution_plan.md` + `task_output.md` before finish review.
6. Read task scope, execution plan, output, ledgers, and linked evidence.
7. Produce schema-valid finish-review enrichment JSON in a temporary file outside the repository.
8. Run `lbai finish-task --enrichment <temp-json>` or include the selected task folder before the flag.
9. Report `auto_intake`, `auto_execute`, task status, commit readiness, review reminder, sync status, and exact next step from the command result.

Never use broad Git staging. Never sync credentials, temporary files, Prompt Lab raw runs, or artifacts outside the contract allowlist.
