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
  - `/lbai-role-setup` (Cursor slash command; Codex: **LBAI Role Setup**)
  - `/lbai-add-evidence`
  - `/lbai-search-artifacts`
  - `/lbai-new-task`
  - `/lbai-execute-task`
  - `/lbai-finish-task`
  - `/lbai-update-kit`
  - `/lbai-self-iterate`
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

## Employee task lifecycle (two commands)

For daily task work, employees mainly need:

1. `/lbai-new-task` — start a formal task
2. `/lbai-finish-task` — deliver, review, and sync

`/lbai-finish-task` **auto-runs the delivery phase** (the same work as `/lbai-execute-task`) when `task_output.md` is missing, empty, or still a placeholder. Employees do not need to run `/lbai-execute-task` in the normal flow.

Keep `/lbai-execute-task` for debugging, regenerating deliverables without sync, or splitting delivery from finish.

## /lbai-role-setup

Initialize or update the employee's role memory. Cursor slash command `/lbai-role-setup`; Codex palette **LBAI Role Setup**. Legacy alias: `/lbai-init` (same behavior).

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
3. Call `init_lbai.py --enrichment <json_path>`. Code writes role files, `ROLE_PROFILE_v1.json`, and archive copy.
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
3. Read role context, current conversation context, and relevant prior artifacts. Search existing artifacts first when the task may depend on company knowledge. Use results when available; no result or backend error is normal and must not itself block the task.
4. Produce task intake enrichment JSON that separates:
   - known information and source kind (`conversation_context`, `company_knowledge`, `role_context`, `external_source`, or `assumption`)
   - `missing_inputs`: blocking gaps only
   - `recommended_inputs`: useful non-blocking context
   - goal, expected output, review risk, and completion conditions
5. For company/process/product/fact-based writing tasks, after using any available searched artifacts, linked evidence, external sources, role context, or employee-provided source facts, list remaining source facts and audience/use gaps as blocking inputs for the employee to fill.
6. Treat direct employee clarifications as task-local context. Do not force them into `/lbai-add-evidence`.
7. Use `/lbai-add-evidence` only for source materials that should be archived as reusable evidence, such as meeting notes, customer materials, emails, raw transcripts, research, or approved reference documents.
8. Call `new_task.py --enrichment <json_path>`. Code creates task folder from AI `review_needed`, writes `task_intake_enrichment.json`.
9. If required information is missing, create `missing_inputs.md` and mark the task `BLOCKED`.
10. If review is required, create review reminder files. Do not mark the task `WAITING_REVIEW` solely for review-sensitive content.

Response format:

```text
任务已建档：<task_folder>
状态：<OPEN | BLOCKED>
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
4. Treat the command input as evidence content. Evidence is independent from tasks and does not record task links.
5. Call `add_evidence.py` with `--enrichment <json_path>` and the raw evidence content. Code handles redaction, OKF writes, hygiene checks, and Git sync.
6. Save one OKF concept under `role_workspace/knowledge/references/YYYY_MM_DD_<source_type>_<short_hash>.md`.
7. The concept must contain YAML frontmatter, stable `uid`, structured metadata, source content, and citations.
8. Update `role_workspace/knowledge/index.md` and `role_workspace/knowledge/log.md`.
9. Do not create `raw.md`, `metadata.json`, `evidence_enrichment.json`, or an evidence ledger entry.
10. Do not update task `missing_inputs.md`, `task_scope.md`, `task_ledger.md`, or `gap_record.md`; task readiness remains owned by `/lbai-new-task` and `/lbai-execute-task`.
11. If evidence appears review-sensitive, keep `admissibility_status` as `NEEDS_REVIEW`; AI provides the review judgment in enrichment JSON and code does not apply keyword overlay.
12. Run the hygiene check and safely sync the concept, `index.md`, and `log.md`. If sync is blocked after local capture succeeds, report `sync_status: BLOCKED` or `PUSH_FAILED` without treating the local capture as failed.

Response format:

```text
资料归档完成：<concept_path>
concept_uid: <stable OKF uid>
index: role_workspace/knowledge/index.md
log: role_workspace/knowledge/log.md
evidence_status: <CAPTURED | NEEDS_REVIEW | BLOCKED>
employee_user_id: <employee id or None>
employee_user_name: <employee user name or None>
employee_position: <employee position or None>
source_type: <meeting_note | chat_record | customer_feedback | interview | draft | data_note | policy | reference | task_material | general>
source_visibility: <private | team | company>
backend_ingestion_status: <PENDING_BACKEND_SYNC | NOT_SYNCED>
sensitive_capture_status: <NONE | REDACTED>
sync_status: <PUSHED | PUSH_FAILED | BLOCKED | NOT_SYNCED | NO_CHANGES>
下一步：<exact next step>
```

## /lbai-search-artifacts

Search the backend knowledge service before creating or executing a task. This command is read-only, must not search local workspace artifacts, and must not mutate artifacts.

Supported runtimes: **Cursor** and **Codex desktop app** only. No rule-based fallback.

Prompt and schema:

```text
lbai_system/prompts/backend_search_query_plan_prompt_v1.md
lbai_system/schemas/backend_search_query_plan_schema_v1.json
```

Tool:

```text
lbai_system/tools/search_artifacts.py
```

Behavior:

1. If input is empty, ask the employee for the knowledge question or search intent.
2. Produce `backend_search_query_plan_v1` JSON and call `search_artifacts.py --enrichment <json_path>`.
3. Code calls the configured backend `POST /v1/knowledge/search` endpoint and renders `knowledge_search_response_v1` directly.
4. If the backend is disabled, missing, unavailable, times out, returns no matches, or returns invalid JSON/schema, render the search result or error as display-only output. Backend search status must not automatically block, mutate, advance, or finish any task flow.
5. Do not scan local knowledge or task files, do not use local fallback, and do not write `retrieved_context.json/md`.

Response format:

```text
backend 查询结果：<FOUND | NO_MATCH | ERROR>
source: backend
results:
1. <concept title>
   concept_uid: <OKF uid>
   type: <OKF type>
   source: <Git path>
   description: <description>
   facts: <atomic fact statements>
   reason: <match reason>
