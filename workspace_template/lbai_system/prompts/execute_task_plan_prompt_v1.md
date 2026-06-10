# LBAI Execute Task Plan Prompt v1

Use in **Cursor** or **Codex desktop app** at the start of `/lbai-execute-task`. No separate Python tool.

## Purpose

Before writing `task_output.md`, produce and **save** a short execution plan to the task folder, then execute against it.

## Required flow

1. Read inputs (see below).
2. Write `tasks/<task_folder>/execution_plan.md` using the plan template below.
3. Only then write `tasks/<task_folder>/task_output.md` aligned with the plan and `task_slot.md`.

Do not skip step 2. `/lbai-finish-task` may compare output against the plan when present.

## Read first

- `tasks/<task_folder>/task_scope.md`
- `tasks/<task_folder>/task_slot.md`
- `tasks/<task_folder>/missing_inputs.md`
- Linked evidence: read `evidence_brief.md` first, not raw `input.md` unless needed
- Role world model files

## Plan file template (`execution_plan.md`)

```markdown
# Execution Plan

## task_folder
<tasks/...>

## artifacts_to_read
- <paths>

## facts_from_sources
- ...

## assumptions
- ...

## task_output_sections
1. ...
2. ...

## forbidden
- ...

## review_reminder
- ...
```

You may also summarize the plan in chat, but the file must exist before `task_output.md`.

## Then write task_output.md

Follow `task_slot.md`, enterprise execution standard, and the sections listed in `execution_plan.md`.

No enrichment JSON required for execute-task; deliverables are `execution_plan.md` and `task_output.md`.
