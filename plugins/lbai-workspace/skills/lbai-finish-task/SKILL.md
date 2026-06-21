---
name: lbai-finish-task
description: Review, finish, and safely synchronize an LBAI task. Use when the user asks to close a task, validate completion, update ledgers, perform hygiene checks, or push approved task artifacts to the private Git repository.
---

# LBAI Finish Task

Route reads and writes through the registered active workspace (`lbai workspace show`). Commands work from any Codex project once `lbai init-workspace` or `lbai workspace set` has run.

1. Run `lbai doctor --json --plugin-version 1.4.17 --min-workspace-version 1.4.1`. Stop on an invalid or incompatible workspace.
2. Read the workspace `AGENTS.md`, `lbai_system/runner_contracts/lbai_command_contract_v1.md`, `lbai_system/prompts/finish_review_enrichment_prompt_v1.md`, and `lbai_system/schemas/finish_review_enrichment_schema_v1.json`.
3. Resolve the current task. If multiple candidates remain, ask the user to choose.
4. Read task scope, execution plan, output, ledgers, and linked evidence.
5. Produce schema-valid finish-review enrichment JSON in a temporary file outside the repository.
6. Run `lbai finish-task --enrichment <temp-json>` or include the selected task folder before the flag.
7. Report task status, commit readiness, review reminder, sync status, and exact next step from the command result.

Never use broad Git staging. Never sync credentials, temporary files, Prompt Lab raw runs, or artifacts outside the contract allowlist.
