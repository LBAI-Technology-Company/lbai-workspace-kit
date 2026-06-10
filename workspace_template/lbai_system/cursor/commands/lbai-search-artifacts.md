# /lbai-search-artifacts

Cursor command wrapper for the shared LBAI workflow contract.

Search query:

{{input}}

## Required behavior

Read `lbai_system/runner_contracts/lbai_command_contract_v1.md` and execute the `/lbai-search-artifacts` section.

Before returning search results:

1. Run `python3 lbai_system/tools/search_artifacts.py --print-catalog`.
2. Read `lbai_system/prompts/search_enrichment_prompt_v1.md` and produce search enrichment JSON per `lbai_system/schemas/search_enrichment_schema_v1.json`.
3. Run `python3 lbai_system/tools/search_artifacts.py --enrichment <json_path>`.

If AI enrichment is unavailable, return `artifact 查询结果：BLOCKED`. Do not call the tool without `--enrichment`.

Supported runtimes: Cursor and Codex desktop app only. No rule-based fallback.

## Response format

Use the `/lbai-search-artifacts` response format from `lbai_system/runner_contracts/lbai_command_contract_v1.md`.
