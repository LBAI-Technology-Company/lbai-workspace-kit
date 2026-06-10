# Migration From Current Project

## Current State

The existing project:

```text
lbai_cursor_workspace_kit_v7
```

is the working prototype and should remain unchanged during this planning step.

It already contains:

- `AGENTS.md`
- Cursor command adapters
- Codex project adapters
- `lbai_system/`
- `role_workspace/`
- `tasks/`
- `workspace_dashboard.html`

## Target State

This new project:

```text
lbai-workspace-kit
```

will become the single public distribution repo.

## Migration Steps

1. Keep the current project as a reference implementation.
2. Move template files into `workspace_template/`.
3. Move deterministic command logic into `lbai_core/`.
4. Keep `/lbai-*` employee command names stable.
5. Make generated Codex and Cursor adapters call installed `lbai` commands.
6. Add `install.sh`.
7. Add `lbai init-workspace` for the existing private repo flow.
8. Add `lbai update-kit` for managed template upgrades.

## Compatibility Rule

Daily employee command surface must remain:

```text
/lbai-init
/lbai-add-evidence
/lbai-search-artifacts
/lbai-new-task
/lbai-execute-task
/lbai-finish-task
/lbai-update-kit
```

The implementation behind those commands may move from local scripts to installed `lbai_core`, but the employee-facing commands should stay stable.

