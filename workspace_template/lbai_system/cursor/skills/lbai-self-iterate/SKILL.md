# LBAI Self Iterate Skill

Read `lbai_system/runner_contracts/lbai_command_contract_v1.md` and use `lbai_system/prompt_lab/prompt_lab.py`.

Flow: start Prompt Lab run → follow next-step instructions → generate scenario/evaluation JSON with the current AI → run deterministic tools in the isolated workspace → score → propose and conditionally apply experimental prompt patch.

Do not configure a separate LLM API and do not edit `lbai_system/prompts/`.

Do not commit or push mock scenario data to GitHub. After approval, use `prompt_lab.py finalize --run <run_dir>` to remove raw run data and keep only optimized experimental prompts.
