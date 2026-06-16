# /lbai-search-artifacts

Cursor command wrapper for the shared LBAI workflow contract.

Search query:

{{input}}

## Required behavior

Read `lbai_system/runner_contracts/lbai_command_contract_v1.md` and execute the `/lbai-search-artifacts` section.

Before returning search results:

1. Read `lbai_system/prompts/backend_search_query_plan_prompt_v1.md` and produce JSON per `lbai_system/schemas/backend_search_query_plan_schema_v1.json`.
2. Run `python3 lbai_system/tools/search_artifacts.py --enrichment <json_path>`.
3. Display the backend response directly.
4. If backend search is disabled, unavailable, times out, returns no matches, or returns invalid data, display the result or error only. Do not search local evidence, task folders, or references, and do not automatically block, mutate, advance, or finish any task flow.

If AI enrichment is unavailable, return `artifact 查询结果：BLOCKED`. Do not call the tool without `--enrichment`.

Supported runtimes: Cursor and Codex desktop app only. No rule-based fallback.

## Response format

Use the `/lbai-search-artifacts` response format from `lbai_system/runner_contracts/lbai_command_contract_v1.md`.
