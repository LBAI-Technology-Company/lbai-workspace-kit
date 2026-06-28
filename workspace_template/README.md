# LBAI Role Workspace Kit

**让聪明模型在公司规则、证据边界、任务流程、交付标准里稳定工作。**

LBAI 是面向员工的 AI 办公工作区：在 Cursor 或 Codex 里用 `/lbai-*` 命令，把聊天里的正式工作变成**可追踪任务**和**可检索资料**，检查通过后同步到你的 private GitHub 仓库。

**优势（简要）：**

- **有边界**：公司 guardrail、review 提醒、来源与缺口检查，减少幻觉和越权表述。
- **可追溯**：任务文件夹、台账、OKF 资料库，方便复盘和交接。
- **可同步**：资料与已完成任务自动 push 到 private GitHub，后端可入库检索。
- **多入口**：Cursor 用 `/lbai-*` 或 MCP `lbai_*`；Codex 用 **LBAI …** 命令面板；其他 MCP 客户端（Claude Desktop、Windsurf、Cline 等）手动加载同一 server（见 [MCP 配置文档](docs/MCP_SETUP.md)）。

> 业务命令请在 **Cursor 或 Codex 桌面 App** 里触发，不要在终端裸跑 `lbai new-task` 等（会缺少 AI enrichment 而 BLOCKED）。详见 [员工 FAQ](docs/EMPLOYEE_FAQ.zh-CN.md)。

---

## 1. 这是什么

员工在 Cursor / Codex 里处理会议纪要、反馈汇总、内部文案、行动项等办公任务时，LBAI 提供统一工作流：

1. **资料**先归档为 OKF 知识（可选）。
2. **任务**按「建档 → 执行 → 收尾」留下结构化记录。
3. **收尾**时做 hygiene 检查并同步到 GitHub。

工作区主要目录：

```text
.cursor/          Cursor 的 /lbai-* 命令入口
lbai_system/      公司维护的工作流（日常勿改）
role_workspace/   岗位记忆、资料库、台账
tasks/            任务记录与交付物
```

日常主要看 `tasks/`、`role_workspace/ledgers/` 和 `workspace_dashboard.html`。

---

## 2. 安装与首次配置

### 2.1 系统要求

| 依赖 | 说明 |
|------|------|
| Git | 安装脚本会检查；缺失时尝试自动安装 |
| Python 3.10+ | 安装脚本会检查；缺失时尝试自动安装 |
| 网络 | 需能访问 GitHub |

安装路径：`~/.lbai/bin/lbai`（Windows：`%USERPROFILE%\.lbai\bin\lbai.cmd`）

### 2.2 安装 lbai CLI

Mac / Linux：

```bash
curl -fsSL https://github.com/LBAI-Technology-Company/lbai-workspace-kit/releases/latest/download/install.sh | sh
source ~/.zshrc
```

Windows（PowerShell，完成后请**重新打开**终端）：

```powershell
irm https://github.com/LBAI-Technology-Company/lbai-workspace-kit/releases/latest/download/install-bootstrap.ps1 | iex
```

若中文乱码，请使用 `install-bootstrap.ps1`（勿用 `install.ps1 | iex`）。手动方式：

```powershell
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$bytes = (New-Object Net.WebClient).DownloadData("https://github.com/LBAI-Technology-Company/lbai-workspace-kit/releases/latest/download/install.ps1")
iex ([Text.Encoding]::UTF8.GetString($bytes))
```

安装的是**最新 Release**（`@latest`），不是 main 开发分支。

### 2.3 登录 GitHub（必做）

```bash
lbai github auth token
```

- 首次：粘贴管理员发的 GitHub Token（需 private repo 读写权限）。
- 已保存过、仅 push 401：**直接回车**重新同步 Git 凭据。

确认就绪：

```bash
lbai auth doctor
```

应看到 `auth_status: READY`。

### 2.4 配置后端检索（可选）

```bash
lbai auth backend-login
```

按提示粘贴后端 API Key（只保存在本机，不写入 Git 仓库）。完成后 `lbai auth doctor` 应显示 `backend_api_key_available: yes`。

### 2.5 绑定 GitHub 工作区

