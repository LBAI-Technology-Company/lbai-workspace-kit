# LBAI Workspace Kit

**让聪明模型在公司规则、证据边界、任务流程、交付标准里稳定工作。**

这是 LBAI 员工 AI 办公工作区的公开分发项目。

## 员工 Day-1 清单

1. **安装 CLI**（macOS / Linux）：
   ```bash
   curl -fsSL https://cdn.jsdelivr.net/gh/LBAI-Technology-Company/lbai-workspace-kit@latest/install.sh | sh
   source ~/.zshrc
   ```
   Windows PowerShell：
   ```powershell
   irm https://cdn.jsdelivr.net/gh/LBAI-Technology-Company/lbai-workspace-kit@latest/install.ps1 | iex
   ```
2. **登录 GitHub**：`lbai auth login`（粘贴有 repo 权限的 Token，或已登录 `gh` 时直接回车）。
3. **配置后端检索 Key**：`lbai auth backend-login`（可选；只保存在本机）。
4. **初始化工作区**：`lbai init-workspace`，输入管理员提供的 private repo URL，选择本地目录。
5. **用 Cursor 或 Codex 打开 init 输出的 `cursor_open` 目录**（不要打开外层父目录）。
6. **在 Cursor/Codex 桌面 App 里运行** `/lbai-init` 完成岗位问答。
7. 日常任务：`/lbai-new-task` → `/lbai-execute-task` → `/lbai-finish-task`；资料用 `/lbai-add-evidence`，查找用 `/lbai-search-artifacts`；prompt 实验用 `/lbai-self-iterate`。

> 业务命令必须在 Cursor/Codex 里输入 `/lbai-*`。不要在终端裸跑 `lbai new-task` 等命令。详见 [员工 FAQ](docs/EMPLOYEE_FAQ.zh-CN.md)。

目标很简单：让员工安装一个 `lbai` 命令，绑定已有的 private GitHub 仓库，选择本地目录，然后继续在 Codex 或 Cursor 里使用同一套 `/lbai-*` 工作流。

## 产品决策

第一阶段使用一个 public 仓库。

```text
lbai-workspace-kit
├── install.sh          Mac / Linux 安装入口
├── install.ps1         Windows 安装入口
├── lbai_core/
├── workspace_template/
├── docs/
├── VERSION
└── README.md
```

这个项目本身是工作模板和安装工具，不包含公司敏感业务数据；单仓库更简单，也更容易维护。

## 第一阶段范围

第一阶段是：

```text
lbai-core + init-workspace installer
```

需要支持：

- `lbai auth login`
- `lbai auth backend-login`
- `lbai init-workspace`
- `lbai doctor`
- `lbai update-kit`
- `lbai remove-kit`
- `lbai uninstall`
- 初始化后的工作区继续支持 `/lbai-*` 员工命令

暂时不做：

- Codex 插件市场安装
- Cursor extension
- GitHub Enterprise
- 公司专属安装域名
- 独立 LLM agent runtime

## 系统要求

支持 **macOS** 和 **Windows**。

| 依赖 | 说明 |
|------|------|
| Git | 安装程序会自动检查；缺失时尝试自动安装 |
| Python 3.10+ | 安装程序会自动检查；缺失时尝试自动安装 |
| 网络 | 需能访问 GitHub 或安装镜像 |

安装完成后，本机 `lbai` 命令位于 `~/.lbai/bin/lbai`（Windows 为 `%USERPROFILE%\.lbai\bin\lbai.cmd`）。

## 员工使用流程

打开终端，按顺序执行下面 3 步。安装程序会**自动检查并安装** Git 和 Python 3.10+（如本机缺失）。

**第 1 步：安装**

