# LBAI Workspace Kit

**Help capable AI models work inside company rules, evidence boundaries, task lifecycle, and delivery standards.**

This repository is the public distribution kit for LBAI employee AI workspaces. It packages:

- a local `lbai` command-line tool
- a reusable employee workspace template
- Codex and Cursor project adapters
- workflow scripts for evidence, task records, checks, and updates

For the full Chinese guide, see [README.zh-CN.md](README.zh-CN.md).

## What This Project Does

LBAI Workspace Kit replaces manual folder copying with a repeatable install and initialization flow:

```text
install lbai -> authenticate GitHub -> initialize a private workspace repo -> use /lbai-* in Codex or Cursor
```

Employees get a private GitHub workspace that contains the same workflow rules, command entry points, ledgers, and quality checks. The public kit remains the source for upgrades, while employee-owned work stays in the private workspace.

## Repository Layout

```text
lbai-workspace-kit/
├── install.sh              macOS / Linux installer entry
├── install.ps1             Windows installer entry
├── lbai_core/              Python CLI and workspace orchestration
├── workspace_template/     Files copied into employee private repos
├── docs/                   Architecture, install flow, token policy, roadmap
├── VERSION                 Kit version
├── README.md               English overview
└── README.zh-CN.md         Chinese guide and tutorial
```

The project intentionally starts as one public repository. Installer, CLI core, and workspace template share one version so releases are easy to reason about.

## Current Scope

Stage 1 provides the core installer and workspace bootstrap flow.

Terminal commands:

```bash
lbai auth login
lbai auth backend-login
lbai auth doctor
lbai init-workspace
lbai doctor
lbai update-kit
lbai remove-kit
lbai uninstall
lbai serve-dashboard
```

AI desktop workflow commands:

```text
/lbai-init
/lbai-add-evidence
/lbai-new-task
/lbai-search-artifacts
/lbai-execute-task
/lbai-finish-task
/lbai-update-kit
/lbai-self-iterate
```

These employee workflow commands are available through Cursor and the Codex desktop app project adapters. AI enrichment is required where listed below; terminal-only workflow commands such as bare `lbai add-evidence` or `lbai new-task` are intentionally blocked without enrichment.

Not in scope yet:

- Codex marketplace plugin distribution
- Cursor or VS Code extension distribution
- GitHub Enterprise-specific setup
- custom company install domain
- standalone LLM runtime

## System Requirements

Supported platforms: **macOS** and **Windows**.

| Dependency | Notes |
|------------|-------|
| Git | Checked by the installer; auto-installed when possible |
| Python 3.10+ | Checked by the installer; auto-installed when possible |
| Network | Access to GitHub or install mirrors |

After install, the CLI lives at `~/.lbai/bin/lbai` on macOS/Linux and `%USERPROFILE%\.lbai\bin\lbai.cmd` on Windows.

## Install

Recommended release install. The installer checks for Git and Python 3.10+ and attempts to install them when missing.

macOS / Linux:

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/LBAI-Technology-Company/lbai-workspace-kit@latest/install.sh | sh
source ~/.zshrc
lbai auth login
lbai auth backend-login
lbai init-workspace
```

Windows (PowerShell):

```powershell
irm https://cdn.jsdelivr.net/gh/LBAI-Technology-Company/lbai-workspace-kit@latest/install.ps1 | iex
```

Close and reopen PowerShell after install, then run:

```powershell
lbai auth login
lbai auth backend-login
lbai init-workspace
```

The install command uses `@latest` (always the newest GitHub Release, not the main development branch). The installer also resolves the latest release package at runtime and prints the installed version when finished, for example:

```text
Installed version: <version>
Release: v<version>
```

If Git or Python installation opens a system dialog, complete it and rerun the same install command.

The installer places the kit under:

```text
~/.lbai/kit
```

and creates the command wrapper at:

```text
~/.lbai/bin/lbai
```

The installer also adds `~/.lbai/bin` to your shell PATH when possible.

Local development install from this checkout:

```bash
./install.sh
```

Verify:

```bash
lbai --version
lbai --help
```

## GitHub Authentication

Use authentication as a separate step:

```bash
lbai auth login
lbai auth backend-login
lbai auth doctor
```

`lbai auth login` behavior:

- First run: paste a GitHub token when prompted
- Token already saved: press Enter to keep the existing token
- Already authenticated through `gh auth login`: press Enter to continue without changes

Do not pass tokens in command arguments. Avoid commands like:

```bash
lbai init-workspace --github-token ghp_xxx
```

Authentication source priority:

```text
saved token at ~/.lbai/auth/github_token
-> GITHUB_TOKEN / GH_TOKEN environment variables
-> GitHub CLI (gh auth login)
```

Backend knowledge search uses a separate local API key:

```bash
lbai auth backend-login
```

That key is stored at `~/.lbai/auth/knowledge_service.json` with user-only file permissions. It is not written into the workspace repository, `.lbai/workspace.json`, `role_workspace/`, or `tasks/`, and `lbai update-kit` does not remove it.

The saved token file is restricted to the current user. The token needs permission to clone, commit, and push to the employee private workspace repository.

## Initialize An Employee Workspace

Use an existing private GitHub repository for the employee workspace.

Interactive:

```bash
lbai init-workspace
```

On macOS and Windows, `lbai init-workspace` opens a folder picker after you enter the repo URL. Cancel the picker to use the default path `./<repo-name>` in the current directory.

Non-interactive:

```bash
lbai init-workspace \
  --repo-url https://github.com/LBAI-Technology-Company/lbai-workspace-zhangsan.git \
  --path ~/LBAI/lbai-workspace-zhangsan
