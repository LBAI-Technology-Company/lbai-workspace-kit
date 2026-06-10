# LBAI Workspace Kit

**让聪明模型在公司规则、证据边界、任务流程、交付标准里稳定工作。**

这是 LBAI 员工 AI 办公工作区的公开分发项目。

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
| Python 3 | 安装程序会自动检查；缺失时尝试自动安装 |
| 网络 | 需能访问 GitHub 或安装镜像 |

安装完成后，本机 `lbai` 命令位于 `~/.lbai/bin/lbai`（Windows 为 `%USERPROFILE%\.lbai\bin\lbai.cmd`）。

## 员工使用流程

打开终端，按顺序执行下面 3 步。安装程序会**自动检查并安装** Git 和 Python 3（如本机缺失）。

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

安装的是**最新 Release 版本**（`@latest` 始终指向最新 Release，不是 main 开发分支）。完成后会显示：

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

初始化完成后，用 Cursor 或 Codex 打开本地工作区，运行 `/lbai-init` 填写岗位信息。

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

在工作区目录内，可使用终端命令或 Cursor / Codex 里的 `/lbai-*` 命令：

```bash
lbai init                  # 首次填写岗位信息
lbai add-evidence          # 保存资料，不自动建任务
lbai search-artifacts      # 搜索历史资料
lbai new-task "任务标题"   # 创建正式任务
lbai execute-task          # 准备任务，交给 Cursor/Codex 执行
lbai finish-task           # 完成任务并同步 GitHub
lbai doctor                # 检查工作区是否正常
```

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

`install.sh` / `install.ps1`：安装本地 `lbai` 命令，自动检查 Git 和 Python 3，并下载最新 Release。

`lbai_core/`：轻量 CLI core。第一版负责安装、初始化、升级、doctor，并把日常工作流命令转发到每个工作区里的 `lbai_system/tools/`。

`workspace_template/`：已经迁移进来的员工 private repo 工作区模板。

`docs/`：记录架构、安装初始化、GitHub token 策略、升级策略和迁移计划。

## 核心边界

安装后的 `lbai` CLI 负责确定性流程：

- 初始化工作区
- 保存 evidence
- 搜索历史 artifacts
- 创建任务骨架
- 运行 hygiene check
- 更新 ledger
- 升级 workflow kit
- 安全 Git 同步

Codex 和 Cursor 继续作为模型执行环境。它们负责读取上下文、生成任务输出，但底层业务流程应该调用同一个 `lbai_core`，不要在两个平台各写一套规则。

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
