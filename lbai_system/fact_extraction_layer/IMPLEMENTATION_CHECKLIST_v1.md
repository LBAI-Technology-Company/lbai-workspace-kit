# Implementation Checklist v1

本文档回答：要把事实抽取层做成稳定系统，还需要哪些文档、代码和运行流程。

## 当前第一版已包含

```text
事实字典规范
字段治理规则
事实抽取 Prompt
宿主 AI 执行器契约
事实字典 JSON Schema
事实抽取输出 JSON Schema
样例事实字典
样例抽取结果
样例字段变更申请
Python 校验脚本
流程运行脚本
回归测试脚本
字段规则影响映射表
回归用例集
```

这已经可以支撑第一版闭环：

```text
Cursor、Codex 或子 Agent 抽取事实
  ↓
代码校验字段合法性
  ↓
发现 unmapped_facts
  ↓
提出字段变更申请
  ↓
人确认后更新事实字典
```

## 要做到生产级稳定，还需要的文档

### 1. 业务术语表

文件建议：

```text
BUSINESS_GLOSSARY_v1.md
```

作用：

- 定义业务词汇的标准含义。
- 解决“应收阶段”“回款阶段”“催收阶段”等近似说法。
- 约束 AI 不把相似词误映射。

示例：

```text
应收账款阶段：财务侧对回款状态的阶段定义。
项目阶段：交付侧对项目推进状态的阶段定义。
验收状态：客户是否完成合同约定验收。
```

### 2. 来源优先级文档

文件建议：

```text
FACT_SOURCE_PRIORITY_v1.md
```

作用：

- 定义不同来源冲突时谁优先。
- 解决用户口述、ERP、合同、邮件、人工备注不一致的问题。

示例：

```text
合同 > ERP > 发票系统 > CRM > 邮件 > 人工输入 > 用户口述
```

### 3. 规则影响映射表

文件建议：

```text
FIELD_RULE_IMPACT_MAP_v1.md
```

作用：

- 每个正式决策字段必须标明影响哪些规则。
- 新增字段时可以知道后续代码和规则要改哪里。

示例：

```text
project.region_type -> receivable_region_policy_v1
receivable.overdue_days -> receivable_overdue_policy_v1
acceptance.completed_status -> receivable_acceptance_policy_v1
```

### 4. 字段变更记录

文件建议：

```text
FIELD_CHANGELOG_v1.md
```

作用：

- 记录谁在什么时候为什么新增、合并、废弃字段。
- 便于回滚和解释历史输出差异。

### 5. 回归测试用例集

文件建议：

```text
REGRESSION_CASES_v1.jsonl
```

作用：

- 每次改字段、prompt、规则后回放。
- 防止新字段破坏旧判断。

每条用例至少包含：

```json
{
  "input": "印尼海外项目，应收逾期 42 天，客户未验收。",
  "expected_facts": {
    "project.region_type": "overseas",
    "receivable.overdue_days": 42,
    "acceptance.completed_status": "not_completed"
  },
  "expected_state": "ready_for_rule_check"
}
```

### 6. 人工确认原则

文件建议：

```text
HUMAN_REVIEW_POLICY_v1.md
```

作用：

- 明确什么时候必须问人。
- 防止 AI 为了完成任务而猜边界。

必须人工确认的情况：

```text
字段会影响决策但未注册
字段来源冲突
枚举值无法归类
规则边界缺失
历史规则可能被新字段改变
```

## 是否需要 Python 文件

需要。文档只能约束人和 AI，Python 或其他确定性程序负责把约束变成“过不了就不能继续”的门禁。

第一版 Python 至少要做：

```text
JSON 是否可解析
是否符合 JSON Schema
字段是否存在于事实字典
字段类型是否正确
枚举值是否合法
字段是否放在正确层级
正式决策字段是否有消费规则
deprecated 字段是否有替代字段
unmapped_facts 是否阻断 ready_for_rule_check
missing_facts 是否都是已注册字段
```

后续生产版 Python 还应增加：

```text
批量回归测试
字段变更申请校验
字段迁移检查
规则影响面检查
来源冲突检测
schema 版本兼容检查
抽取结果与规则引擎联动校验
```

## 建议的运行命令

```bash
python3 lbai_system/fact_extraction_layer/tools/validate_fact_layer.py \
  --catalog lbai_system/fact_extraction_layer/examples/fact_catalog_sample_v1.json \
  --output lbai_system/fact_extraction_layer/examples/fact_extraction_output_sample_v1.json
```

## 当前最小闭环

当前已补齐最小闭环文件：

```text
FIELD_RULE_IMPACT_MAP_v1.md
REGRESSION_CASES_v1.jsonl
tools/run_fact_regression.py
tools/run_fact_extraction_flow.py
```

这样事实抽取层已经能从“单次校验”升级为“每次变更自动回放”。

## 当前仍未包含

以下能力仍需要后续接入：

```text
字段变更申请自动写回事实字典
规则引擎裁决
解释模板生成
历史数据迁移
CI 自动执行回归
```

独立 LLM API 不是必需项。默认运行方式是：由 Cursor、Codex 或宿主子 Agent 读取 `fact_extraction_ai_request.md`，产出 `fact_extraction_output_v1` JSON，再交给代码校验。

因此当前状态是：事实抽取层的工程闭环已跑通，宿主 AI 抽取契约已明确，但最终业务决策闭环还没有完成。
