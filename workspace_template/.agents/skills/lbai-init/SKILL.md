---
name: lbai-init
description: Initialize or update employee role memory in role_workspace/. Use when the user types /lbai-init.
---

Read `AGENTS.md` and execute `/lbai-init` per `lbai_system/runner_contracts/lbai_command_contract_v1.md`. Tools: `lbai_system/tools/`.

Read `lbai_system/prompts/init_enrichment_prompt_v1.md`.

1. Collect answers (use `--print-questions` if needed)
2. Produce init enrichment JSON per `lbai_system/schemas/init_enrichment_schema_v1.json`
3. Run `python3 lbai_system/tools/init_lbai.py --enrichment <json_path>`

No rule-based fallback.