安装脚本会自动创建公用工作区 `~/.lbai/workspace`（Windows：`%USERPROFILE%\.lbai\workspace`）。此时**尚未**绑定 GitHub，也**不会**复制企业模板。

向管理员索取 **private GitHub 仓库地址**，然后：

```bash
lbai bind-github
```

按提示粘贴 repo URL；工作区路径默认为 `~/.lbai/workspace`，无需再选目录。

绑定后会先检查远端仓库：

- **已是 LBAI 工作区**：clone/pull 个人仓库，**不会**用安装器模板覆盖已有岗位/任务数据
- **空仓库或仅有 GitHub boilerplate**：本地注入 `workspace_template/`（仅本地），首次 commit/push **员工数据**（不含 `lbai_system/`、`.cursor/` 等工作流模版）

完成后注册 active workspace（`~/.lbai/config.json`），并运行 `lbai auth doctor` 确认 `github_repo_status: BOUND`。

**Codex**：绑定后可在**任意 Codex 项目**中使用 **LBAI …** 命令，数据写入 active workspace。

**Cursor 或需自定义本地路径时**（可选）：

```bash
lbai init-workspace \
  --repo-url https://github.com/<org>/lbai-workspace-<name>.git \
  --path ~/LBAI/lbai-workspace-<name>
```

交互运行 `lbai init-workspace` 时，Mac / Windows 会弹出文件夹选择窗口；取消则默认保存在当前目录下的 `<仓库名>/` 子文件夹。

**Cursor 用户**：请打开输出中的 **`cursor_open`** 目录（含 `.cursor/commands/`），不要只打开外层父目录。

### 2.6 安装 Codex 插件（Codex 用户）

运行 `install.sh` / `install.ps1` 后，安装器通常会配置 Codex marketplace 并安装 `lbai-workspace` 插件。手动安装或排查见 [Codex 插件文档](docs/CODEX_PLUGIN_INTERNAL_MARKETPLACE.md)。

插件安装后，在 Codex **命令面板**选择 **LBAI Role Setup**、**LBAI New Task** 等 8 个命令；数据写入本机注册的 active workspace（`~/.lbai/config.json`）。

### 2.7 MCP 接入（Cursor 及其他 AI 工具）

LBAI 提供 stdio MCP server（`cursor_plugin/mcp_server.py`），暴露 9 个 `lbai_*` 工具；数据写入 registered active workspace（`~/.lbai/config.json`），与 Codex 插件相同。

**Cursor（自动）** — 运行 `install.sh` / `install.ps1` 后，安装器写入 `~/.cursor/mcp.json`，并将 `/lbai-*` 安装到 `~/.cursor/commands/`（任意项目可用）。**重启 Cursor** 后生效。跳过 MCP：`LBAI_SKIP_CURSOR_MCP=1`；跳过全局斜杠命令：`LBAI_SKIP_CURSOR_COMMANDS=1`。

**其他 MCP 客户端（手动）** — 将同一 server 配置块合并到对应配置文件：

| AI 工具 | 配置文件 |
|---------|----------|
| Claude Desktop | macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`<br>Windows: `%APPDATA%\Claude\claude_desktop_config.json` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` |
| Cline（VS Code） | `.../globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json` |
| VS Code 原生 MCP | 项目级 `.vscode/mcp.json` |

通用配置块（路径按本机替换）：

```json
{
  "mcpServers": {
    "lbai-workspace": {
      "command": "<venv-python>",
      "args": ["<kit>/cursor_plugin/mcp_server.py"],
      "env": { "PYTHONPATH": "<kit>/lbai_core" }
    }
  }
}
```

- macOS：`<venv-python>` = `~/.lbai/venv/bin/python3`，`<kit>` = `~/.lbai/kit`
- Windows：`<venv-python>` = `%USERPROFILE%\.lbai\venv\Scripts\python.exe`

完整说明：[MCP 配置文档](docs/MCP_SETUP.md) · Cursor 专项：[Cursor MCP 文档](docs/CURSOR_MCP_SETUP.md)

### 2.8 首次岗位配置

在 Cursor 或 Codex 中打开工作区后运行：