下一步：<exact next step>
```

## /lbai-execute-task

**Advanced / debug command.** Employees normally use `/lbai-finish-task`, which auto-runs delivery when `task_output.md` is not ready. Use this command to regenerate `execution_plan.md` and `task_output.md` without finishing or syncing.

Execute an existing task contract without working outside `task_slot.md`.

Prompt (agent plan, no JSON tool):

```text
lbai_system/prompts/execute_task_plan_prompt_v1.md
```

Tools:

```text
lbai_system/tools/prepare_execute_task.py <task_folder>
lbai_system/tools/resolve_current_task.py execute
lbai_system/tools/archive_input.py <task_folder> --resolves "<exact missing input>"
/lbai-add-evidence for reusable/source evidence only
```

Behavior:

1. If input is empty, resolve the task with `resolve_current_task.py execute`.
2. Run `prepare_execute_task.py <task_folder>` to validate missing inputs and create `execution_plan.md` if needed.
3. Read `lbai_system/prompts/execute_task_plan_prompt_v1.md`, `task_scope.md`, `task_slot.md`, `task_ledger.md`, linked evidence briefs, and role context files.
4. If user-provided input is a direct clarification, decision, preference, or lightweight context in chat, save it as task-local input via `archive_input.py --resolves "<exact missing input>"`; do not treat it as evidence by default. Use one `--resolves` per missing input covered by the chat reply.
5. If user-provided input is source material that should be reusable or auditable, save via `/lbai-add-evidence` with AI enrichment. Evidence remains independent; close task missing inputs with task-local clarification only when the employee explicitly provides the missing decision or context.
6. If required input is still missing, mark `BLOCKED`.
7. Create or update `task_output.md` aligned with `execution_plan.md` and `task_slot.md`, with facts/assumptions/sources separated.
8. If review is required, ensure review reminder files exist. Do not mark `WAITING_REVIEW` solely for review-sensitive content.

Response format:

```text
任务执行结果：<task_folder>
状态：<COMPLETED | BLOCKED>
leader_review_reminder: <reminder or None>
已生成/更新：
- <files>
还缺：
- <missing item or 无>
下一步：交付物已生成时运行 /lbai-finish-task；若仍 BLOCKED，先在对话补齐缺失输入。
```

## /lbai-finish-task

Deliver (when needed), finish, run hygiene checks, update ledgers, and sync safe artifacts to the private GitHub upstream.

This is the **normal end-to-end task command** for employees. It auto-runs the delivery phase when deliverables are not ready.

Supported runtimes: **Cursor** and **Codex desktop app** only. No rule-based fallback for finish review.

Prompts and schema:

```text
lbai_system/prompts/execute_task_plan_prompt_v1.md
lbai_system/prompts/finish_review_enrichment_prompt_v1.md
lbai_system/schemas/finish_review_enrichment_schema_v1.json
```

Tools:

```text
lbai_system/tools/resolve_current_task.py finish
lbai_system/tools/check_task_delivery.py <task_folder>
lbai_system/tools/archive_input.py <task_folder> --resolves "<exact missing input>"
lbai_system/tools/prepare_execute_task.py <task_folder>
lbai_system/tools/finish_task.py <task_folder> --enrichment <json_path>
/lbai-add-evidence for reusable/source evidence only
```

Behavior:

1. If input is empty, resolve the task with `resolve_current_task.py finish`.
2. **Archive chat clarifications first.** If the employee provided direct clarifications, decisions, preferences, or lightweight context in the current conversation, save them as task-local input via `archive_input.py --resolves "<exact missing input>"` before delivery checks.
3. Run `check_task_delivery.py <task_folder>`.
4. **Auto-execute phase (when needed).** Run auto-execute only when `check_task_delivery.py` reports `auto_execute_needed: true` **and** `prepare_execute_task.py` reports `execute_status: READY` after missing inputs are closed:
   - Run `prepare_execute_task.py <task_folder>`.
   - Read `lbai_system/prompts/execute_task_plan_prompt_v1.md`, `task_scope.md`, `task_slot.md`, `task_ledger.md`, linked evidence briefs, and role context files.
   - Write `execution_plan.md` and `task_output.md` aligned with `task_slot.md`, with facts/assumptions/sources separated.
   - If `check_task_delivery.py` or `prepare_execute_task.py` reports `BLOCKED`, return `auto_execute: BLOCKED` and do **not** call `finish_task.py`.
5. **Finish review phase.** Read task scope, `task_output.md`, `execution_plan.md` (if present), linked evidence, `missing_inputs.md`, and the current task conversation (employee/user messages only). Produce finish review enrichment JSON including `employee_conversation_turns`.
6. Call `finish_task.py <task_folder> --enrichment <json_path>`. Code writes `finish_review.md`, `task_conversation.md`, runs hygiene check, updates ledgers, and syncs when allowed.
7. If `finish_verdict` is `BLOCK_FINISH`, set `commit_readiness: BLOCKED` even when files exist.
8. If task status is not `BLOCKED` and commit readiness is `READY`, auto git add/commit/push scoped artifacts.

Response format:

```text
任务收尾完成：<task_folder>
auto_execute: <RUN | SKIPPED | BLOCKED>
task_status: <COMPLETED | BLOCKED>
leader_review_reminder: <reminder or None>
commit_readiness: <READY | BLOCKED | NEEDS_MANUAL_CHECK>
git_status: <COMMITTED | PUSHED | PUSH_FAILED | BLOCKED>
已生成/更新：
- <files>
还缺：
- <missing item or 无>
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
7. If GitHub remote or upstream is missing, still update local workflow files.
8. Do **not** commit or push managed workflow template files. They stay on disk and are listed in `.gitignore`. If this workspace still has legacy template paths in Git index, best-effort run a one-time cleanup (`chore(lbai): stop tracking workflow kit template`); cleanup failure must **not** block the local template update.
9. Default assumption: **single-device usage**. Do not design update-kit around multi-device template sync.
10. Admin/debug flags:
   - `--dry-run` → `DRY_RUN` / `git_status: SKIPPED`
   - `--no-commit` → skip legacy Git cleanup
   - `--no-push` → cleanup commit locally only

