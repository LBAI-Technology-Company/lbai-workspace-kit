# 员工 FAQ（LBAI）

## `/lbai-*` 命令在 Cursor 里找不到

1. 确认打开的是 **`lbai init-workspace` 输出的工作区根目录**（含 `AGENTS.md`、`.cursor/commands/`），不是外层父文件夹。
2. 在 Cursor 执行 **Reload Window** 或重启 Cursor。
3. 运行 `lbai doctor`，查看 `cursor_commands` 是否为 OK。

## 我在终端跑了 `lbai new-task`，显示 BLOCKED

这是预期行为。`new-task`、`add-evidence`、`search-artifacts`、`finish-task`、`init` 都需要 AI 先生成 enrichment JSON。

**正确做法**：在 Cursor 或 Codex 桌面 App 中输入 `/lbai-new-task`（或其他对应 `/lbai-*` 命令）。

## Git push 失败

1. 运行 `lbai auth doctor` 检查 Token。
2. 确认 remote 指向你的 private repo：`git remote -v`。
3. 若 upstream 未设置，联系管理员或在仓库设置默认分支后重试 `lbai finish-task`（通过 `/lbai-finish-task`）。

## AI enrichment 缺失 / BLOCKED

- 不要在终端裸跑需要 `--enrichment` 的命令。
- 在 Cursor/Codex 里使用 `/lbai-*`；模型会按 `lbai_system/prompts/*_enrichment_prompt_v1.md` 生成 JSON 再调用 Python 工具。
- 若 JSON 校验失败，按输出里的 `next_step` 重新生成 enrichment。

## dashboard 打不开或读不到 Markdown

浏览器直接打开 `workspace_dashboard.html` 时，可能因 `file://` 限制无法读取本地文件。

**做法**：在工作区运行 `lbai serve-dashboard`，用浏览器打开 `http://127.0.0.1:8765/workspace_dashboard.html`。

## 换电脑怎么恢复

1. 重新安装：`curl ... install.sh | sh` 或 Windows 的 `install.ps1`。
2. `lbai auth login`。
3. `git clone` 你的 private 工作区 repo，或 `lbai init-workspace` 绑定已有 repo。
4. 用 Cursor/Codex 打开克隆目录，运行 `lbai doctor` 确认 READY。

## 工作区 kit 怎么升级

- **CLI 本身**：重跑安装命令（`@latest`）。
- **工作区模板**：在 Cursor/Codex 用 `/lbai-update-kit`，或终端 `lbai update-kit`（两者调用同一 `update_kit.py`）。

## 更多

- 安装与初始化：[INSTALL_AND_INIT_FLOW.md](INSTALL_AND_INIT_FLOW.md)
- Kit 升级策略：[UPDATE_KIT_STRATEGY.md](UPDATE_KIT_STRATEGY.md)
