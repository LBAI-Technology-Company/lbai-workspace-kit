# Install And Init Flow

## Public Install Command

Employee install commands (auto-check Git and Python 3.10+):

macOS / Linux:

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/LBAI-Technology-Company/lbai-workspace-kit@v0.1.16/install.sh | sh
source ~/.zshrc
lbai auth login
lbai init-workspace
```

Windows (PowerShell):

```powershell
irm https://cdn.jsdelivr.net/gh/LBAI-Technology-Company/lbai-workspace-kit@v0.1.16/install.ps1 | iex
```

Close and reopen PowerShell after install, then run:

```powershell
lbai auth login
lbai init-workspace
```

The installer downloads the latest release package through internal mirrors when needed. It also checks for Git and Python 3.10+ and attempts to install them when missing.

## Authentication

Do not pass tokens as command-line arguments.

Good:

```bash
lbai auth login
```

`lbai auth login` behavior:

- First run: paste a GitHub token when prompted
- Token already saved: press Enter to keep the existing token
- Already authenticated through `gh auth login`: press Enter to continue without changes

Authentication source priority:

```text
saved token at ~/.lbai/auth/github_token
-> GITHUB_TOKEN / GH_TOKEN environment variables
-> GitHub CLI (gh auth login)
```

Avoid:

```bash
lbai init-workspace --github-token ghp_xxx
```

## Existing Repo Flow

The selected MVP path is:

```text
Use an existing private GitHub repo.
```

`lbai init-workspace` should ask for the existing private repo URL, then open a folder picker on macOS and Windows. Cancel the picker to use `./<repo-name>` in the current directory.

Example interactive result:

```text
GitHub repo URL: https://github.com/LBAI-Technology-Company/lbai-workspace-zhangsan.git
Local folder path: ./lbai-workspace-zhangsan
```

Non-interactive:

```bash
lbai init-workspace \
  --repo-url https://github.com/LBAI-Technology-Company/lbai-workspace-zhangsan.git \
  --path ~/LBAI/lbai-workspace-zhangsan
```

## Init Steps

```text
1. Read GitHub authentication from `lbai auth login`, `GITHUB_TOKEN`, `GH_TOKEN`, or GitHub CLI credential state.
2. Clone the private repo into the selected local path, or use an existing local Git repo.
3. Copy files from `workspace_template/`.
4. Overwrite company-managed paths.
5. Fill missing employee default paths without overwriting existing `role_workspace/` or `tasks/` files.
6. Write workspace version metadata.
7. Stage only initialized template files.
8. Commit with a clear initialization message.
9. Push to the existing private repo unless `--no-push` is used.
10. Run `lbai doctor`.
```

Recommended initialization commit:

```text
chore(lbai): initialize workspace kit
```

## Local-Only Fallback

If GitHub authentication or repo access fails, the current CLI stops and reports the blocked reason. A later convenience feature may offer local-only initialization and a separate reconnect command.

```text
Create local workspace without GitHub sync now?
```

That reconnect command is not implemented in the current MVP.

## Open The Correct IDE Workspace Folder

`lbai init-workspace` writes the workspace into `<parent>/<repo-name>/`, not directly into the parent folder you were in when you ran the command.

Example:

```text
Current directory: ~/projects/my-folder
Repo name: lbai-workspace-zhangsan
Actual workspace: ~/projects/my-folder/lbai-workspace-zhangsan/
```

Cursor and Codex only load `/lbai-*` commands from `.cursor/commands/` at the workspace root. Opening the outer parent folder will make `/lbai` appear empty even though initialization succeeded.

After init, use the printed `cursor_open:` path. To avoid the extra nested folder, pass an explicit destination:

```bash
lbai init-workspace --path ~/LBAI/lbai-workspace-zhangsan
```
