# LBAI Role Workspace Kit v0.6

**让聪明模型在公司规则、证据边界、任务流程、交付标准里稳定工作。**

如果这个工作区是通过 `lbai-workspace-kit` 初始化的，可以在终端使用 `lbai doctor`、`lbai update-kit` 等命令；在 Codex 或 Cursor 里仍然使用 `/lbai-*` 日常工作流入口。

这份文档给第一次使用 LBAI 企业办公工作区的员工使用。

你可以把这个项目理解成：**公司给每位员工准备的 AI 办公工作区模板**。它用于把日常办公任务整理成可追踪、可复盘、可交接的工作记录，并在检查通过后同步到你的 private GitHub 仓库。

当前工作区支持两种入口：

- Cursor：使用 `.cursor/commands/` 里的 `/lbai-*` 命令入口。
- Codex：打开本项目后，可以直接输入或提到 `/lbai-*` 命令，由项目内 Codex 适配说明触发同一套工作流。
- 企业 Codex Marketplace：安装 `lbai-workspace` 后，可使用 `$lbai-workspace:lbai-*` 命名空间 Skills 或自然语言触发同一套工作流；项目本地 `$lbai-*` 与 `/lbai-*` 兼容入口继续保留。

企业插件的安装、升级、数据边界和故障排查见 [`docs/CODEX_PLUGIN_INTERNAL_MARKETPLACE.md`](docs/CODEX_PLUGIN_INTERNAL_MARKETPLACE.md)。

最快使用路径：

```text
拿到 private 仓库 -> 用 Cursor 或 Codex 打开 -> /lbai-init -> /lbai-add-evidence 或 /lbai-search-artifacts 或 /lbai-new-task -> /lbai-execute-task -> /lbai-finish-task

Prompt 实验和本地自迭代使用 `/lbai-self-iterate`。它默认优先使用你的真实任务上下文；如果当前工作区没有任务上下文，就自动使用 mock 数据。实验记录保存在 `prompt_lab/`，不会自动修改公司正式 prompt；每轮会在 `prompt_lab/admin_feedback/outbox/` 生成给管理员看的问题、优化方案和优化后效果摘要。只有 `handoff_status=READY` 时才发送；如果显示 `BLOCKED_REDACTION_REQUIRED`，先脱敏并重新评估。
```

---

## 1. 这个项目是做什么的

### 1.1 解决什么问题

员工平时会在 Cursor 或 Codex 里处理很多企业办公任务，例如：

- 整理会议纪要
- 汇总用户反馈
- 编写内部周报
- 整理资料和行动项
- 起草需要 review 的文案

这个工作区会把正式工作保存成任务记录，也允许你先把会议记录、反馈、草稿、SOP、日志和背景资料保存成 evidence。资料不会因为被粘贴进来就自动变成任务；只有你确认或运行 `/lbai-new-task` 时，才会进入正式任务生命周期。

### 1.2 工作区里有什么

这个项目有五个主要部分：

```text
.cursor/        Cursor 项目命令入口
.agents/        项目本地 agent 适配文件
lbai_system/    公司维护的工作流配置、Codex 适配、工具和默认模板
role_workspace/ 员工岗位记忆、资料库和台账
tasks/          每天产生的任务记录和结果
```

员工日常主要看 `tasks/`、`role_workspace/ledgers/` 和 `workspace_dashboard.html`。

`.cursor/` 保存 Cursor 里的 `/lbai-*` 命令入口。

`.agents/` 保存项目本地 agent 适配文件，只负责把 `/lbai-*` 命令指回共享契约。当前稳定使用方式仍是直接输入 `/lbai-*`；这些文件不代表 Codex 一定会自动显示 `$lbai-*` skill。

`role_workspace/` 保存你的岗位职责、边界、优先级、资料库和任务/evidence 台账。

`lbai_system/templates/role_workspace/` 保存公司维护的岗位默认模板，用来给新员工或缺失文件补齐初始结构。

`lbai_system/` 是公司维护的工作流系统，日常不要手动修改。

### 1.3 核心功能

