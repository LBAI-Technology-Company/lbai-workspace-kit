# LBAI Prompt Lab Records

This folder stores local prompt iteration records.

Prompt Lab writes experiment runs, tool outputs, evaluations, and experimental prompt versions here. It does not store normal employee task artifacts; those remain under `tasks/`.

Formal workflow prompts remain under `lbai_system/prompts/` and are not changed automatically by Prompt Lab.

`/lbai-self-iterate` uses real task context when task records are available and falls back to mock office scenarios when no task context exists. Real context snapshots stay under `prompt_lab/runs/<run_id>/real_task_context/`.

Administrator handoff summaries are written to `prompt_lab/admin_feedback/outbox/<run_id>/<round>/`. These summaries list clear problems, the optimization plan, optimized effect, score, changed prompt files, and artifact references. Send the summary only when `handoff_status=READY`; if it says `BLOCKED_REDACTION_REQUIRED`, redact sensitive text and rerun/evaluate before sending.

Mock run data is local-only and should be removed with `prompt_lab.py finalize --run <run_dir>` after human approval. The final retained artifact is the optimized experimental prompt under `prompt_versions/current/`.

Do not commit `prompt_lab/runs/` or `prompt_lab/finalized_reports/`; they are gitignored. Raw run data is local working data, not the administrator handoff package. Only use `prompt_lab.py run-tool` against isolated workspaces under `prompt_lab/runs/*/workspaces/`.

For full lifecycle iteration (meeting mock → task → execute → finish), start with `--chain-mode full_lifecycle` and read `lbai_system/prompt_lab/FULL_CHAIN_ITERATION.md`.
