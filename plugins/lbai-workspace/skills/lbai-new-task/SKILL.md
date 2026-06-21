---
name: lbai-new-task
description: Create a formal evidence-aware LBAI task. Use when the user explicitly asks to start, register, or formalize work that needs scoped deliverables, missing-input tracking, review handling, and an auditable task folder.
---

# LBAI New Task

Route reads and writes through the registered active workspace (`lbai workspace show`). Commands work from any Codex project once `lbai init-workspace` or `lbai workspace set` has run.

1. Run `lbai doctor --json --plugin-version 1.4.15 --min-workspace-version 1.4.1`. Stop on an invalid or incompatible workspace.
2. Read the workspace `AGENTS.md` and `lbai_system/runner_contracts/lbai_command_contract_v1.md`.
3. Read role context plus `lbai_system/prompts/task_intake_enrichment_prompt_v1.md` and `lbai_system/schemas/task_intake_enrichment_schema_v1.json`.
4. Use one clear task from the conversation. If intent is ambiguous, ask for one concise task description.
5. Search company artifacts first when the task depends on company knowledge; absence of search results does not itself block task creation.
6. Produce schema-valid intake enrichment JSON in a temporary file outside the repository.
7. Run `lbai new-task --enrichment <temp-json> <task-description>`.
8. Report the created task folder, state, missing inputs, review reminder, and exact next step using the contract response format.

Do not invent source facts. Do not convert ordinary conversation or saved evidence into a formal task without explicit task intent.