- 同时支持 Cursor 和 Codex，使用同一套 `/lbai-*` 命令和任务合同。
- 用 `/lbai-add-evidence` 保存会议记录、反馈、草稿、SOP、日志和背景资料，不自动创建任务。资料归档需先在 **Cursor 或 Codex 桌面 App** 中由 AI 生成 enrichment JSON，再由代码落盘；无规则 fallback。
- 用 `/lbai-search-artifacts` 查询后端知识服务返回的证据包，不扫描本地 evidence、任务或 references，也不自动关联或改状态。
- 用三步任务生命周期把工作从聊天转成正式记录：建档、执行、收尾。
- 自动识别必要缺口和推荐补充；普通说明、偏好和决策保存为任务本地上下文，资料型来源保存为独立 evidence。
- 已有任务缺口由 `/lbai-new-task` 和 `/lbai-execute-task` 本地判断；`/lbai-add-evidence` 不记录 `related_tasks`，也不自动关闭任务缺口。
- 要求任务输出客观、可核查、可执行；数据、指标、案例和结论必须有来源。
- 保存岗位记忆、职责边界和任务总台账。
- 对需要 review 的资料标记 `NEEDS_REVIEW` 并在对话中提醒负责人 review；流程不再因 review 边界阻断执行或收尾。
- 对敏感信息、临时文件和提交范围做收尾检查。
- 检查通过后自动提交并推送到员工自己的 private GitHub 仓库。
- 提供 `workspace_dashboard.html` 状态显示页面，可查看岗位信息、任务信息、阻断事项和工作流边界。
- 支持 `/lbai-update-kit` 更新公司维护的工作流文件，同时保留员工自己的 `role_workspace/` 和 `tasks/`。

### 1.4 员工需要记住哪些命令

日常任务主链只需要三个命令：

```text
/lbai-new-task
/lbai-execute-task
/lbai-finish-task
```

如果只是先保存资料、证据或知识，不想立刻创建任务，用：

```text
/lbai-add-evidence
```

如果想先查后端知识服务里的历史资料、旧结论或证据包，用：

```text
/lbai-search-artifacts
```

第一次配置岗位，或者岗位职责变化时，用：

```text
/lbai-init
```

管理员通知模板有新版时，用：

```text
/lbai-update-kit
```

### 1.5 哪些文件不会被模板更新覆盖

后续运行 `/lbai-update-kit` 时，系统只更新公司维护的模板层，不会覆盖员工自己的工作内容。

这里要分清两类文件：

```text
role_workspace/                       员工私有岗位记忆，不覆盖
lbai_system/templates/role_workspace/ 公司最新岗位默认模板，可更新
```

不会覆盖：

```text
role_workspace/
tasks/
```

所以 `/lbai-init` 填写的岗位信息、`/lbai-new-task` 创建的任务、以及日常任务结果，都会保留。

如果公司后来调整了岗位默认模板，更新会先进入 `lbai_system/templates/role_workspace/`。老员工已经填写过的 `role_workspace/` 不会自动被改写；只有当某个岗位记忆文件缺失时，系统检查才会从默认模板补一个空白初始文件。

---

## 2. 安装和打开工作区

### 2.1 管理员先做什么

管理员会先在 GitHub 上为员工创建一个 private 仓库。仓库名建议使用员工或岗位可识别的名称，例如：

```text
lbai-workspace-zhangsan
```

创建完成后，管理员把员工专属 private 仓库地址发给员工。这个仓库不需要从旧模板仓库手动复制内容，后续由 `lbai init-workspace` 写入标准工作区文件。

### 2.2 员工从哪里开始

员工不需要 clone 公开的 `lbai-workspace-kit` 仓库，也不要手动复制 `workspace_template/`。

员工只需要：

1. 从管理员那里拿到自己的 private 仓库地址和 GitHub Token
2. 在终端运行公司安装命令（见下方）
3. 运行 `lbai auth login`
4. 运行 `lbai init-workspace`
5. 用 Cursor 或 Codex 打开初始化后的本地工作区
6. 运行 `/lbai-init` 填写岗位信息

公司安装命令：

Mac：

```bash
curl -fsSL https://github.com/LBAI-Technology-Company/lbai-workspace-kit/releases/latest/download/install.sh | sh
source ~/.zshrc
```

