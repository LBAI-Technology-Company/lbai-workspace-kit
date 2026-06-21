---
name: lbai-execute-task
description: Execute the current formal LBAI task contract and produce its deliverables. Use when the user asks to continue or complete an existing task after intake and required inputs are ready.
---

# LBAI Execute Task

Route reads and writes through the registered active workspace (`lbai workspace show`). Commands work from any Codex project once `lbai init-workspace` or `lbai workspace set` has run.

1. Run `lbai doctor --json --plugin-version 1.4.18 --min-workspace-version 1.4.1`. Stop on an invalid or incompatible workspace.
2. Read the workspace `AGENTS.md`, `lbai_system/runner_contracts/lbai_command_contract_v1.md`, and `lbai_system/prompts/execute_task_plan_prompt_v1.md`.
3. Resolve the current task from the conversation or run `lbai execute-task`. If multiple candidates remain, ask the user to choose a task folder.
4. Run `lbai execute-task <task-folder>` when a folder is known. Stop if the preparation command reports blocking inputs.
5. Read the generated execution plan, task scope, task slot, role context, guardrails, and linked evidence.
6. Produce only the contracted deliverables under the selected task folder. Separate facts, assumptions, uncertainty, recommendations, and next steps.
7. Re-read the task output against completion conditions and report the exact next step.

Do not work outside `task_slot.md`. Do not fabricate facts, metrics, approvals, or evidence. Do not finish or sync the task unless the user invokes the finish workflow.
