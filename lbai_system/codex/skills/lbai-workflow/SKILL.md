---
name: lbai-workflow
description: Use this project-level skill when the user types or refers to /lbai-role-setup, /lbai-add-evidence, /lbai-search-artifacts, /lbai-new-task, /lbai-execute-task, /lbai-finish-task, /lbai-update-kit, /lbai-self-iterate, or asks Codex to run the LBAI role workspace workflow in this repository.
---

# LBAI Workflow for Codex

This is a project-local Codex adapter. It must affect only this repository.

## First conversation bootstrap

When the user says **开始**, **怎么用**, **初始化**, or asks how LBAI works in this repo, reply with this command list and recommend `/lbai-role-setup` if role files are empty:

```text
/lbai-role-setup
/lbai-new-task
/lbai-finish-task
/lbai-add-evidence
/lbai-search-artifacts
/lbai-update-kit
/lbai-self-iterate
```

Daily task work is **finish-first**: `/lbai-finish-task` is the main command. It auto-runs retroactive intake when no task exists and auto-runs delivery when `task_output.md` is not ready. `/lbai-new-task` is optional.

Advanced/debug only: `/lbai-execute-task` regenerates deliverables without finishing or syncing.

Remind them: run these in the **Codex desktop app** with this workspace folder open—not in a bare terminal.

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
- Direct employee clarifications, preferences, and decisions can be saved as task-local context with `archive_input.py --resolves "<exact missing input>"`. Use `/lbai-add-evidence` only for source material that should be archived as reusable evidence.
- `/lbai-new-task` must separate known information by source, blocking gaps, and recommended non-blocking context before execution.
- Recommendations must be feasible under stated constraints. If feasibility is unverified, label it as an assumption and provide a validation step.

## Boundaries

- Do not install, copy, or write this skill to `~/.codex/skills/`.
- Do not make this workflow global for other Codex projects.
- Do not duplicate command logic here; the shared command contract is the source of truth.
- Do not edit `.cursor/`, `lbai_system/`, `AGENTS.md`, `README.md`, or `workspace_dashboard.html` during normal employee task work.
- `/lbai-update-kit` is the normal exception for company-maintained workflow updates.
- `/lbai-self-iterate` is the normal exception for Prompt Lab experiments. It may write under root `prompt_lab/` and isolated experiment workspaces, but must not edit formal prompts under `lbai_system/prompts/`.

## Commands

Supported employee-facing commands:

```text
/lbai-role-setup
/lbai-add-evidence
/lbai-search-artifacts
/lbai-new-task
/lbai-finish-task
/lbai-update-kit
/lbai-self-iterate
```

Daily task work: `/lbai-finish-task` (main). Optional early intake: `/lbai-new-task`. Finish auto-runs retroactive intake and delivery when needed.

Advanced/debug: `/lbai-execute-task` regenerates deliverables without sync.

Codex can execute these commands when the user types them or describes them in natural language. Use the **Codex desktop app only** (not Codex CLI).

## AI enrichment commands (no fallback)

| Command | Prompt | Tool |
|---------|--------|------|
| `/lbai-role-setup` | `init_enrichment_prompt_v1.md` | `init_lbai.py --enrichment` |
| `/lbai-add-evidence` | `evidence_enrichment_prompt_v1.md` | `add_evidence.py --enrichment` |
| `/lbai-search-artifacts` | `backend_search_query_plan_prompt_v1.md` | backend search query plan via `search_artifacts.py --enrichment`; backend-only, display-only when backend is unavailable or has no matches |
| `/lbai-new-task` | `task_intake_enrichment_prompt_v1.md` | `new_task.py --enrichment` |
| `/lbai-finish-task` | `execute_task_plan_prompt_v1.md` + `finish_review_enrichment_prompt_v1.md` | auto-execute when needed, then `finish_task.py --enrichment` |
| `/lbai-execute-task` | `execute_task_plan_prompt_v1.md` | write `execution_plan.md` + `task_output.md` (advanced/debug) |
| `/lbai-self-iterate` | Prompt Lab generated scenarios/evaluations | `prompt_lab/prompt_lab.py` |

`/lbai-update-kit` remains code-only via `update_kit.py`.
