---
name: lbai-search-artifacts
description: Search the backend knowledge service. Use when the user types /lbai-search-artifacts.
---

Read `AGENTS.md` and execute `/lbai-search-artifacts` per `lbai_system/runner_contracts/lbai_command_contract_v1.md`. Tools: `lbai_system/tools/`.

Read `lbai_system/prompts/backend_search_query_plan_prompt_v1.md`.

1. Produce backend query plan JSON per `lbai_system/schemas/backend_search_query_plan_schema_v1.json`.
2. Run `python3 lbai_system/tools/search_artifacts.py --enrichment <json_path>`.
3. Display the backend response directly. If backend search is disabled, unavailable, has no matches, or returns invalid data, display the result or error only.
4. Do not search local workspace artifacts and do not automatically block, mutate, advance, or finish any task flow.

No rule-based fallback.
