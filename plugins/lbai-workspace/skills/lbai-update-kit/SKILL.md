---
name: lbai-update-kit
description: Update company-maintained LBAI workflow files while preserving employee-owned work. Use when the user asks to upgrade the workspace kit, repair an outdated workflow template, or resolve plugin/workspace compatibility warnings.
---

# LBAI Update Kit

Route reads and writes through the registered active workspace (`lbai workspace show`). Commands work from any Codex project once `lbai init-workspace` or `lbai workspace set` has run.

1. Run `lbai doctor --json --plugin-version 1.4.7 --min-workspace-version 1.4.1`, but allow `workspace_update_required` to proceed. Doctor resolves the registered active workspace even when Codex is opened on another project.
2. Read the workspace `AGENTS.md` and `lbai_system/runner_contracts/lbai_command_contract_v1.md`.
3. Run `lbai update-kit`.
4. Verify the command changed only company-managed paths and did not overwrite `role_workspace/`, `tasks/`, or normal employee Prompt Lab data.
5. Run `lbai doctor --json --plugin-version 1.4.7 --min-workspace-version 1.4.1` again.
6. Report previous version, new version, changed managed paths, commit/push status, and any remaining blocker.

Do not manually copy templates or use broad Git staging. Do not modify employee-owned artifacts.
