# LBAI Role Workspace Agent Instructions

This repo is an LBAI enterprise role workspace for employee office work.

## Command quick reference (run in Cursor or Codex desktop app)

| Command | When to use |
|---------|-------------|
| `/lbai-init` | First-time role setup or role updates |
| `/lbai-new-task` | Start a formal task |
| `/lbai-add-evidence` | Capture meeting notes, feedback, or source material |
| `/lbai-search-artifacts` | Find prior tasks, evidence, or references |
| `/lbai-execute-task` | Execute the current task and write deliverables |
| `/lbai-finish-task` | Finish, hygiene-check, and sync to GitHub |
| `/lbai-update-kit` | Update company-maintained workflow files |
| `/lbai-self-iterate` | Run Prompt Lab self-iteration experiments for prompt improvement |

Do **not** run `lbai new-task` / `lbai add-evidence` in a bare terminal without `--enrichment`; use the `/lbai-*` commands above instead.

## Workspace structure

- `.cursor/` contains Cursor project command entries and project rules.
- `.agents/` contains project-local agent adapter files for LBAI commands when a runtime supports project-scoped skill discovery. These files are thin adapters that point back to the shared command contract; the stable employee command surface remains `/lbai-*`.
- `lbai_system/` is the company-maintained workflow machine: Cursor/Codex adapters, rules, skills, commands, tools, templates, and docs. Do not modify during normal task work.
- `lbai_system/templates/role_workspace/` contains company-maintained default role-memory templates for new or missing role files.
- `role_workspace/` is the employee's role memory: world model, role boundary, ledgers, and archive.
- `tasks/` contains the employee's daily task artifacts. Employees mainly inspect this folder.
- `prompt_lab/` contains Prompt Lab experiment records and experimental prompt versions. It is separate from employee task artifacts.

## Enterprise work standard

When discussing, planning, executing, or finishing work:

- Treat outputs as internal company work products, not casual chat.
- Be objective, evidence-seeking, concise, and role-aware.
- Do not flatter, appease, or simply confirm the employee's first framing.
- Use first-principles reasoning to identify the actual problem, constraints, desired outcome, and tradeoffs.
- Separate facts, assumptions, uncertainty, recommendations, and next steps.
- Do not invent data, sources, success metrics, customer evidence, product capabilities, pricing, legal positions, approvals, or company commitments.
- Any metric, benchmark, case result, market claim, performance claim, or customer claim must trace to task inputs, approved sources, or explicitly cited external sources when browsing is allowed.
- If needed inputs are missing, state the exact missing materials, background, decisions, or source documents.
- Recommendations must be feasible under stated constraints. If feasibility is unverified, label it as an assumption and provide a validation step.

## Employee-facing commands

For regular work and workflow updates, employees only need to know:

```text
/lbai-new-task
/lbai-add-evidence
/lbai-search-artifacts
/lbai-execute-task
/lbai-finish-task
/lbai-update-kit
/lbai-self-iterate
```

The three task lifecycle commands are `/lbai-new-task`, `/lbai-execute-task`, and `/lbai-finish-task`; they may be used without arguments when the current task is unambiguous. If ambiguous, ask the employee to choose from candidate task folders. `/lbai-add-evidence` saves source material or reference knowledge and must not automatically create a task. `/lbai-search-artifacts` searches prior evidence, references, and task outputs without changing task state.

## Codex project adapter

When this repository is opened in Codex, the same employee-facing commands are supported as project-local workflow commands. If the user types or refers to `/lbai-init`, `/lbai-add-evidence`, `/lbai-search-artifacts`, `/lbai-new-task`, `/lbai-execute-task`, `/lbai-finish-task`, `/lbai-update-kit`, or `/lbai-self-iterate`, read:

- `lbai_system/codex/skills/lbai-workflow/SKILL.md`
- `lbai_system/runner_contracts/lbai_command_contract_v1.md`