```

Initialization will:

1. clone the private repository if the local path is empty
2. copy `workspace_template/` into the repository
3. preserve employee-owned default folders such as `role_workspace/` and `tasks/`
4. write `.lbai/workspace.json` with kit version, employee identity defaults, and optional backend knowledge service configuration
5. stage the generated workspace files
6. commit with `chore(lbai): initialize workspace kit`
7. push to the private repository
8. run `lbai doctor`

Useful options:

```bash
lbai init-workspace --no-commit
lbai init-workspace --no-push
```

Use `--no-commit` for local inspection before committing. Use `--no-push` when you want to commit locally but push later.

### Open The Correct Cursor Workspace Folder

`lbai init-workspace` creates a child folder named after the repository under the current directory or the folder you pick. For example, if you run init from `~/projects/my-folder` for repo `lbai-workspace-zhangsan`, the actual workspace is:

```text
~/projects/my-folder/lbai-workspace-zhangsan/   <- open this
├── .cursor/commands/                           <- /lbai-* commands live here
├── lbai_system/
└── role_workspace/
```

Cursor slash commands are loaded only from `.cursor/commands/` at the workspace root. If you open the outer parent folder instead, typing `/lbai` will show nothing.

After init, the CLI prints `cursor_open: <path>`. Open that folder in Cursor (`File -> Open Folder` or `cursor <path>`), then run `/lbai-init`.

To place the workspace at an exact path without an extra nested folder, pass `--path` explicitly:

```bash
lbai init-workspace --path ~/LBAI/lbai-workspace-zhangsan
```

## Daily Workspace Usage

Run these commands inside an initialized LBAI workspace.

**Use `/lbai-*` in Cursor or the Codex desktop app for employee workflows.** Terminal `lbai new-task` and similar commands fail without AI enrichment JSON.

### Unified pattern: AI enrichment + code capture

| Command | AI prompt | Code tool |
|---------|-----------|-----------|
| `/lbai-init` | `init_enrichment_prompt_v1.md` | `init_lbai.py --enrichment` |
| `/lbai-add-evidence` | `evidence_enrichment_prompt_v1.md` | `add_evidence.py --enrichment` |
| `/lbai-search-artifacts` | `backend_search_query_plan_prompt_v1.md` | `search_artifacts.py --enrichment` (backend only) |
| `/lbai-new-task` | `task_intake_enrichment_prompt_v1.md` | `new_task.py --enrichment` |
| `/lbai-execute-task` | `execute_task_plan_prompt_v1.md` | Agent writes `execution_plan.md` + `task_output.md` |
| `/lbai-finish-task` | `finish_review_enrichment_prompt_v1.md` | `finish_task.py --enrichment` |
| `/lbai-update-kit` | none | `update_kit.py` (code only) |
| `/lbai-self-iterate` | runtime AI JSON (real task context first, mock fallback) | `prompt_lab.py` (experimental prompts + admin handoff report only) |

Commands that require a prebuilt enrichment JSON file → **BLOCKED** without it. `/lbai-self-iterate` and `/lbai-update-kit` are exceptions: Prompt Lab JSON is produced at runtime by the current AI, and update-kit is code-only.

`/lbai-self-iterate` defaults to `context_mode=auto`: it uses real task context when task records exist, and falls back to mock office scenarios when no task context is available. It writes administrator-facing summaries to `prompt_lab/admin_feedback/outbox/<run_id>/<round>/`, including clear problems, the optimization plan, optimized effect, score, changed prompt files, and artifact references. Send the handoff package only when `handoff_status=READY`; if it says `BLOCKED_REDACTION_REQUIRED`, redact and rerun before sending. Do not commit or push raw `prompt_lab/runs/` data.

Initialize role context:

```text
/lbai-init
```

`/lbai-init` captures the employee user name, position, and conversation preference in `ROLE_PROFILE_v1.json`.

`.lbai/workspace.json` stores technical identity and non-secret backend settings, including `employee_user_id`, optional display/email/department fields, `workspace_repo_id`, and `knowledge_service` configuration. The backend API key is stored locally under `~/.lbai/auth/knowledge_service.json`, not in the workspace repo. `ROLE_PROFILE_v1.json` stores role-facing profile fields for model context.

Create a formal task record:

```text
/lbai-new-task Summarize this week's customer feedback
```

`/lbai-new-task` first evaluates the task against the current conversation, role context, and relevant searchable artifacts:

- Known information is recorded with its source: conversation context, company knowledge, role context, linked evidence, external source, or assumption.
- Required gaps block execution and go to `missing_inputs.md`.
- Recommended gaps improve quality but do not block execution.
- Direct clarifications, preferences, and decisions can be supplied in chat as task-local context and used to close the matching gap. Use `/lbai-add-evidence` only for source material that should be archived as reusable evidence.

Save source material without creating a task.

Use **`/lbai-add-evidence` in Cursor or the Codex desktop app**. Do not run bare `lbai add-evidence` from the terminal without AI enrichment.

Capture is **AI enrichment + deterministic capture**. There is **no rule-based fallback**.

| Step | Owner | Action |
|------|-------|--------|
| 1 | **AI** (Cursor / Codex desktop) | Read `lbai_system/prompts/evidence_enrichment_prompt_v1.md` and produce enrichment JSON |
| 2 | **Code** | Run `add_evidence.py --enrichment <json>` for redaction, files, ledger, hygiene, and git |

AI only fills lightweight metadata such as title, source type, visibility, related tasks, and ingestion hint. It must not generate reusable facts, decisions, action items, risks, or gap analysis in the employee plugin.

Code handles redaction, folder/ledger/git/hygiene. `NEEDS_REVIEW` follows **AI enrichment only**; no keyword overlay in code.

If AI enrichment is unavailable, the workflow returns `evidence_status: BLOCKED`.

Prompt and schema:

```text
lbai_system/prompts/evidence_enrichment_prompt_v1.md
lbai_system/schemas/evidence_enrichment_schema_v1.json
```

Each evidence folder includes:

```text
raw.md
metadata.json
evidence_enrichment.json
```

`metadata.json` and `EVIDENCE_LEDGER_v1.md` include employee identity and backend ingestion status. The backend can asynchronously index pushed evidence after GitHub sync.

Evidence and tasks are independent. `/lbai-add-evidence` archives source material, does not record `related_tasks`, and does not update `missing_inputs.md`, `task_scope.md`, `task_ledger.md`, or `gap_record.md`; `/lbai-new-task` and `/lbai-execute-task` still decide locally whether required inputs are missing.

Search backend knowledge:

```text
/lbai-search-artifacts customer-feedback
```

Search calls the configured backend knowledge service and prints FOUND / NO_MATCH / ERROR status. If the backend is disabled, unavailable, or has no matches, the command displays the result only, does not scan local workspace artifacts, and does not automatically block or advance other task flows.

Prepare the selected task for model execution:

```text
/lbai-execute-task
```

Finish the selected task and run checks:

```text
/lbai-finish-task
```

Open the local dashboard:

```bash
lbai serve-dashboard
```

The same workflow is also exposed through `/lbai-*` project commands in Codex and Cursor after initialization.

## Workspace Update

If the local `lbai` command is broken or outdated, rerun the installer:

macOS / Linux:

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/LBAI-Technology-Company/lbai-workspace-kit@latest/install.sh | sh
source ~/.zshrc
```

