# lbai_core

`lbai_core` is the installable command-line core for LBAI workspace operations.

In this first migrated version, `lbai_core` owns installation, initialization, update, doctor, and command routing. Daily workflow behavior is forwarded to the migrated `lbai_system/tools/` scripts inside each workspace so behavior stays compatible with the existing project.

## Commands

Terminal commands:

```text
lbai github auth token
lbai auth doctor
lbai init-workspace
lbai doctor
lbai update-kit
lbai remove-kit
lbai uninstall
```

AI desktop workflow commands are exposed as `/lbai-*` commands in Cursor and the Codex desktop app:

```text
/lbai-init
/lbai-add-evidence
/lbai-search-artifacts
/lbai-new-task
/lbai-execute-task
/lbai-finish-task
```

These workflows are routed through `lbai_system/tools/`, but commands that need AI-generated enrichment JSON should be launched from Cursor or the Codex desktop app. There is no rule-based fallback.

## MVP Command Boundaries

`lbai github auth token` captures GitHub authentication safely. It must not accept tokens through command-line arguments. After saving a token, it syncs Git credential helpers so bare `git push` works. Pressing Enter re-syncs credentials without requiring a new token unless the user wants to replace it.

`lbai init-workspace` uses the existing private repo flow:

```text
repo URL -> folder picker or default ./<repo-name> -> clone -> copy template -> commit -> push -> doctor
```

`lbai update-kit` updates company-managed template files in an existing workspace and must not overwrite employee-owned `role_workspace/` or `tasks/`.

`lbai remove-kit --confirm` removes company-managed template files from the current workspace and keeps `role_workspace/` and `tasks/`.

`lbai uninstall` removes `~/.lbai/kit/` and `~/.lbai/bin/lbai`. Use `--purge-auth` to delete the saved GitHub token as well.

To repair or upgrade the installed CLI, rerun `install.sh` (macOS/Linux) or `install.ps1` (Windows). There is no separate `self-update` command.

`lbai execute-task` may still rely on Codex or Cursor for model-generated work output in Stage 1. The CLI can prepare context, validate inputs, and write/check artifacts, but it should not become a full LLM runtime unless explicitly scoped later.

## Core Acceptance Standard

Every command should preserve:

- Company rules
- Evidence boundaries
- Task lifecycle state
- Delivery artifacts and hygiene checks
