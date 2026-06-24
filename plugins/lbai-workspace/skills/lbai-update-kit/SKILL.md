---
name: lbai-update-kit
description: Update company-maintained LBAI workflow files while preserving employee-owned work. Use when the user asks to upgrade the workspace kit, repair an outdated workflow template, or resolve plugin/workspace compatibility warnings.
---

# LBAI Update Kit

Route reads and writes through the registered active workspace (`lbai workspace show`).

1. Run `lbai doctor --json --plugin-version 1.4.26 --min-workspace-version 1.4.1`, but allow `workspace_update_required` to proceed.
2. Read `lbai_system/runner_contracts/lbai_command_contract_v1.md` for `/lbai-update-kit`.
3. Run `lbai update-kit`.
4. Verify only company-managed paths changed locally; `role_workspace/`, `tasks/`, and normal Prompt Lab data must stay intact.
5. Run `lbai doctor --json --plugin-version 1.4.26 --min-workspace-version 1.4.1` again.
6. Report previous version, new version, updated local paths, and `git_status`.

Expected Git behavior (single-device default):

- Template files (`lbai_system/`, `.cursor/`, etc.) are updated **locally only**.
- Normal output: `git_status: LOCAL_ONLY` — this is success, not a sync failure.
- GitHub continues to receive only employee artifacts via `/lbai-finish-task` and `/lbai-add-evidence`.
- Legacy one-time Git cleanup may run in the background; it must not block the local update.

Do not manually copy templates or use broad Git staging. Do not modify employee-owned artifacts.