Windows（PowerShell）：

```powershell
irm https://github.com/LBAI-Technology-Company/lbai-workspace-kit/releases/latest/download/install.ps1 | iex
```

Windows 安装完成后请**关闭并重新打开 PowerShell**，再执行 `lbai auth login` 和 `lbai init-workspace`。

Codex 不需要把本项目的 LBAI skill 安装到 `~/.codex/skills/`。本项目通过 `AGENTS.md` 和 `lbai_system/codex/skills/lbai-workflow/SKILL.md` 提供项目级适配，只影响当前仓库；`.agents/skills/` 是项目内薄适配文件，只做命令入口转发准备，真实规则仍以共享契约为准。当前稳定入口是 `/lbai-*`，不是 `$lbai-*`。

### 2.3 快速配置流程

新员工建议按这个顺序配置：

1. 安装 `lbai` 命令。
2. 运行 `lbai auth login`，保存 GitHub 认证。首次使用粘贴 Token；已保存过 Token 或已通过 `gh auth login` 登录时，直接回车即可。
3. 运行 `lbai init-workspace`，输入管理员提供的 private repo URL；Mac / Windows 会弹出文件夹选择窗口，取消则默认保存在当前目录下的仓库同名文件夹。
4. 进入初始化后的本地工作区，运行 `lbai doctor`。
5. 用 Cursor 或 Codex 打开这个本地工作区。
6. 运行 `/lbai-init`，填写用户姓名、岗位名称、主要职责和对话习惯。
7. 可先运行 `/lbai-add-evidence` 保存一份测试资料，确认资料会进入 evidence ledger，且不会自动创建任务。
8. 创建第一条测试任务，例如 `/lbai-new-task 整理一次测试任务记录`。
9. 如果任务提示缺信息，普通说明、偏好和决策可直接在对话框补充；会议纪要、客户材料、邮件、原始转写、研究资料等资料型来源，先用 `/lbai-add-evidence` 独立归档，再回到任务对话说明它补充了哪项信息。
10. 确认输出后运行 `/lbai-finish-task`，让系统检查、落账并同步到 private GitHub。
11. 打开 `workspace_dashboard.html` 或运行 `lbai serve-dashboard`，确认任务状态、资料记录和岗位信息能正常显示。

日常使用时主要重复第 8-10 步；如果只是先保存资料或知识，可先做第 7 步。

### 2.4 推荐方式：用 lbai 初始化

在终端运行：

```bash
lbai auth login
lbai init-workspace
```

`lbai init-workspace` 会询问 GitHub 仓库地址。Mac 和 Windows 上会弹出文件夹选择窗口；取消则默认保存在当前目录下的仓库同名文件夹。

示例（取消文件夹选择窗口时使用默认路径）：

```text
GitHub repo URL: https://github.com/LBAI-Technology-Company/lbai-workspace-zhangsan.git
Local folder path: ./lbai-workspace-zhangsan
```

也可以一次性传入参数：

```bash
lbai init-workspace \
  --repo-url https://github.com/LBAI-Technology-Company/lbai-workspace-zhangsan.git \
  --path ~/LBAI/lbai-workspace-zhangsan
```

初始化完成后，再用 Cursor 或 Codex 打开这个本地路径。

### 2.5 已初始化工作区换电脑时怎么打开

如果这个 private 仓库已经由 `lbai init-workspace` 初始化过，换电脑时可以直接 clone 这个员工 private 仓库，然后在仓库根目录运行：

```bash
lbai doctor
```

如果还没有安装本机 `lbai` 命令，先运行上面的公司安装命令；不要把 GitHub token 写进仓库文件、聊天记录或 README。

### 2.6 初始化完成后检查

初始化完成后，在 Cursor 或 Codex 的文件树里应能看到：

```text
.cursor/
.agents/
.gitignore
lbai_system/
role_workspace/
tasks/
AGENTS.md
README.md
```

然后在 Cursor 里输入 `/lbai`，应该能看到：

```text
/lbai-init
/lbai-add-evidence
/lbai-search-artifacts
/lbai-new-task
/lbai-execute-task
/lbai-finish-task
/lbai-update-kit
/lbai-self-iterate
```