Windows (PowerShell):

```powershell
irm https://cdn.jsdelivr.net/gh/LBAI-Technology-Company/lbai-workspace-kit@latest/install.ps1 | iex
```

Update an employee workspace template from the installed kit:

```bash
lbai update-kit
```

Useful options:

```bash
lbai update-kit --no-commit
lbai update-kit --no-push
```

Remove company-managed workflow kit files from the current workspace while keeping employee-owned `role_workspace/` and `tasks/`:

```bash
lbai remove-kit --confirm
```

Uninstall the local `lbai` command and kit without deleting employee workspaces or private GitHub repositories:

```bash
lbai uninstall
```

Delete the saved GitHub token during uninstall:

```bash
lbai uninstall --purge-auth
```

`lbai update-kit` may update managed files:

```text
AGENTS.md
README.md
.gitignore
.cursor/
.agents/
lbai_system/
workspace_dashboard.html
.lbai/workspace.json
```

It must preserve employee-owned work:

```text
role_workspace/
tasks/
```

## Doctor Checks

Run:

```bash
lbai doctor
```

The doctor checks whether the current folder is a valid LBAI workspace and verifies bootstrap files, Codex adapter files, and Cursor command files.

If checking a specific workspace:

```bash
lbai doctor --path ~/LBAI/lbai-workspace-zhangsan
```

## Development Notes

Run the CLI directly from a checkout:

```bash
PYTHONPATH=lbai_core python3 -m lbai.cli --help
```

Install from the checkout:

```bash
./install.sh
```

The root CLI forwards daily workflow commands to scripts under:

```text
workspace_template/lbai_system/tools/
```

Inside an initialized workspace, those scripts live at:

```text
lbai_system/tools/
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Install and init flow](docs/INSTALL_AND_INIT_FLOW.md)
- [GitHub token policy](docs/GITHUB_TOKEN_POLICY.md)
- [Update kit strategy](docs/UPDATE_KIT_STRATEGY.md)
- [Roadmap](docs/ROADMAP.md)

## Release Direction

Stage 1 keeps this repository as the single public distribution source. Later stages may add a Codex adapter package and a Cursor extension, but those layers should remain thin entry points over `lbai_core`.
