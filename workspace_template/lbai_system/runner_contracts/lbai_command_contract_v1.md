# lbai_command_contract_v1

## Purpose

Define the employee-facing LBAI commands once so Cursor and Codex adapters do not duplicate workflow logic.

## Core Acceptance Standard

The core function of this plugin is:

```text
让聪明模型在公司规则、证据边界、任务流程、交付标准里稳定工作。
```

Every Cursor or Codex adapter action is acceptable only when all four controls are preserved:

- Company rules: apply role boundary, review boundary, sensitive-data boundary, and protected-file rules before treating output as company work.
- Evidence boundary: distinguish approved source-supported facts from drafts, assumptions, uncertainty, review-sensitive claims, and redacted sensitive material.
- Task process: do not turn chat or saved evidence into formal work unless the employee uses `/lbai-new-task` or explicitly asks to create task artifacts.
- Delivery standard: formal work must land in auditable repo artifacts, update ledgers, pass hygiene checks, and sync only safe artifact scopes when applicable.

## Runtime Scope

- Cursor adapters live under `.cursor/` and `lbai_system/cursor/`.
- Codex project adapters live under `lbai_system/codex/`.
- Core execution lives under `lbai_system/tools/`.
- Employee-owned data lives under `role_workspace/` and `tasks/`.

Adapters must read this contract, then call or follow the listed tools. Do not install project commands into global user-level Codex skills.

## Shared Command Rules

- Accept the same command names in Cursor and Codex:
  - `/lbai-init`
  - `/lbai-add-evidence`
  - `/lbai-search-artifacts`
  - `/lbai-new-task`
  - `/lbai-execute-task`
  - `/lbai-finish-task`
  - `/lbai-update-kit`
- If a command argument is omitted and exactly one current task is clear, use it.
- If the task is ambiguous, list candidate task folders and ask the employee to choose.
- Do not invent missing source facts.
- Treat task outputs as internal company work products: objective, concise, evidence-seeking, and scoped to the employee's role.
- Do not flatter, appease, or simply confirm the employee's first framing.
- Separate facts, assumptions, uncertainty, recommendations, and next steps.
- Do not fabricate data, metrics, benchmarks, success stories, customer evidence, product capabilities, pricing, legal positions, approvals, or company commitments.
- Any metric, benchmark, case result, market claim, performance claim, or customer claim must trace to task inputs, approved references, or explicitly cited external sources when browsing is allowed.
- If required inputs are missing, state the exact missing materials, background, decisions, or source documents.
- Do not ask the employee to manually create templates.
- During normal task work, do not edit `.cursor/`, `lbai_system/`, `AGENTS.md`, `README.md`, or `workspace_dashboard.html`.
- Do not modify `role_workspace/` or `tasks/` during `/lbai-update-kit`.

## /lbai-init

Initialize or update the employee's role memory. This is not a business task and must not create a task folder.

Supported runtimes: **Cursor** and **Codex desktop app** only. No rule-based fallback.

Prompt and schema:

```text
lbai_system/prompts/init_enrichment_prompt_v1.md
lbai_system/schemas/init_enrichment_schema_v1.json
```

Tool:

```text
lbai_system/tools/init_lbai.py
```

Behavior:

1. If input is empty, show questions via `python3 lbai_system/tools/init_lbai.py --print-questions` and collect answers in chat.
2. Produce AI init enrichment JSON with cleaned `sections`.
3. Call `init_lbai.py --enrichment <json_path>`. Code writes role files and archive copy.
4. If AI enrichment is unavailable, return `岗位设定更新：BLOCKED`.

Response format:

```text
岗位设定更新：<UPDATED | BLOCKED>
已更新：
- <files or 无>
还缺：
- <missing item or 无>
下一步：<exact next step>
```

## /lbai-new-task

Start a formal LBAI task lifecycle.

Supported runtimes: **Cursor** and **Codex desktop app** only. No rule-based fallback.

Prompt and schema:

```text
lbai_system/prompts/task_intake_enrichment_prompt_v1.md
lbai_system/schemas/task_intake_enrichment_schema_v1.json
```

Tool:

```text
lbai_system/tools/new_task.py
```

Behavior:

1. If input is empty but the current conversation contains exactly one clear task, use that description for intake enrichment.
2. If input is empty and the task is unclear, ask for one concise task description.
3. Read role context and optional prior artifacts; produce task intake enrichment JSON.
4. Call `new_task.py --enrichment <json_path>`. Code creates task folder from AI `review_needed`, writes `task_intake_enrichment.json`.
5. If required information is missing, create `missing_inputs.md` and mark the task `BLOCKED`.
6. If review is required, create review reminder files. Do not mark the task `WAITING_REVIEW` solely for review-sensitive content.

Response format:

```text
任务已建档：<task_folder>
状态：<OPEN | BLOCKED | READY_TO_EXECUTE>
leader_review_reminder: <reminder or None>
已创建：
- <files>
缺少：
- <missing item or 无>
下一步：<exact command or exact input request>
```

## /lbai-add-evidence