如果看不到这些命令，重启 Cursor，或运行 Cursor 的 Reload Window。在 **Codex 桌面 App** 中打开同一工作区，输入 `/lbai-add-evidence` 等命令即可触发工作流（不使用 Codex CLI）。

---

## 3. 第一次初始化岗位

### 3.1 什么时候运行

第一次打开自己的工作区后，先运行：

```text
/lbai-init
```

以后岗位职责或对话习惯变化时，也可以再次运行。

### 3.2 它会问什么

工作区助手会问一些简单问题，包括：

- 用户姓名
- 岗位名称
- 主要职责
- 对话习惯，例如简洁、详细、先给结论再给依据

你按实际情况回答即可，不需要正式措辞。

### 3.3 它会保存到哪里

`/lbai-init` 只会更新：

```text
role_workspace/world_model/
role_workspace/archive/
```

其中 `role_workspace/world_model/ROLE_PROFILE_v1.json` 会保存服务端可检索的员工画像字段：`employee_user_name`、`employee_position` 和 `conversation_preference`。

它不会修改公司模板文件，也不会创建业务任务。它写入的是员工自己的 `role_workspace/`，不是 `lbai_system/templates/role_workspace/`。

---

## 4. 日常怎么使用

### 4.0 可选：先保存资料或知识

如果你只是想提交会议记录、用户反馈、邮件、草稿、SOP、日志或背景资料，不想立刻创建任务，在 **Cursor 或 Codex 桌面 App** 中运行：

```text
/lbai-add-evidence
```

然后直接粘贴资料。

**不要**在终端单独运行 `lbai add-evidence`；也不要使用 Codex CLI。AI 不可用时会直接失败，不会降级为规则处理。

### 4.0a 资料归档怎么分工

| 环节 | 执行方 | 说明 |
|------|--------|------|
| Teams 转写清洗 | AI | 去掉 UI 垃圾、时间戳噪声，写入 `cleaned_content` |
| 轻量元数据 | AI | 标题、资料类型、来源、可见范围、关联对象 |
| 后端入库提示 | AI | 给后端分片、索引、权限判断提供 hint，不在员工端分析事实 |
| review 初判 | AI | `admissibility_status`、`review_reasons` |
| review 判定 | AI | enrichment 中 `admissibility_status` / `review_needed`；代码不做关键词 overlay |
| 脱敏 | 代码 | 密钥、手机号等正则替换 |
| 目录 / 台账 / git / hygiene | 代码 | 确定性落盘与同步 |

AI 必须先按 prompt 产出 JSON：

```text
lbai_system/prompts/evidence_enrichment_prompt_v1.md
lbai_system/schemas/evidence_enrichment_schema_v1.json
```

然后调用：

```bash
python3 lbai_system/tools/add_evidence.py --enrichment <json_path> --content "..."
```

Cursor / Codex 桌面里的助手会自动完成「生成 JSON + 调脚本」两步；员工只需粘贴资料。

落盘后会创建一个 OKF Concept：

```text
role_workspace/knowledge/references/YYYY_MM_DD_<source_type>_<short_hash>.md
```

还会：

- 写入 OKF YAML frontmatter、稳定 UID、正文和 citations
- 更新 `role_workspace/knowledge/index.md` 与 `role_workspace/knowledge/log.md`
- 文件名使用日期、资料类型和短 hash，不把原始资料正文放进路径
- 代码侧自动脱敏
- 标记资料状态，例如 `CAPTURED` 或 `NEEDS_REVIEW`
- 标记后端入库状态：已 push 时为 `PENDING_BACKEND_SYNC`，否则为 `NOT_SYNCED`
- 如果资料适合形成任务，只给出建议，不自动创建任务
- 检查通过后只同步当前 Concept、`index.md` 和 `log.md`

如果资料已经本地归档，但 GitHub 同步因为 hygiene check、remote/upstream 或 push 问题被阻断，系统会保留本地 Concept，并输出 `sync_status: BLOCKED` 或 `PUSH_FAILED`。这表示同步未完成，不表示资料没有保存。

Evidence 与 task 保持独立：`/lbai-add-evidence` 不记录 `related_tasks`，也不会自动修改任务的 `missing_inputs.md`、`task_scope.md`、`task_ledger.md` 或 `gap_record.md`。

