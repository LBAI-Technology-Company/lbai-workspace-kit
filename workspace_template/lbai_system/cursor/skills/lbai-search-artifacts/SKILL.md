# LBAI Search Artifacts Skill

Read `lbai_system/runner_contracts/lbai_command_contract_v1.md` and `lbai_system/prompts/backend_search_query_plan_prompt_v1.md`.

Flow: AI backend query plan JSON → `search_artifacts.py --enrichment`. The tool calls only the backend knowledge service and displays the backend response directly. If the backend is disabled, unavailable, has no matches, or returns invalid data, display the result or error only; do not search local workspace artifacts and do not automatically block, mutate, advance, or finish any task flow.
