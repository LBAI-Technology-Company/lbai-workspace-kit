# LBAI Prompt Lab Records

This folder stores local prompt iteration records.

Prompt Lab writes experiment runs, tool outputs, evaluations, and experimental prompt versions here. It does not store normal employee task artifacts; those remain under `tasks/`.

Formal workflow prompts remain under `lbai_system/prompts/` and are not changed automatically by Prompt Lab.

Mock run data is local-only and should be removed with `prompt_lab.py finalize --run <run_dir>` after human approval. The final retained artifact is the optimized experimental prompt under `prompt_versions/current/`.

Do not commit `prompt_lab/runs/` or `prompt_lab/finalized_reports/`; they are gitignored. Only use `prompt_lab.py run-tool` against isolated workspaces under `prompt_lab/runs/*/workspaces/`.