This Codex adapter is project-local. Thin project-local command adapter files may live under `.agents/skills/`, but current Codex usage should still rely on `/lbai-*` commands and the `lbai_system/codex/skills/lbai-workflow/SKILL.md` project adapter. The `.agents/skills/` files must point back to `lbai_system/runner_contracts/lbai_command_contract_v1.md` and must not duplicate command logic. Do not install, copy, or write these skills to `~/.codex/skills/`, and do not make them affect other Codex projects. The shared command contract is the source of truth for command behavior; Cursor and Codex adapters should stay thin.

The optional enterprise Codex plugin `lbai-workspace` exposes the same workflows as namespaced plugin Skills, for example `$lbai-workspace:lbai-init`. Project-local `$lbai-*` or `/lbai-*` compatibility entry points remain available. In every case, read the workspace copy of the shared command contract and use the installed `lbai` CLI for preflight and command execution. The plugin must not contain employee role memory, task artifacts, workspace credentials, or a duplicate workspace template.

For first-time setup or later role changes, employees may use:

```text
/lbai-init
```

This command updates only `role_workspace/` role memory files and should not create a business task folder.

For company workflow template updates, employees may use:

```text
/lbai-update-kit
```

This command updates only company-maintained workflow files, including `lbai_system/templates/role_workspace/`, and must not modify employee-owned `role_workspace/` or `tasks/`.

For Prompt Lab prompt experiments, employees may use:

```text
/lbai-self-iterate
```

This command writes under root `prompt_lab/` and isolated experiment workspaces. It must not modify employee-owned `role_workspace/`, `tasks/`, or formal prompts under `lbai_system/prompts/`.

## Default behavior

During task discussion, planning, execution, and finishing, consider:

- `role_workspace/world_model/ROLE_WORLD_MODEL_v1.md`
- `role_workspace/world_model/ROLE_BOUNDARY_v1.md`
- `role_workspace/ledgers/TASK_LEDGER_v1.md`
- `role_workspace/ledgers/EVIDENCE_LEDGER_v1.md`
- `role_workspace/ledgers/BLOCKED_ITEMS_v1.md`

Formal task artifacts must be created under `tasks/`.

## System protection

Do not edit these unless the user explicitly asks to upgrade the LBAI workflow kit:

- `.cursor/`
- `.agents/`
- `lbai_system/`
- `AGENTS.md`
- `README.md`

`/lbai-update-kit` is the normal exception when the user explicitly asks to upgrade the workflow kit. It may update only the company-maintained allowlist:

- `.cursor/`
- `.agents/`
- `lbai_system/`
- `.gitignore`
- `AGENTS.md`
- `README.md`
- `workspace_dashboard.html`

Even when `lbai_system/templates/role_workspace/` changes, `/lbai-update-kit` must not overwrite existing files under root `role_workspace/`. Missing root role files may be restored from the templates during bootstrap only.

`/lbai-self-iterate` is a controlled experiment workflow. It may write under root `prompt_lab/` and isolated Prompt Lab workspaces, but it must not write normal employee task artifacts under root `tasks/` or role memory under root `role_workspace/`. Prompt Lab may update only experimental prompt copies under `prompt_lab/prompt_versions/current/`; it must not edit `lbai_system/prompts/`. Mock Prompt Lab data must stay local and must not be committed or pushed to GitHub; after approval, clean it with `prompt_lab.py finalize --run <run_dir>`.

## GitHub sync rule

`/lbai-finish-task` includes the pre-commit hygiene check and private GitHub sync.

When task status is not `BLOCKED` and commit readiness is `READY`, the workflow should automatically run safe git add, commit, and push to the current upstream.

Use this commit message format:

```bash
git commit -m "docs(lbai): finish <task_slug>"
```

After the first task push succeeds, the workflow may append a sync-status update with:

```bash
git commit -m "chore(lbai): sync-status <task_slug>"
```

Manual Git commands are fallback/debug guidance only, not the normal employee flow. Do not use broad staging for employee task sync; stage only the current task folder and `role_workspace/ledgers/TASK_LEDGER_v1.md`.

Rely on `.gitignore` plus the hygiene check to exclude secrets and temp files. Do not commit `.env`, keys, or other sensitive artifacts.

`/lbai-update-kit` automatically stages only managed workflow paths, commits with:

```bash
git commit -m "chore(lbai): update workflow kit to <version>"
```

and pushes to the current upstream when the update is safe.
