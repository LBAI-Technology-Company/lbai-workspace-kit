# Field Governance v1

字段治理用于控制事实字典的增长，防止字段随 AI 输出漂移。

## 总规则

1. AI 不允许在正式输出中直接创造新字段。
2. 新信息无法映射时，必须进入 `unmapped_facts`。
3. 新字段进入正式字典前，必须通过字段变更申请。
4. 正式决策字段必须同步更新规则、代码校验、测试和解释模板。
5. 字段合并、废弃和改名必须考虑历史数据兼容。

## 新增字段规则

满足任一条件时，可以提出新增字段：

- 当前规则无法表达一个反复出现的业务维度。
- 当前字段粒度过粗，导致不同决策场景被混在一起。
- 当前字段语义过载，一个字段承载了多个独立概念。
- 下游规则、流程、审批、风险判断明确需要该字段。

新增字段申请必须包含：

```json
{
  "change_type": "create_field",
  "field": {
    "id": "project.region_type",
    "type": "enum",
    "enum": ["domestic", "overseas", "unknown"],
    "layer": "base_facts",
    "lifecycle": "formal_decision",
    "definition": "项目交付和收款规则所适用的区域类型。"
  },
  "reason": "国内和海外项目在应收账款处理规则上不同。",
  "decision_impact": "影响应收账款催收路径和人工复核条件。",
  "consumers_to_update": [
    "fact_catalog",
    "rule_engine",
    "validator",
    "regression_tests",
    "explanation_template"
  ],
  "sample_cases": []
}
```

### 新增字段准入门槛

字段进入 `formal_decision` 前必须满足：

```text
字段定义清楚
字段类型清楚
未知值处理清楚
至少一个消费方清楚
至少两个正例和一个反例
至少一个回归测试
和已有字段边界不冲突
```

如果暂时没有消费方，应进入 `observation` 或 `candidate`，不要进入正式决策字段。

## 合并字段规则

当多个字段表达同一个稳定概念时，可以合并。

例如：

```text
project.location_type
project.region_category
project.region_type
```

若实际都表示“项目适用国内还是海外规则”，应合并为：

```text
project.region_type
```

合并前必须检查：

1. 两个字段定义是否完全一致。
2. 取值范围是否一致。
3. 来源优先级是否一致。
4. 历史数据中是否存在语义差异。
5. 下游规则是否使用了不同语义。

如果不完全一致，不能直接合并，只能建立映射或保留两个字段。

## 拆分字段规则

当一个字段包含多个独立概念时，必须拆分。

坏例子：

```json
{
  "project_case_type": "overseas_late_receivable"
}
```

拆分为：

```json
{
  "project.region_type": "overseas",
  "receivable.stage": "late_collection"
}
```

拆分条件：

- 字段值由多个业务维度拼接而成。
- 某一部分可以独立影响规则。
- 某一部分可复用于其他规则。
- 字段枚举持续膨胀，出现组合爆炸。

## 分层规则

字段必须放在正确层级。

### base_facts

基础事实：可从输入或系统记录直接得到。

例如：

```text
project.region_type
receivable.overdue_days
invoice.issued_status
```

### derived_facts

推导事实：由规则或确定性计算得到。

例如：

```text
receivable.risk_level
receivable.collection_priority
```

### decision_state

流程状态：描述系统当前能否决策。

例如：

```text
state = needs_fact
state = needs_rule
state = conflict
state = final
```

### metadata

辅助信息：暂不参与决策。

例如：

```text
raw_source
document_id
extractor_model
extraction_time
```

## 废弃字段规则

字段不能直接删除。废弃流程：

```text
标记 deprecated
  ↓
保留 alias 或 migration_map
  ↓
更新规则和测试
  ↓
跑历史样例
  ↓
确认无消费方后移除
```

废弃字段必须说明替代字段。

## 人工确认点

AI 在以下情况必须请求人确认：

- 信息影响决策，但没有字段表达。
- 两个字段看似相似，但定义边界不清楚。
- 同一字段有多个来源且值冲突。
- 枚举值无法归类。
- 新字段会影响已有规则路径。
- 新字段会导致历史数据解释变化。

## 字段治理 Prompt

```text
你是事实字段治理助手。你的任务不是直接修改事实字典，而是判断当前信息是否需要新增、合并、拆分或废弃字段。

请遵守：
1. 不要创造正式字段并直接用于决策。
2. 如果现有字段可以表达，返回 reuse_existing_field。
3. 如果只是补充描述，返回 keep_as_observation。
4. 如果会影响决策且现有字段无法表达，返回 propose_create_field。
5. 如果字段粒度过粗，返回 propose_split_field。
6. 如果多个字段语义重复，返回 propose_merge_fields。
7. 每个建议必须说明 decision_impact、consumer_rules、sample_cases。

输出 JSON，不要输出自然语言解释。
```