Save evidence or reference material into the employee role workspace. This command must not create a formal task unless the employee explicitly confirms task creation through `/lbai-new-task` or asks to create task artifacts.

Supported runtimes: **Cursor** and **Codex desktop app** only. There is **no rule-based fallback** and **no Codex CLI** path.

Prompt and schema:

```text
lbai_system/prompts/evidence_enrichment_prompt_v1.md
lbai_system/schemas/evidence_enrichment_schema_v1.json
```

Tool:

```text
lbai_system/tools/add_evidence.py
```

Behavior:

1. If input is empty, ask the employee to paste the evidence or reference material.
2. Read `lbai_system/prompts/evidence_enrichment_prompt_v1.md` and produce AI enrichment JSON matching `lbai_system/schemas/evidence_enrichment_schema_v1.json`.
3. If AI enrichment is unavailable (model unavailable, quota exhausted, invalid JSON), stop with `evidence_status: BLOCKED`. Do **not** call `add_evidence.py` without enrichment.
4. If input starts with `tasks/<task_folder>`, link the saved evidence to that task. Read `missing_inputs.md` first; enrichment must include `gap_analysis` with `covers_gaps` and `remaining_gaps`.
5. Call `add_evidence.py` with `--enrichment <json_path>` and the raw evidence content. Code handles redaction, file writes, ledger updates, hygiene check, and git sync.
6. Save standalone evidence under `role_workspace/knowledge/evidence/YYYY_MM_DD_<source_kind>_<short_hash>/`. Do not put raw evidence content into folder names.
7. Create `input.md`, `evidence_metadata.md`, `evidence_brief.md`, and `evidence_enrichment.json`.
8. Update `role_workspace/ledgers/EVIDENCE_LEDGER_v1.md`.
9. If linked to a task, update that task's `missing_inputs.md`, `task_scope.md`, `task_ledger.md`, and `gap_record.md` using enrichment gap analysis.
10. If all required missing inputs are covered, mark the task `READY_TO_EXECUTE`; otherwise keep it `BLOCKED`.
11. If evidence appears review-sensitive, keep `admissibility_status` as `NEEDS_REVIEW`, set `leader_review_reminder`, and do not treat it as approved source. AI provides the review judgment in enrichment JSON; code does not upgrade or downgrade it via keyword rules. Do not block the linked task solely for review-sensitive evidence.
12. If evidence appears useful for a new task, suggest a task in enrichment but do not create one automatically.
13. Run the evidence hygiene check and safely sync only the evidence folder, `EVIDENCE_LEDGER_v1.md`, and linked task gap/ledger files when applicable. If sync is blocked after local capture succeeds, report `sync_status: BLOCKED` or `PUSH_FAILED` without treating the local capture as failed.

Response format:

```text
资料归档完成：<evidence_folder>
evidence_brief: <evidence_folder>/evidence_brief.md
evidence_status: <CAPTURED | NEEDS_REVIEW | ADMITTED | REJECTED | BLOCKED>
source_kind: <transcript | feedback | interview | draft | data_notes | source | notes | general | reference>
converted_artifact_status: <REFERENCE_ONLY | TASK_SUGGESTED | LINKED_TO_TASK | CONVERTED_TO_TASK_OUTPUT | CONVERTED_TO_ROLE_DELTA>
sensitive_capture_status: <NONE | REDACTED>
linked_task: <task_folder or None>
covers_gaps:
- <gap or None>
remaining_gaps:
- <gap or None>
leader_review_reminder: <reminder or None>
task_suggestion: <suggestion or None>
sync_status: <PUSHED | PUSH_FAILED | BLOCKED | NOT_SYNCED | NO_CHANGES>
下一步：<exact next step>
```

## /lbai-search-artifacts

Search prior evidence, references, and task outputs before creating or executing a task. This command is read-only and must not mutate artifacts.

Supported runtimes: **Cursor** and **Codex desktop app** only. No rule-based fallback.

Prompt and schema:

```text
lbai_system/prompts/search_enrichment_prompt_v1.md
lbai_system/schemas/search_enrichment_schema_v1.json
```

Tool:

```text
lbai_system/tools/search_artifacts.py
```

Behavior:

1. If input is empty, ask the employee for search keywords.
2. Run `python3 lbai_system/tools/search_artifacts.py --print-catalog` to export artifact catalog JSON.
3. Produce AI search enrichment JSON with semantically ranked matches from the catalog only.
4. Call `search_artifacts.py --enrichment <json_path>` to render results. Code validates paths and prints the response format.
5. Do not create a task, link artifacts, or mutate repo state.

Response format:

```text
artifact 查询结果：<FOUND | NO_MATCH | BLOCKED>
query: <query or None>
matches:
1. <artifact_path>
   type: <evidence | task | reference>
   title: <title>
   status: <status>
   usage: <usage>
   linked_task: <task or ->
   risk: <normal | needs_review | sensitive_redacted>
   match_reason: <reason>
   preview: <short preview>
   suggested_use: <how to use safely>
下一步：<exact next step>
```

## /lbai-execute-task

Execute an existing task contract without working outside `task_slot.md`.

