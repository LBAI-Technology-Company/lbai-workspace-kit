# 员工端资料提交格式规范

## 1. 设计原则

员工通过 `/lbai-add-evidence` 提交资料时，插件端只负责保存原始资料、补齐基础元数据、做确定性敏感扫描，并提交到员工 private GitHub workspace。

大资料不建议放进 JSON 字段。推荐：

```text
资料正文：Markdown 或原始附件文件
元数据：JSON
```

这样做的好处：

```text
大文本不受 JSON 字符串转义影响
Git diff 更容易查看
人可以直接阅读原文
后端可以按文件流式读取和分片处理
JSON 保持轻量、稳定、可校验
```

## 2. 推荐目录结构

每次提交一份资料，生成一个 evidence 目录：

```text
role_workspace/knowledge/evidence/<YYYY_MM_DD>_<source_type>_<hash>/
  raw.md
  metadata.json
  attachments/
    <optional files>
```

历史 workspace 可能仍有旧文件名：

```text
input.md
evidence_metadata.md
evidence_brief.md
```

新资料不再生成这些旧文件；员工搜索命令只查后端，不再做本地 fallback 搜索。新主格式是：

```text
raw.md：已脱敏、轻度清理后的资料正文
metadata.json：资料元数据
evidence_enrichment.json：AI 生成的轻量元数据补齐结果
```

## 3. 文件说明

### 3.1 raw.md

保存用户提交资料经过插件端基础处理后的正文。

这里的 `raw.md` 不是完全未经处理的原始输入，而是：

```text
已替换敏感信息
经过简单格式清理
尽量保留原始语义、结构、时间、发言人和上下文
```

适合：

```text
会议纪要
聊天记录
公司章程摘录
制度文本
客户反馈
项目说明
任务补充材料
```

格式：

```markdown
# Evidence Raw Input

## title
6月购车讨论会议纪要

## source_type
meeting_note

## source_occurred_at
2026-06-10

## content

这里保存用户提交资料经过敏感信息替换和简单格式清理后的正文。
尽量保留标题、时间、发言人、段落结构。
```

插件端可以做轻度清理：

```text
替换确定性识别到的敏感信息
去除明显 UI 噪声
压缩连续空行
统一换行
保留正文结构
```

插件端不应做：

```text
总结原文
改写事实
提取决定
判断风险
生成行动项
分析任务缺口
```

### 3.2 metadata.json

保存资料元数据，不保存大段正文。

推荐字段：

```json
{
  "schema_version": "employee_evidence_metadata_v1",
  "evidence_id": "2026_06_12_meeting_note_a1b2c3d4",
  "title": "6月购车讨论会议纪要",
  "source_type": "meeting_note",
  "source_origin": "飞书会议转写",
  "source_occurred_at": "2026-06-10",
  "submitted_at": "2026-06-12T10:30:00+08:00",
  "submitted_by": "zhangsan",
  "submitted_by_display_name": "张三",
  "submitted_by_email": "zhangsan@company.com",
  "source_visibility": "team",
  "related_objects": ["company_vehicle_purchase"],
  "language": "zh-CN",
  "content_files": ["raw.md"],
  "attachment_files": [],
  "content_hash": "sha256:...",
  "sensitive_scan_status": "redacted",
  "redacted": true,
  "redaction_note": "sensitive values replaced locally before commit",
  "backend_ingestion_status": "PENDING_GITHUB_SYNC",
  "backend_ingestion_hint": "source_for_company_knowledge"
}
```

字段说明：

```text
evidence_id：本次资料提交 ID。
title：资料标题。
source_type：资料类型。
source_origin：资料来源，例如飞书会议转写、公司章程、制度文件。
source_occurred_at：资料所描述事件发生时间。
submitted_at：提交时间。
submitted_by：上传人 ID，来自 .lbai/workspace.json。
source_visibility：可见范围建议。
related_objects：用户可选填写的关联对象。
content_files：正文文件列表。
attachment_files：附件文件列表。
content_hash：正文哈希，用于去重和追溯。
sensitive_scan_status：本地确定性敏感扫描状态，只记录状态，不记录敏感明细。
redacted：是否发生本地替换。
backend_ingestion_status：后端同步提示状态。
```

