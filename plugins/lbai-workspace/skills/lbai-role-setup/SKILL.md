---
name: lbai-role-setup
description: Initialize or update LBAI employee role memory. Use when the user asks to set up, revise, or review their role, responsibilities, boundaries, priorities, or conversation preferences in an initialized LBAI workspace.
---

# LBAI Role Setup

Route reads and writes through the registered active workspace (`lbai workspace show`). Commands work from any Codex project once `lbai init-workspace` or `lbai workspace set` has run.

1. Run `lbai doctor --json --plugin-version 1.4.23 --min-workspace-version 1.4.1`. If the workspace is invalid or incompatible, stop and show the reported next step. Never display credentials.
2. Read `AGENTS.md` and `lbai_system/runner_contracts/lbai_command_contract_v1.md` from the current workspace. The contract is the source of truth.
3. Read `lbai_system/prompts/init_enrichment_prompt_v1.md` and `lbai_system/schemas/init_enrichment_schema_v1.json`.
4. If role input is incomplete, run `lbai init --print-questions` and collect the missing answers.
5. Produce schema-valid enrichment JSON in a temporary file outside the repository.
6. Run `lbai init --enrichment <temp-json>`.
7. Report updated files, missing information, and the exact next step using the contract response format.

Do not create a business task. Do not edit company-maintained workflow files. There is no rule-based fallback.
