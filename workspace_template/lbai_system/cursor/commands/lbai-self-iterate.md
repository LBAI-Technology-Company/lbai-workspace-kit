# /lbai-self-iterate

Cursor command wrapper for LBAI Prompt Lab.

User input:

{{input}}

## Required behavior

Read `lbai_system/runner_contracts/lbai_command_contract_v1.md` and execute the `/lbai-self-iterate` section.

Use `lbai_system/prompt_lab/prompt_lab.py` as the deterministic coordinator. Codex/Cursor AI is the model executor; do not request or configure a separate LLM API key.

Default arguments:

```text
rounds=1
scenarios_per_round=6
focus=general_office_writing
review_mode=human_each_round
auto_continue=false
apply_threshold=80
```

Flow:

1. Run `python3 lbai_system/prompt_lab/prompt_lab.py start` with parsed arguments.
2. Run `python3 lbai_system/prompt_lab/prompt_lab.py next-step --run <run_dir>`.
3. Follow the next-step instructions: generate scenarios, validate JSON, run allowed LBAI tools **only** via `prompt_lab.py run-tool` in the isolated workspace, write evaluation JSON, score the round, propose a prompt patch, and apply it only when Prompt Lab says the round qualifies.
4. Never run `lbai_system/tools/*.py` directly against the employee workspace root during this command. `run-tool` blocks non-isolated workspaces and forces local-only sync behavior.
5. Do not commit or push mock Prompt Lab data. After human approval, run `python3 lbai_system/prompt_lab/prompt_lab.py finalize --run <run_dir>` so final state keeps only the optimized experimental prompt.

Do not edit `lbai_system/prompts/` during this command. Prompt updates apply only to `prompt_lab/prompt_versions/current/`.

## Response format

```text
Prompt Lab：<STARTED | BLOCKED | ROUND_REVIEW_READY>
run_dir: <path>
current_round: <n>
next_step:
- <exact command or AI action>
human_review: <path or None>
```