如果这份资料确实补齐了任务所需输入，请在当前任务对话中说明它补充了哪项信息；`/lbai-new-task` 和 `/lbai-execute-task` 会继续在本地判断 `missing_inputs`，并决定任务是否可以执行。

如果 evidence 涉及对外发布边界，资料会标记 `NEEDS_REVIEW`，并在对话中提醒负责人 review。

注意：`/lbai-add-evidence` 不会自动创建任务。正式任务仍需要你确认，或使用 `/lbai-new-task` 创建。

### 4.0b 可选：查询后端知识

在 **Cursor 或 Codex 桌面 App** 中运行：

```text
/lbai-search-artifacts 记忆单元 ladder
```

流程：

1. Agent 按 `lbai_system/prompts/backend_search_query_plan_prompt_v1.md` 生成后端搜索 query plan
2. 调用 `.lbai/workspace.json` 配置的后端 knowledge service，并显示 FOUND / NO_MATCH / ERROR
3. 如果后端未启用、不可用、超时、没有命中或返回无效数据，只展示结果或错误，不搜索本地 evidence、任务或 references，也不自动阻断、修改或推进其他任务流程

只读，不会改任务状态或自动关联。

如果你决定使用某个候选资料，需要在 `/lbai-new-task` 或当前任务 artifacts 中明确引用来源和使用方式。

### 4.1 第一步：创建任务

当你要做一件需要留下记录的工作时，先运行：

```text
/lbai-new-task 你的任务描述
```

例如：

```text
/lbai-new-task 整理今天市场会议纪要和 action items
```

如果当前对话里任务已经很清楚，也可以只输入：

```text
/lbai-new-task
```

如果工作区助手不确定你要做哪件事，它会让你补充一句任务描述。

### 4.2 第二步：补充资料

如果工作区助手说缺信息，先看缺口类型：普通说明、偏好、决策可以直接在对话框回复；会议记录、客户材料、邮件、原始转写、研究资料等资料型来源，再按提示使用 `/lbai-add-evidence` 独立归档。Cursor/Codex 也可以在你直接粘贴资料型内容时，按项目规则把内容保存成 evidence。

常见可以粘贴的内容包括：

- 会议全文
- 会议笔记
- 用户反馈
- 访谈记录
- 文案草稿
- 产品说明
- 数据表说明

工作区助手会把资料型来源保存为独立 evidence；普通对话补充会保存在当前任务文件夹。任务输入文件可能包括：

```text
input_transcript.md
input_feedback.md
input_draft.md
input_source.md
input_user_provided.md
```

如果你粘贴的内容里有 API key、token、密码、手机号等敏感信息，工作区助手会尽量自动脱敏，避免把敏感信息写进公司 repo。邮箱地址不会按敏感信息处理。包含官网、对外承诺、价格、法律、投资人、媒体、客户承诺、安全或财务等内容的草稿，会被标记为需要 review。

### 4.3 第三步：执行任务

任务缺口补齐、状态回到 `OPEN` 后，运行：

```text
/lbai-execute-task
```

如果有多个任务，工作区助手会列出来让你选择，不会随便猜。

`/lbai-execute-task` 会读取任务要求、linked evidence、旧版 task-local 输入、岗位记忆和公司边界，先写入 `execution_plan.md`，再生成 `task_output.md`。如果还有缺口，它应继续更新任务 artifacts，而不是只把缺口留在聊天里。

### 4.4 第四步：收尾并同步

任务执行完后，运行：

```text
/lbai-finish-task
```

它会：

- 检查任务文件是否齐全
- 更新任务记录
- 更新总任务台账
- 把 linked evidence 写入任务和总台账的来源字段
- 检查敏感信息和临时文件
- 判断能否安全提交到 GitHub
- 检查通过后只提交当前任务文件夹和 `role_workspace/ledgers/TASK_LEDGER_v1.md`，并推送到当前 private GitHub upstream

它会显示：

```text
task_status
commit_readiness
git_status
```

`PUSHED` 表示已经同步到 private GitHub。

