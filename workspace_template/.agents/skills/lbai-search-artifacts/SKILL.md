---
name: lbai-search-artifacts
description: Search prior evidence and task outputs in this LBAI workspace. Use when the user types /lbai-search-artifacts.
---

Read `AGENTS.md` and execute `/lbai-search-artifacts` per `lbai_system/runner_contracts/lbai_command_contract_v1.md`. Tools: `lbai_system/tools/`.

Read `lbai_system/prompts/search_enrichment_prompt_v1.md`.

1. Run `python3 lbai_system/tools/search_artifacts.py --print-catalog`
2. Produce search enrichment JSON per `lbai_system/schemas/search_enrichment_schema_v1.json`
3. Run `python3 lbai_system/tools/search_artifacts.py --enrichment <json_path>`

No rule-based fallback.
