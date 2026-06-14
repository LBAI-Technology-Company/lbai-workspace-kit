# LBAI 后端知识服务产品技术说明书

## 1. 目标

建设一个集中式后端知识服务，用于同步多个员工 GitHub workspace 的最新资料，将资料整理为结构化事实和可查询证据包，供员工插件在新任务中自动检索公司背景。

核心目标：

```text
员工插件只负责把资料提交到 GitHub。
后端服务负责同步 GitHub 更新、整理入库、检索和返回证据包。
```

最终效果：

```text
员工发起新任务
  ↓
插件调用后端检索
  ↓
后端返回相关历史资料、最新决策、证据和开放问题
  ↓
Cursor / Codex AI 基于证据完成任务
```

## 2. 总体架构

```text
多个员工 private GitHub workspace
  ↓
GitHub webhook / 定时同步
  ↓
后端同步服务
  ↓
文件变更识别
  ↓
文档解析
  ↓
事实抽取 JSON
  ↓
Schema 校验
  ↓
fact_event 生成
  ↓
结构化数据库 + 原文存储 + 检索服务
  ↓
知识检索 API
  ↓
员工插件 / Cursor / Codex
```

## 3. 系统边界

### 员工插件负责

```text
使用现有 /lbai-add-evidence 提交资料
将资料、元数据、AI enrichment 写入员工 private GitHub workspace
commit / push 到 GitHub
发起任务或搜索时由 AI 先生成 backend_search_query_plan_v1
调用后端 POST /v1/search/evidence 检索 API
把后端返回的证据包交给 Cursor / Codex AI
后端不可用、无匹配或返回错误时，只展示后端结果，不回退本地搜索
```

### 后端服务负责

```text
同步多个 GitHub workspace 的更新
解析新增或变更资料
对资料进行事实抽取和 JSON 化
校验 JSON 结构和字段
生成 fact_event
构建关键词索引、同义词索引和 LLM 相关性筛选流程
根据权限过滤资料
返回结构化证据包
记录同步、检索和引用日志
```

## 4. 核心数据来源

后端主要读取员工 workspace 中的标准文件。

### evidence 资料

```text
role_workspace/knowledge/evidence/<evidence_id>/raw.md
role_workspace/knowledge/evidence/<evidence_id>/metadata.json
role_workspace/knowledge/evidence/<evidence_id>/evidence_enrichment.json
role_workspace/knowledge/evidence/<evidence_id>/attachments/**
role_workspace/knowledge/evidence/<evidence_id>/chunks/**
```

第一版主格式：

```text
raw.md
metadata.json
evidence_enrichment.json
```

历史 workspace 可能存在 `input.md`、`evidence_metadata.md`、`evidence_brief.md`；后端入库可以按需兼容读取，但员工搜索命令不再执行本地 fallback，新资料也不再生成这些旧文件。

用途：

```text
会议纪要
证据材料
公司章程
制度文件
客户反馈
项目资料
决策记录
外部材料摘录
```

### task 任务资料

```text
task_scope.md
task_ledger.md
task_output.md
execution_plan.md
missing_inputs.md
```

用途：

```text
任务目标
执行过程
缺失输入
最终交付
任务决策
任务中引用的证据
```

### role workspace 资料

```text
role_workspace/world_model/*.md
role_workspace/ledgers/*.md
```

用途：

```text
岗位信息
长期工作背景
员工职责边界
对话习惯
```

## 5. 产品功能

### 5.1 GitHub 项目注册

管理员在后端登记需要同步的员工 workspace repo。

每个 repo 记录：

```json
{
  "repo_id": "lbai-workspace-zhangsan",
  "repo_url": "https://github.com/LBAI-Technology-Company/lbai-workspace-zhangsan",
  "owner_user_id": "zhangsan",
  "department": "product",
  "sync_enabled": true,
  "default_visibility": "private"
}
```

技术实现：

```text
后端保存 repo 配置表
使用 GitHub App 或专用 service token 读取 repo
每个 repo 独立记录 last_synced_commit
```

### 5.2 GitHub 更新同步

支持两种同步方式：

```text
GitHub webhook：有 push 时触发同步
定时同步：兜底扫描未处理更新
```

同步流程：

```text
收到 repo 更新
  ↓
读取最新 commit
  ↓
比较 last_synced_commit
  ↓
获取 changed files
  ↓
筛选可入库文件
  ↓
创建 ingestion job
```

技术实现：

```text
Webhook endpoint: POST /webhooks/github
定时任务: 每 5-15 分钟扫描一次
GitHub API: compare commits / list files
同步状态表: repo_id, last_synced_commit, last_success_at, last_error
```

