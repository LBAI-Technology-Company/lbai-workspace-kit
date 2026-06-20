# Install And Init Flow

## Public Install Command

Employee install commands (auto-check Git and Python 3.10+):

macOS / Linux:

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/LBAI-Technology-Company/lbai-workspace-kit@latest/install.sh | sh
source ~/.zprofile
source ~/.zshrc
lbai auth login
lbai init-workspace
```

Piped `@latest` installers auto-fetch the newest `install.sh` from GitHub release tags before proceeding, so employees should always use `@latest` rather than pinning a version tag.

Windows (PowerShell):

```powershell
irm https://cdn.jsdelivr.net/gh/LBAI-Technology-Company/lbai-workspace-kit@latest/install.ps1 | iex
```

Close and reopen PowerShell after install, then run:

```powershell
lbai auth login
lbai init-workspace
```

The installer downloads the latest release package through internal mirrors when needed. It also checks for Git and Python 3.10+ and attempts to install them when missing. Piped `@latest` install scripts auto-fetch the newest installer from GitHub release tags before proceeding. On macOS and Linux it also attempts to install the OpenAI Codex CLI (official script, npm, or GitHub binary fallback) and register the `lbai-workspace` Codex plugin from the same release tag when missing (set `LBAI_SKIP_CODEX_CLI=1` or `LBAI_SKIP_CODEX_PLUGIN=1` to skip).

## Authentication

Do not pass tokens as command-line arguments.

Good:

```bash
lbai auth login
```

`lbai auth login` behavior:

- First run: paste a GitHub token when prompted; LBAI saves it and **automatically syncs Git credentials** so bare `git push` works
- Token already saved: press Enter to **re-sync Git credentials** (fixes 401 after token rotation without re-pasting if the saved file is already updated)
- Replace token: paste the new token when prompted
- Already authenticated through `gh auth login` with no saved token: press Enter to configure Git to use `gh`

After login, run `lbai auth doctor` and confirm `auth_status: READY` before `lbai init-workspace`.

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
11. Register the initialized path as the machine-wide active workspace in `~/.lbai/config.json`.
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

## 管理员发给员工的复制模板

```text
【LBAI 办公环境 — 首次安装】

1. 安装（选你的系统）：
   macOS/Linux:
   curl -fsSL https://cdn.jsdelivr.net/gh/LBAI-Technology-Company/lbai-workspace-kit@latest/install.sh | sh
   source ~/.zshrc

   Windows PowerShell:
   irm https://cdn.jsdelivr.net/gh/LBAI-Technology-Company/lbai-workspace-kit@latest/install.ps1 | iex
   （安装后请关闭并重新打开 PowerShell）

2. 登录 GitHub：
   lbai auth login
   （向管理员索取 GitHub Token，需有 private repo 读写权限；粘贴后会自动同步 Git 凭据）
   lbai auth doctor
   （确认 auth_status: READY 后再继续）

3. 初始化工作区：
   lbai init-workspace
   仓库地址：<你的 private repo URL，例如 https://github.com/LBAI-Technology-Company/lbai-workspace-zhangsan.git>
   本地目录：按提示选择，或 --path 指定

4. 打开 Cursor 或 Codex：
   打开 init 成功输出里的 cursor_open 路径（不要打开外层父目录）

5. 第一条命令：
   /lbai-init

常见问题见 docs/EMPLOYEE_FAQ.zh-CN.md
```
