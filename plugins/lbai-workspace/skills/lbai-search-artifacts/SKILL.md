---
name: lbai-search-artifacts
description: Search the configured LBAI backend knowledge service for approved company evidence. Use when the user asks to find prior decisions, historical evidence, company references, or source material before creating or executing work.
---

# LBAI Search Artifacts

Route reads and writes through the registered active workspace (`lbai workspace show`). Commands work from any Codex project once `lbai init-workspace` or `lbai workspace set` has run.

1. Run `lbai doctor --json --plugin-version 1.4.17 --min-workspace-version 1.4.1 --require-backend`. If backend authentication is missing, stop and direct the user to `lbai auth backend-login`.
2. Read the workspace `AGENTS.md` and `lbai_system/runner_contracts/lbai_command_contract_v1.md`.
3. Read `lbai_system/prompts/backend_search_query_plan_prompt_v1.md` and `lbai_system/schemas/backend_search_query_plan_schema_v1.json`.
4. Ask for search intent only when it is not inferable from the conversation.
5. Produce schema-valid query-plan JSON in a temporary file outside the repository.
6. Run `lbai search-artifacts --enrichment <temp-json>`.
7. Display the backend result without changing task or workspace state.

Do not scan local evidence, task, or reference folders. Do not invent a fallback result. Backend errors and no-match responses are display-only.