Prompt (agent plan, no JSON tool):

```text
lbai_system/prompts/execute_task_plan_prompt_v1.md
```

Tools:

```text
lbai_system/tools/prepare_execute_task.py <task_folder>
lbai_system/tools/resolve_current_task.py execute
/lbai-add-evidence <task_folder>
```

Behavior:

1. If input is empty, resolve the task with `resolve_current_task.py execute`.
2. Run `prepare_execute_task.py <task_folder>` to validate missing inputs and create `execution_plan.md` if needed.
3. Read `lbai_system/prompts/execute_task_plan_prompt_v1.md`, `task_scope.md`, `task_slot.md`, `task_ledger.md`, linked evidence briefs, and role context files.
4. If user-provided input is in chat but not saved, save via `/lbai-add-evidence <task_folder>` with AI enrichment.
5. If required input is still missing, mark `BLOCKED`.
6. Create or update `task_output.md` aligned with `execution_plan.md` and `task_slot.md`, with facts/assumptions/sources separated.
7. If review is required, ensure review reminder files exist. Do not mark `WAITING_REVIEW` solely for review-sensitive content.

Response format:

```text
任务执行结果：<task_folder>
状态：<COMPLETED | BLOCKED>
leader_review_reminder: <reminder or None>
已生成/更新：
- <files>
还缺：
- <missing item or 无>
下一步：<exact command or exact input request>
```

## /lbai-finish-task

Finish a task, run hygiene checks, update ledgers, and sync safe artifacts to the private GitHub upstream.

Supported runtimes: **Cursor** and **Codex desktop app** only. No rule-based fallback for finish review.

Prompt and schema:

```text
lbai_system/prompts/finish_review_enrichment_prompt_v1.md
lbai_system/schemas/finish_review_enrichment_schema_v1.json
```

Tools:

```text
lbai_system/tools/resolve_current_task.py finish
lbai_system/tools/finish_task.py <task_folder> --enrichment <json_path>
```

Behavior:

1. If input is empty, resolve the task with `resolve_current_task.py finish`.
2. Read task scope, task output, and linked evidence; produce finish review enrichment JSON.
3. Call `finish_task.py <task_folder> --enrichment <json_path>`. Code writes `finish_review.md`, runs hygiene check, updates ledgers, and syncs when allowed.
4. If `finish_verdict` is `BLOCK_FINISH`, set `commit_readiness: BLOCKED` even when files exist.
5. If task status is not `BLOCKED` and commit readiness is `READY`, auto git add/commit/push scoped artifacts.

Response format:

```text
任务收尾完成：<task_folder>
task_status: <COMPLETED | BLOCKED>
leader_review_reminder: <reminder or None>
commit_readiness: <READY | BLOCKED | NEEDS_MANUAL_CHECK>
git_status: <COMMITTED | PUSHED | PUSH_FAILED | BLOCKED>
已更新：
- <files>
阻断原因：<reason or 无>
GitHub 同步：
<completed | blocked_or_failed + detail>
下一步：<exact next step>
```

## /lbai-update-kit

Update only company-maintained workflow files. Never overwrite employee-owned role memory or task artifacts.

Tool:

```text
lbai_system/tools/update_kit.py
```

Behavior:

1. If input is a Git URL or local folder, pass it as `--source "<input>"`.
2. If input is empty, use the standard company lbai-workspace-kit release source.
3. Sync only managed workflow paths:
   - `.cursor/`
   - `lbai_system/`
   - `.gitignore`
   - `AGENTS.md`
   - `README.md`
   - `workspace_dashboard.html`
4. Do not modify `role_workspace/`, `tasks/`, `.env`, keys, tokens, or local secrets.
5. If managed workflow files already have local changes, show `dirty_managed_files` and ask the employee to choose exactly one:
   - `覆盖升级`
   - `暂不升级`
6. If the employee chooses `覆盖升级`, rerun `update_kit.py` with `--overwrite-managed` and the same source.
7. If GitHub remote or upstream is missing, block before copying workflow files.
8. If the update creates safe managed changes, commit with `chore(lbai): update workflow kit to <version>` and push to the current upstream.
9. Admin/debug flags may return non-employee sync states:
   - `--dry-run` may return `DRY_RUN` and `git_status: SKIPPED`.
   - `--no-commit` may return `git_status: COMMIT_SKIPPED`.

Response format:

```text
工作流更新完成：<UPDATED | NO_CHANGES | BLOCKED | DRY_RUN>
commit_readiness: <READY | BLOCKED | NEEDS_MANUAL_CHECK>
git_status: <PUSHED | COMMITTED | NO_CHANGES | PUSH_FAILED | BLOCKED | SKIPPED | COMMIT_SKIPPED>
当前版本：<workspaceKitVersion，来自 GitHub release 的 lbai-workspace-kit VERSION，写入 .lbai/workspace.json>
已更新：
- <files or 无>
GitHub 同步：
<completed | blocked_or_failed + detail>
如需确认：
<覆盖升级 | 暂不升级 | 无>
下一步：<exact next step>
```
