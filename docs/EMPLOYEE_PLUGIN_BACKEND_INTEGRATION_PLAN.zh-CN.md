# 员工端插件接入后端知识服务修改清单与方案

## 1. 目标

在保持当前 LBAI Workspace Kit 轻量安装和 `/lbai-*` 工作流的前提下，升级员工端插件能力：

```text
资料提交：员工端只提交到 GitHub private workspace
资料处理：后端监听 GitHub 更新后异步整理入库
资料查询：员工端通过后端 API 查询公司知识证据包
AI 执行：Cursor / Codex 基于证据包完成任务
```

## 2. 当前项目现状

当前项目已经具备：

```text
lbai CLI 安装和初始化员工 private workspace
Cursor / Codex /lbai-* 命令
/lbai-add-evidence 资料提交
/lbai-search-artifacts 本地资料搜索
资料元数据补齐 + Python 落盘
Git commit / push 到员工 GitHub workspace
```

当前 `/lbai-add-evidence` 已经比较接近目标形态：

```text
插件接收原始资料
Python 保存原文和 metadata
更新 EVIDENCE_LEDGER_v1.md
git commit / push 到 private GitHub repo
```

需要进一步收窄的是：

```text
员工端不再分析原文，不生成 usable_facts / decisions / action_items / risks。
员工端只补齐资料来源、时间、可见范围等元数据。
资料理解、事实抽取和任务关联分析统一交给后端。
```

需要重点改造的是：

```text
/lbai-search-artifacts 从本地 catalog 搜索，升级为调用后端知识检索 API。
```

## 3. 总体方案

```text
员工提交资料
  ↓
/lbai-add-evidence 写入 private GitHub workspace
  ↓
git push
  ↓
后端通过 GitHub webhook / 定时同步拉取更新
  ↓
后端 JSON 化、校验、fact_event 入库
  ↓
员工发起新任务或搜索
  ↓
/lbai-search-artifacts 调用后端检索 API
  ↓
后端返回 evidence_pack
  ↓
Cursor / Codex AI 使用证据包完成任务
```

## 4. 员工端职责

员工端保持轻量，只做：

```text
资料提交
资料来源和时间补齐
基础敏感信息扫描
任务发起
本地任务记录
GitHub 同步
后端检索 API 调用
证据包交给 AI 使用
```

员工端不做：

```text
公司级资料入库
事实抽取重处理
原文语义分析
资料提交阶段的任务缺口覆盖分析
统一知识库维护
向量数据库
跨员工权限裁决
最终事实裁决
```

说明：

```text
/lbai-add-evidence 不再判断一份资料是否覆盖某个任务缺口。
/lbai-new-task 和 /lbai-execute-task 仍需要在本地判断 missing_inputs，
否则任务是否可以执行没有入口。
```

## 5. 后端职责

后端负责：

```text
监听多个员工 workspace repo
拉取新增或变更资料
解析 evidence/task/ledger 文件
事实抽取 JSON 化
Schema 校验
fact_event 入库
关键词 / 同义词搜索
候选事件 LLM 相关性判断
权限过滤
最新事实裁决
证据包返回
同步和查询日志
```

## 6. 必须修改清单

资料提交格式详见：

```text
docs/EMPLOYEE_EVIDENCE_SUBMISSION_FORMAT.zh-CN.md
```

### 6.1 增加后端配置

需要在员工 workspace 中支持员工身份和后端服务配置。员工身份是后续资料上传人、权限过滤、审计追踪的基础字段。

建议新增或扩展：

```text
.lbai/workspace.json
```

新增字段：

```json
{
  "employee_identity": {
    "employee_user_id": "zhangsan",
    "display_name": "张三",
    "email": "zhangsan@company.com",
    "department": "product"
  },
  "knowledge_service": {
    "enabled": true,
    "base_url": "https://workflow-kit.lbai.ai",
    "api_key_header": "X-LBAI-API-Key",
    "auth_mode": "local_api_key",
    "workspace_repo_id": "lbai-workspace-zhangsan",
    "search_timeout_seconds": 20
  }
}
```

注意：

```text
employee_user_id 必须在初始化工作区时采集
display_name / email / department 可由员工输入或管理员配置
后续 /lbai-add-evidence 自动写入 submitted_by，不依赖员工每次手填
不要把长期 API token 写入 repo；后端 API Key 通过 lbai auth backend-login 保存在 ~/.lbai/auth/knowledge_service.json
员工身份认证优先走本机安全存储、环境变量、SSO 或 GitHub 身份映射
```

