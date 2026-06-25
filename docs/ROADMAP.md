# Roadmap

## Stage 1: Installer And Core

Goal: replace manual folder copying.

Deliverables:

- Public GitHub repo `lbai-workspace-kit`
- `install.sh` and `install.ps1`
- Local `lbai` command
- `lbai github auth token`
- `lbai init-workspace`
- Existing private repo flow
- Workspace template copy
- `lbai doctor`
- `lbai update-kit`

Success criteria:

- Employee can initialize a usable private workspace without manually copying folders.
- Generated workspace supports the current `/lbai-*` daily workflow in Codex and Cursor.
- No GitHub token is stored in repo artifacts.
- `/lbai-update-kit` continues to upgrade managed workflow files.

## Stage 2: Codex Adapter Package

Goal: improve Codex entry experience.

Deliverables:

- Codex project adapter package or plugin wrapper
- Better command discovery
- Direct bridge from `/lbai-*` to installed `lbai` CLI

Constraint:

Codex adapter remains thin. It must not duplicate business workflow logic.

## Stage 3: Cursor Extension ✅ (delivered via global MCP server, v1.5.0)

Goal: improve Cursor native UI.

Deliverables:

- ✅ Global MCP server (`cursor_plugin/mcp_server.py`) registered in `~/.cursor/mcp.json` — available in any Cursor project
- ✅ 9 MCP tools: eight LBAI workflows + health check (`lbai_doctor`)
- ✅ Installer auto-registration (`install.sh` / `install.ps1`) with `LBAI_SKIP_CURSOR_MCP` flag
- ✅ `lbai doctor --json` includes advisory `cursor_mcp` check
- ✅ `docs/CURSOR_MCP_SETUP.md` (manual install, troubleshooting, naming table)
- ✅ Version sync: `cursor_plugin/manifest.json` tracked by `scripts/bump_version.py`

Constraint:

MCP server remains thin. Each tool shells out to the `lbai` CLI — it does not duplicate business workflow logic, enrichment prompts, or workspace management.

## Later Options

- Company install domain, such as `https://install.lbai.com`
- Browser OAuth or device-code authentication
- Auto-create private repos
- Admin-managed employee repo provisioning
- Optional standalone LLM execution provider

