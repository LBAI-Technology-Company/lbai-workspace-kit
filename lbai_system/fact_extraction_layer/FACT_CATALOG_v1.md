# Fact Catalog v1

事实字典是事实抽取层的字段契约。代码只消费事实字典中注册过的标准字段名。

## 字段选择原则

字段不是按“文本中出现了什么”来拆，而是按“业务判断需要哪些独立维度”来拆。

采用以下判断标准：

1. 这个信息是否会改变后续决策、规则路径或风险等级。
2. 这个信息是否会被多个规则复用。
3. 这个信息是否能被稳定抽取或由业务系统稳定提供。
4. 这个信息是否有清晰类型、枚举、单位或来源。
5. 这个信息和已有字段的边界是否清楚。

如果第 1 条为“是”，通常应该进入正式字段，但必须同步补规则、测试和解释。

如果第 1 条为“否”，先放入 `metadata`、`raw_evidence`、`signals` 或 `unmapped_facts`，不要急着升级为正式字段。

## 粒度原则：最小可判定颗粒度

事实字段应细到规则可以稳定判断，粗到不会制造暂时无人消费的碎片。

例如“海外项目处于应收账款阶段”不应设计成：

```json
{
  "overseas_receivable_stage": "payment_due"
}
```

应拆成两个独立维度：

```json
{
  "project.region_type": "overseas",
  "receivable.stage": "payment_due"
}
```

因为“项目区域”和“应收账款阶段”可以独立影响规则，也可以组合参与判断。

## 字段命名原则

字段名采用：

```text
业务对象.稳定属性
```

推荐：

```text
project.region_type
project.country
receivable.stage
receivable.overdue_days
receivable.amount
contract.signed_status
invoice.issued_status
acceptance.completed_status
customer.type
customer.credit_level
```

避免：

```text
status
type
flag
is_special
overseas_case
domestic_stage
receivable_stage_for_overseas_project
```

一个字段名必须回答：

```text
这是谁的什么属性？
```

## 字段分层

事实抽取结果应分为四层：

```json
{
  "raw_evidence": [],
  "base_facts": {},
  "derived_facts": {},
  "decision_state": {}
}
```

### raw_evidence

原始证据。来自用户输入、系统记录、合同、邮件、表格或人工备注。

该层只保存证据，不做业务判断。

### base_facts

基础事实。来自输入或业务系统，可以被事实字典直接定义。

例如：

```json
{
  "project.region_type": "overseas",
  "receivable.overdue_days": 42
}
```

### derived_facts

推导事实。由规则、代码或确定性计算产生。

例如：

```json
{
  "receivable.risk_level": "medium"
}
```

注意：不要让 AI 在没有规则依据时直接生成推导事实。

### decision_state

流程状态，不是事实本身。

例如：

```json
{
  "state": "needs_rule",
  "next_action": "ask_human"
}
```

## 字段生命周期

字段必须标记生命周期：

- `formal_decision`：正式决策字段，会影响规则、流程或裁决。
- `formal_supporting`：正式辅助字段，用于解释、记录或后续分析，但不直接裁决。
- `observation`：观察字段，暂不进入正式规则。
- `candidate`：候选字段，需要人确认。
- `deprecated`：废弃字段，只为兼容历史数据存在。

## 字段定义模板

```json
{
  "id": "project.region_type",
  "title": "项目区域类型",
  "layer": "base_facts",
  "lifecycle": "formal_decision",
  "type": "enum",
  "enum": ["domestic", "overseas", "unknown"],
  "definition": "项目交付和收款规则所适用的区域类型。",
  "aliases": ["海外项目", "国内项目", "境外项目", "境内项目"],
  "positive_examples": ["印度尼西亚项目", "美国客户项目"],
  "negative_examples": ["外地项目", "跨省项目"],
  "source_priority": ["contract", "erp", "human_input", "user_text"],
  "unknown_policy": "allow_unknown_and_request_fact",
  "conflict_policy": "ask_human",
  "consumer_rules": ["receivable_region_policy_v1"],
  "owner": "business_owner",
  "version": "v1"
}
```

## 应收账款场景建议初始字段

第一版建议只放最小集合：

```text
project.region_type
project.country
project.customer_type
receivable.stage
receivable.amount
receivable.currency
receivable.overdue_days
receivable.has_dispute
contract.signed_status
invoice.issued_status
acceptance.completed_status
customer.credit_level
```

后续字段通过治理流程增加。