身份字段边界：

```text
.lbai/workspace.json 保存技术身份和后端服务配置：
- employee_user_id
- email
- department
- workspace_repo_id

role_workspace/world_model/ROLE_PROFILE_v1.json 保存岗位画像：
- employee_user_name
- employee_position
- conversation_preference

后端检索、权限、审计、submitted_by 使用 .lbai/workspace.json。
岗位经验聚合、角色化上下文和对话偏好使用 ROLE_PROFILE_v1.json。
不要把两个文件都当作同一类身份信息的权威来源。
```

涉及文件：

```text
lbai_core/lbai/cli.py
workspace_template/.lbai/workspace.json 生成逻辑
workspace_template/lbai_system/tools/task_utils.py
```

初始化流程需要增加：

```text
lbai init-workspace
  ↓
输入或确认员工用户名 employee_user_id
  ↓
可选输入 display_name / email / department
  ↓
写入 .lbai/workspace.json
  ↓
后续资料提交自动使用该身份
```

### 6.2 改造 `/lbai-search-artifacts`

当前逻辑：

```text
本地导出 catalog
AI 对 catalog 做语义排序
返回本地 artifact
```

目标逻辑：

```text
读取员工查询
读取 workspace 后端配置
调用后端 /v1/search/evidence
返回后端 evidence_pack
后端不可用时直接阻断员工搜索命令
```

推荐执行顺序：

```text
1. 如果 knowledge_service.enabled = true，优先调用后端 API
2. 后端返回 FOUND，直接展示 evidence_pack
3. 后端返回 NO_MATCH，展示无匹配和下一步建议
4. 后端不可用、无结果或返回错误时，只展示后端搜索结果或错误，不执行本地搜索，也不自动阻断、修改或推进其他任务流程
```

涉及文件：

```text
workspace_template/lbai_system/tools/search_artifacts.py
workspace_template/.cursor/commands/lbai-search-artifacts.md
workspace_template/.agents/skills/lbai-search-artifacts/SKILL.md
workspace_template/lbai_system/cursor/skills/lbai-search-artifacts/SKILL.md
```

建议新增工具：

```text
workspace_template/lbai_system/tools/search_backend.py
```

职责：

```text
读取后端配置
构造 search request
调用后端 API
校验 response schema
渲染 evidence_pack
失败时返回明确状态
```

### 6.3 新增后端检索响应 Schema

员工端需要校验后端返回，避免把不合规结果直接交给 AI。

建议新增：

```text
workspace_template/lbai_system/schemas/backend_evidence_search_response_schema_v1.json
```

核心字段：

```json
{
  "schema_version": "backend_evidence_search_response_v1",
  "query_status": "FOUND",
  "evidence_pack": [],
  "open_questions": [],
  "conflicts": [],
  "next_step": "Use returned evidence as task context."
}
```

### 6.4 调整 `/lbai-search-artifacts` Prompt

当前 prompt 让 AI 对本地 catalog 排序。

目标 prompt 改为：

```text
AI 负责理解员工查询，生成 query_plan。
Python 工具负责调用后端。
后端负责搜索和返回证据包。
AI 不再对本地全量 catalog 做主搜索。
```

query_plan 示例：

```json
{
  "schema_version": "backend_search_query_plan_v1",
  "query": "整理提车前要准备什么",
  "keywords": ["提车", "购车", "买车", "车辆交付"],
  "concepts": ["company_vehicle_purchase"],
  "entity_types": ["decision", "policy", "action_item", "open_question"],
  "prefer_status": ["confirmed", "open"],
  "limit": 10
}
```

建议新增：

```text
workspace_template/lbai_system/schemas/backend_search_query_plan_schema_v1.json
workspace_template/lbai_system/prompts/backend_search_query_plan_prompt_v1.md
```

### 6.5 明确 `/lbai-add-evidence` 仍只提交 GitHub

当前 `/lbai-add-evidence` 不需要改成直接调用后端。

需要做的是接收原始资料、补齐基础 metadata、做确定性敏感信息扫描，方便后端识别和入库。

建议把员工端 evidence 文件调整为：

```text
raw.md                  已脱敏、轻度清理后的资料正文
metadata.json           员工或插件补齐的元数据
attachments/            可选附件目录
```

历史 workspace 可能存在：

```text
input.md
evidence_metadata.md
evidence_brief.md
```

新资料不再生成这些旧文件；后端同步可按需兼容读取。语义上应把旧文件视为：

