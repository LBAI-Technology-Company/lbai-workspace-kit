# Install And Init Flow

## Public Install Command

Employee install commands download the latest `install.sh` / `install.ps1` directly from GitHub release assets (`releases/latest/download`). This is not a pinned version tag; it always follows the current GitHub latest release.

macOS / Linux:

```bash
curl -fsSL https://github.com/LBAI-Technology-Company/lbai-workspace-kit/releases/latest/download/install.sh | sh
source ~/.zprofile
source ~/.zshrc
lbai github auth token
lbai auth backend-login
```

Install also creates and registers a shared workspace at `~/.lbai/workspace`. After that, open **any** Codex project and run `/lbai-init`.

If GitHub is slow or unreachable from your network, use the ghproxy mirror:

```bash
curl -fsSL https://ghproxy.net/https://github.com/LBAI-Technology-Company/lbai-workspace-kit/releases/latest/download/install.sh | sh
```

Windows (PowerShell):

```powershell
irm https://github.com/LBAI-Technology-Company/lbai-workspace-kit/releases/latest/download/install.ps1 | iex
```

ghproxy mirror:

```powershell
irm https://ghproxy.net/https://github.com/LBAI-Technology-Company/lbai-workspace-kit/releases/latest/download/install.ps1 | iex
```

Close and reopen PowerShell after install, then run:

```powershell
lbai github auth token
lbai auth backend-login
```

Install also creates and registers a shared workspace at `%USERPROFILE%\.lbai\workspace`. After that, open **any** Codex project and run `/lbai-init`.

The installer downloads the latest release package through internal mirrors when needed. It also checks for Git and Python 3.10+ and attempts to install them when missing. Piped installers auto-fetch the newest script from GitHub release assets when the local copy is stale. On macOS, Linux, and Windows it also attempts to install the OpenAI Codex CLI (official script, npm, or GitHub binary fallback), register the `lbai-workspace` Codex plugin, and create the shared workspace at `~/.lbai/workspace` (set `LBAI_SKIP_CODEX_CLI=1`, `LBAI_SKIP_CODEX_PLUGIN=1`, or `LBAI_SKIP_WORKSPACE_INIT=1` to skip). When install finishes, the script prints an **安装结果汇总** table showing OK / failed / skipped status for each component.

## Authentication

Do not pass tokens as command-line arguments.

Good:

```bash
lbai github auth token
```

`lbai github auth token` behavior:

- First run: paste a GitHub token when prompted; LBAI saves it and **automatically syncs Git credentials** so bare `git push` works
- Token already saved: press Enter to **re-sync Git credentials** (fixes 401 after token rotation without re-pasting if the saved file is already updated)
- Replace token: paste the new token when prompted
- Already authenticated through `gh auth login` with no saved token: press Enter to configure Git to use `gh`

After login, run `lbai auth doctor` and confirm `auth_status: READY`. The shared workspace is already registered during install; use `lbai workspace show` to verify `active_workspace`.

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
1. Read GitHub authentication from `lbai github auth token`, `GITHUB_TOKEN`, `GH_TOKEN`, or GitHub CLI credential state.
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
   curl -fsSL https://github.com/LBAI-Technology-Company/lbai-workspace-kit/releases/latest/download/install.sh | sh
   source ~/.zshrc

   Windows PowerShell:
   irm https://github.com/LBAI-Technology-Company/lbai-workspace-kit/releases/latest/download/install.ps1 | iex
   （安装后请关闭并重新打开 PowerShell）

   国内网络 GitHub 较慢时，可在 URL 前加 ghproxy：
   curl -fsSL https://ghproxy.net/https://github.com/LBAI-Technology-Company/lbai-workspace-kit/releases/latest/download/install.sh | sh

2. 登录 GitHub：
   lbai github auth token
   （向管理员索取 GitHub Token，需有 private repo 读写权限；粘贴后会自动同步 Git 凭据）
   lbai auth doctor
   lbai auth backend-login

3. 公用工作区（安装时已自动创建）：
   lbai workspace show
   （默认路径 ~/.lbai/workspace，任意 Codex 项目均可使用 /lbai-*）

4. 可选 — 绑定 private GitHub 仓库同步：
   lbai init-workspace --repo-url <你的 private repo URL> --path ~/.lbai/workspace

5. 打开任意 Codex 项目，运行：
   /lbai-init

常见问题见 docs/EMPLOYEE_FAQ.zh-CN.md
```
