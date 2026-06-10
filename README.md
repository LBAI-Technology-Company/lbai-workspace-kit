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
├── install.sh              Installer for the local lbai command
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

Supported commands:

```bash
lbai auth login
lbai auth doctor
lbai init-workspace
lbai doctor
lbai update-kit
lbai remove-kit
lbai uninstall
lbai init
lbai new-task
lbai add-evidence
lbai search-artifacts
lbai execute-task
lbai finish-task
lbai serve-dashboard
```

Not in scope yet:

- Codex marketplace plugin distribution
- Cursor or VS Code extension distribution
- GitHub Enterprise-specific setup
- custom company install domain
- standalone LLM runtime

## Install

Recommended release install:

```bash
curl -fsSL https://raw.githubusercontent.com/LBAI-Technology-Company/lbai-workspace-kit/v0.1.0/install.sh | sh
```

The installer places the kit under:

```text
~/.lbai/kit
```

and creates the command wrapper at:

```text
~/.lbai/bin/lbai
```

Add it to your shell PATH if needed:

```bash
export PATH="$HOME/.lbai/bin:$PATH"
```

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
lbai auth doctor
```

Do not pass tokens in command arguments. Avoid commands like:

```bash
lbai init-workspace --github-token ghp_xxx
```

The current CLI stores the token outside any workspace at:

```text
~/.lbai/auth/github_token
```

The file is restricted to the current user. Future versions can prefer OS keychains or GitHub CLI credentials.

The token needs permission to clone, commit, and push to the employee private workspace repository.

## Initialize An Employee Workspace

Use an existing private GitHub repository for the employee workspace.

Interactive:

```bash
lbai init-workspace
```

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
4. write `.lbai/workspace.json`
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

## Daily Workspace Usage

Run these commands inside an initialized LBAI workspace.

Initialize role context:

```bash
lbai init
```

Save source material without creating a task:

```bash
lbai add-evidence --kind meeting --content "meeting notes..."
```

Search prior evidence, task outputs, and references:

```bash
lbai search-artifacts customer-feedback --limit 5
```

Create a formal task record:

```bash
lbai new-task "Summarize this week's customer feedback"
```

Prepare the selected task for model execution:

```bash
lbai execute-task
```

Finish the selected task and run checks:

```bash
lbai finish-task
```

Open the local dashboard:

```bash
lbai serve-dashboard
```

The same workflow is also exposed through `/lbai-*` project commands in Codex and Cursor after initialization.

## Workspace Update

If the local `lbai` command is broken or outdated, rerun the installer:

```bash
curl -fsSL https://raw.githubusercontent.com/LBAI-Technology-Company/lbai-workspace-kit/v0.1.0/install.sh | sh
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