```text
input.md = 已脱敏、轻度清理后的资料正文
evidence_metadata.md = 元数据，不是事实分析结果
evidence_brief.md = 历史 AI 摘要，不作为新主产物
```

建议在 metadata 中增加：

```text
title
source_type
source_origin
source_occurred_at
submitted_at
submitted_by
submitted_by_display_name
submitted_by_email
source_visibility
related_objects
backend_ingestion_status
backend_ingestion_hint
sensitive_scan_status
redacted
content_hash
```

示例：

```json
{
  "title": "6月购车讨论会议纪要",
  "source_type": "meeting_note",
  "source_origin": "飞书会议转写",
  "source_occurred_at": "2026-06-10",
  "submitted_at": "2026-06-12",
  "submitted_by": "zhangsan",
  "submitted_by_display_name": "张三",
  "submitted_by_email": "zhangsan@company.com",
  "source_visibility": "team",
  "related_objects": ["company_vehicle_purchase"],
  "sensitive_scan_status": "passed",
  "redacted": false,
  "backend_ingestion_status": "PENDING_GITHUB_SYNC"
}
```

其中：

```text
source_type 用于后端判断资料类型
source_origin 用于记录资料来自哪里，例如会议转写、公司章程、制度文件
source_occurred_at 用于后端判断资料实际发生时间
submitted_by 来自 .lbai/workspace.json 的 employee_user_id
source_visibility 用于后端权限初筛
related_objects 是员工可选填写的关联对象，不要求准确完整
backend_ingestion_status 仅是员工端提示，最终状态以后端为准
```

如果继续使用 Markdown metadata，可写为：

```text
## backend_ingestion_status
PENDING_GITHUB_SYNC

## backend_ingestion_hint
source_for_company_knowledge

## source_visibility
private | team | company

## source_occurred_at
<date or unknown>
```

涉及文件：

```text
workspace_template/lbai_system/tools/add_evidence.py
workspace_template/lbai_system/schemas/evidence_enrichment_schema_v1.json
workspace_template/lbai_system/prompts/evidence_enrichment_prompt_v1.md
```

### 6.6 调整 `/lbai-add-evidence` 预处理边界

员工端只做确定性和元数据级处理：

```text
接收原始资料
保留原文
基础格式清理
补齐资料标题
补齐资料来源
补齐资料发生时间
从 workspace 配置读取提交人身份
补齐提交时间
补齐可见范围建议
补齐相关项目/客户/任务等可选标签
确定性敏感信息扫描
必要时本地脱敏保存
写入 GitHub workspace
```

员工端不做：

```text
usable_facts 提取
decisions 提取
action_items 提取
risks 提取
missing_info 分析
资料提交阶段的任务 missing_inputs 覆盖分析
完整事实字典映射
fact_event 生成
公司级冲突判断
最新事实裁决
跨资料关联分析
```

这些统一放到后端或任务阶段处理。其中 `/lbai-new-task` 和 `/lbai-execute-task` 仍需要在本地判断任务是否存在 blocking `missing_inputs`。

原来的 `gap_analysis` 用于“某个任务缺资料时，用户直接给任务补证据，由插件判断是否覆盖缺口”。在新方案中，主流程改为：

```text
先提交资料
后端异步入库
任务执行时再调用后端检索证据包
任务阶段 AI 判断信息是否充足
```

因此 `/lbai-add-evidence` 主流程不再需要关联任务缺口分析。

### 6.7 更新命令说明和 README

需要更新员工文档：

```text
README.zh-CN.md
README.md
docs/EMPLOYEE_FAQ.zh-CN.md
workspace_template/lbai_system/docs/QUICK_TEST.md
workspace_template/lbai_system/docs/CURSOR_MANUAL_TEST_CASE.md
```

重点说明：

```text
/lbai-add-evidence：资料提交到 GitHub，后端异步入库
/lbai-search-artifacts：优先查询后端公司知识服务
后端不可用时：显示明确错误并阻断员工搜索命令
```

## 7. 建议修改清单

### 7.1 后端同步状态提示

员工提交资料后，可以查看后端是否已处理。

不新增命令。第一版只在 `/lbai-add-evidence` 和 `/lbai-search-artifacts` 返回中提示：

```text
资料已 push 到 GitHub；后端将异步入库。可稍后搜索。
```

后续如确实需要，再把状态查询合并进现有 `/lbai-search-artifacts` 或 `lbai doctor`，不单独增加员工常用命令。

### 7.2 `/lbai-finish-task` 增加岗位经验沉淀

