# Changelog

## 1.4.2

- Route plugin and CLI workflows to the registered global active workspace in `~/.lbai/config.json`.
- Allow LBAI commands from any Codex project once `lbai init-workspace` or `lbai workspace set` has registered the workspace.
- Record optional `source_project_path` on tasks created from an external project directory.
- Migrate backend knowledge search to `/v1/knowledge/search` with identity-token support in `lbai auth backend-login`.
- Decouple `/lbai-add-evidence` from automatic task linkage; evidence saves no longer require task context.
- Replace local evidence ledger flows with backend knowledge hygiene checks.
- Auto-install Git and Python 3.10+ prerequisites in `install.sh` when Homebrew or Linux package managers are available.

## 1.4.1

- Align plugin, LBAI CLI, and Workspace Kit version numbers.
- Require LBAI CLI and Workspace Kit 1.4.1 or later.

## 1.0.0

- Package eight LBAI workflows as Codex plugin skills.
- Add machine-readable CLI and plugin preflight checks.
- Add internal Git Marketplace metadata and product assets.
- Declare compatibility with LBAI CLI and Workspace Kit 1.4.0 or later.
