# LBAI Role Workspace Agent Instructions

This repo is an LBAI enterprise role workspace for employee office work.

## Command quick reference (run in Cursor or Codex desktop app)

| Command | When to use |
|---------|-------------|
| `/lbai-role-setup` | First-time role setup or role updates (Codex: **LBAI Role Setup**) |
| `/lbai-new-task` | Start a formal task |
| `/lbai-add-evidence` | Capture meeting notes, feedback, or source material |
| `/lbai-search-artifacts` | Find prior tasks, evidence, or references |
| `/lbai-finish-task` | Deliver (when needed), review, hygiene-check, and sync to GitHub |
| `/lbai-execute-task` | **Advanced:** regenerate deliverables without finishing or syncing |
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
/lbai-finish-task
/lbai-add-evidence
/lbai-search-artifacts
/lbai-update-kit
/lbai-self-iterate
```

The normal task lifecycle is **finish-first**: employees mainly run `/lbai-finish-task`, which auto-runs retroactive intake when no task exists and auto-runs delivery when `task_output.md` is not ready. `/lbai-new-task` is optional for early formal intake. Keep `/lbai-execute-task` for debugging or regenerating deliverables without sync.

Arguments are optional when the current task is unambiguous. If ambiguous, ask the employee to choose from candidate task folders. `/lbai-add-evidence` saves source material or reference knowledge and must not automatically create a task. `/lbai-search-artifacts` searches prior evidence, references, and task outputs without changing task state.

## Codex project adapter

When this repository is opened in Codex, the same employee-facing commands are supported as project-local workflow commands. If the user types or refers to `/lbai-role-setup`, `/lbai-add-evidence`, `/lbai-search-artifacts`, `/lbai-new-task`, `/lbai-execute-task`, `/lbai-finish-task`, `/lbai-update-kit`, or `/lbai-self-iterate`, read:

- `lbai_system/codex/skills/lbai-workflow/SKILL.md`
- `lbai_system/runner_contracts/lbai_command_contract_v1.md`

This Codex adapter is project-local. Thin project-local command adapter files may live under `.agents/skills/`, but current Codex usage should still rely on `/lbai-*` commands and the `lbai_system/codex/skills/lbai-workflow/SKILL.md` project adapter. The `.agents/skills/` files must point back to `lbai_system/runner_contracts/lbai_command_contract_v1.md` and must not duplicate command logic. Do not install, copy, or write these skills to `~/.codex/skills/`, and do not make them affect other Codex projects. The shared command contract is the source of truth for command behavior; Cursor and Codex adapters should stay thin.

The optional enterprise Codex plugin `lbai-workspace` exposes the same workflows through eight command-palette entries: **LBAI Role Setup**, **LBAI New Task**, **LBAI Add Evidence**, **LBAI Search Artifacts**, **LBAI Execute Task**, **LBAI Finish Task**, **LBAI Update Kit**, and **LBAI Self Iterate**. You can also reference skills as `$lbai-role-setup`, `$lbai-new-task`, `$lbai-self-iterate`, and so on. See `docs/CODEX_PLUGIN_INTERNAL_MARKETPLACE.md` for the full mapping to `/lbai-*` Cursor commands. After `lbai bind-github` or `lbai workspace set`, commands route to the registered active workspace in `~/.lbai/config.json`, so they work from any Codex project while task and evidence data stay in one unified workspace.

## Cursor MCP adapter

The LBAI MCP server (`cursor_plugin/mcp_server.py`) exposes the same eight workflows plus a health-check tool as MCP tools. The installer registers it globally in `~/.cursor/mcp.json` so that `lbai_*` tools are available in any Cursor project without per-project configuration.

When a Cursor agent invokes an `lbai_*` tool, the MCP server shells out to the `lbai` CLI subcommand. The CLI resolves the active workspace from `~/.lbai/config.json` and routes reads/writes there — mirroring how Codex plugin commands route to the same registered workspace. Each MCP tool is a thin wrapper; the shared command contract (`lbai_system/runner_contracts/lbai_command_contract_v1.md`) remains the single source of truth for command behavior.

The MCP server does not bundle or cache enrichment prompts, schemas, role memory, credentials, or workspace templates. Tools that require AI enrichment accept an `enrichment_json` argument; the Cursor agent generates it from the matching `lbai_system/schemas/*_schema_v1.json` before invocation, following the same contract as Codex skills.

- Global registration: `~/.cursor/mcp.json` → `mcpServers.lbai-workspace` with the venv Python and `cursor_plugin/mcp_server.py` as entrypoint.
- Health check: `lbai doctor --json` includes a `cursor_mcp` check (advisory, non-blocking).
- Manual reference: `docs/CURSOR_MCP_SETUP.md`.
- Entrypoints:
  - `lbai_role_setup`, `lbai_new_task`, `lbai_add_evidence`, `lbai_search_artifacts`, `lbai_execute_task`, `lbai_finish_task`, `lbai_update_kit`, `lbai_self_iterate`, `lbai_doctor`.

Project-local Cursor commands (`.cursor/commands/lbai-*.md`) remain available as a fallback when the workspace folder is opened directly in Cursor.

For first-time setup or later role changes, employees may use:

```text
/lbai-role-setup
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
- `role_workspace/knowledge/index.md`
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

`/lbai-update-kit` updates company-maintained workflow files **locally only**. Template paths (`lbai_system/`, `.cursor/`, etc.) are in `.gitignore` and are not synced to GitHub. Legacy repos may receive a one-time cleanup commit to stop tracking template files that were committed before this policy.