### 5.3 文件筛选

只处理符合规则的文件，避免全仓库无差别入库。

第一版处理：

```text
tasks/**/task_scope.md
tasks/**/task_ledger.md
tasks/**/task_output.md
tasks/**/execution_plan.md
tasks/**/missing_inputs.md
role_workspace/**/*.md
role_workspace/knowledge/evidence/**/raw.md
role_workspace/knowledge/evidence/**/metadata.json
role_workspace/knowledge/evidence/**/evidence_enrichment.json
role_workspace/knowledge/evidence/**/chunks/*.md
role_workspace/knowledge/evidence/**/attachments/*
```

跳过：

```text
.git/**
.cursor/**
lbai_system/**
临时文件
二进制文件
过大文件
敏感配置文件
```

技术实现：

```text
使用路径 allowlist
使用文件大小限制
使用 MIME/type 检查
使用敏感文件 denylist
```

### 5.4 原文存储

后端保存原文快照，确保后续证据可追溯。

存储字段：

```json
{
  "document_id": "doc_xxx",
  "repo_id": "lbai-workspace-zhangsan",
  "commit_sha": "abc123",
  "path": "tasks/2026_06_11_xxx/task_output.md",
  "source_type": "task_output",
  "raw_text": "...",
  "content_hash": "sha256:...",
  "created_at": "2026-06-11T10:00:00+08:00"
}
```

技术实现：

```text
原文可存对象存储或数据库 text 字段
content_hash 用于去重
commit_sha 用于追溯 GitHub 版本
```

### 5.5 文档解析

把不同文件解析成统一内部结构。

统一结构：

```json
{
  "document_id": "doc_xxx",
  "source": {
    "repo_id": "lbai-workspace-zhangsan",
    "path": "role_workspace/knowledge/evidence/xxx/raw.md",
    "commit_sha": "abc123",
    "source_type": "evidence"
  },
  "text": "...",
  "metadata": {},
  "sections": []
}
```

技术实现：

```text
Markdown 按标题切分 sections
JSON 文件直接解析
metadata 文件按字段解析
保留原文行号或段落位置
```

### 5.6 事实抽取 JSON 化

使用 AI 将文档内容抽取成结构化事实。

输入：

```text
文档原文
文档元数据
事实字典
抽取 prompt
```

输出：

```json
{
  "schema_version": "fact_extraction_output_v1",
  "task_type": "company_knowledge_ingestion",
  "raw_evidence": [],
  "base_facts": {},
  "derived_facts": {},
  "unmapped_facts": [],
  "field_change_requests": [],
  "decision_state": {}
}
```

技术实现：

```text
第一版可使用后端 LLM 调用
也可将抽取任务排队给内部 Agent worker
抽取结果必须通过 JSON Schema 校验
抽取失败进入 retry / manual_review 队列
```

### 5.7 JSON 校验

后端使用 Python 校验抽取结果。

校验内容：

```text
JSON 是否可解析
schema_version 是否正确
字段是否注册
类型是否正确
枚举值是否合法
状态是否合法
来源和证据是否存在
unmapped_facts 是否需要字段治理
```

技术实现：

```text
复用 fact_extraction_layer/schemas
校验失败不入正式 fact_event
记录 validation_errors
```

### 5.8 fact_event 生成

将抽取结果转成事实事件，追加存储。

fact_event 示例：

```json
{
  "schema_version": "fact_event_v1",
  "event_id": "evt_xxx",
  "subject": {
    "type": "feature",
    "id": "feature.team_permissions",
    "name": "团队权限管理"
  },
  "entity": {
    "type": "decision",
    "id": "dec_custom_roles_v1"
  },
  "field_id": "decision.scope",
  "value": "v1_no_custom_roles",
  "status": "confirmed",
  "validity": {
    "source_occurred_at": "2026-06-08",
    "recorded_at": "2026-06-08T10:00:00+08:00",
    "extracted_at": "2026-06-08T10:30:00+08:00"
  },
  "source": {
    "type": "meeting_note",
    "id": "mtg_20260608",
    "path": "role_workspace/knowledge/evidence/xxx/raw.md",
    "priority": 60
  },
  "evidence_text": "最终确认第一版不支持自定义角色",
  "confidence": 0.96
}
```

技术实现：

```text
每次更新追加新 event
不覆盖旧 event
用 supersedes 表示覆盖关系
用 source.path + commit_sha 追溯原文
```

### 5.9 结构化数据库

