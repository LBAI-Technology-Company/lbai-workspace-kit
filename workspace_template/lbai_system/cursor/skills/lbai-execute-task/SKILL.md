# LBAI Execute Task Skill

**Advanced/debug only.** Employees normally use `/lbai-finish-task`, which auto-runs delivery when needed.

Read `lbai_system/runner_contracts/lbai_command_contract_v1.md` and `lbai_system/prompts/execute_task_plan_prompt_v1.md`.

Run `python3 lbai_system/tools/prepare_execute_task.py <task_folder>` first. Then read `execution_plan.md` and write `task_output.md`.

If the employee provides missing details in chat, save direct clarifications as task-local input with `archive_input.py --resolves "<exact missing input>"`. Use one `--resolves` per covered missing input. Use `/lbai-add-evidence` only for source material that should be archived as reusable evidence.