如果任务缺少 `task_output.md`、仍有 `missing_inputs.md` 未解决、缺少 Git remote/upstream，或卫生检查发现敏感信息/非允许范围变更，收尾会返回 `BLOCKED` 或 `PUSH_FAILED`，不会把任务当作完成。

---

## 5. 更新公司模板

### 5.1 什么时候更新

当管理员通知模板有新版时，在 Cursor 或 Codex 输入：

```text
/lbai-update-kit
```

### 5.2 它会更新什么

`/lbai-update-kit` 会调用同一套 `lbai update-kit` 底层流程，从已安装的 `lbai-workspace-kit` 同步公司维护的工作流文件：

```text
.cursor/
.agents/
lbai_system/
.gitignore
AGENTS.md
README.md
workspace_dashboard.html
.lbai/workspace.json
```

如果需要先升级本机 `lbai` 命令，按公司发布的新版安装方式重新安装后，再在当前工作区运行 `lbai update-kit` 或 `/lbai-update-kit`。

其中 `lbai_system/templates/role_workspace/` 也属于公司维护的模板层，可以随新版一起更新。

它不会修改：

```text
role_workspace/
tasks/
```

如果 `role_workspace/` 或 `tasks/` 里还有本地变更，模板更新不会把它们作为公司模板文件覆盖。需要同步这些员工内容时，应按资料或任务流程分别使用 `/lbai-add-evidence` 或 `/lbai-finish-task`。

因此，如果公司更新了岗位默认模板：

```text
会更新：lbai_system/templates/role_workspace/
不会覆盖：role_workspace/
```

老员工自己的岗位记忆继续保留。新员工后续拿到新版仓库，或者老员工缺失某个岗位文件时，才会使用新版默认模板补齐。

### 5.3 手动升级公共模板

如果 `/lbai-update-kit` 暂时不可用，或者管理员要求手动升级，也可以从新版 `lbai-workspace-kit` 的 `workspace_template/` 手动合入当前工作区。

手动升级只允许覆盖这些公共模板和工作流文件：

```text
.cursor/
.agents/
lbai_system/
.gitignore
AGENTS.md
README.md
workspace_dashboard.html
.lbai/workspace.json
```

不要覆盖这些员工个人文件：

```text
role_workspace/
tasks/
```

推荐流程：

1. 从公司发布的新版 `lbai-workspace-kit` 获取 `workspace_template/`。
2. 只复制上面列出的公共模板和工作流路径。
3. 保留当前仓库里的 `role_workspace/` 和 `tasks/`。
4. 运行 `lbai doctor`，再打开 `workspace_dashboard.html` 或运行一次普通任务，确认工作区能正常读取岗位信息和任务记录。
5. 确认无误后，再提交并同步到员工自己的 private GitHub 仓库。

换句话说，手动升级更新的是“工作流机器”和“默认模板”，不是员工自己的岗位知识库。已有岗位设定、任务输入、任务输出、任务台账和历史沉淀都应保留。

### 5.4 如果误改了模板文件

如果你不小心改过公司维护的 workflow 文件，例如 `.cursor/`、`lbai_system/`、`.gitignore`、`AGENTS.md`、`README.md` 或 `workspace_dashboard.html`，系统会先列出被改过的文件，并让你选择：

```text
覆盖升级
暂不升级
```

选择 `覆盖升级` 会丢弃这些公司维护 workflow 文件里的本地改动，并继续升级；不会覆盖 `role_workspace/` 或 `tasks/`。

不确定时请选择 `暂不升级`，再联系管理员确认。

---

## 6. 哪些内容需要提醒负责人 review

以下内容在对外发布前，一般需要负责人 review。工作区助手会在对话中提醒你，但**不会因此阻断任务执行或收尾**：

- 官网文案
- 对外发布内容
- 公司定位说明
- 价格、套餐、报价
- 法律或合规相关内容
- 投资人材料
- 媒体稿
- 产品能力承诺
- 客户承诺
- 安全、财务、招聘敏感内容

如果任务涉及上述内容，生成结果并收尾后，工作区助手会：

- 在对话中明确提醒「对外发布前请负责人 review」
- 在 artifact 中保留 `review_needed: true` 和 `leader_review_reminder`
- 任务状态仍为 `COMPLETED`（不再使用 `WAITING_REVIEW` 阻断）

