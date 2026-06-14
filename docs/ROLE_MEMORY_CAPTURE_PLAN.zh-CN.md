# 岗位经验记忆收集与调用方案

## 1. 目标

在不增加员工命令负担的前提下，通过 `/lbai-finish-task` 收集任务后的岗位经验反馈，并由后端汇总同岗位多人的经验，形成岗位级工作习惯、检查项和 AI 防错规则。

员工工作时不直接读取本地个人习惯文件，而是通过后端 API 获取经过整理的岗位经验上下文。

## 2. 核心原则

```text
不新增员工命令，复用 /lbai-finish-task
员工端只提交经验反馈候选
后端汇总同岗位多人的反馈
后端产出岗位级工作习惯
员工执行任务时通过 API 获取岗位经验
本地 workspace 不保存权威岗位记忆
```

## 3. 总体流程

```text
员工完成任务
  ↓
/lbai-finish-task
  ↓
AI 根据任务过程生成岗位经验反馈候选
  ↓
用户确认 / 修改 / 放弃
  ↓
插件写入任务目录 role_memory_feedback 文件
  ↓
git commit / push 到员工 GitHub workspace
  ↓
后端通过 GitHub 同步读取 role_memory_feedback
  ↓
后端按 role_id 聚合同岗位多人反馈
  ↓
负责人或规则流程审核
  ↓
后端生成岗位级 role_memory_context
  ↓
新任务开始时插件调用 API 获取岗位经验上下文
  ↓
Cursor / Codex AI 基于岗位经验 + 公司证据包执行任务
```

## 4. 员工端职责

员工端负责：

```text
在 /lbai-finish-task 中生成岗位经验反馈候选
展示给用户确认
将确认后的反馈写入任务目录并提交 GitHub
在新任务或执行任务前调用后端获取岗位经验上下文
把岗位经验上下文交给 Cursor / Codex AI 使用
```

员工端不负责：

```text
不在本地维护权威岗位记忆
不把个人习惯直接覆盖成岗位规则
不直接读取本地 ROLE_MEMORY 作为任务依据
GitHub 只保存任务反馈留痕，不作为权威岗位规则来源
不做同岗位多人经验合并
```

## 5. 后端职责

后端负责：

```text
通过 GitHub 同步读取员工任务目录中的 role_memory_feedback
按 role_id / department / task_type 聚合
去重、合并、降噪
识别高频 AI 出错点
识别岗位通用检查项
识别合理交付偏好
生成岗位级 role_memory_context
提供查询 API
保留审计和来源任务
```

## 6. 员工提交格式

员工端保存的是“反馈”，不是最终岗位规则。反馈文件随任务一起提交到 GitHub，后端异步扫描入库。

推荐文件：

```text
tasks/<task>/role_memory_feedback.json
tasks/<task>/role_memory_feedback.md
```

JSON 示例：

```json
{
  "schema_version": "role_memory_feedback_v1",
  "feedback_id": "fb_20260612_001",
  "employee_user_id": "zhangsan",
  "role_id": "product_manager",
  "department": "product",
  "source_task": "tasks/2026_06_12_xxx",
  "task_type": "meeting_summary",
  "feedback_items": [
    {
      "type": "ai_failure_pattern",
      "title": "AI 容易把会议讨论当成最终决定",
      "content": "处理会议纪要时，AI 曾把 proposed 内容写成 confirmed decision。",
      "trigger": "会议纪要里出现“可能、建议、先这样”等表达。",
      "suggested_rule": "必须区分 proposed、confirmed、open_question。",
      "source_types": ["meeting_note"],
      "tags": ["meeting_note", "decision_status"],
      "severity": "medium"
    }
  ],
  "confirmed_by_user": true,
  "created_at": "2026-06-12T10:30:00+08:00"
}
```

## 7. 后端岗位经验格式

后端整理后，对外提供岗位级上下文，不暴露未经整理的个人习惯。

API：

```text
POST /v1/role-memory/context
```

