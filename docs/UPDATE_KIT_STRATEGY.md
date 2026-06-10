# Update Kit Strategy

## Two Upgrade Layers

There are two different upgrade operations.

## 1. CLI/Core Upgrade

Repair or upgrade the installed `lbai` command by rerunning the release installer:

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/LBAI-Technology-Company/lbai-workspace-kit@v0.1.5/install.sh | sh
```

There is no separate `lbai self-update` command.

## 2. Workspace Template Upgrade

Upgrade the current employee workspace:

```bash
lbai update-kit
```

Inside Codex or Cursor, `/lbai-update-kit` should call the same operation.

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
5. Preserve employee-owned role and task artifacts.
6. Run hygiene checks.
7. Stage only managed paths.
8. Commit the update.
9. Push to the existing private repo.
```

Recommended commit message:

```text
chore(lbai): update workflow kit to <version>
```

## Version Metadata

Each initialized workspace should include a local metadata file such as:

```text
.lbai/workspace.json
```

Example:

```json
{
  "workspaceKitVersion": "0.1.0",
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