这不代表可以未经负责人确认就对外发布。private GitHub 同步也不代表内容已经获批。

---

## 7. 常见用法

### 7.1 会议纪要

```text
/lbai-new-task 整理今天市场会议纪要和 action items
```

工作区助手让你补会议全文后，先独立归档 evidence：

```text
/lbai-add-evidence
```

然后粘贴会议内容，并回到任务对话说明这份资料补充了会议全文。任务缺口补齐、状态回到 `OPEN` 后再运行：


```text
/lbai-execute-task
/lbai-finish-task
```

### 7.2 用户反馈整理

```text
/lbai-new-task 整理用户反馈并提炼产品问题
```

补充用户反馈：

```text
/lbai-add-evidence
```

然后粘贴用户反馈，并回到任务对话说明这份资料补充了用户反馈。任务缺口补齐、状态回到 `OPEN` 后运行：


```text
/lbai-execute-task
/lbai-finish-task
```

### 7.3 内部周报

```text
/lbai-new-task 整理本周内容运营周报，不对外发布
```

补充本周材料：

```text
/lbai-add-evidence
```

然后运行：

```text
/lbai-execute-task
/lbai-finish-task
```

### 7.4 官网或对外文案

```text
/lbai-new-task 根据这段产品说明写官网首页中文文案
```

补充产品说明或草稿时，用：

```text
/lbai-add-evidence
```

如果资料或任务涉及官网、对外发布、产品能力承诺等 review 边界，资料可能标记 `NEEDS_REVIEW`，对话中会提醒负责人 review。任务仍可正常执行和收尾。

请在外部渠道交给负责人确认后再发布，不要直接对外发送。

---

## 8. 本地看板

看板文件位于仓库根目录：

```text
workspace_dashboard.html
```

这个页面不会上传数据，也不会修改文件。它会读取工作区里的 Markdown 文件，并显示：

- 岗位名称、岗位目标和角色边界
- 最近任务、任务状态、review 状态和 GitHub 同步状态
- evidence 数量、最近 evidence、linked task、review 状态和同步状态
- 常用命令里包含 `/lbai-search-artifacts`，用于提示后端知识查询入口
- 阻断事项和下一步依赖
- 常用 `/lbai-*` 命令
- 公司 review 边界和敏感信息边界

### 8.1 为什么双击打开可能读不到数据

路径本身没有问题。浏览器在 `file://` 模式下通常会禁止页面用 `fetch()` 读取同目录 Markdown，所以看板会提示“未能读取”。

这不是 `tasks/` 或 `role_workspace/` 路径写错，而是浏览器安全限制。

### 8.2 推荐打开方式

方式 A：点击看板里的「选择工作区文件夹」，选中当前 LBAI 仓库根目录。

方式 B：启动本地 HTTP 服务后再打开：

```text
python3 lbai_system/tools/serve_dashboard.py
```

然后在浏览器访问：

```text
http://127.0.0.1:8765/workspace_dashboard.html
```

如果看不到最新任务，通常是因为还没有运行 `/lbai-finish-task` 更新总任务台账。如果看不到最新知识，通常是因为还没有运行 `/lbai-add-evidence`，或 `role_workspace/knowledge/index.md` 尚未更新。

---

## 9. 你不需要做什么

你不需要：

- 手动创建任务模板
- 手动维护 task scope
- 手动维护 task slot
- 手动创建输入文件
- 手动维护 evidence metadata
- 手动判断是否把资料自动变成任务
- 记住单独的提交前检查命令
- 手动运行 git add / commit / push
- 自己判断所有 review 规则

工作区助手会负责提醒、建档、保存 evidence、记录资料与任务关系、生成结果、更新记录和检查提交状态。AI 可以建议任务，但不会因为你保存资料就自动创建任务。

---

## 10. 一句话记住

```text
/lbai-init 配置岗位
/lbai-add-evidence 保存资料
/lbai-search-artifacts 查询后端知识
/lbai-new-task 建档
/lbai-execute-task 执行
/lbai-finish-task 收尾
/lbai-update-kit 更新公司模版
```
