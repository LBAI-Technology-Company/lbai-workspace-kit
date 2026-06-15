# Prompt Lab 全链路迭代方案

## 目标

在现有 `intake_evidence` 模式（只测资料归档 + 任务建档）之上，增加 `full_lifecycle` 模式，用 mock 会议记录驱动完整员工流程：

```text
mock 会议记录 → add_evidence → new_task → prepare_execute → task_output → finish_task → 评估/改 prompt
```

## 两种 chain_mode

| 模式 | 命令 | 测什么 |
|------|------|--------|
| `intake_evidence`（默认） | `start` 不带参数 | evidence enrichment、task intake、边界 guardrail |
| `full_lifecycle` | `start --chain-mode full_lifecycle` | 上述 + execute plan、交付物写作、finish review |

## 全链路单场景标准流程

以「产品周会 → 完成一项会议决议」为例：

### Step 0 — AI 生成场景

`scenarios.json` 中至少 1 个 `lifecycle: full_chain` 场景，包含：

- `source_material`：完整 mock 会议记录（时间/参会/议题/决议/负责人/截止）
- `meeting_action_item`：本场景要完成的唯一行动项
- `expected_finish_verdict`：`APPROVE_FINISH` 或 `BLOCK_FINISH`

### Step 1 — 归档会议

```bash
prompt_lab.py run-tool --workspace <isolated> --tool add_evidence.py \
  --output round_001/tool_outputs/<id>_01_evidence.json -- \
  --enrichment <evidence.json> --content "<meeting mock>"
```

**测：** `evidence_enrichment_prompt`、会议日期推断、review/visibility

### Step 2 — 根据会议决议建任务

```bash
prompt_lab.py run-tool --workspace <isolated> --tool new_task.py \
  --output round_001/tool_outputs/<id>_02_new_task.json -- \
  --enrichment <task_intake.json>
```

**测：** `task_intake_enrichment_prompt`、OPEN/BLOCKED、guardrail

从 stdout 记录 `TASK_FOLDER tasks/...`。

### Step 3 — 准备执行

```bash
prompt_lab.py run-tool --workspace <isolated> --tool prepare_execute_task.py \
  --output round_001/tool_outputs/<id>_03_prepare.json -- \
  tasks/<task_folder>
```

**测：** 任务前置条件、execution_plan.md 生成

### Step 4 — AI 写交付物（无独立 enrichment 工具）

AI 读取隔离 workspace 内实验版 `execute_task_plan_prompt_v1.md`，按 `execution_plan.md` 的 `task_output_sections` 撰写 mock 交付物，保存到：

```text
prompt_lab/runs/<run>/round_001/chain_outputs/<scenario_id>/task_output.md
```

**测：** `execute_task_plan_prompt`（执行规划、来源分离、不过度承诺）

### Step 5 — 写入隔离 workspace

```bash
prompt_lab.py write-task-artifact --workspace <isolated> --task tasks/<task_folder> \
  --artifact task_output.md \
  --source prompt_lab/runs/<run>/round_001/chain_outputs/<scenario_id>/task_output.md \
  --output round_001/tool_outputs/<id>_04_task_output.json
```

### Step 6 — 收尾 review

```bash
prompt_lab.py run-tool --workspace <isolated> --tool finish_task.py \
  --output round_001/tool_outputs/<id>_05_finish.json -- \
  tasks/<task_folder> --enrichment <finish_review.json>
```

**测：** `finish_review_enrichment_prompt`、finish_review_accuracy 评分维度

### Step 7 — 评估与改 prompt

- 每个场景一份 `evaluations/<scenario_id>.json`
- `finish_review_accuracy` 在全链路场景必须反映 finish 步骤
- `prompt_lab.py score` → `apply-prompt-patch`（仅 `prompt_lab/prompt_versions/current/`）

## 推荐场景组合（每轮 6–8 个）

| lifecycle | 数量建议 | 示例 |
|-----------|----------|------|
| `evidence_only` | 2–3 | 产品周会、客户复盘会、1:1 例会 |
| `task_intake` | 1–2 | 会议决议建 task（BLOCKED 或 OPEN） |
| `full_chain` | 2–3 | 周会决议 → 写方案 → APPROVE_FINISH |
| `full_chain` + BLOCK | 1 | 缺来源的会议行动项 → BLOCK_FINISH |

## 启动命令

```bash
# 全链路模式
python3 lbai_system/prompt_lab/prompt_lab.py start \
  --chain-mode full_lifecycle \
  --scenarios-per-round 6 \
  --focus meeting_to_finish \
  --run-id run_full_chain_001

python3 lbai_system/prompt_lab/prompt_lab.py next-step --run prompt_lab/runs/run_full_chain_001
```

## 允许的工具（run-tool）

| 工具 | 阶段 |
|------|------|
| `add_evidence.py` | 归档会议 |
| `new_task.py` | 任务 intake |
| `prepare_execute_task.py` | 执行准备 |
| `archive_input.py` | 可选：补 task-local 输入 |
| `finish_task.py` | 收尾 |
| `init_lbai.py` | 可选：岗位初始化场景 |

**不允许：** `search_artifacts.py`（避免打生产后端）

**execute 写作：** 由 AI + `write-task-artifact` 完成，不新增 execute enrichment 工具。

## 评估维度与环节对应

| 评分字段 | intake 模式 | full_lifecycle |
|----------|-------------|----------------|
| schema_compliance | enrichment JSON | 全步骤 |
| boundary_handling | intake/evidence | + task_output/finish |
| source_grounding | 来源边界 | + 执行稿是否引用会议来源 |
| missing_input_handling | BLOCKED 逻辑 | 同左 |
| task_quality | 任务结构 | + 交付物结构 |
| finish_review_accuracy | N/A 或弱 | **必评** |

## 与员工命令映射

| Prompt Lab 步骤 | 员工命令 |
|-------------------|----------|
| add_evidence | `/lbai-add-evidence` |
| new_task | `/lbai-new-task` |
| prepare + task_output | `/lbai-execute-task` |
| finish_task | `/lbai-finish-task` |

## 清理

```bash
python3 lbai_system/prompt_lab/prompt_lab.py finalize --run prompt_lab/runs/<run_id>
```

Mock 数据不入库；仅保留实验 prompt 副本。