保存文档、事实事件、同步状态、权限和查询日志。

第一版推荐：

```text
PostgreSQL
```

核心表：

```text
repos
documents
fact_events
ingestion_jobs
concept_aliases
permissions
query_logs
```

`fact_events` 关键字段：

```text
event_id
repo_id
subject_type
subject_id
entity_type
entity_id
field_id
value_json
status
source_occurred_at
recorded_at
extracted_at
source_type
source_path
source_priority
evidence_text
confidence
content_hash
```

### 5.10 候选事件筛选与 LLM 相关性判断

第一版不建设向量数据库。后端先通过结构化字段、关键词和同义词召回候选事件，再把候选事件的精简字段交给 LLM 判断与当前任务的相关性。

候选事件精简字段：

```text
event_id
subject.name
entity.type
field_id
value 摘要
status
source_occurred_at
source.priority
evidence_text
```

LLM 相关性判断输入：

```json
{
  "task_text": "整理提车前要准备什么",
  "candidate_events": [
    {
      "event_id": "evt_xxx",
      "subject": "公司购车",
      "entity_type": "policy",
      "status": "confirmed",
      "source_occurred_at": "2026-05-20",
      "evidence_text": "车辆交付前需要确认保险、上牌、付款凭证。"
    }
  ]
}
```

LLM 相关性判断输出：

```json
{
  "relevant_events": [
    {
      "event_id": "evt_xxx",
      "relevance": "high",
      "reason": "与提车前准备事项直接相关"
    }
  ],
  "irrelevant_events": []
}
```

技术规则：

```text
Python 先做候选粗筛，避免把全部事件交给 LLM
每次最多提交固定数量候选事件，例如 30-50 条
LLM 只判断相关性，不做最终事实裁决
Python 根据 event_id 取回完整证据包
数据量变大后再增加向量搜索作为召回层
```

### 5.11 关键词和同义词索引

用于前期候选事件召回，解决“买车 / 购车 / 提车”等不同说法的命中问题。

概念词典示例：

```json
{
  "concept_id": "company_vehicle_purchase",
  "name": "公司购车",
  "aliases": ["买车", "购车", "提车", "车辆采购", "车辆交付", "公司用车"]
}
```

技术实现：

```text
PostgreSQL full-text search 或简单 LIKE/tsvector
concept_aliases 表维护同义词
查询时扩展关键词
```

### 5.12 检索 API

员工插件调用后端检索 API 获取证据包。

Endpoint：

```text
POST /v1/search/evidence
Content-Type: application/json
Accept: application/json
```

请求字段必须兼容员工端 `workspace_template/lbai_system/tools/search_backend.py` 当前实现。

请求：

```json
{
  "workspace_repo_id": "lbai-workspace-zhangsan",
  "employee_user_id": "zhangsan",
  "task_text": "整理提车前要准备什么",
  "query_plan": {
    "schema_version": "backend_search_query_plan_v1",
    "query": "整理提车前要准备什么",
    "keywords": ["提车", "购车", "买车", "车辆交付"],
    "concepts": ["company_vehicle_purchase"],
    "entity_types": ["decision", "policy", "action_item"],
    "prefer_status": ["confirmed", "open"],
    "limit": 10
  },
  "limit": 10
}
```

字段说明：

```text
workspace_repo_id：员工 workspace repo 标识，来自 .lbai/workspace.json 的 knowledge_service.workspace_repo_id；缺省时员工端会用 workspace 根目录名。
employee_user_id：员工技术身份，来自 .lbai/workspace.json 的 employee_identity.employee_user_id，用于权限过滤和审计。
task_text：员工原始查询意图，通常等于 query_plan.query。
query_plan：Cursor / Codex 依据 backend_search_query_plan_v1 schema 生成的检索计划。
limit：本次证据包返回上限；后端仍需设置服务端最大值。
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
        "path": "role_workspace/knowledge/evidence/vehicle/raw.md",
        "commit_sha": "abc123"
      },
      "evidence_text": "车辆交付前需要确认保险、上牌、付款凭证。",
      "reason": "与当前任务主题相关，且为 confirmed 状态"
    }
  ],
  "open_questions": [],
  "conflicts": [],
  "next_step": "Use returned evidence as task context."
}
```

响应字段必须兼容员工端 `workspace_template/lbai_system/schemas/backend_evidence_search_response_schema_v1.json` 当前实现。

状态枚举：