- **Cursor**：`/lbai-role-setup`
- **Codex**：命令面板 **LBAI Role Setup**

填写用户姓名、岗位名称、主要职责、对话习惯。写入 `role_workspace/world_model/`，不自动创建业务任务。

### Day-1 速查

```text
1. 安装 lbai CLI
2. lbai github auth token  →  lbai auth doctor
3. lbai bind-github（粘贴 private repo URL）
4. Cursor 打开 cursor_open 目录（或重启 Cursor / 其他 MCP 客户端加载 `lbai_*` 工具）；Codex 任意项目即可
5. /lbai-role-setup（Cursor）或 LBAI Role Setup（Codex）
6. 日常：/lbai-finish-task（无任务时会自动补建档、生成交付物并收尾；可选 /lbai-new-task 提前建档）
   资料：/lbai-add-evidence    搜索：/lbai-search-artifacts
```

换电脑 / 多端：本插件默认**单端使用**（同一台电脑上的 Cursor/Codex + 本地工作区）。GitHub 仅保存任务与资料；工作流模版（`lbai_system/`、`.cursor/` 等）在本地由 `/lbai-update-kit` 维护，不依赖 Git 同步。

---

## 3. 功能说明

### 3.1 命令一览

| 命令 | 用途 |
|------|------|
| `/lbai-role-setup` | 首次或更新岗位记忆 |
| `/lbai-add-evidence` | 归档会议记录、反馈、草稿等资料（不自动建任务） |
| `/lbai-search-artifacts` | 查询后端知识服务（只读） |
| `/lbai-new-task` | 创建正式任务 |
| `/lbai-finish-task` | 交付（按需）、审稿、检查、同步 GitHub |
| `/lbai-execute-task` | **高级/调试：** 只重生成交付物，不同步 |
| `/lbai-update-kit` | 升级公司工作流模板（**仅本地**，不 push 模版） |
| `/lbai-self-iterate` | Prompt Lab 实验（管理员向） |

