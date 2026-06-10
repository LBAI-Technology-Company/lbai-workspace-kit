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

Tool:

```text
lbai_system/tools/init_lbai.py
```

Behavior:

1. If input is empty, show the questions from `python3 lbai_system/tools/init_lbai.py --print-questions`.
2. If answers are provided, update only:
   - `role_workspace/world_model/ROLE_WORLD_MODEL_v1.md`
   - `role_workspace/world_model/ROLE_BOUNDARY_v1.md`
   - `role_workspace/world_model/ROLE_CURRENT_PRIORITIES_v1.md`
   - `role_workspace/archive/init_lbai_answers_*.md`
3. Required answers are role name, responsibilities, common tasks, common sources, common outputs, decisions requiring review, review-needed cases, and current 1-2 week priorities.

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

Tool:

```text
lbai_system/tools/new_task.py
```

Behavior:

1. If input is empty but the current conversation contains exactly one clear task, pass that task description to the tool.
2. If input is empty and the task is unclear, ask for one concise task description.
3. Create a task folder under `tasks/YYYY_MM_DD_task_slug/`.
4. Create `task_scope.md`, `task_slot.md`, and `task_ledger.md`.
5. If required information is missing, create `missing_inputs.md` and mark the task `BLOCKED`.
6. If review is required, create `overclaim_check.md`, `release_boundary_check.md`, and `founder_review_needed.md`, and remind the employee that leader review is required before external release. Do not mark the task `WAITING_REVIEW` solely for review-sensitive content.

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

Tool:

```text
lbai_system/tools/add_evidence.py
```

Behavior:

1. If input is empty, ask the employee to paste the evidence or reference material.
2. If input starts with `tasks/<task_folder>`, link the saved evidence to that task and evaluate whether it covers existing missing inputs.
3. Save standalone evidence under `role_workspace/knowledge/evidence/YYYY_MM_DD_<source_kind>_<short_hash>/`. Do not put raw evidence content into folder names.
4. Create `input.md`, `evidence_metadata.md`, and `evidence_brief.md`.
5. Update `role_workspace/ledgers/EVIDENCE_LEDGER_v1.md`.
6. If linked to a task, update that task's `missing_inputs.md`, `task_scope.md`, `task_ledger.md`, and `gap_record.md` as needed.
7. If all required missing inputs are covered, mark the task `READY_TO_EXECUTE`; otherwise keep it `BLOCKED`.
8. If evidence appears review-sensitive, keep `admissibility_status` as `NEEDS_REVIEW`, set `leader_review_reminder`, and do not treat it as approved source. Do not block the linked task solely for review-sensitive evidence.
9. If evidence appears useful for a new task, suggest a task but do not create one automatically.
10. Run the evidence hygiene check and safely sync only the evidence folder, `EVIDENCE_LEDGER_v1.md`, and linked task gap/ledger files when applicable. If sync is blocked after local capture succeeds, report `sync_status: BLOCKED` or `PUSH_FAILED` without treating the local capture as failed.

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

Tool:

```text
lbai_system/tools/search_artifacts.py
```

Behavior:

1. If input is empty, ask the employee for search keywords.
2. Search `role_workspace/ledgers/EVIDENCE_LEDGER_v1.md` and matching evidence folders under `role_workspace/knowledge/evidence/`.
3. Search `role_workspace/ledgers/TASK_LEDGER_v1.md` and task artifacts under `tasks/`, including `task_scope.md`, `task_ledger.md`, `task_slot.md`, and `task_output.md` when present.
4. Search long-term references under `role_workspace/knowledge/references/`.
5. Return ranked candidate artifacts with type, path, status, usage, review risk, match reason, preview, and suggested use.
6. Do not create a task.
7. Do not link results to a task automatically.
8. Do not change task status, missing inputs, ledgers, evidence metadata, role world model, or Git state.
9. If the employee wants to use a result in a task, instruct them to explicitly reference it in `/lbai-new-task` or ask to link it to the current task artifacts.

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

Tools:

```text
lbai_system/tools/resolve_current_task.py execute
lbai_system/tools/add_evidence.py <task_folder> --kind auto
```

Behavior:

1. If input is empty, resolve the task with `resolve_current_task.py execute`.
2. Read `task_scope.md`, `task_slot.md`, `task_ledger.md`, `missing_inputs.md` if present, linked evidence paths from `evidence_artifacts`, `role_workspace/ledgers/EVIDENCE_LEDGER_v1.md`, legacy `input_*.md` files when present, and role context files under `role_workspace/world_model/`.
3. If user-provided input is in chat but not saved, save and link it through `/lbai-add-evidence <task_folder>` or `add_evidence.py <task_folder> --kind auto`. `archive_input.py` and task-local `input_*.md` are legacy fallback only.
4. If required input is still missing, update `missing_inputs.md` and mark `BLOCKED`.
5. If enough input exists, create or update `task_output.md`.
6. If review is required, create `overclaim_check.md`, `release_boundary_check.md`, and `founder_review_needed.md`, and remind the employee that leader review is required before external release. Do not mark the task `WAITING_REVIEW` solely for review-sensitive content.

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

Tools:

```text
lbai_system/tools/resolve_current_task.py finish
lbai_system/tools/finish_task.py <task_folder>
```

Behavior:

1. If input is empty, resolve the task with `resolve_current_task.py finish`.
2. Run or follow `finish_task.py <task_folder>`. This script includes the hygiene check.
3. Check required task files and review files when review is required.
4. Update `task_ledger.md`.
5. Update `role_workspace/ledgers/TASK_LEDGER_v1.md`.
6. Output `task_status`, `commit_readiness`, and `git_status`.
7. If task status is not `BLOCKED` and commit readiness is `READY`, automatically stage only:
   - the current `tasks/<task>/` folder
   - `role_workspace/ledgers/TASK_LEDGER_v1.md`
8. Commit with `docs(lbai): finish <task_slug>` and push to the current upstream.
9. After the first push succeeds, update sync status if needed, commit with `chore(lbai): sync-status <task_slug>`, and push again.
10. Rely on `.gitignore` plus the hygiene check for secrets and temp files.

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
当前版本：<version>
已更新：
- <files or 无>
GitHub 同步：
<completed | blocked_or_failed + detail>
如需确认：
<覆盖升级 | 暂不升级 | 无>
下一步：<exact next step>
```
