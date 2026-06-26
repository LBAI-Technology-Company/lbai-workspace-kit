# 员工 FAQ（LBAI）

## Codex 插件命令和 Cursor 命令有什么区别？

**Cursor** 使用斜杠命令：`/lbai-init`、`/lbai-new-task`、`/lbai-self-iterate` 等。

**Codex（全局 `lbai-workspace` 插件）** 在命令面板显示 **LBAI …** 名称。岗位设定固定为 **LBAI Role Setup**（对应 `/lbai-init`）；其余命令与 slash 名一一对应，例如 `/lbai-self-iterate` → **LBAI Self Iterate**。

| Codex 命令面板 | Cursor 等价 |
|---|---|
| LBAI Role Setup | `/lbai-init` |
| LBAI New Task | `/lbai-new-task` |
| LBAI Add Evidence | `/lbai-add-evidence` |
| LBAI Search Artifacts | `/lbai-search-artifacts` |
| LBAI Execute Task | `/lbai-execute-task` |
| LBAI Finish Task | `/lbai-finish-task` |
| LBAI Update Kit | `/lbai-update-kit` |
| LBAI Self Iterate | `/lbai-self-iterate` |

在 Codex 对话里也可以写 `$lbai-init`、`$lbai-new-task` 等 skill 引用。完整说明见 [CODEX_PLUGIN_INTERNAL_MARKETPLACE.md](CODEX_PLUGIN_INTERNAL_MARKETPLACE.md)。

## `/lbai-*` 命令在 Cursor 里找不到

1. 确认打开的是 **`lbai init-workspace` 输出的工作区根目录**（含 `AGENTS.md`、`.cursor/commands/`），不是外层父文件夹。
2. 在 Cursor 执行 **Reload Window** 或重启 Cursor。
3. 运行 `lbai doctor`，查看 `cursor_commands` 是否为 OK。

## 我在终端跑了 `lbai new-task`，显示 BLOCKED

这是预期行为。`new-task`、`add-evidence`、`search-artifacts`、`finish-task`、`init` 都需要 AI 先生成 enrichment JSON。

**正确做法**：
- **Cursor**：输入 `/lbai-new-task`（或其他 `/lbai-*` 命令）。
- **Codex**：在命令面板选择 **LBAI New Task**（或其他 **LBAI …** 命令），或写 `$lbai-new-task`。

## Git push 失败 / 401 认证失败

**日常同步任务请用 Cursor 里的 `/lbai-finish-task`，不要手动 git push。** 若必须排查 push 问题，按下面顺序做：

### 第 1 步：检查认证

```bash
lbai auth doctor
```

看输出里这两项：

| 字段 | 期望 |
|------|------|
| `auth_status` | `READY` |
| `git_credential_sync` | `ok` |

### 第 2 步：一键修复（最常见）

```bash
lbai github auth token
```

- **换了新 Token**：粘贴新 Token 回车（会自动同步到 Git）
- **Token 没换、只是 push 报 401**：**直接回车**（会重新同步 Git 凭据，无需重贴 Token）

然后再运行：

```bash
lbai auth doctor
```

确认 `auth_status: READY` 后再继续。

### 第 3 步：仍失败时

1. 确认 remote 指向你的 private repo：`git remote -v`
2. 向管理员确认 Token 是否有 **repo** 读写权限
3. 把 `lbai auth doctor` 的完整输出发给管理员（不要截图 Token 本身）

## AI enrichment 缺失 / BLOCKED

- 不要在终端裸跑需要 `--enrichment` 的命令。
- 在 Cursor/Codex 里使用 `/lbai-*`；模型会按 `lbai_system/prompts/` 中对应 prompt 生成 JSON 再调用 Python 工具，其中搜索命令使用后端 query plan。
- 若 JSON 校验失败，按输出里的 `next_step` 重新生成 enrichment。

## `/lbai-new-task` 说缺信息，我一定要用 `/lbai-add-evidence` 吗？

不一定。

