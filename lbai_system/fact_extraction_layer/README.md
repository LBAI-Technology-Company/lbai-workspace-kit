# Fact Extraction Layer v1

本目录用于沉淀“事实抽取层”的规则、字段字典、提示词、样例和校验工具。

目标不是让 AI 自由决定字段，而是让 AI 在已注册的事实模型内输出可校验、可回放、可迭代的状态化产物。

## 核心原则

1. 事实字段是系统契约，不是随手增加的 JSON key。
2. AI 只能输出事实字典中已注册的字段；无法归类的信息进入 `unmapped_facts`。
3. 正式决策字段必须绑定消费方：规则、校验、流程、解释或测试。
4. 字段粒度遵循“最小可判定颗粒度”：细到足以稳定判断，粗到不制造无用碎片。
5. 新字段必须经过字段变更流程，不能由 AI 在业务输出中直接生效。
6. 所有新增、合并、废弃字段都必须留下样例和回归测试。

## 文件说明

- `FACT_CATALOG_v1.md`：事实字典设计和字段命名原则。
- `FIELD_GOVERNANCE_v1.md`：新增、合并、分层、废弃字段的治理规则。
- `FACT_EXTRACTION_PROMPT_v1.md`：给 AI 使用的事实抽取 prompt。
- `HOST_AI_EXECUTOR_CONTRACT_v1.md`：Cursor、Codex 或子 Agent 执行事实抽取的契约。
- `FACT_EVENT_STORE_AND_QUERY_v1.md`：多来源、多时间事实事件存储和查询规则。
- `schemas/fact_catalog_schema_v1.json`：事实字典机器校验 Schema。
- `schemas/fact_extraction_output_schema_v1.json`：事实抽取输出机器校验 Schema。
- `schemas/fact_event_schema_v1.json`：长期存储的事实事件 Schema。
- `examples/fact_catalog_sample_v1.json`：应收账款场景的事实字典样例。
- `examples/fact_extraction_output_sample_v1.json`：事实抽取输出样例。
- `examples/field_change_request_sample_v1.json`：字段变更申请样例。
- `examples/user_input_receivable_sample.md`：用户输入文档样例。
- `examples/fact_events_sample_v1.jsonl`：多时间、多来源事实事件样例。
- `tools/validate_fact_layer.py`：校验事实字典和抽取结果。
- `tools/run_fact_extraction_flow.py`：串起“输入文档、AI 请求、AI 输出校验、流程报告”的运行器。
- `tools/run_fact_regression.py`：回放历史样例，检查字段抽取是否稳定。
- `tools/query_fact_events.py`：查询当前有效事实、历史脉络和待办列表。

## 推荐流程

```text
业务输入
  ↓
Cursor、Codex 或子 Agent 根据事实字典抽取结构化事实
  ↓
代码校验字段、类型、枚举、来源、未知值
  ↓
无法表达的信息进入 unmapped_facts
  ↓
AI 提出字段变更申请
  ↓
人确认新增/合并/拒绝/观察
  ↓
更新事实字典、规则、测试和解释模板
```

## 跑通流程

### 1. 用户输入文档生成宿主 AI 抽取请求

```bash
python3 lbai_system/fact_extraction_layer/tools/run_fact_extraction_flow.py \
  --input lbai_system/fact_extraction_layer/examples/user_input_receivable_sample.md \
  --catalog lbai_system/fact_extraction_layer/examples/fact_catalog_sample_v1.json \
  --output-dir /tmp/fact_flow_demo
```

该命令会生成：

```text
/tmp/fact_flow_demo/fact_extraction_ai_request.md
/tmp/fact_flow_demo/fact_extraction_flow_report.json
```

第一份给 Cursor、Codex 或子 Agent，第二份给代码判断当前流程状态。

### 2. 宿主 AI 返回 JSON 后执行校验

```bash
python3 lbai_system/fact_extraction_layer/tools/run_fact_extraction_flow.py \
  --input lbai_system/fact_extraction_layer/examples/user_input_receivable_sample.md \
  --catalog lbai_system/fact_extraction_layer/examples/fact_catalog_sample_v1.json \
  --extraction lbai_system/fact_extraction_layer/examples/fact_extraction_output_sample_v1.json \
  --output-dir /tmp/fact_flow_demo
```

如果通过，会得到 `ready_for_rule_engine`；如果没有字段表达，会得到 `needs_schema_change`；如果 JSON 不合法，会得到 `validation_failed`。

### 3. 回放回归样例

```bash
python3 lbai_system/fact_extraction_layer/tools/run_fact_regression.py \
  --catalog lbai_system/fact_extraction_layer/examples/fact_catalog_sample_v1.json \
  --cases lbai_system/fact_extraction_layer/REGRESSION_CASES_v1.jsonl
```

### 4. 查询多来源事实事件

```bash
python3 lbai_system/fact_extraction_layer/tools/query_fact_events.py \
  --events lbai_system/fact_extraction_layer/examples/fact_events_sample_v1.jsonl \
  --subject-id feature.team_permissions \
  --entity-type decision \
  --field-id decision.scope \
  --status confirmed \
  --mode current
```

该命令用于查询某个对象当前最新的确认结论。需要历史脉络时，把 `--mode current` 改成 `--mode history`。

## 本层不负责什么

- 不负责最终业务决策。
- 不负责绕过规则直接执行动作。
- 不负责把置信度当作裁决依据。
- 不负责把临时信息自动升级成正式字段。
