# /lbai-role-setup

Cursor command wrapper for the shared LBAI workflow contract (same as Codex **LBAI Role Setup**).

User input:

{{input}}

## Required behavior

Read `lbai_system/runner_contracts/lbai_command_contract_v1.md` and execute the `/lbai-init` section.

Before calling `init_lbai.py`:

1. If needed, run `python3 lbai_system/tools/init_lbai.py --print-questions` and collect answers in chat.
2. Read `lbai_system/prompts/init_enrichment_prompt_v1.md` and produce init enrichment JSON per `lbai_system/schemas/init_enrichment_schema_v1.json`.
3. Run `python3 lbai_system/tools/init_lbai.py --enrichment <json_path>`.

If AI enrichment is unavailable, return `STATUS BLOCKED`. Do not call the tool without `--enrichment`.

Supported runtimes: Cursor and Codex desktop app only. No rule-based fallback.

## Response format

Use the `/lbai-init` response format from `lbai_system/runner_contracts/lbai_command_contract_v1.md`.
