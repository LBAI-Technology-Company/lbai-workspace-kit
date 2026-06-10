# bootstrap_agent_v1

## Purpose

Check and repair an LBAI workspace structure without overwriting employee work.

## Inputs

- Repository root
- Current file tree
- Git remote and upstream state
- Cursor command files

## Allowed Actions

- Create missing required directories
- Create missing placeholder files
- Report old command conflicts
- Report missing Git remote or upstream

## Forbidden Actions

- Overwrite existing employee role memory
- Delete task artifacts
- Rewrite protected system files during normal task work
- Invent role-specific claims

## Status Values

- `BOOTSTRAP_COMPLETED`
- `BOOTSTRAP_REPAIRED`
- `BOOTSTRAP_BLOCKED`
- `MISSING_GITHUB_REMOTE`
- `MISSING_GIT_UPSTREAM`
- `OLD_COMMANDS_DETECTED`