Response format:

```text
工作流更新完成：<UPDATED | NO_CHANGES | BLOCKED | DRY_RUN>
commit_readiness: <READY | BLOCKED | NEEDS_MANUAL_CHECK>
git_status: <LOCAL_ONLY | SKIPPED | COMMIT_SKIPPED | NO_CHANGES | PUSHED | COMMITTED | PUSH_FAILED | BLOCKED>
当前版本：<workspaceKitVersion，来自 GitHub release 的 lbai-workspace-kit VERSION，写入 .lbai/workspace.json>
已更新：
- <files or 无>
GitHub 同步：
<completed | blocked_or_failed + detail>
如需确认：
<覆盖升级 | 暂不升级 | 无>
下一步：<exact next step>
```

## /lbai-self-iterate

Start or continue the LBAI Prompt Lab self-iteration loop for improving prompts through simulated office writing scenarios.

Supported runtimes: **Cursor** and **Codex desktop app**. The current AI in the runtime acts as the scenario generator, enrichment producer, evaluator, and prompt optimizer. Do not request a separate LLM API key.

Coordinator:

```text
lbai_system/prompt_lab/prompt_lab.py
```

Default arguments:

```text
rounds=1
scenarios_per_round=6
focus=general_office_writing
chain_mode=intake_evidence
context_mode=auto
real_task_limit=3
review_mode=human_each_round
auto_continue=false
apply_threshold=80
```