```text
FOUND：至少返回一条可见 evidence_pack。
NO_MATCH：请求有效，但权限过滤和检索后没有可返回证据。
ERROR：请求可被服务端解析，但后端检索失败、权限身份异常或内部处理失败。HTTP 层仍可根据错误类型返回 4xx / 5xx。
```

ERROR 响应示例：

```json
{
  "schema_version": "backend_evidence_search_response_v1",
  "query_status": "ERROR",
  "evidence_pack": [],
  "open_questions": [],
  "conflicts": [],
  "next_step": "Check backend service configuration or retry later.",
  "error": "employee_user_id is not registered or not allowed to query this workspace_repo_id"
}
```

插件端行为约束：

```text
FOUND：直接展示 evidence_pack。
NO_MATCH：展示无匹配和 next_step。
ERROR / HTTP 错误 / 超时 / 非法 JSON / schema 校验失败：展示错误。
以上情况均不回退本地 workspace catalog 搜索，也不自动阻断、修改或推进任务流程。
```

后端实现要求：

```text
先校验 schema_version 和必要字段。
先用 employee_user_id + workspace_repo_id 做身份识别、权限过滤和审计记录。
所有 evidence_pack 条目必须带可追溯 source.path / source.commit_sha 或同等来源信息。
open_questions 和 conflicts 即使为空也返回数组。
next_step 必须返回，供插件端直接展示。
```

### 5.13 搜索排序

检索分四步：

```text
1. Python 按权限、字段、状态、时间做粗筛
2. 关键词 / 同义词召回候选事件
3. LLM 判断候选事件与当前任务的相关性
4. Python 按状态、时间、来源优先级过滤和排序
```

排序规则：

```text
权限可见
状态优先 confirmed / open
排除 rejected / superseded
主题相关度高
source_occurred_at 新
source.priority 高
confidence 高
```

### 5.14 权限控制

所有检索必须先经过权限过滤。

权限维度：

```text
员工本人 workspace
部门可见资料
公司公共制度
项目成员可见资料
负责人可见资料
敏感资料限制
```

技术实现：

```text
permissions 表记录 employee_user_id、repo_id、document_id、visibility
查询时先过滤可见 document_id / event_id
敏感资料只返回摘要或禁止返回原文
记录访问日志
```

### 5.15 冲突检测

同一对象、同一字段出现多个有效值时，标记冲突。

冲突条件：

```text
subject_id 相同
field_id 相同
status 均为 confirmed
时间或来源优先级无法裁决
value 不同
```

返回：

```json
{
  "conflicts": [
    {
      "subject_id": "feature.team_permissions",
      "field_id": "decision.scope",
      "events": ["evt_1", "evt_2"],
      "reason": "同一字段存在多个 confirmed 值"
    }
  ]
}
```

### 5.16 管理后台

第一版可做简化后台。

功能：

```text
查看 repo 同步状态
查看 ingestion job 状态
查看抽取失败记录
查看字段变更申请
查看冲突列表
维护概念词典
维护权限规则
```

## 6. 技术模块

### 6.1 API 服务

职责：

```text
GitHub webhook
检索 API
管理 API
权限校验
```

推荐：

```text
Python FastAPI
```

### 6.2 同步 Worker

职责：

```text
拉取 GitHub 变更
下载文件内容
生成 ingestion job
```

推荐：

```text
后台队列 worker
```

### 6.3 抽取 Worker

职责：

```text
读取文档
调用 AI 抽取 JSON
执行 Schema 校验
生成 fact_event
```

### 6.4 索引 Worker

职责：

```text
更新全文索引
更新 concept alias 命中字段
刷新候选事件搜索字段
```

### 6.5 查询服务

职责：

```text
接收 query_plan
权限过滤
关键词 / 同义词召回
LLM 相关性判断
字段过滤
排序
证据包生成
```

## 7. 推荐技术栈

第一版保持简洁：

```text
后端框架：FastAPI
数据库：PostgreSQL
队列：PostgreSQL job table 或 Redis Queue
对象存储：本地磁盘 / S3 兼容存储
GitHub 接入：GitHub App
AI 抽取：后端统一 LLM 调用或内部 Agent worker
相关性判断：后端统一 LLM 调用或内部 Agent worker
```

第一版可以只使用：

```text
FastAPI + PostgreSQL + GitHub App
```

## 8. API 设计

### 8.1 GitHub webhook

```text
POST /webhooks/github
```

功能：

```text
接收 push event
校验 GitHub signature
创建 repo sync job
```

### 8.2 手动同步 repo

```text
POST /admin/repos/{repo_id}/sync
```

功能：

```text
管理员手动触发同步
```

### 8.3 查询证据包

