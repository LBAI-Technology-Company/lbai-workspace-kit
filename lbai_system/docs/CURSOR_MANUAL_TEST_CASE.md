# LBAI Cursor Adapter 手工测试用例

这个测试用例用于验证员工把 role workspace kit 文件放进 Cursor 后，Cursor 入口的 evidence + 任务闭环是否能正常工作：

```text
/lbai-new-task
/lbai-add-evidence
/lbai-search-artifacts
/lbai-execute-task
/lbai-finish-task
```

如果是第一次配置员工工作区，可以先运行 `/lbai-init` 完成岗位设定。本测试重点验证 evidence 归档、历史 artifact 查询和日常任务三命令。

测试对象是一个办公室文职人员常见任务：整理内部会议纪要和行动项。

---

## 测试目标

通过这个测试，确认 Cursor 能做到：

1. 自动创建任务记录
2. 信息不足时明确告诉员工缺什么
3. 员工补充缺失信息时，Cursor 能区分普通对话补充和资料型来源；会议内容这类资料型来源通过 `/lbai-add-evidence` 保存为独立 evidence，不和 task 建立 metadata 关联
4. 根据输入生成任务结果
5. 收尾时更新任务记录和总台账
6. 提交前检查通过且 Git upstream 已配置时自动提交并推送

---

## 测试任务

虚拟任务：

```text
整理一次内部市场会议纪要，输出会议总结、action items、owner、due date 和 blocked items。这是内部任务，不对外发布，不涉及 pricing/legal/investor/media，也不包含敏感信息。
```

---

## 第 1 步：创建任务

在 Cursor 对话框输入：

```text
/lbai-new-task 整理一次内部市场会议纪要，输出会议总结、action items、owner、due date 和 blocked items。这是内部任务，不对外发布，不涉及 pricing/legal/investor/media，也不包含敏感信息。
```

### 预期 Cursor 做什么

Cursor 应该创建一个任务文件夹，例如：

```text
tasks/2026_05_27_整理一次内部市场会议纪要_输出会议总结_action_items/
```

日期和文件夹名称可能略有不同，长任务描述会被自动缩短；以 Cursor 实际创建为准。

### 预期生成文件

至少应生成：

```text
task_scope.md
task_slot.md
task_ledger.md
missing_inputs.md
```

### 预期状态

因为还没有会议全文，任务应是：

```text
BLOCKED
```

### 预期回复类似这样

```text
任务已建档：tasks/<task_folder>
状态：BLOCKED
已创建：
- task_scope.md
- task_slot.md
- task_ledger.md
- missing_inputs.md
缺少：
- 会议全文或会议笔记
下一步：请直接粘贴会议全文或会议笔记；这是资料型来源，我会使用 /lbai-add-evidence 独立归档。若它补齐了当前任务缺口，请在任务对话中明确说明补充了哪项信息；若只是补充偏好或决策，可直接在对话框回复。
```

### 通过标准

- Cursor 没有要求员工手动创建模板
- Cursor 明确说缺会议全文或会议笔记，并说明资料型来源才需要 `/lbai-add-evidence`
- Cursor 没有开始编造会议内容

---

## 第 2 步：粘贴会议内容

继续在 Cursor 对话框直接粘贴下面这段测试会议记录：

```text
会议主题：内部市场周会
会议日期：2026-05-27
参会人：Mia、Leo、Anna、Kai

会议内容：
1. Mia 说明本周官网访问量上涨，但转化率没有明显提升，需要检查首页文案是否表达清楚。
2. Leo 提到用户反馈里有很多人看不懂“artifact workflow”的含义，建议在后续内部培训材料中改成更简单的说法。
3. Anna 负责整理本周用户反馈，周五前输出一版问题分类。
4. Kai 负责检查帮助文档里是否有过时截图，下周一前给出列表。
5. 团队决定本周先不发布新的对外文案，只整理内部材料。

行动项：
- Anna：整理本周用户反馈并分类，due date：2026-05-29
- Kai：检查帮助文档过时截图，due date：2026-06-01
- Mia：整理首页文案问题清单，due date：2026-05-30

Blocked items：
- 暂时缺少最近一周完整用户反馈导出
- 首页转化率数据还需要运营同事确认
```

### 预期 Cursor 做什么

Cursor 应该把这段内容保存到 role workspace 的 evidence 区，且不写入任务关联字段：

```text
role_workspace/knowledge/evidence/YYYY_MM_DD_<source_type>_<short_hash>/raw.md
role_workspace/knowledge/evidence/YYYY_MM_DD_<source_type>_<short_hash>/metadata.json
role_workspace/knowledge/evidence/YYYY_MM_DD_<source_type>_<short_hash>/evidence_enrichment.json
role_workspace/ledgers/EVIDENCE_LEDGER_v1.md
```

### 预期状态

保存 evidence 后，任务不应因为 `/lbai-add-evidence` 自动消除缺口。任务是否可执行仍由 `/lbai-new-task` 或 `/lbai-execute-task` 根据本地 `missing_inputs.md` 判断。

```text
BLOCKED 或 OPEN，取决于任务本地 missing_inputs 判断
```

### 预期回复类似这样

```text
evidence_status: CAPTURED
evidence_path: role_workspace/knowledge/evidence/YYYY_MM_DD_<source_type>_<short_hash>
backend_ingestion_status: PENDING_GITHUB_SYNC
下一步：资料已保存并可 push；后端将异步入库。若这是任务必需输入，请在当前任务对话中说明并重新执行本地缺口判断。
```

### 通过标准

