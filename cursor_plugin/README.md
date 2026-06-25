# LBAI Cursor MCP Plugin

`lbai-workspace` MCP server exposes the eight LBAI enterprise workflows plus a
health-check tool to any Cursor project. After registration in
`~/.cursor/mcp.json`, the tools are available globally and route reads/writes
to the registered active workspace in `~/.lbai/config.json`.

This is the Cursor counterpart of the Codex `lbai-workspace` plugin. The LBAI
CLI remains the single source of truth for authentication, workspace
initialization, versioning, and Git synchronization.

## Responsibility boundary

The MCP server handles tool discovery and command dispatch only. The `lbai`
CLI handles GitHub/backend auth, workspace initialization, template upgrades,
the doctor check, and Git sync. The server never bundles an employee's
`role_workspace/`, `tasks/`, credentials, or workspace template copy.

## Install

The LBAI installer (`install.sh` / `install.ps1`) configures `~/.cursor/mcp.json`
automatically. Manual install or troubleshooting:

```bash
# 1. Install + authenticate the lbai CLI first.
lbai github auth token
lbai auth backend-login   # optional, for knowledge search

# 2. Register the MCP server globally.
#    <kit> is the lbai-workspace-kit source root (e.g. ~/.lbai/kit).
```

Merge this block into `~/.cursor/mcp.json` (create it if absent):

```json
{
  "mcpServers": {
    "lbai-workspace": {
      "command": "<venv-python>",
      "args": ["<kit>/cursor_plugin/mcp_server.py"],
      "env": { "PYTHONPATH": "<kit>/lbai_core" }
    }
  }
}
```

`<venv-python>` is the Python in the installer venv (typically
`~/.lbai/venv/bin/python3`). After saving, restart Cursor and open any
project; the LBAI tools appear in the agent tool list.

## Tools

| MCP tool | CLI subcommand | Cursor command | Codex palette |
|---|---|---|---|
| `lbai_role_setup` | `lbai init --enrichment` | `/lbai-role-setup` | LBAI Role Setup |
| `lbai_new_task` | `lbai new-task --enrichment` | `/lbai-new-task` | LBAI New Task |
| `lbai_add_evidence` | `lbai add-evidence --enrichment` | `/lbai-add-evidence` | LBAI Add Evidence |
| `lbai_search_artifacts` | `lbai search-artifacts --enrichment` | `/lbai-search-artifacts` | LBAI Search Artifacts |
| `lbai_execute_task` | `lbai execute-task` | `/lbai-execute-task` | LBAI Execute Task |
| `lbai_finish_task` | `lbai finish-task --enrichment` | `/lbai-finish-task` | LBAI Finish Task |
| `lbai_update_kit` | `lbai update-kit` | `/lbai-update-kit` | LBAI Update Kit |
| `lbai_self_iterate` | `lbai self-iterate` | `/lbai-self-iterate` | LBAI Self Iterate |
| `lbai_doctor` | `lbai doctor --json` | — | — |

Tools that take `enrichment_json` require a JSON object generated per the
matching `lbai_system/schemas/*_schema_v1.json`. The server writes it to a
temporary file and passes `--enrichment <tmpfile>` to the CLI.

## Upgrade and uninstall

```bash
lbai update-kit              # upgrade workflow templates (does not touch the server)
```

To remove the MCP server, delete the `lbai-workspace` entry from
`~/.cursor/mcp.json` and restart Cursor. To verify health:

```bash
lbai doctor --json           # checks.cursor_mcp reports READY when registered
```

## Data and credentials

- GitHub token is stored locally under `~/.lbai/auth/` and never written to
  the repo, tasks, or chat artifacts.
- Employee work products are written only to the registered private workspace.
- `lbai_doctor` reports whether auth is available; it does not emit tokens or
  API keys.

## Troubleshooting

| Symptom | Fix |
|---|---|
| tools not visible in Cursor | restart Cursor after editing `mcp.json` |
| `lbai_cli_missing` | reinstall the LBAI CLI, reopen the terminal |
| `workspace_not_initialized` | run `lbai init-workspace` or `lbai workspace set --path <ws>` |
| `workspace_update_required` | run `lbai update-kit` in the workspace |
| GitHub auth unavailable | run `lbai github auth token` |
| knowledge auth unavailable | run `lbai auth backend-login` |
