# LBAI Workspace Kit

**让聪明模型在公司规则、证据边界、任务流程、交付标准里稳定工作。**

LBAI Workspace Kit 是员工 AI 办公工作区的**安装包与工作流模板**：安装 `lbai` CLI，绑定 private GitHub 工作区，在 Cursor 或 Codex 中用 `/lbai-*` 把正式工作变成可追踪任务和 OKF 资料，并同步到 GitHub 供后端入库检索。

**优势（简要）：**

- 聊天工作 → 结构化任务与资料，可复盘、可交接。
- 公司 guardrail、缺口检查、review 提醒，降低幻觉与越权风险。
- 资料与已完成任务 push 到 private GitHub，后端可异步索引。
- Cursor（`/lbai-*`）与 Codex（**LBAI …** 插件命令）共用同一套契约。

> 业务命令请在 Cursor / Codex 桌面 App 中触发，不要裸跑 `lbai new-task` 等。详见 [员工 FAQ](docs/EMPLOYEE_FAQ.zh-CN.md)。

---

## 1. 这是什么

本项目（`lbai-workspace-kit`）提供：

- **`install.sh` / `install.ps1`**：安装本机 `lbai` 命令。
- **`lbai_core/`**：CLI（认证、init、doctor、update-kit、命令转发）。
- **`workspace_template/`**：初始化时复制到员工 private repo 的工作区模板。

员工 daily 使用发生在**初始化后的 private 工作区**里，不是在 kit 源码仓库里。工作区内的完整员工手册见该仓库根目录 **README.md**（init 后自动生成）。

---

## 2. 安装与首次配置

### 2.1 系统要求

macOS / Windows；Git + Python 3.10+（安装脚本会检查并尝试安装）。

### 2.2 安装 lbai CLI

Mac / Linux：

```bash
curl -fsSL https://github.com/LBAI-Technology-Company/lbai-workspace-kit/releases/latest/download/install.sh | sh
source ~/.zshrc
```

Windows（PowerShell，完成后重新打开终端）：

```powershell
irm https://github.com/LBAI-Technology-Company/lbai-workspace-kit/releases/latest/download/install.ps1 | iex
```

### 2.3 登录与认证

```bash
lbai github auth token      # 必做：粘贴 private repo 权限的 Token
lbai auth doctor            # 确认 auth_status: READY
lbai auth backend-login     # 可选：后端知识检索 API Key
```

### 2.4 初始化工作区

```bash
lbai init-workspace
```

输入管理员提供的 **private GitHub 仓库 URL**，选择本地目录。成功后注册 active workspace（`~/.lbai/config.json`）。

### 2.5 Codex 插件

`install.sh` 通常会配置 Codex marketplace 并安装 **`lbai-workspace`** 插件。手动安装、命令对照与故障排查：[Codex 插件文档](docs/CODEX_PLUGIN_INTERNAL_MARKETPLACE.md)。

### 2.6 打开工作区并完成岗位配置

1. 用 Cursor 或 Codex 打开 init 输出的 **`cursor_open`** 目录（含 `.cursor/commands/`）。
2. 运行 **`/lbai-init`**（Codex：**LBAI Role Setup**）填写岗位信息。

### Day-1 速查

```text
安装 CLI → github auth → init-workspace → 打开工作区 → /lbai-init
日常：/lbai-new-task → /lbai-execute-task → /lbai-finish-task
资料：/lbai-add-evidence    搜索：/lbai-search-artifacts
```

---

## 3. 功能说明

### 3.1 员工命令

| Cursor | Codex 命令面板 | 用途 |
|--------|----------------|------|
| `/lbai-init` | LBAI Role Setup | 岗位记忆 |
| `/lbai-add-evidence` | LBAI Add Evidence | 归档资料 |
| `/lbai-search-artifacts` | LBAI Search Artifacts | 后端知识检索 |
| `/lbai-new-task` | LBAI New Task | 创建任务 |
| `/lbai-execute-task` | LBAI Execute Task | 执行任务 |
| `/lbai-finish-task` | LBAI Finish Task | 收尾与 Git 同步 |
| `/lbai-update-kit` | LBAI Update Kit | 升级公司模板 |
| `/lbai-self-iterate` | LBAI Self Iterate | Prompt Lab |

### 3.2 任务主链

```text
/lbai-new-task     建档（评估缺口，本地落盘，此时不 push）
/lbai-execute-task 执行（execution_plan.md + task_output.md）
/lbai-finish-task  收尾（审查、写 task_conversation.md、hygiene、push GitHub）
```

资料型输入用 `/lbai-add-evidence` 单独归档；与任务无自动关联，需在任务对话中说明补充了哪项缺口。

### 3.3 数据同步与服务端边界

按 **建档 → 执行 → 收尾** 官方流程，服务端经 GitHub 收到的是**结构化工作记录**，**不是**插件会话完整镜像。

| 数据 | 何时上 GitHub |
|------|---------------|
| OKF 资料 | `add-evidence` push 成功 → 后端 `PENDING_BACKEND_SYNC` |
| 任务整包 | `finish-task` push 成功（含交付物、finish_review、员工对话摘要 `task_conversation.md`） |
| 任务台账 | finish 时一并 push `TASK_LEDGER_v1.md` |

**有：** 任务 artifact、OKF 资料、收尾审查、员工侧对话摘要。  
**无：** AI 助手全文；未 finish 的任务；仅聊天未落盘内容。push 失败则可能仅本地可见。

### 3.4 统一模式

需 AI 的命令：Cursor/Codex 生成 enrichment JSON → `lbai_system/tools/*.py` 落盘/同步。无 JSON 则 **BLOCKED**。

终端可直接用：`lbai doctor`、`lbai update-kit`。

---

## 4. 仓库结构与维护

```text
lbai-workspace-kit/
├── install.sh / install.ps1
├── lbai_core/              CLI
├── workspace_template/     员工工作区模板（init 时复制）
├── docs/                   安装、插件、架构文档
└── VERSION
```

| 命令 | 作用 |
|------|------|
| `lbai update-kit` | 升级工作区公司模板（不动 `role_workspace/`、`tasks/`） |
| `lbai remove-kit --confirm` | 移除模板，保留员工数据 |
| `lbai uninstall` | 卸载本机 CLI |

开发/回归测试（kit 根目录）：`bash tests/run_tests.sh`。

后续路线：Codex 插件体验增强、Cursor extension；业务逻辑仍由 `lbai_core` 统一提供。详见 [ROADMAP](docs/ROADMAP.md)。

更多文档：[安装流程](docs/INSTALL_AND_INIT_FLOW.md) · [GitHub Token 策略](docs/GITHUB_TOKEN_POLICY.md) · [产品介绍](docs/LBAI_WORKSPACE_KIT_SERVICE_PRODUCT_INTRO.zh-CN.md)