```text
POST /v1/search/evidence
```

功能：

```text
员工插件根据当前任务或搜索请求查询相关背景。
请求体必须使用 workspace_repo_id、employee_user_id、task_text、query_plan、limit。
query_plan.schema_version 必须是 backend_search_query_plan_v1。
响应体必须使用 backend_evidence_search_response_v1，并返回 query_status、evidence_pack、open_questions、conflicts、next_step。
query_status 使用 FOUND / NO_MATCH / ERROR。
后端必须支持员工端对响应做 JSON Schema 校验。
```

### 8.4 查询当前事实

```text
POST /v1/facts/current
```

功能：

```text
查询某个 subject / field 的当前有效事实
```

### 8.5 查询历史脉络

```text
POST /v1/facts/history
```

功能：

```text
查询某个事实的历史变化链
```

### 8.6 查询反馈来源

第一版不提供员工端直接写入反馈的 API。

查询反馈、岗位经验反馈、任务执行反馈统一先落到员工 GitHub workspace：

```text
tasks/<task>/
  role_memory_feedback.json
  finish_review.md
  task_output.md
```

后端通过 GitHub 同步读取这些反馈，用于优化召回和排序。

## 9. 数据处理流程

### 9.1 入库流程

```text
GitHub push
  ↓
Webhook
  ↓
repo_sync_job
  ↓
changed files
  ↓
document records
  ↓
fact extraction job
  ↓
fact_extraction_output JSON
  ↓
validation
  ↓
fact_events
```

### 9.2 查询流程

```text
插件发起查询
  ↓
Cursor / Codex 生成 backend_search_query_plan_v1
  ↓
插件读取 .lbai/workspace.json 中的 employee_identity 和 knowledge_service，并从 ~/.lbai/auth/knowledge_service.json 读取本机后端 API Key
  ↓
POST /v1/search/evidence
  ↓
校验 schema_version、employee_user_id、workspace_repo_id、query_plan
  ↓
权限校验
  ↓
概念词扩展
  ↓
关键词召回
  ↓
候选事件粗筛
  ↓
LLM 相关性判断
  ↓
合并去重
  ↓
字段过滤
  ↓
状态/时间/来源排序
  ↓
生成 evidence_pack
  ↓
返回 backend_evidence_search_response_v1
```

## 10. MVP 范围

第一版只做必要闭环：

```text
GitHub repo 注册
Webhook / 定时同步
读取 evidence 和 task 文件
保存原文
AI 抽取 JSON
Schema 校验
fact_event 入库
PostgreSQL 关键词搜索
同义词 / 概念词典搜索
候选事件 LLM 相关性判断
权限按 repo/employee_user_id 粗粒度过滤
返回 backend_evidence_search_response_v1 evidence_pack
同步状态和错误日志
```

暂缓：

```text
复杂图数据库
复杂审批流
自动字段字典合并
全自动冲突修复
细粒度段落级权限
多模型评测平台
向量数据库
embedding 索引
```

## 11. 里程碑

### M1：GitHub 同步和原文入库

交付：

```text
repo 注册
webhook 接收
changed files 识别
documents 表
同步日志
```

### M2：事实抽取和校验

交付：

```text
抽取 worker
fact_extraction_output
schema validation
fact_events 表
失败重试
```

### M3：基础检索 API

交付：

```text
关键词搜索
同义词概念词典
权限过滤
evidence_pack 返回
插件可调用并通过 backend_evidence_search_response_v1 schema 校验
```

### M4：LLM 相关性判断和排序优化

交付：

```text
候选事件压缩
LLM 相关性判断
相关性 reason 返回
排序策略
```

### M5：事实裁决和冲突检测

交付：

```text
current fact 查询
history 查询
supersedes 支持
conflict 列表
```

## 12. 成功指标

```text
资料提交后能在后端入库
新任务能自动召回相关背景
证据包包含来源和时间
能区分最终决定和历史讨论
能返回 open question / action item
能发现冲突
员工重复解释背景的次数下降
AI 输出引用公司资料的比例提升
```

## 13. 简版结论

后端知识服务采用简洁架构：

```text
GitHub 作为员工资料提交源
后端监听 GitHub 更新
AI 做事实抽取
Python 做校验和裁决
PostgreSQL 存结构化事实
LLM 判断候选事件相关性
检索 API 返回证据包
员工插件保持轻量
```

这套方案与当前 LBAI Workspace Kit 的定位一致：员工继续使用本地 private workspace 和 `/lbai-*` 工作流，后端负责把分散资料沉淀为公司级可检索知识库。
