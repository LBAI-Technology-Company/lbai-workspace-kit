# Fact Event Store and Query v1

事实抽取层负责把不同来源材料 JSON 化；事实事件层负责把这些 JSON 变成可长期检索、可追溯、可裁决的事件库。

核心原则：

```text
不要覆盖旧事实，追加新事件。
查询时按对象、字段、状态、时间、来源优先级计算当前有效结果。
```

## 为什么不能只存最新 JSON

一个工作可能关联多种材料：

```text
会议纪要
产品需求文档
客户反馈
设计评审
开发讨论
财务数据
人工确认
```

同一件事可能被多次提到：

```text
6 月 1 日：第一版可能支持自定义角色
6 月 3 日：暂定不支持
6 月 8 日：最终确认第一版不支持
```

如果只覆盖旧 JSON，会丢掉“为什么最后这么决定”的证据链。

所以应该把每次抽取结果转为事实事件：

```text
source document -> extracted JSON -> fact events -> query current state/history
```

## 事实事件结构

每个事实事件是一条 JSONL 记录。

```json
{
  "event_id": "evt_20260608_001",
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
    "valid_from": "2026-06-08"
  },
  "source": {
    "type": "meeting_note",
    "id": "mtg_20260608_product_review",
    "path": "meeting_records/2026-06-08/raw.md",
    "priority": 60
  },
  "evidence_text": "最终确认第一版不支持自定义角色，只保留 owner/admin/member。",
  "supersedes": ["evt_20260601_001", "evt_20260603_001"],
  "related_to": ["req_team_permissions_roles"],
  "confidence": 0.96
}
```

## 时间字段

必须区分三种时间：

```text
source_occurred_at：材料所描述的业务发生时间，例如会议日期。
recorded_at：材料记录时间，例如纪要保存时间。
extracted_at：AI 抽取成 JSON 的时间。
```

查询“最新决定”通常按：

```text
source_occurred_at > recorded_at > extracted_at
```

而不是按文件修改时间。

## 状态字段

非数字型事实主要靠状态判断。

推荐状态：

```text
draft
proposed
confirmed
rejected
superseded
open
closed
blocked
unknown
```

查询“最后做的决定”时，默认只取：

```text
status = confirmed
```

如果没有 confirmed，再返回 proposed/open，并标记不是最终结论。

## 来源优先级

当同一对象同一字段出现多个候选值时，先按状态和时间，再按来源优先级。

建议默认优先级：

```text
human_confirmation: 100
signed_contract: 95
approved_prd: 90
task_ledger: 85
official_decision_log: 80
meeting_note: 60
chat: 40
raw_user_input: 30
ai_summary: 20
```

## 查询语义

### 查询当前有效事实

```text
subject.id = feature.team_permissions
entity.type = decision
field_id = decision.scope
mode = current
status = confirmed
```

返回一条当前有效记录，并附带证据。

### 查询历史脉络

```text
subject.id = feature.team_permissions
entity.id = dec_custom_roles_v1
mode = history
```

返回所有相关事件，按时间排序。

### 查询待处理事项

```text
entity.type = action_item
status = open
mode = list
```

返回所有未完成行动项。

## 当前有效事实裁决规则

默认排序：

```text
1. 排除 status = rejected/superseded，除非 include_inactive=true
2. 优先 status = confirmed
3. source_occurred_at 最新
4. recorded_at 最新
5. source.priority 最高
6. confidence 最高
```

如果出现同等优先级但值不同：

```text
返回 conflict，不自动选择。
```

## 调用方式

```bash
python3 lbai_system/fact_extraction_layer/tools/query_fact_events.py \
  --events lbai_system/fact_extraction_layer/examples/fact_events_sample_v1.jsonl \
  --subject-id feature.team_permissions \
  --entity-type decision \
  --field-id decision.scope \
  --status confirmed \
  --mode current
```

## 和事实抽取层的关系

```text
事实抽取层：把材料变成结构化 JSON。
事实事件层：把结构化 JSON 变成可检索事件。
规则引擎层：基于当前有效事实做裁决。
```

事实事件层负责回答：

```text
当前最新确认结论是什么？
这个结论来自哪里？
历史上是否有不同说法？
是否存在未解决冲突？
```

