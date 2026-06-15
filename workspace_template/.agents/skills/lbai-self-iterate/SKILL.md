---
name: lbai-self-iterate
description: Start or continue the LBAI Prompt Lab self-iteration loop. Use when the user types /lbai-self-iterate.
---

Read `AGENTS.md` and execute `/lbai-self-iterate` per `lbai_system/runner_contracts/lbai_command_contract_v1.md`. Tools: `lbai_system/tools/` and `lbai_system/prompt_lab/prompt_lab.py`.

Use Codex/Cursor AI as the executor. Do not configure a separate LLM API.

Prompt changes must apply only to `prompt_lab/prompt_versions/current/`, not `lbai_system/prompts/`.

Mock scenario data must not be committed or pushed to GitHub. After approval, use `prompt_lab.py finalize --run <run_dir>` to remove raw run data and keep only optimized experimental prompts.
