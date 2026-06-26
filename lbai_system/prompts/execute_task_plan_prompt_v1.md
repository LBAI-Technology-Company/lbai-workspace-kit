# LBAI Execute Task Plan Prompt v1

Use in **Cursor** or **Codex desktop app** at the start of `/lbai-execute-task`, or during the **auto-execute phase** inside `/lbai-finish-task`. No separate Python tool.

## Purpose

Before writing `task_output.md`, produce and **save** a short execution plan to the task folder, then execute against it.

## Required flow

1. Read inputs (see below).
2. Write `tasks/<task_folder>/execution_plan.md` using the plan template below.
3. Only then write `tasks/<task_folder>/task_output.md` aligned with the plan and `task_slot.md`.

Do not skip step 2. `/lbai-finish-task` may compare output against the plan during finish review.

## Read first

- `tasks/<task_folder>/task_scope.md`
- `tasks/<task_folder>/task_slot.md`
- `tasks/<task_folder>/missing_inputs.md`
- `tasks/<task_folder>/recommended_inputs.md`
- explicit backend search results pasted by the employee, if present in the conversation
- Linked OKF Concepts: read the referenced Markdown files under `role_workspace/knowledge/`
- Task-local chat clarifications saved under the task folder, such as `input_user_provided.md`, `input_notes.md`, or `input_draft.md`
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

If the employee provides missing details in chat during execution, treat concise clarifications, preferences, and decisions as task-local context. Save them with `archive_input.py --resolves "<exact missing input>"` so the matching blocking gap is closed. Do not force `/lbai-add-evidence` unless the employee provides source material that should be archived as reusable evidence.

No enrichment JSON required for execute-task; deliverables are `execution_plan.md` and `task_output.md`.
