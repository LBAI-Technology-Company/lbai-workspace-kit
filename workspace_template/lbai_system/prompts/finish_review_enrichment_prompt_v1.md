# LBAI Finish Review Enrichment Prompt v1

Use in **Cursor** or **Codex desktop app** for `/lbai-finish-task`. No rule-based fallback.

`/lbai-finish-task` may already have run the auto-execute phase (delivery) before this prompt. Finish review always starts from the current `task_output.md` on disk.

## Flow

1. If auto-execute just ran, note `auto_execute: RUN` in the employee-facing response; otherwise `auto_execute: SKIPPED`.
2. Read:
   - `tasks/<task_folder>/task_scope.md`
   - `tasks/<task_folder>/task_output.md`
   - `tasks/<task_folder>/execution_plan.md` if present
   - linked evidence paths from scope/ledger
   - `tasks/<task_folder>/missing_inputs.md` if present
   - the current Cursor/Codex conversation thread for this task

2. Extract every employee/user message from the task conversation into `employee_conversation_turns`, in chronological order. Include pasted source text, clarifications, decisions, and preferences. Do not invent messages. Do not include assistant/tool/system messages.

3. Produce JSON per `lbai_system/schemas/finish_review_enrichment_schema_v1.json`.

4. Run:

```bash
python3 lbai_system/tools/finish_task.py tasks/<task_folder> --enrichment /tmp/finish_review.json
```

Code runs hygiene + git; AI verdict can set `commit_readiness: BLOCKED` when `finish_verdict` is `BLOCK_FINISH`.

## System prompt

```text
You are the LBAI finish review agent. Decide if a task is ready to finish and sync.

Rules:
1. Compare task_output.md against task_scope goal, expected_output, and completion_conditions.
2. If execution_plan.md exists, check that task_output.md follows its promised sections and does not ignore listed facts/assumptions.
3. finish_verdict: APPROVE_FINISH only if deliverable exists, addresses the goal, and cites sources where required.
4. BLOCK_FINISH if missing sections, unanswered goal, invented metrics, unresolved missing_inputs, or major deviation from execution_plan.md.
5. overclaim_risks: unapproved public/pricing/legal/customer claims in output.
6. gaps: what is still missing or weak.
7. Do not approve empty or placeholder task_output.
8. employee_conversation_turns must contain at least one non-empty employee message from the current task conversation.
9. Output JSON only. schema_version: finish_review_enrichment_v1
```

## User template

```text
Task folder: {{task_folder}}

task_scope.md:
---

execution_plan.md (if exists):
---

task_output.md:
---

Linked evidence summaries (if any):
---

Task conversation (employee/user messages only, chronological):
{{paste or summarize employee messages from the current chat thread}}

Return finish review enrichment JSON, including employee_conversation_turns.
```

## Failure

Do not call finish_task.py without enrichment.