Mac（终端）：

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/LBAI-Technology-Company/lbai-workspace-kit@latest/install.sh | sh
source ~/.zshrc
```

Windows（PowerShell）：

```powershell
irm https://cdn.jsdelivr.net/gh/LBAI-Technology-Company/lbai-workspace-kit@latest/install.ps1 | iex
```

安装的是**最新 Release 版本**（`@latest` 始终指向最新 Release，不是 main 开发分支）。安装脚本会在运行时再次解析并下载最新 Release 包。完成后会显示：

```text
已安装版本: <版本号>
Release: v<版本号>
```

如提示安装 Git / Python，按窗口指引完成后**重新运行同一条安装命令**。Windows 安装完成后请**关闭并重新打开 PowerShell**，再执行后续步骤。

**第 2 步：登录 GitHub**

```bash
lbai auth login
```

- 首次使用：按提示粘贴管理员发给你的 GitHub Token
- 已保存过 Token：直接回车保持不变
- 已通过 `gh auth login` 登录：直接回车即可，无需重复配置

如需使用后端知识检索，再运行：

```bash
lbai auth backend-login
```

这个服务端 API Key 只保存在员工本机 `~/.lbai/auth/knowledge_service.json`，不会写入工作区 Git 仓库。

可先运行 `lbai auth doctor` 检查认证状态。

**第 3 步：初始化工作区**

```bash
lbai init-workspace
```

按提示输入管理员发给你的 GitHub 仓库地址。Mac 和 Windows 会弹出文件夹选择窗口；直接取消则默认保存在当前目录下的仓库同名文件夹。

`lbai init-workspace` 使用“已有 private repo”方案：

```text
1. 输入管理员发给你的 private GitHub 仓库地址。
2. Mac / Windows 弹出文件夹选择窗口；取消则默认保存在当前目录下的仓库同名文件夹。
3. clone 这个 repo（如本地还没有）。
4. 把 workspace_template/ 里的模板复制进去。
5. 创建或更新 Codex 和 Cursor 适配文件。
6. commit 并 push 初始化后的工作区。
7. 运行 lbai doctor。
```

初始化完成后，用 Cursor 或 Codex 打开本地工作区，运行 `/lbai-init` 填写用户姓名、岗位信息和对话习惯。

如需使用后端知识检索，先运行：

```bash
lbai auth backend-login
```

服务端 API Key 会保存在员工本机 `~/.lbai/auth/knowledge_service.json`，不会写入 workspace repo、`.lbai/workspace.json`、`role_workspace/` 或 `tasks/`，`lbai update-kit` 也不会清除它。

`.lbai/workspace.json` 保存技术身份和非敏感后端服务配置，例如 `employee_user_id`、邮箱/部门、`workspace_repo_id` 和 `knowledge_service`；`ROLE_PROFILE_v1.json` 保存面向模型上下文的岗位画像，例如用户姓名、岗位名称和对话习惯。

### 打开正确的 Cursor 工作区目录

`lbai init-workspace` 会在**当前目录或所选目录下**再创建一层与仓库同名的子目录。例如你在 `~/projects/my-folder` 里 init 仓库 `lbai-workspace-zhangsan`，实际工作区是：

```text
~/projects/my-folder/lbai-workspace-zhangsan/   ← 打开这个
├── .cursor/commands/                           ← /lbai-* 命令在这里
├── lbai_system/
└── role_workspace/
```

Cursor 的 `/` 命令只读取**工作区根目录**下的 `.cursor/commands/`。如果打开的是外层父目录（例如 `~/projects/my-folder`），输入 `/lbai` 不会出现任何命令。

初始化完成后，终端会打印 `cursor_open: <路径>`。请用 Cursor **File → Open Folder** 打开该路径（或 `cursor <路径>`），再运行 `/lbai-init`。

若希望工作区就在指定路径、不再套一层子目录，可显式传入 `--path`：

```bash
lbai init-workspace --path ~/LBAI/lbai-workspace-zhangsan
```

## 日常工作流

在工作区目录内，可使用终端命令或 Cursor / Codex 桌面 App 里的 `/lbai-*` 命令：

```bash
lbai doctor                # 检查工作区是否正常
lbai update-kit            # 升级公司模板（纯代码）
```

**除 `update-kit` / `doctor` 外，员工向命令请在 Cursor 或 Codex 桌面 App 中使用 `/lbai-*`。** 终端里的 `lbai new-task` 等会因缺少 AI enrichment 而失败。

### 统一模式：AI enrichment + 代码落盘

| 命令 | AI prompt | 代码工具 |
|------|-----------|----------|
| `/lbai-init` | `init_enrichment_prompt_v1.md` | `init_lbai.py --enrichment` |
| `/lbai-add-evidence` | `evidence_enrichment_prompt_v1.md` | `add_evidence.py --enrichment` |
| `/lbai-search-artifacts` | `backend_search_query_plan_prompt_v1.md` | `search_artifacts.py --enrichment`（仅后端搜索） |
| `/lbai-new-task` | `task_intake_enrichment_prompt_v1.md` | `new_task.py --enrichment` |
| `/lbai-execute-task` | `execute_task_plan_prompt_v1.md` | Agent 写 `execution_plan.md` + `task_output.md` |
| `/lbai-finish-task` | `finish_review_enrichment_prompt_v1.md` | `finish_task.py --enrichment` |
| `/lbai-update-kit` | 无 | `update_kit.py`（纯代码） |
| `/lbai-self-iterate` | 运行时 AI 生成 JSON（无预置 enrichment 文件） | `prompt_lab.py`（实验 prompt，不改正式 prompt） |

需要预置 enrichment JSON 的命令 → 无文件则 **BLOCKED**。`/lbai-self-iterate` 与 `/lbai-update-kit` 例外：Prompt Lab JSON 由当前 AI 运行时生成，update-kit 为纯代码。

Schema 均在 `lbai_system/schemas/`；其中搜索命令使用后端 query plan schema，其余 AI 命令使用 enrichment schema。

开发/回归测试（不影响工作区数据）：在 kit 根目录运行 `bash tests/run_tests.sh`。

### 创建任务（`/lbai-new-task`）

`/lbai-new-task` 不只是创建文件夹。它会先结合当前对话、岗位上下文和可检索的历史资料评估任务：

- 已知信息：标明来源是当前对话、公司知识库、角色上下文、已归档 evidence、外部来源或假设。
- 必要缺口：缺了就不能正式执行，会写入 `missing_inputs.md` 并阻止 `/lbai-execute-task`。
- 推荐补充：有助于提高质量，但不阻止先出初稿，会写入 `recommended_inputs.md` 或任务范围。
- 补充方式：普通说明、偏好、决策可直接在对话框补充，并关闭对应缺口；会议纪要、客户材料、邮件、原始研究等资料型来源才使用 `/lbai-add-evidence` 归档。

### 保存资料（`/lbai-add-evidence`）

**请在 Cursor 或 Codex 桌面 App 中使用** `/lbai-add-evidence`，不要单独在终端里裸跑 `lbai add-evidence`。

资料归档是 **AI 增强 + 代码落盘**，没有规则 fallback：

| 步骤 | 谁做 | 做什么 |
|------|------|--------|
| 1 | **AI**（Cursor / Codex 桌面） | 读 `lbai_system/prompts/evidence_enrichment_prompt_v1.md`，生成 enrichment JSON |
| 2 | **代码** | `add_evidence.py --enrichment <json>`：脱敏、写文件、台账、hygiene、git |

AI 只负责补齐轻量元数据，例如标题、资料类型、可见范围、关联对象和后端入库提示。员工端插件不再生成 reusable facts、decisions、action items、risks 或缺口分析。

代码负责：脱敏、目录/台账/git/hygiene。`NEEDS_REVIEW` **仅由 AI enrichment 判定**，代码不做关键词 overlay。

若 AI 不可用（模型不可用、额度用尽、JSON 无效），直接 `evidence_status: BLOCKED`，**不会**降级为规则处理。

Prompt 与 schema：

```text
lbai_system/prompts/evidence_enrichment_prompt_v1.md
lbai_system/schemas/evidence_enrichment_schema_v1.json
```

每个 evidence 目录包含：

```text
raw.md
metadata.json
evidence_enrichment.json
```

`metadata.json` 和 `EVIDENCE_LEDGER_v1.md` 会写入员工身份和后端入库状态。资料 push 到 GitHub 后，后端可异步读取并入库。

Evidence 与 task 保持独立：`/lbai-add-evidence` 只归档资料，不记录 `related_tasks`，也不会自动修改 `missing_inputs.md`、`task_scope.md`、`task_ledger.md` 或 `gap_record.md`。如果一份资料能帮助当前任务，请在任务对话里明确说明它补充了哪项信息；任务是否可执行仍由 `/lbai-new-task` 和 `/lbai-execute-task` 判断。

## GitHub Token 原则

不要把 token 放在安装命令或初始化命令参数里。

推荐：

```bash
lbai auth login
```

避免：

```bash
lbai init-workspace --github-token ghp_xxx
```

token 不应写入：

```text
README
AGENTS.md
.env
role_workspace/
tasks/
evidence
task artifacts
日志
命令行历史
```

认证来源优先级：`lbai auth login` 保存的 Token → 环境变量 `GITHUB_TOKEN` / `GH_TOKEN` → GitHub CLI（`gh auth login`）。

## 项目目录职责

`install.sh` / `install.ps1`：安装本地 `lbai` 命令，自动检查 Git 和 Python 3.10+，并下载最新 Release。

`lbai_core/`：轻量 CLI core。第一版负责安装、初始化、升级、doctor，并把日常工作流命令转发到每个工作区里的 `lbai_system/tools/`。

`workspace_template/`：已经迁移进来的员工 private repo 工作区模板。

`docs/`：记录架构、安装初始化、GitHub token 策略、升级策略和迁移计划。

## 核心边界

安装后的 `lbai` CLI 负责确定性流程：

- 初始化工作区
- 调用后端知识检索
- 创建任务骨架
- 运行 hygiene check
- 更新 ledger
- 升级 workflow kit
- 安全 Git 同步

资料归档（add-evidence）的**落盘、脱敏、台账、git** 由 `add_evidence.py` 完成；**轻量元数据补齐** 必须在 Cursor 或 Codex 桌面 App 中由 AI 先生成 enrichment JSON，无 fallback。员工端不再做事实抽取、brief 生成或缺口分析。

Codex 和 Cursor 继续作为模型执行环境。它们负责读取上下文、生成 enrichment 与任务输出，但底层业务流程应该调用同一个 `lbai_core`，不要在两个平台各写一套规则。

## 升级与卸载

| 命令 | 作用 | 在哪运行 | 会不会动个人数据 |
|------|------|----------|------------------|
| `lbai update-kit` | 升级工作区里的公司模板 | 工作区目录内 | 不会动 `role_workspace/`、`tasks/` |
| `lbai remove-kit` | 从工作区移除公司模板 | 工作区目录内 | 保留 `role_workspace/`、`tasks/` |
| `lbai uninstall` | 卸载本机 `lbai` 命令 | 任意目录 | 不删工作区文件夹和 GitHub 仓库 |

本机 `lbai` 命令坏了或需要升级时，**重新运行第 1 步的安装命令**即可：

Mac：

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/LBAI-Technology-Company/lbai-workspace-kit@latest/install.sh | sh
source ~/.zshrc
```

