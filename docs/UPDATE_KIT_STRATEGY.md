# Update Kit Strategy

## Two Upgrade Layers

There are two different upgrade operations.

## 1. CLI/Core Upgrade

Repair or upgrade the installed `lbai` command by rerunning the release installer:

macOS / Linux:

```bash
curl -fsSL https://github.com/LBAI-Technology-Company/lbai-workspace-kit/releases/latest/download/install.sh | sh
source ~/.zshrc
```

Windows (PowerShell):

```powershell
irm https://github.com/LBAI-Technology-Company/lbai-workspace-kit/releases/latest/download/install.ps1 | iex
```

There is no separate `lbai self-update` command. The installer auto-detects the latest release and checks Git / Python 3.10+.

Starting with versions that include unified update support, `lbai update-kit` also attempts to update the installed CLI/core from the same release archive. This means normal employees can use one command for both workspace workflow files and the local `lbai` command. If the employee is upgrading from an older workspace whose `update_kit.py` does not yet include this logic, run `lbai update-kit` once to update the workspace tool, then run it again to update the installed CLI/core.

## 2. Workspace Template Upgrade

Upgrade the current employee workspace:

```bash
lbai update-kit
```

Inside Codex or Cursor, `/lbai-update-kit` calls the same workspace tool:

```bash
python lbai_system/tools/update_kit.py
```

The CLI command `lbai update-kit` is a thin wrapper that forwards to `lbai_system/tools/update_kit.py` in the current workspace. It fetches the latest release from GitHub and syncs managed paths only. `init-workspace` still uses the locally installed kit template for first-time setup.

By default, the same command also updates the installed CLI/core under `~/.lbai/kit` when the release source contains `lbai_core/`, but only after workspace sync and hygiene checks pass and the relevant Git step succeeds (or after `--no-commit` / `NO_CHANGES` when no push is required). Use `--skip-core-update` only for admin/debug cases where the workspace template should be updated without touching the local CLI install.

Do **not** maintain a second update implementation in `lbai_core/lbai/cli.py`.

## Managed Paths

`lbai update-kit` may update:

```text
AGENTS.md
README.md
.gitignore
.cursor/
.agents/
lbai_system/
workspace_dashboard.html
```

It must not overwrite:

```text
role_workspace/
tasks/
```

## Update Flow

```text
1. Confirm current directory is an LBAI workspace.
2. Read workspace version metadata.
3. Fetch the selected release of lbai-workspace-kit.
4. Copy only managed paths from workspace_template/.
5. Preserve employee-owned role, task, and prompt_lab artifacts.
6. Run hygiene checks.
7. Stage only managed paths.
8. Commit the update.
9. Push to the existing private repo.
10. Best-effort update the installed CLI/core from the same release archive after workspace sync and Git steps succeed (or after `--no-commit` / `NO_CHANGES` when no push is required).
```

Recommended commit message:

```text
chore(lbai): update workflow kit to <version>
```

## Version Metadata

Each initialized workspace stores the kit version in:

```text
.lbai/workspace.json
```

The version comes from the GitHub release tag of `LBAI-Technology-Company/lbai-workspace-kit` (root `VERSION` file). Do not maintain a separate `lbai_system/VERSION`.

Example:

```json
{
  "workspaceKitVersion": "1.3.1",
  "coreVersionRequired": ">=0.1.0",
  "templateSource": "LBAI-Technology-Company/lbai-workspace-kit",
  "managedPaths": [
    "AGENTS.md",
    "README.md",
    ".gitignore",
    ".cursor",
    ".agents",
    "lbai_system",
    "workspace_dashboard.html"
  ]
}
```