不新增命令，直接复用 `/lbai-finish-task`。

任务完成时，AI 根据任务过程生成岗位经验反馈候选，用户确认后写入任务目录并随任务一起提交到 GitHub。后端通过 GitHub 同步读取同岗位多人的反馈，整理成岗位级工作习惯、检查项和 AI 防错规则。员工执行任务时通过 API 获取岗位经验上下文。

可沉淀内容：

```text
处理某类任务的关注点
AI 多次出错的点
岗位常见检查项
岗位交付偏好
下次同类任务应先查的资料
```

员工端不维护权威岗位记忆文件。第一版可在任务目录中临时保存候选，便于用户 review：

```text
tasks/<task>/role_memory_feedback.json
tasks/<task>/role_memory_feedback.md
```

后端提供岗位经验上下文接口：

```text
POST /v1/role-memory/context
```

具体方案见：

```text
docs/ROLE_MEMORY_CAPTURE_PLAN.zh-CN.md
```

### 7.3 本地搜索不再作为员工命令 fallback

员工侧 `/lbai-search-artifacts` 只调用后端 knowledge service。旧本地 catalog 能力不再作为员工命令路径，用于历史开发调试时也必须和员工命令隔离：

```text
后端不可用
员工离线
调试本地 workspace
查找当前员工个人未入库资料
```

但产品默认路径应为：

```text
后端搜索优先
本地搜索备用
```

### 7.4 搜索结果写入任务上下文

当新任务调用后端检索后，建议将 evidence_pack 的引用写入任务目录：

```text
不写入任务级 `retrieved_context.json/md`
```

作用：

```text
记录 AI 使用了哪些背景
方便 review
方便 /lbai-finish-task 检查证据来源
```

边界：

```text
搜索结果只在当前命令响应中展示，用来说明当时后端返回了哪些证据。
它不是权威知识库，也不代表后端最新事实。
后续任务应重新调用后端检索，而不是复用旧搜索结果作为最新依据。
```

涉及文件：

```text
workspace_template/lbai_system/tools/new_task.py
workspace_template/lbai_system/tools/prepare_execute_task.py
workspace_template/lbai_system/prompts/execute_task_plan_prompt_v1.md
```

### 7.5 增加后端可用性检查

扩展：

```text
lbai doctor
```

检查：

```text
knowledge_service.enabled
base_url 是否配置
employee_identity.employee_user_id 是否配置
后端健康检查是否通过
员工身份是否可识别
```

涉及文件：

```text
lbai_core/lbai/cli.py
workspace_template/lbai_system/tools/bootstrap_check.py
workspace_template/lbai_system/tools/hygiene_check.py
```

## 8. 暂不修改

以下能力放到后端或后续阶段，不在员工插件第一版实现：

```text
向量数据库
fact_event 生成
公司级事实字典治理
跨员工资料冲突裁决
复杂权限审批
自动将后端入库状态写回 GitHub
```

## 9. 推荐实施步骤

### 阶段 1：员工端搜索接后端

改动：

```text
新增 knowledge_service 配置
新增 search_backend.py
新增后端 response schema
改造 /lbai-search-artifacts 优先调用后端
不保留员工命令本地 fallback
```

交付效果：

```text
员工新任务或查询时，可以拿到后端 evidence_pack。
```

### 阶段 2：资料提交 metadata 轻量增强

改动：

```text
init-workspace 增加员工用户名采集
workspace.json 增加 employee_identity
add_evidence.py 增加 backend_ingestion_status
将 evidence_enrichment_schema 调整为 evidence_metadata_schema
增加 source_occurred_at / source_visibility / source_origin / related_objects / submitted_by
移除 usable_facts / decisions / action_items / risks / gap_analysis 等分析字段
add-evidence prompt 改为元数据补齐提示，不分析原文
```

交付效果：

```text
后端更容易识别资料来源、权限、时间和上传人；原文分析统一在后端完成。
```

### 阶段 3：任务上下文落盘

改动：

```text
新任务或执行任务前调用后端检索
直接展示 evidence_pack，不写入 retrieved_context.json/md
execute prompt 明确只参考用户显式提供的后端搜索结果
```

交付效果：

```text
每个任务都有可追溯的后端检索背景。
```

### 阶段 4：doctor 和状态提示

改动：

```text
lbai doctor 检查后端服务可用性
/lbai-add-evidence 返回后端异步入库说明
/lbai-search-artifacts 返回后端状态
```

交付效果：