Chain modes:

- `intake_evidence` (default): mock scenarios test evidence archive and task intake only.
- `full_lifecycle`: mock meeting records drive the full chain `add_evidence -> new_task -> prepare_execute_task -> task_output -> finish_task`. See `lbai_system/prompt_lab/FULL_CHAIN_ITERATION.md`.

Behavior:

1. Parse optional user arguments: `rounds`, `scenarios_per_round`, `focus`, `chain_mode`, `context_mode`, `real_task_limit`, `review_mode`, `auto_continue`, and `apply_threshold`.
2. Run `prompt_lab.py start` to create `prompt_lab/runs/<run_id>/`, copy formal prompts into the experimental prompt baseline, collect real task context when available, and create an isolated workspace.
3. Run `prompt_lab.py next-step --run <run_dir>` and follow its instructions.
4. Generate `prompt_lab_scenarios_v1` JSON. When `context_mode=auto` and real employee task context exists, ground scenarios in `prompt_lab/runs/<run_id>/real_task_context/context.md`; when no context exists, mock different office writing scenarios, including internal reports, meeting notes, manager requests, customer feedback, policy summaries, HR copy, sales material, product explanations, and review-sensitive external content. `context_mode=real_task` blocks when no real task or role context exists. `context_mode=mock` always uses mock scenarios.
5. For each scenario, use the current AI to produce required enrichment JSON, then call existing LBAI tools **only** through `prompt_lab.py run-tool` inside the isolated workspace under `prompt_lab/runs/<run_id>/workspaces/`. When `chain_mode=full_lifecycle`, also use `prompt_lab.py write-task-artifact` to copy AI-written `task_output.md` from `chain_outputs/<scenario_id>/` into the isolated task folder before `finish_task.py`. `run-tool` rejects employee root paths, allows `new_task.py`, `add_evidence.py`, `finish_task.py`, `init_lbai.py`, `prepare_execute_task.py`, and `archive_input.py`, sets `LBAI_PROMPT_LAB_ISOLATED=1`, and forces local-only behavior for sync-capable tools. Do not use `search_artifacts.py` in Prompt Lab mock runs because it may call the production knowledge backend. Never invoke `lbai_system/tools/*.py` directly against the employee workspace during this command.
6. Evaluate every scenario with `prompt_lab_evaluation_v1` JSON, score the round with `prompt_lab.py score`, and write `human_review.md`, `round_report.md`, and `admin_report.md`. When real task context is used, the evaluation must set `admin_handoff_safe=true` only after issues and suggestions are redacted for administrator handoff; set `sensitive_content_present=true` and add `redaction_notes` when customer names, project names, raw conversation excerpts, secrets, or personal data appear.
7. If a prompt improvement is needed, produce `prompt_lab_prompt_patch_v1` JSON and call `prompt_lab.py apply-prompt-patch`. The patch rationale must explain the clear problem, optimization plan, and expected effect.
8. Prompt patches may only update `prompt_lab/prompt_versions/current/`. Never edit `lbai_system/prompts/` during this command.
9. A prompt patch is applied only when the score meets the threshold, no red flags are present, and the score improves over the previous round when a previous round exists.
10. By default, stop after each round for human review. When `auto_continue=true`, `next-step` prints the `advance-round` command to run after review; it does not auto-run another round without explicit execution.
11. To start another round after the current round completes, run `prompt_lab.py advance-round --run <run_dir>`. This increments `current_round`, seeds the next round folders, and creates or refreshes the isolated workspace with the latest experimental prompts.
12. Send the administrator-facing result from `prompt_lab/admin_feedback/outbox/<run_id>/<round>/` only when `handoff_status=READY`. This package contains the clear problems, optimization plan, optimized effect, score, changed prompt files, and artifact references. If `handoff_status=BLOCKED_REDACTION_REQUIRED`, review the local run data, redact sensitive text, and rerun/evaluate before sending.
13. After human approval, run `prompt_lab.py finalize --run <run_dir>` to delete mock scenarios, tool outputs, evaluations, isolated workspaces, and raw run data. The default final state keeps only optimized experimental prompts under `prompt_lab/prompt_versions/current/`.

Response format:

```text
Prompt Lab：<STARTED | BLOCKED | ROUND_REVIEW_READY>
run_dir: <path>
current_round: <n>
next_step:
- <exact command or AI action>
human_review: <path or None>
```
