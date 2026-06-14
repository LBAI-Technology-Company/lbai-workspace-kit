# LBAI New Task Skill

Read `lbai_system/runner_contracts/lbai_command_contract_v1.md` and `lbai_system/prompts/task_intake_enrichment_prompt_v1.md`.

Flow: read role context + conversation context + relevant prior artifacts → AI task intake JSON → `new_task.py --enrichment`. No fallback.

The intake JSON must separate known information by source, blocking gaps, and recommended non-blocking context. Direct employee clarifications are task-local context; `/lbai-add-evidence` is only for reusable/source material.