Windows（PowerShell）：

```powershell
irm https://cdn.jsdelivr.net/gh/LBAI-Technology-Company/lbai-workspace-kit@latest/install.ps1 | iex
```

### 升级工作区模板

```bash
lbai update-kit
```

在 Codex 或 Cursor 里，`/lbai-update-kit` 应该调用同一个底层操作。

### 从工作区移除公司模板（保留个人数据）

只删除公司维护的文件，**不删除** `role_workspace/`、`tasks/`，也不删除 GitHub 仓库。

```bash
lbai remove-kit --confirm
```

可选：

```bash
lbai remove-kit --confirm --no-commit
lbai remove-kit --confirm --no-push
```

移除后，这个目录会变成普通 Git 仓库，仍保留你的岗位记忆和任务产出。需要时可再运行 `lbai init-workspace` 重新注入模板。

### 卸载本机 lbai 命令

只删除本机安装的 `lbai` 命令和 kit，不删除员工工作区文件夹，也不删除 GitHub 仓库。

```bash
lbai uninstall
```

如需同时删除保存的 GitHub token：

```bash
lbai uninstall --purge-auth
```

`lbai update-kit` 可以更新：

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

不能覆盖：

```text
role_workspace/
tasks/
```

## 后续路线

第二阶段：做 Codex 插件或更好的项目级适配包。

第三阶段：做 Cursor extension，提供命令面板、状态显示和一键 doctor/update-kit。

这两个阶段都应该保持“薄入口”原则：插件只负责入口和体验，业务逻辑仍然由 `lbai_core` 统一提供。