Codex 命令面板名称对照见 [Codex 插件文档](docs/CODEX_PLUGIN_INTERNAL_MARKETPLACE.md#日常入口)。

终端仅建议：`lbai doctor`、`lbai update-kit`（与 `/lbai-update-kit` 相同底层）。

### 3.2 任务主链：建档 → 结束

**第一步：创建任务**

```text
/lbai-new-task 整理今天市场会议纪要和 action items
```

会评估已知信息、必要缺口（`missing_inputs.md`）和推荐补充；缺 blocking 信息时状态为 `BLOCKED`，需先补齐。

**第二步：补充并在对话中讨论**

- 普通说明、偏好、决策：在对话框补充，保存为任务本地输入。
- 会议记录、邮件、研究资料等：用 `/lbai-add-evidence` 独立归档，再在任务对话说明补充了哪项。

**第三步：结束并同步**

```text
/lbai-finish-task
```

若 `task_output.md` 尚未生成，finish 会先自动生成交付物（`execution_plan.md` + `task_output.md`），再检查交付物、更新台账、hygiene 检查；通过后 push **当前任务文件夹** + `role_workspace/ledgers/TASK_LEDGER_v1.md`。输出 `git_status: PUSHED` 表示已同步。

高级/调试：只用 `/lbai-execute-task` 重生成交付物，不同步。

### 3.3 保存资料（`/lbai-add-evidence`）

在 Cursor / Codex 中粘贴资料，由 AI 生成 enrichment JSON，代码落盘为 OKF Concept：

```text
role_workspace/knowledge/references/YYYY_MM_DD_<source_type>_<short_hash>.md
```

归档成功且检查通过后**立即 push**（不等 finish）。Evidence 与 task **独立**：不自动关闭任务缺口、不自动关联任务。

### 3.4 查询知识（`/lbai-search-artifacts`）

只查**后端知识服务**，不扫描本地文件；只读，不改任务状态。后端不可用或无命中时仅展示结果，不阻断任务流程。

### 3.5 数据同步与服务端边界

按官方流程 **建档 → 执行 → 收尾** 使用时，服务端（经 private GitHub 同步）收到的是**结构化工作记录**，**不是** Cursor/Codex 插件会话的完整镜像。

| 数据 | 何时进入 GitHub | 说明 |
|------|-----------------|------|
| 资料（OKF） | `/lbai-add-evidence` push 成功后 | 后端异步入库，可检索 |
| 任务包 | `/lbai-finish-task` push 成功后 | 含 scope、plan、output、finish_review、**task_conversation.md**（员工对话摘要）等 |
| 任务台账 | 同上 | `TASK_LEDGER_v1.md` |
| 工作流模版 | **不上 GitHub** | `lbai_system/`、`.cursor/` 等仅本地；由 `/lbai-update-kit` 更新 |

**包含：** 任务契约与交付物、收尾审查（gaps / overclaim）、员工侧对话摘要、已归档 OKF 资料。

**不包含：** 公司 workflow 模版；AI 助手全文回复；create/execute 阶段未 finish 的中间态；仅存在于聊天、未落盘的内容；finish 或 push 失败时可能仅留本地。

敏感信息在落盘时会脱敏；sync 被 BLOCK 时服务端可能看不到对应数据。

### 3.6 工作模式：AI enrichment + 代码落盘

| 命令 | AI 负责 | 代码负责 |
|------|---------|----------|
| `/lbai-role-setup` | 整理岗位问答 JSON | 写入 `role_workspace/` |
| `/lbai-add-evidence` | 资料元数据 JSON | OKF 落盘、脱敏、git |
| `/lbai-search-artifacts` | 后端 query plan | 调用知识 API |
| `/lbai-new-task` | 任务 intake JSON | 创建 `tasks/<folder>/` |
| `/lbai-finish-task` | auto-execute（按需）+ 收尾审查 + 对话提取 JSON | 审查落盘、hygiene、git push |
| `/lbai-execute-task` | 执行计划与交付物（高级/调试） | Agent 写 artifact，不同步 |

无 AI enrichment 时相关命令返回 **BLOCKED**，无规则 fallback。

### 3.7 岗位初始化（`/lbai-role-setup`）

会问：用户姓名、岗位名称、主要职责、对话习惯。保存到 `role_workspace/world_model/`（含 `ROLE_PROFILE_v1.json`）。岗位职责变化时可再次运行。

### 3.8 其他

- **`/lbai-update-kit`**：只更新公司维护文件（`.cursor/`、`lbai_system/`、`AGENTS.md` 等），**不覆盖**你的 `role_workspace/` 和 `tasks/`。
- **`/lbai-self-iterate`**：Prompt Lab 实验，写入 `prompt_lab/`，与日常任务分离。
- **Dashboard**：`lbai serve-dashboard` 后打开 `http://127.0.0.1:8765/workspace_dashboard.html`。

---

## 4. 维护与参考

### GitHub Token 原则

不要把 token 写进 README、`.env`、任务 artifact 或命令行历史。推荐只用 `lbai github auth token`。

### 升级与卸载

| 命令 | 作用 |
|------|------|
| `lbai update-kit` | 升级工作区公司模板 |
| `lbai remove-kit --confirm` | 移除模板，保留 `role_workspace/`、`tasks/` |
| `lbai uninstall` | 卸载本机 `lbai` 命令（不删工作区文件夹） |

重新安装 CLI：再次运行第 2.2 节安装命令即可。

### 常见问题

- **Cursor 看不到 `/lbai-*`**：确认打开的是工作区根目录（含 `.cursor/commands/`），Reload Window。
- **Cursor agent 看不到 `lbai_*` 工具**：确认 `~/.cursor/mcp.json` 含 `lbai-workspace` 条目，重启 Cursor。其他 MCP 客户端见 [MCP 配置文档](docs/MCP_SETUP.md)。
- **终端 `lbai new-task` BLOCKED**：请在 Cursor/Codex 里用 `/lbai-new-task`。
- **push 失败**：`lbai auth doctor` → 检查 Token、remote、upstream；任务数据仍在本地。

更多见 [员工 FAQ](docs/EMPLOYEE_FAQ.zh-CN.md)、[安装流程](docs/INSTALL_AND_INIT_FLOW.md)、[MCP 配置](docs/MCP_SETUP.md)、[架构说明](docs/ARCHITECTURE.md)。