- Cursor 自动保存 evidence，不要求员工手动建文件
- evidence 写入 `role_workspace/knowledge/evidence/`，并更新 `role_workspace/ledgers/EVIDENCE_LEDGER_v1.md`
- 当前任务的 `missing_inputs.md`、`task_scope.md`、`task_ledger.md`、`gap_record.md` 不会被 `/lbai-add-evidence` 自动改写
- 后续 `/lbai-execute-task` 仍会本地判断 missing inputs；如需历史资料，先显式运行 `/lbai-search-artifacts` 查看后端结果，搜索结果不写入本地 `retrieved_context.md/json`

---

## 第 3 步：执行任务

在 Cursor 对话框输入：

```text
/lbai-execute-task
```

如果 Cursor 提示有多个候选任务，就选择刚才创建的会议纪要任务。

也可以直接输入完整任务目录：

```text
/lbai-execute-task tasks/<task_folder>
```

### 预期 Cursor 做什么

Cursor 应该读取任务要求和会议内容，生成：

```text
task_output.md
```

### 预期输出内容包括

`task_output.md` 中应包含：

```text
会议总结
Action Items
Owner
Due Date
Blocked Items
```

### 预期状态

因为这是内部任务，且明确不对外发布、不涉及 pricing/legal/investor/media，正常应是：

```text
COMPLETED
```

或者 Cursor 也可能提示下一步进入收尾：

```text
下一步：/lbai-finish-task tasks/<task_folder>
```

### 通过标准

- Cursor 没有编造会议里没有的信息
- 输出基于你粘贴的会议内容
- 没有生成不必要的 review 文件
- 没有把任务误判成对外发布任务

---

## 第 4 步：收尾任务

在 Cursor 对话框输入：

```text
/lbai-finish-task
```

如果 Cursor 提示有多个候选任务，就选择刚才创建的会议纪要任务。

也可以直接输入完整任务目录：

```text
/lbai-finish-task tasks/<task_folder>
```

### 预期 Cursor 做什么

Cursor 应该：

- 检查任务文件是否齐全
- 更新 `task_ledger.md`
- 更新 `role_workspace/ledgers/TASK_LEDGER_v1.md`
- 执行提交前检查
- 给出 `task_status`
- 给出 `commit_readiness`
- 给出 `git_status`

### 预期状态

任务本身应是：

```text
task_status: COMPLETED
```

提交状态可能是以下之一：

```text
commit_readiness: READY
```

或者：

```text
commit_readiness: NEEDS_MANUAL_CHECK
```

如果当前文件夹不是 Git 仓库，出现 `NEEDS_MANUAL_CHECK` 是正常的。

### 预期回复类似这样

```text
任务收尾完成：tasks/<task_folder>
task_status: COMPLETED
commit_readiness: READY 或 NEEDS_MANUAL_CHECK
git_status: PUSHED 或 BLOCKED
已更新：
- tasks/<task_folder>/task_ledger.md
- role_workspace/ledgers/TASK_LEDGER_v1.md
阻断原因：无，或当前目录不是 Git 仓库
GitHub 同步：
completed，或 blocked_or_failed + 原因
下一步：查看同步结果，或先人工检查 Git 状态。
```

### 通过标准

- Cursor 显示 `task_status`
- Cursor 显示 `commit_readiness`
- Cursor 显示 `git_status`
- Cursor 更新任务 ledger
- Cursor 更新总任务 ledger
- Cursor 在 `commit_readiness: READY` 且 Git upstream 正常时自动提交并推送

---

## 最终检查清单

完成测试后，检查是否出现以下文件：

```text
tasks/<task_folder>/task_scope.md
tasks/<task_folder>/task_slot.md
tasks/<task_folder>/task_ledger.md
tasks/<task_folder>/missing_inputs.md
tasks/<task_folder>/task_output.md
role_workspace/knowledge/evidence/YYYY_MM_DD_<source_type>_<short_hash>/raw.md
role_workspace/knowledge/evidence/YYYY_MM_DD_<source_type>_<short_hash>/metadata.json
role_workspace/knowledge/evidence/YYYY_MM_DD_<source_type>_<short_hash>/evidence_enrichment.json
role_workspace/ledgers/EVIDENCE_LEDGER_v1.md
role_workspace/ledgers/TASK_LEDGER_v1.md
```

如果都有，说明基础流程通过。

---

## 失败时怎么判断问题

### 情况 1：Cursor 没有自动保存会议内容

说明 evidence 归档没有生效。

期望行为是：如果员工粘贴的是会议记录、客户材料、邮件等资料型来源，Cursor 使用 `/lbai-add-evidence` 保存为独立 evidence，不更新任务缺口状态；如果只是补充偏好、决策或一句背景说明，则保存为任务本地上下文，并可按 `--resolves` 关闭对应缺口。

### 情况 2：Cursor 让员工自己创建模板

说明三命令流程没有生效。

期望行为是：Cursor 自己创建任务文件，不让员工手动填模板。

### 情况 3：Cursor 生成了会议里没有的信息

说明执行边界没有守住。

期望行为是：只根据会议内容整理，不编造事实。

### 情况 4：内部任务被标记为需负责人 review

说明 review 判断可能过度触发。

这个测试任务已经明确：

```text
不对外发布，不涉及 pricing/legal/investor/media
```

正常不应设置 `review_needed: true`、`leader_review_reminder` 或历史 `WAITING_REVIEW` 状态。

### 情况 5：`commit_readiness` 为 BLOCKED 但 Cursor 仍提交或推送

说明提交前检查没有生效。

期望行为是：有敏感信息或缺失文件时标记 `BLOCKED`，不要提交或推送。