请求示例：

```json
{
  "employee_user_id": "zhangsan",
  "role_id": "product_manager",
  "task_type": "meeting_summary",
  "source_types": ["meeting_note"],
  "domains": ["product"],
  "limit": 10
}
```

返回示例：

```json
{
  "schema_version": "role_memory_context_v1",
  "role_id": "product_manager",
  "context_status": "FOUND",
  "memory_items": [
    {
      "memory_id": "rolemem_pm_001",
      "type": "ai_failure_pattern",
      "title": "区分会议讨论和最终决定",
      "rule": "处理会议纪要时，必须区分 proposed、confirmed、open_question，不得把讨论直接写成最终决定。",
      "applies_to": {
        "task_types": ["meeting_summary", "prd_drafting"],
        "source_types": ["meeting_note", "chat_log"],
        "domains": ["product"]
      },
      "confidence": "high",
      "support_count": 8,
      "last_updated_at": "2026-06-12"
    }
  ]
}
```

## 8. `/lbai-finish-task` 需要增加的能力

### 8.1 Prompt 增强

`finish_review_enrichment_prompt_v1.md` 增加：

```text
请根据本次任务过程，提出最多 3 条岗位经验反馈候选。
只提出可复用、对同岗位后续任务有帮助的经验。
不要记录私人信息、情绪化评价或一次性细节。
这些候选只是供后端通过 GitHub 同步汇总的反馈，不是最终岗位规则。
```

### 8.2 Schema 增强

`finish_review_enrichment_schema_v1.json` 增加：

```json
{
  "role_memory_feedback_candidates": [
    {
      "type": "ai_failure_pattern",
      "title": "string",
      "content": "string",
      "trigger": "string",
      "suggested_rule": "string",
      "task_type": "string",
      "source_types": [],
      "tags": [],
      "severity": "medium"
    }
  ]
}
```

### 8.3 用户确认

`/lbai-finish-task` 返回时展示候选：

```text
本次任务建议写入 GitHub、供后端汇总的岗位经验反馈：
1. ...
2. ...

是否提交这些反馈？
```

用户确认后，插件写入：

```text
tasks/<task>/role_memory_feedback.json
tasks/<task>/role_memory_feedback.md
```

这些记录会正常 commit / push，用于留痕和后端异步入库；但它们不作为后续任务的权威记忆来源。

## 9. 新任务如何使用岗位经验

新任务开始或执行前，插件调用：

```text
POST /v1/role-memory/context
```

同时调用公司知识检索：

```text
POST /v1/search/evidence
```

然后组合上下文：

```text
后端岗位经验上下文
  + 后端公司证据包
  + 当前任务上下文
  ↓
Cursor / Codex AI 执行任务
```

## 10. 和公司知识库的关系

```text
公司知识库：公司事实、证据、会议、制度、决策。
岗位经验库：岗位工作方法、常见坑、AI 防错规则、交付偏好。
```

二者都由后端统一服务提供，但来源不同：

```text
公司知识：来自 /lbai-add-evidence 和 GitHub 同步。
岗位经验：来自 /lbai-finish-task 的用户确认反馈。
```

## 11. 边界

```text
员工可以提交经验反馈。
员工端通过 GitHub 提交反馈，不直接写后端。
后端负责从 GitHub 同步、汇总和整理。
岗位经验上下文通过 API 获取。
本地 GitHub workspace 不保存权威岗位经验库。
GitHub 中的任务反馈只作为留痕和后端入库来源，个人偏好不会直接覆盖岗位规则。
```

## 12. 简版结论

```text
不新增命令。
/lbai-finish-task 生成岗位经验反馈候选。
用户确认后写入任务目录并提交 GitHub。
后端异步读取 GitHub，汇总同岗位多人反馈。
任务执行时插件通过 API 获取岗位经验上下文。
员工不直接读取本地个人习惯，也不把 GitHub 中的个人反馈直接当作岗位规则使用。
```
