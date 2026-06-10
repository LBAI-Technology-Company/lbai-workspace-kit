---
name: lbai-add-evidence
description: Save evidence or reference material into role_workspace/knowledge/evidence/. Use when the user types /lbai-add-evidence or pastes source material to archive without creating a task.
---

Read `AGENTS.md` and execute `/lbai-add-evidence` from `lbai_system/runner_contracts/lbai_command_contract_v1.md`.

## Required AI-first flow

1. Read `lbai_system/prompts/evidence_enrichment_prompt_v1.md`.
2. Follow the system prompt and user message template to produce enrichment JSON matching `lbai_system/schemas/evidence_enrichment_schema_v1.json`.
3. Write enrichment to a temp JSON file.
4. Run `python3 lbai_system/tools/add_evidence.py --enrichment <json_path> ...` with the raw evidence content.
5. If AI enrichment cannot be produced, return `evidence_status: BLOCKED`. Do **not** call `add_evidence.py` without `--enrichment`. There is **no fallback**.

Supported runtimes: **Cursor** and **Codex desktop app** only. Do not use Codex CLI.

Do not duplicate command logic here.
