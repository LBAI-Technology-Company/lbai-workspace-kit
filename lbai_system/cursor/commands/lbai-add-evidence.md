# /lbai-add-evidence

Cursor command wrapper for the shared LBAI workflow contract.

Evidence input or task folder:

{{input}}

## Required behavior

Read `lbai_system/runner_contracts/lbai_command_contract_v1.md` and execute the `/lbai-add-evidence` section.

Before calling `add_evidence.py`:

1. Read `lbai_system/prompts/evidence_enrichment_prompt_v1.md`.
2. Produce AI enrichment JSON per `lbai_system/schemas/evidence_enrichment_schema_v1.json`.
3. Call `python3 lbai_system/tools/add_evidence.py --enrichment <json_path>` with the raw evidence content.

If AI enrichment is unavailable, return `evidence_status: BLOCKED`. Do not call the tool without `--enrichment`.

Supported runtimes: Cursor and Codex desktop app only. No Codex CLI. No rule-based fallback.

## Response format

Use the `/lbai-add-evidence` response format from `lbai_system/runner_contracts/lbai_command_contract_v1.md`.
