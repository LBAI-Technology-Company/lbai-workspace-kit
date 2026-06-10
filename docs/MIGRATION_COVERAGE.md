# Migration Coverage

## Summary

The first migration pass has moved the old workspace kit from a copied-folder model into the new `lbai-workspace-kit` project.

Covered:

- Workspace template files
- Codex project adapters
- Cursor commands and rules
- `.agents` skill adapters
- `lbai_system` contracts, guardrails, schemas, docs, templates, and tools
- Default `role_workspace` structure
- Empty `tasks` structure
- `workspace_dashboard.html`
- Local installer
- Lightweight `lbai` CLI
- Existing private repo initialization flow
- `lbai doctor`
- `lbai update-kit`
- Daily command routing for `init`, `new-task`, `add-evidence`, `search-artifacts`, and `finish-task`

Partially covered:

- `lbai execute-task`: resolves the task and prepares the execution handoff, but still expects Codex or Cursor to generate `task_output.md` because Stage 1 is not a standalone LLM runtime.
- `lbai auth login`: stores a token outside the workspace in the local LBAI home directory. A future version can use system Keychain or GitHub device login.

Not included by design:

- Old employee task history from the prototype workspace.
- Codex marketplace plugin.
- Cursor extension.
- GitHub Enterprise support.

## Verification Performed

- Installed from local checkout into a temporary `LBAI_HOME`.
- Initialized a workspace from a local bare Git repo.
- Verified commit and push to the temporary repo.
- Ran `lbai doctor` in the initialized workspace.
- Ran `lbai add-evidence`.
- Ran `lbai search-artifacts`.
- Ran `lbai new-task`.
- Ran `lbai update-kit --no-commit`.
- Ran Python syntax checks for the CLI and migrated workspace tools.

