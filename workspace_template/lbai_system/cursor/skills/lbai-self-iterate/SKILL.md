---
name: lbai-self-iterate
description: Start or continue the LBAI Prompt Lab self-iteration loop. Use when the user types /lbai-self-iterate.
---

Read `AGENTS.md` and execute `/lbai-self-iterate` per `lbai_system/runner_contracts/lbai_command_contract_v1.md`. Tools: `lbai_system/tools/` and `lbai_system/prompt_lab/prompt_lab.py`.

Use real employee task context when available. If the workspace has no task or role context, fall back to mock office scenarios.

Use Codex/Cursor AI as the executor. Do not configure a separate LLM API.

Prompt changes must apply only to `prompt_lab/prompt_versions/current/`, not `lbai_system/prompts/`.

Raw Prompt Lab run data must not be committed or pushed to GitHub. Send the administrator-facing package from `prompt_lab/admin_feedback/outbox/<run_id>/<round>/`, which lists clear problems, optimization plan, optimized effect, score, changed prompt files, and artifact references. After approval, use `prompt_lab.py finalize --run <run_dir>` to remove raw run data and keep only optimized experimental prompts.

## Chain modes

- Default `intake_evidence`: test evidence archive + task intake only.
- `full_lifecycle`: start with `--chain-mode full_lifecycle`; follow `lbai_system/prompt_lab/FULL_CHAIN_ITERATION.md` for meeting mock → task → execute output → finish.
