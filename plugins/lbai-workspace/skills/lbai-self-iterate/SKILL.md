---
name: lbai-self-iterate
description: Start or continue an isolated LBAI Prompt Lab self-iteration experiment. Use when the user asks to evaluate or improve LBAI prompts using real task context or safe mock office scenarios without changing formal production prompts.
---

# LBAI Self Iterate

Route reads and writes through the registered active workspace (`lbai workspace show`). Commands work from any Codex project once `lbai init-workspace` or `lbai workspace set` has run.

1. Run `lbai doctor --json --plugin-version 1.4.16 --min-workspace-version 1.4.1`. Stop on an invalid or incompatible workspace.
2. Read the workspace `AGENTS.md`, `lbai_system/runner_contracts/lbai_command_contract_v1.md`, and `lbai_system/prompt_lab/README.md`.
3. Choose `intake_evidence` unless the user explicitly needs the full lifecycle chain.
4. Run `lbai self-iterate` with the requested rounds, focus, chain mode, review mode, and context mode.
5. Follow the emitted Prompt Lab next step. Use Codex as the executor; do not configure another LLM API.
6. Keep changes under `prompt_lab/` and isolated experiment workspaces. Only experimental prompt copies under `prompt_lab/prompt_versions/current/` may change.
7. Report run status, score, changed experimental prompts, administrator handoff location, and any redaction blocker.

Never modify `lbai_system/prompts/`, root `tasks/`, or root `role_workspace/`. Never commit raw Prompt Lab run data.
