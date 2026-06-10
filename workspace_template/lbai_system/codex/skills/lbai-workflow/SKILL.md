---
name: lbai-workflow
description: Use this project-level skill when the user types or refers to /lbai-init, /lbai-add-evidence, /lbai-search-artifacts, /lbai-new-task, /lbai-execute-task, /lbai-finish-task, /lbai-update-kit, or asks Codex to run the LBAI role workspace workflow in this repository.
---

# LBAI Workflow for Codex

This is a project-local Codex adapter. It must affect only this repository.

## Required behavior

1. Read `AGENTS.md`.
2. Read `lbai_system/runner_contracts/lbai_command_contract_v1.md`.
3. Match the user's `/lbai-*` command to the shared contract.
4. Call or follow the existing tool under `lbai_system/tools/`.
5. Keep all formal task artifacts under `tasks/`.
6. Keep employee role memory under `role_workspace/`.

## Enterprise execution standard

- Treat LBAI outputs as internal company work products, not casual chat.
- Be objective, concise, evidence-seeking, and scoped to the employee's role.
- Do not flatter, appease, or simply confirm the employee's first framing.
- Use first-principles reasoning to identify the actual problem, constraints, desired outcome, and tradeoffs.
- Separate facts, assumptions, uncertainty, recommendations, and next steps.
- Do not invent source facts, data, metrics, success stories, customer evidence, product capabilities, pricing, legal positions, approvals, or company commitments.
- Any metric, benchmark, case result, market claim, performance claim, or customer claim must trace to task inputs, approved references, or explicitly cited external sources when browsing is allowed.
- If required inputs are missing, state the exact missing materials, background, decisions, or source documents.
- Recommendations must be feasible under stated constraints. If feasibility is unverified, label it as an assumption and provide a validation step.

## Boundaries

- Do not install, copy, or write this skill to `~/.codex/skills/`.
- Do not make this workflow global for other Codex projects.
- Do not duplicate command logic here; the shared command contract is the source of truth.
- Do not edit `.cursor/`, `lbai_system/`, `AGENTS.md`, `README.md`, or `workspace_dashboard.html` during normal employee task work.
- `/lbai-update-kit` is the normal exception for company-maintained workflow updates.

## Commands

Supported employee-facing commands:

```text
/lbai-init
/lbai-add-evidence
/lbai-search-artifacts
/lbai-new-task
/lbai-execute-task
/lbai-finish-task
/lbai-update-kit
```

Codex can execute these commands when the user types them or describes them in natural language. Use the **Codex desktop app only** (not Codex CLI).

## AI enrichment commands (no fallback)

| Command | Prompt | Tool |
|---------|--------|------|
| `/lbai-init` | `init_enrichment_prompt_v1.md` | `init_lbai.py --enrichment` |
| `/lbai-add-evidence` | `evidence_enrichment_prompt_v1.md` | `add_evidence.py --enrichment` |
| `/lbai-search-artifacts` | `search_enrichment_prompt_v1.md` | `--print-catalog` then `--enrichment` |
| `/lbai-new-task` | `task_intake_enrichment_prompt_v1.md` | `new_task.py --enrichment` |
| `/lbai-execute-task` | `execute_task_plan_prompt_v1.md` | write `execution_plan.md` + `task_output.md` |
| `/lbai-finish-task` | `finish_review_enrichment_prompt_v1.md` | `finish_task.py --enrichment` |

`/lbai-update-kit` remains code-only via `update_kit.py`.