### 3.3 敏感信息处理

插件端只做确定性敏感信息扫描和替换，不单独保存敏感扫描明细文件。

推荐处理：

```text
检测到 token / password / api key / 明显密钥：替换为 [REDACTED_SECRET]
检测到手机号等个人信息：按规则替换或部分遮罩；邮箱地址不按敏感信息处理
metadata.json 只记录 sensitive_scan_status 和 redacted
不记录原始敏感值
不记录详细命中内容
```

复杂合规判断交给后端或人工 review。

### 3.4 GitHub 提交追踪

不单独保存 `upload_manifest.json`。

原因：

```text
整个 evidence 目录已经通过 Git commit 提交
GitHub 本身记录 commit、文件清单、提交人和时间
后端可以通过 webhook payload 和 GitHub API 获取变更文件
```

如需在 metadata 中保留轻量提示，可记录：

```json
{
  "github_sync": {
    "status": "PENDING_PUSH",
    "commit_sha": null
  }
}
```

第一版也可以不写该字段，由 GitHub 和后端同步表负责追踪。

## 4. source_type 枚举建议

第一版建议支持：

```text
meeting_note
chat_log
company_policy
company_charter
project_doc
customer_feedback
decision_record
task_material
external_reference
general_note
```

说明：

```text
meeting_note：会议纪要、会议转写。
chat_log：聊天记录。
company_policy：公司制度。
company_charter：公司章程。
project_doc：项目资料。
customer_feedback：客户反馈。
decision_record：明确决策记录。
task_material：任务补充材料。
external_reference：外部参考资料。
general_note：一般笔记。
```

## 5. source_visibility 枚举建议

```text
private
team
department
company
restricted
```

说明：

```text
private：仅提交人可见。
team：团队可见。
department：部门可见。
company：公司可见。
restricted：敏感资料，需要后端或管理员进一步控制。
```

插件端只记录建议值，最终权限以后端规则为准。

## 6. 大资料处理

如果资料很大，不要写入单个 JSON 字段。

推荐处理：

```text
raw.md 保存主文本
attachments/ 保存附件
metadata.json 只记录文件路径和哈希
后端按文件分片读取
后端再做事实抽取和索引
```

大文本分片规则建议：

```text
插件端不强制切片
单个 raw.md 超过阈值时可拆成 chunks/chunk_001.md
metadata.json 的 content_files 记录所有 chunk 文件
后端按 content_files 顺序读取
```

示例：

```text
role_workspace/knowledge/evidence/2026_06_12_policy_xxx/
  metadata.json
  chunks/
    chunk_001.md
    chunk_002.md
    chunk_003.md
```

metadata：

```json
{
  "content_files": [
    "chunks/chunk_001.md",
    "chunks/chunk_002.md",
    "chunks/chunk_003.md"
  ]
}
```

## 7. 后端读取方式

后端监听 GitHub 更新后：

```text
读取 metadata.json
按 content_files 读取 raw.md 或 chunks
通过 GitHub webhook / GitHub API 获取 commit 和变更文件
生成 document record
执行后端事实抽取
生成 fact_event
入库并建立检索索引
```

后端不要依赖插件端做过的语义分析，因为插件端只提交事实材料和元数据。

## 8. 插件端最小交互

用户提交资料时，插件端只需要询问缺失的基础信息：

```text
资料标题是什么？
资料来源是什么？
资料发生时间是什么？
资料可见范围是什么？
是否关联某个项目/客户/主题？
```

如果用户不确定：

```text
source_occurred_at = unknown
related_objects = []
source_visibility = private 或 team
```

不要因为这些字段不完整而阻断资料保存。后端可以后续补充或标记待处理。

## 9. 简版结论

插件提交格式采用：

```text
Markdown 保存已脱敏、轻度清理后的资料正文
JSON 保存元数据
```

不要把大段原文塞入 JSON。

员工端只提交材料，不分析材料；后端负责 JSON 化、事实抽取、索引和检索。