```text
员工知道资料已提交，搜索失败时知道是后端、权限还是无匹配问题。
```

### 阶段 5：岗位经验沉淀

改动：

```text
finish_review_enrichment_prompt 增加 role_memory_feedback_candidates
finish_review_enrichment_schema 增加岗位经验反馈候选字段
finish_task.py 写入 role_memory_feedback.md/json
role_memory_feedback 随任务 commit / push 到 GitHub
后端通过 GitHub 同步读取岗位经验反馈
新任务和执行任务前调用后端 /v1/role-memory/context
prompt 使用后端返回的岗位经验上下文
```

交付效果：

```text
每次任务结束都能提交岗位经验反馈；后端汇总同岗位多人反馈，任务执行时通过 API 返回合理的岗位工作习惯。
```

## 10. API 对接建议

员工端调用：

```text
POST /v1/search/evidence
```

请求：

```json
{
  "workspace_repo_id": "lbai-workspace-zhangsan",
  "task_text": "整理提车前要准备什么",
  "query_plan": {
    "keywords": ["提车", "购车", "车辆交付"],
    "concepts": ["company_vehicle_purchase"],
    "entity_types": ["decision", "policy", "action_item"],
    "prefer_status": ["confirmed", "open"]
  },
  "limit": 10
}
```

返回：

```json
{
  "schema_version": "backend_evidence_search_response_v1",
  "query_status": "FOUND",
  "evidence_pack": [
    {
      "event_id": "evt_xxx",
      "subject": "公司购车",
      "entity_type": "policy",
      "value": "提车前需确认保险、上牌、付款凭证、经办人身份证明",
      "status": "confirmed",
      "source": {
        "repo_id": "lbai-workspace-lisi",
        "path": "evidence/vehicle/raw.md",
        "commit_sha": "abc123"
      },
      "evidence_text": "车辆交付前需要确认保险、上牌、付款凭证。",
      "reason": "与当前任务主题相关"
    }
  ],
  "open_questions": [],
  "conflicts": [],
  "next_step": "Use evidence_pack as task context."
}
```

## 11. 对现有文件的具体修改列表

### 必改

```text
workspace_template/lbai_system/tools/search_artifacts.py
workspace_template/lbai_system/tools/search_backend.py
workspace_template/lbai_system/schemas/backend_evidence_search_response_schema_v1.json
workspace_template/lbai_system/schemas/backend_search_query_plan_schema_v1.json
workspace_template/lbai_system/prompts/backend_search_query_plan_prompt_v1.md
workspace_template/.cursor/commands/lbai-search-artifacts.md
workspace_template/.agents/skills/lbai-search-artifacts/SKILL.md
README.zh-CN.md
docs/EMPLOYEE_FAQ.zh-CN.md
```

### 建议改

```text
workspace_template/lbai_system/tools/add_evidence.py
workspace_template/lbai_system/schemas/evidence_enrichment_schema_v1.json
workspace_template/lbai_system/prompts/evidence_enrichment_prompt_v1.md
workspace_template/.cursor/commands/lbai-add-evidence.md
workspace_template/.agents/skills/lbai-add-evidence/SKILL.md
lbai_core/lbai/cli.py
workspace_template/lbai_system/tools/bootstrap_check.py
workspace_template/.lbai/workspace.json
```

### 后续改

```text
workspace_template/lbai_system/tools/new_task.py
workspace_template/lbai_system/tools/prepare_execute_task.py
workspace_template/lbai_system/tools/finish_task.py
workspace_template/lbai_system/prompts/finish_review_enrichment_prompt_v1.md
workspace_template/lbai_system/schemas/finish_review_enrichment_schema_v1.json
workspace_template/lbai_system/prompts/execute_task_plan_prompt_v1.md
workspace_template/lbai_system/schemas/task_intake_enrichment_schema_v1.json
```

## 12. 简版结论

员工端插件改造应保持轻量：

```text
/lbai-add-evidence 继续只写 GitHub
/lbai-add-evidence 只做原文提交、元数据补齐和基础敏感扫描
后端监听 GitHub 更新并入库
/lbai-search-artifacts 改为优先调用后端 API
本地搜索不作为员工命令 fallback
任务执行时使用后端返回的 evidence_pack
/lbai-finish-task 负责生成岗位经验反馈候选，确认后写入任务目录并提交 GitHub
任务执行时通过后端 API 获取岗位经验上下文
```

这样既保留现有 GitHub workspace 工作流，又能让后端集中沉淀公司知识，减少员工端复杂度。
