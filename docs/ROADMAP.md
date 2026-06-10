# Roadmap

## Stage 1: Installer And Core

Goal: replace manual folder copying.

Deliverables:

- Public GitHub repo `lbai-workspace-kit`
- `install.sh` and `install.ps1`
- Local `lbai` command
- `lbai auth login`
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

## Stage 3: Cursor Extension

Goal: improve Cursor native UI.

Deliverables:

- Cursor or VS Code extension
- Command palette actions
- Workspace health status
- One-click doctor/update-kit

Constraint:

Cursor extension remains thin. It calls `lbai_core`.

## Later Options

- Company install domain, such as `https://install.lbai.com`
- Browser OAuth or device-code authentication
- Auto-create private repos
- Admin-managed employee repo provisioning
- Optional standalone LLM execution provider

