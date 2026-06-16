---
name: lbai-add-evidence
description: Save evidence or reference material into the LBAI role workspace by following the shared LBAI command contract.
---

# LBAI Add Evidence Skill

This Cursor skill is a thin adapter.

Read `lbai_system/runner_contracts/lbai_command_contract_v1.md` and follow the `/lbai-add-evidence` section.

## AI enrichment (required)

1. Read `lbai_system/prompts/evidence_enrichment_prompt_v1.md`.
2. Produce JSON matching `lbai_system/schemas/evidence_enrichment_schema_v1.json`.
3. Run `python3 lbai_system/tools/add_evidence.py --enrichment <json_path>` with the employee's raw evidence content.
4. If enrichment cannot be produced, fail with `evidence_status: BLOCKED`. No rule-based fallback.

Do not duplicate command logic here.
