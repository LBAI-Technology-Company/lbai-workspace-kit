---
name: lbai-execute-task
description: Advanced/debug LBAI delivery only. Regenerate execution_plan.md and task_output.md without finishing or syncing. Employees normally use /lbai-finish-task instead.
---

# LBAI Execute Task

Route reads and writes through the registered active workspace (`lbai workspace show`). Commands work from any Codex project once `lbai init-workspace` or `lbai workspace set` has run.

**Advanced/debug only.** Daily work uses `/lbai-finish-task`, which auto-runs delivery when `task_output.md` is not ready.

1. Run `lbai doctor --json --plugin-version 1.5.4 --min-workspace-version 1.4.1`. Stop on an invalid or incompatible workspace.
2. Read the workspace `AGENTS.md`, `lbai_system/runner_contracts/lbai_command_contract_v1.md`, and `lbai_system/prompts/execute_task_plan_prompt_v1.md`.
3. Resolve the current task. If multiple candidates remain, ask the user to choose.
4. Run `lbai execute-task <task-folder>` when a folder is known. Stop if the preparation command reports blocking inputs.
5. Read the generated execution plan, task scope, task slot, role context, guardrails, and linked evidence.
6. Produce only the contracted deliverables under the selected task folder. Separate facts, assumptions, uncertainty, recommendations, and next steps.
7. Re-read the task output against completion conditions and report the exact next step (`/lbai-finish-task` when ready).

Do not work outside `task_slot.md`. Do not fabricate facts, metrics, approvals, or evidence. Do not finish or sync the task unless the user invokes `/lbai-finish-task`.
