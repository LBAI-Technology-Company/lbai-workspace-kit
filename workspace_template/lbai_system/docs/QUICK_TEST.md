# LBAI v0.6 Quick Test

0. Check Cursor command files and the project-local Codex adapter:

```bash
python3 lbai_system/tools/check_cursor_commands.py
python3 lbai_system/tools/check_codex_adapter.py
```

Expected: both checks report status `OK`. If old commands such as `/new-task` still show in Cursor, delete stale files under `.cursor/commands/` and reload Cursor.

Expected commands include `/lbai-init`, `/lbai-add-evidence`, `/lbai-search-artifacts`, `/lbai-new-task`, `/lbai-execute-task`, `/lbai-finish-task`, and `/lbai-update-kit`.

Evidence intake smoke test:

```text
/lbai-add-evidence 保存这份会议记录，不创建任务：今天讨论运营计划和 action items。
```

Expected: the workspace assistant saves evidence under `role_workspace/knowledge/evidence/`, generates `evidence_brief.md`, updates `role_workspace/ledgers/EVIDENCE_LEDGER_v1.md`, suggests a task if useful, and does not create a `tasks/` folder unless the employee explicitly confirms `/lbai-new-task`.

Artifact search smoke test:

```text
/lbai-search-artifacts 运营计划 action items
```

Expected: the workspace assistant returns candidate evidence, references, or task outputs if available. It must not create a task, link artifacts, update gaps, change task state, or run Git sync.

1. Ask in Cursor or Codex:

```text
这个项目里，LBAI 正式任务开始前你需要参考哪些文件？
```

Expected: the workspace assistant mentions `role_workspace/world_model/`, `role_workspace/ledgers/`, `tasks/`, and `lbai_system/`.

2. Start task:

```text
/lbai-new-task 整理一次内部运营会议纪要，输出 action items、owner、due date 和 blocked items。这是内部任务，不对外发布，不涉及 pricing、legal、investor、media，也不包含敏感信息。
```

3. If the workspace assistant asks for transcript, paste it directly. It should save the content into the current task folder as an input file.

4. Execute:

```text
/lbai-execute-task
```

5. Finish:

```text
/lbai-finish-task
```

Expected: finish includes the pre-commit check, prints `task_status`, `commit_readiness`, and `git_status`, then automatically commits and pushes when commit-ready and an upstream is configured.

6. High-risk review check:

```text
/lbai-new-task 根据这段产品说明写官网首页中文文案
```

Expected: the workspace assistant creates or requires `overclaim_check.md`, `release_boundary_check.md`, and `founder_review_needed.md`, sets `review_needed: true`, and prints or records `leader_review_reminder`. If product input is missing, status may be `BLOCKED`; after output is generated, status may be `COMPLETED`, but external release still requires responsible leader review and must not be represented as approved/public-ready/released.

7. Ambiguous no-argument check:

Create two unfinished tasks, then run:

```text
/lbai-execute-task
```

Expected: the workspace assistant lists candidate task folders and asks the employee to choose. It must not guess and execute one arbitrarily.
