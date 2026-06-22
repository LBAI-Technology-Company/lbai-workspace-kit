---
name: lbai-add-evidence
description: Archive evidence or reusable reference material in an LBAI employee workspace. Use when the user provides meeting notes, emails, customer feedback, transcripts, research, policies, drafts, or other source material to preserve without automatically creating a task.
---

# LBAI Add Evidence

Route reads and writes through the registered active workspace (`lbai workspace show`). Commands work from any Codex project once `lbai init-workspace` or `lbai workspace set` has run.

1. Run `lbai doctor --json --plugin-version 1.4.23 --min-workspace-version 1.4.1`. Stop on an invalid or incompatible workspace and show the reported next step.
2. Read the workspace `AGENTS.md` and `lbai_system/runner_contracts/lbai_command_contract_v1.md`.
3. Read `lbai_system/prompts/evidence_enrichment_prompt_v1.md` and `lbai_system/schemas/evidence_enrichment_schema_v1.json`.
4. Ask for source content only when none was supplied. Treat the supplied content as evidence, not as a task.
5. Produce schema-valid enrichment JSON in a temporary file outside the repository.
6. Run `lbai add-evidence --enrichment <temp-json> --content <raw-content>`.
7. Report local capture, review status, redaction status, and sync status exactly as required by the contract.

Never call the command without enrichment. Do not link or modify tasks. Never expose GitHub or backend credentials.
