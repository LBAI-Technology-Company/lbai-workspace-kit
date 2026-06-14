# Field Rule Impact Map v1

本文档记录正式事实字段会影响哪些规则、校验、解释或流程。

新增 `formal_decision` 字段时，必须同步更新本文件。否则字段虽然存在于事实字典，但没有明确消费方，属于悬空字段。

## Impact Map

| Field | Layer | Lifecycle | Consumers | Update Required When Changed |
| --- | --- | --- | --- | --- |
| `project.region_type` | `base_facts` | `formal_decision` | `receivable_region_policy_v1` | 规则、校验、解释模板、回归用例 |
| `project.country` | `base_facts` | `formal_supporting` | 暂无直接裁决规则 | 解释模板、来源映射 |
| `receivable.stage` | `base_facts` | `formal_decision` | `receivable_stage_policy_v1` | 规则、校验、解释模板、回归用例 |
| `receivable.overdue_days` | `base_facts` | `formal_decision` | `receivable_overdue_policy_v1` | 规则、校验、解释模板、回归用例 |
| `receivable.has_dispute` | `base_facts` | `formal_decision` | `receivable_dispute_policy_v1` | 规则、校验、解释模板、回归用例 |
| `acceptance.completed_status` | `base_facts` | `formal_decision` | `receivable_acceptance_policy_v1` | 规则、校验、解释模板、回归用例 |

## Field Change Rule

字段变更必须检查影响面：

```text
字段定义是否改变
字段枚举是否改变
字段来源优先级是否改变
字段未知值策略是否改变
字段是否影响历史测试
字段是否影响解释文案
字段是否影响规则引擎输入
```

##悬空字段定义

满足以下任一条件，视为悬空字段：

```text
formal_decision 字段没有 consumer_rules
字段在事实字典存在，但没有回归用例
字段被 AI 抽取，但规则和校验都不消费
字段用于解释，但没有说明解释模板
```