- 普通说明、偏好、决策、口头补充：直接在对话框回复即可，助手应把它作为当前任务的补充上下文，并关闭对应缺口。
- 会议纪要、客户材料、邮件、原始转写、研究资料、可复用来源：使用 `/lbai-add-evidence` 独立归档为 evidence。
- 推荐补充信息：有助于提高质量，但不一定阻止 `/lbai-execute-task` 先出初稿。

注意：`/lbai-add-evidence` 只会把资料保存为独立 evidence，不记录 `related_tasks`。它不会自动改写任务的 `missing_inputs.md` 或把任务状态改成 READY；如果资料补充了任务缺口，请回到任务对话中明确说明补充了哪项信息。

## `/lbai-search-artifacts` 是查本地还是查后端？

`/lbai-search-artifacts` 只查后端知识服务，并直接展示后端返回的 FOUND / NO_MATCH / ERROR 等结果。

如果后端未配置、不可用、超时或没有命中结果，搜索命令只负责把结果展示出来，不会回退到本地 catalog 搜索，也不会自动阻断、修改或推进其他任务流程。

新增资料会保存为 `role_workspace/knowledge/references/*.md` 下的 OKF Concept，并更新 `index.md` 与 `log.md`。员工搜索命令只查后端，不读取本地任务或知识文件作为 fallback。

## dashboard 打不开或读不到 Markdown

浏览器直接打开 `workspace_dashboard.html` 时，可能因 `file://` 限制无法读取本地文件。

**做法**：在工作区运行 `lbai serve-dashboard`，用浏览器打开 `http://127.0.0.1:8765/workspace_dashboard.html`。

## Windows 安装时中文乱码

PowerShell 用 `irm install.ps1 | iex` 时，可能把 UTF-8 安装脚本按系统默认编码解析，步骤提示会显示成乱码（安装本身通常仍可继续）。

**推荐**（下一版起）：

```powershell
irm https://github.com/LBAI-Technology-Company/lbai-workspace-kit/releases/latest/download/install-bootstrap.ps1 | iex
```

**当前 v1.4.26 可立即使用**：

```powershell
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$bytes = (New-Object Net.WebClient).DownloadData("https://github.com/LBAI-Technology-Company/lbai-workspace-kit/releases/latest/download/install.ps1")
iex ([Text.Encoding]::UTF8.GetString($bytes))
```

安装完成后重新打开 PowerShell，再运行 `lbai auth doctor`。

## 换电脑怎么恢复

1. 重新安装：`curl ... install.sh | sh` 或 Windows 的 `install.ps1`。
2. `lbai github auth token`。
3. `git clone` 你的 private 工作区 repo 到本机，然后 `lbai workspace set --path <克隆目录>`。
   - 安装器**不会**再自动覆盖企业模板；个人仓库内容就是真相来源。
   - 不要在新电脑上再次运行 `lbai bind-github`（除非目录仍是空的首次绑定）。
4. 用 Cursor/Codex 打开克隆目录，运行 `lbai doctor` 确认 READY。

## 首次绑定 vs 升级

| 场景 | 正确命令 |
|------|----------|
| 安装后目录为空，首次连 GitHub | `lbai bind-github`（空仓库会 seed 企业 template） |
| 个人仓库已有任务/岗位数据 | `lbai bind-github` 会 **clone 个人仓库**，不会用安装器模板覆盖 |
| 升级 kit 版本 | `/lbai-update-kit` 或 `lbai update-kit`（用户主动） |

## 多台电脑交替工作

`/lbai-finish-task`、`/lbai-add-evidence` 和 `lbai bind-github` 在 push 前会**自动 fetch/pull** 远程变更。你通常不需要手动 `git pull`；若 pull 冲突，按终端提示解决冲突后再重试。

## 工作区 kit 怎么升级

- **CLI 本身**：重跑安装命令（`@latest`）。
- **工作区模板**：在 Cursor/Codex 用 `/lbai-update-kit`，或终端 `lbai update-kit`（两者调用同一 `update_kit.py`）。

## 更多

- 安装与初始化：[INSTALL_AND_INIT_FLOW.md](INSTALL_AND_INIT_FLOW.md)
- Kit 升级策略：[UPDATE_KIT_STRATEGY.md](UPDATE_KIT_STRATEGY.md)
