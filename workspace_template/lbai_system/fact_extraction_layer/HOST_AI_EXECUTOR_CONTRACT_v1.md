# Host AI Executor Contract v1

本文档定义事实抽取层如何使用 Cursor、Codex 或子 Agent 执行 AI 抽取。

结论：本层不强制接入独立 LLM API。优先使用宿主环境已经提供的 AI 能力。

## 执行模式

### 1. Inline Host Agent

当前 Cursor 或 Codex 会话直接执行事实抽取。

流程：

```text
run_fact_extraction_flow.py 生成 fact_extraction_ai_request.md
  ↓
当前 Agent 阅读请求
  ↓
当前 Agent 输出 fact_extraction_output_v1 JSON
  ↓
run_fact_extraction_flow.py 校验 JSON 并生成 report
```

适用场景：

- 单个文档较短。
- 人希望当前会话直接看到抽取过程。
- 不需要并行处理多个文档。

### 2. Host Sub-Agent

由 Codex、Cursor 或其他宿主能力启动子 Agent 处理抽取任务。

流程：

```text
主 Agent 生成 fact_extraction_ai_request.md
  ↓
主 Agent 启动子 Agent
  ↓
子 Agent 只负责读取请求并输出 JSON
  ↓
主 Agent 运行校验脚本
  ↓
校验通过后进入规则引擎或字段变更流程
```

适用场景：

- 多文档批处理。
- 希望隔离事实抽取和业务决策。
- 希望一个子 Agent 专门做字段映射，另一个子 Agent 做边界审查。

### 3. External LLM API

独立模型 API 是可选增强，不是默认要求。

适用场景：

- 需要无人值守批量处理。
- 需要后端服务化。
- 需要在没有 Cursor/Codex 的环境中运行。

## Agent 职责边界

Host Agent 或 Sub-Agent 可以做：

```text
读取用户输入文档
读取事实字典
抽取 base_facts
标注 raw_evidence
发现 unmapped_facts
提出 field_change_requests
输出 fact_extraction_output_v1 JSON
```

Host Agent 或 Sub-Agent 不可以做：

```text
绕过事实字典创造正式字段
直接修改正式事实字典
跳过代码校验
把 confidence 当作最终裁决依据
直接输出最终业务决策
直接执行外部动作
```

## 子 Agent 输入

子 Agent 应收到：

```text
fact_extraction_ai_request.md
fact_catalog_sample_v1.json 或正式 fact_catalog.json
fact_extraction_output_schema_v1.json
当前用户输入文档
```

## 子 Agent 输出

子 Agent 只输出一个 JSON 文件：

```text
fact_extraction_output_v1.json
```

该 JSON 必须符合：

```text
schemas/fact_extraction_output_schema_v1.json
```

不允许混入解释性自然语言。解释可以放入 `evidence_text`、`unmapped_facts.reason` 或 `field_change_requests.reason`。

## 主 Agent 校验流程

子 Agent 返回后，主 Agent 必须运行：

```bash
python3 lbai_system/fact_extraction_layer/tools/run_fact_extraction_flow.py \
  --input <user_input.md> \
  --catalog <fact_catalog.json> \
  --extraction <fact_extraction_output.json> \
  --output-dir <flow_output_dir>
```

主 Agent 只根据 `fact_extraction_flow_report.json` 推进状态：

```text
ready_for_rule_engine -> 进入规则引擎
needs_fact -> 请求补充事实
needs_schema_change -> 进入字段变更流程
needs_rule -> 请求人补规则边界
conflict -> 请求人处理来源冲突
validation_failed -> 要求重做抽取或修复 JSON
```

## 为什么不让 AI 直接进入下一步

事实抽取层的稳定性来自：

```text
AI 负责生成候选结构化事实
代码负责校验字段契约
规则引擎负责最终裁决
人负责补充边界和字段治理
```

因此即使使用 Cursor/Codex 的宿主 AI，AI 仍然只是“状态化产物生成器”，不是最终裁判。

