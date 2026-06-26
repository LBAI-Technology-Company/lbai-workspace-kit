# Changelog

## 1.5.4

- **Two-command task lifecycle**: `/lbai-finish-task` auto-runs delivery when `task_output.md` is not ready; employees normally use `/lbai-new-task` → `/lbai-finish-task` only.
- **`check_task_delivery.py`**: new tool reports `auto_execute_needed` before finish review.
- **`finish_task.py` gate**: blocks finish when `task_output.md` is missing or unresolved `missing_inputs` remain.
- **`resolve_current_task.py`**: `finish` resolves OPEN/BLOCKED tasks without requiring `task_output.md` first.
- **Docs/adapters**: execute-task marked advanced/debug; contract, MCP, Codex plugin, FAQ, and manual test docs updated.
- **Tests**: `tests/integration/test_finish_delivery.py` covers resolve, delivery check, and finish gate.

## 1.5.3

- **Release tooling**: add `scripts/publish_release_assets.sh` to upload `install.sh`, `install.ps1`, and `install-bootstrap.ps1` to GitHub Releases (fixes `releases/latest/download/install.sh` 404 when assets are missing).
- **Docs**: Codex plugin release checklist now requires running the publish script after `gh release create`.

## 1.5.2

- **Installer**: `install.sh` / `install.ps1` now copy eight `/lbai-*` slash commands to `~/.cursor/commands/` on every install (idempotent overwrite), so `/lbai` works in any Cursor project without opening the employee workspace root.
- **Skip flag**: `LBAI_SKIP_CURSOR_COMMANDS=1` to opt out; install summary table adds a Cursor global commands row.
- **Docs**: README and `docs/CURSOR_MCP_SETUP.md` updated for auto-installed global slash commands.

## 1.5.1

- **Windows UTF-8 bootstrap**: add `install-bootstrap.ps1` release asset so `irm … | iex` decodes `install.ps1` as UTF-8 on Chinese Windows; document manual UTF-8 fallback in install docs and employee FAQ.
- **MCP docs**: add `docs/MCP_SETUP.md` for Claude Desktop, Windsurf, Cline, VS Code MCP, and other stdio clients; expand README MCP section and cross-link from `docs/CURSOR_MCP_SETUP.md`.
- **Installer hardening**: `install.ps1` gains `Ensure-ConsoleUtf8` / `Get-RemoteUtf8Text` helpers (integrity tests updated).
- **Tests**: fix doctor JSON smoke test to assert installed CLI version; fix remote workspace inspect test after template-local `.gitignore` policy.

## 1.5.0

- **Cursor MCP server**: add `cursor_plugin/` (stdlib MCP server + 9 tools + manifest) — eight LBAI workflows plus `lbai_doctor` available as MCP tools in any Cursor project via global `~/.cursor/mcp.json` registration.
- **Installer auto-registration**: `install.sh` / `install.ps1` now run `ensure_cursor_mcp()` to upsert `lbai-workspace` into `~/.cursor/mcp.json`; new `LBAI_SKIP_CURSOR_MCP` env flag; summary table gains Cursor MCP row.
- **Doctor integration**: `cursor_mcp` check added to `lbai doctor --json` checks (advisory, non-blocking); new `lbai_system/tools/check_cursor_mcp.py`.
- **Version sync**: `cursor_plugin/manifest.json` version field tracked by `scripts/bump_version.py` and verified in `tests/quality/test_cursor_mcp.py`.
- **Docs**: new `docs/CURSOR_MCP_SETUP.md`; README §2.7 plus Day-1 quickstart updated; AGENTS.md Cursor MCP adapter section; ROADMAP Stage 3 marked delivered.
- **Tests**: `tests/quality/test_cursor_mcp.py`, `tests/unit/test_mcp_json_merge.py`, and `test_cli_doctor_json_includes_cursor_mcp_check`.

## 1.4.26

- **Template-local Git policy**: workflow kit files (`lbai_system/`, `.cursor/`, `.agents/`, etc.) stay on disk only; GitHub sync is limited to employee artifacts (`tasks/`, `role_workspace/`, `prompt_lab/`, `.gitignore`).
- **`/lbai-update-kit` simplified**: always reports `git_status: LOCAL_ONLY` on success; legacy Git index cleanup is best-effort and non-blocking.
- **`lbai init-workspace`**: first commit/push stages employee data only (`GIT_TRACKED_PATHS`).
- Add `workspace_template/.gitignore` rules to prevent accidental template commits; add `tests/integration/test_git_sync_boundary.py`.
- Update employee docs, command contract, and Codex update-kit skill for single-device default.

## 1.4.25

- Capture employee/user conversation at `/lbai-finish-task` into `task_conversation.md` (redacted, synced with the task folder on GitHub push).
- Require `employee_conversation_turns` in finish-review enrichment JSON; update finish-task prompts, schema, and adapters.
- Restructure `README.md` and `README.zh-CN.md`: product summary → install → features, including a concise server sync boundary section.
- Streamline post-install setup hints in `lbai` CLI output.

## 1.4.24

- Add the required `role_workspace/knowledge/index.md` to every workspace template source so newly initialized and updated workspaces pass OKF validation.

## 1.4.23

- Resolve the repository identity from a repository API key during `lbai auth backend-login`.
- Persist the resolved `workspace_repo_id` with backend credentials and use it for knowledge searches, preventing false `401 Unauthorized` responses from shared workspace directory names.
- Keep the installer self-update version parser intact during future automated version bumps.
- Add explicit merge behavior for Git 2.54+ and make remote workspace inspection independent of a bare repository's default `HEAD`.

## 1.4.22

- Fix `install.sh` self-update version check: the sed pattern had its `[^"]*` placeholder clobbered to the literal version, causing `RE error: parentheses not balanced` and a broken remote-version comparison.
- Fix `install.sh` Python dependency install failing with `Missing dependencies for SOCKS support` when the caller's shell sets a SOCKS proxy (`all_proxy`/`ALL_PROXY`); pip now runs with proxy env vars stripped so it talks to PyPI directly.

## 1.4.21

- Drop the backend knowledge-service `identity token` requirement: the server now authenticates with the API Key only. `lbai auth backend-login` no longer prompts or blocks on an `identity_token`, the `--identity-token` / `--identity-header` flags are removed, the `X-LBAI-Identity-Token` header is no longer sent on searches, and `auth doctor` / `doctor` no longer report `backend_identity_token_available`.

## 1.4.20

- Add `scripts/bump_version.py` to atomically bump `workspaceKitVersion` / plugin / installer versions across every version-bearing file (fixes past drift in root `.lbai/workspace.json`).
- Clarify missing-information guidance: dialog input vs `/lbai-add-evidence` archival in `new_task.py` and `prepare_execute_task.py`.

## 1.4.19

- **Personal-repo-first bootstrap**: install only creates an empty workspace directory (`PENDING_BIND`); `lbai bind-github` and `lbai init-workspace` inspect the private repo first—restore existing LBAI workspaces without overlaying the installer template; seed enterprise template only for empty or boilerplate repos.
- **Pull before push**: `bind-github`, `/lbai-finish-task`, `/lbai-add-evidence`, and `/lbai-update-kit` fetch/pull remote changes before push (including unrelated-history merge on first bind).
- Update employee FAQ and install docs for multi-machine restore and explicit `/lbai-update-kit` upgrades.

## 1.4.18

- Add `lbai setup-guide` with a six-step beginner post-install checklist (shell reload, GitHub token, bind repo, doctor, backend login, role setup).
- Add `lbai bind-github` so employees paste only the private repo URL; the active workspace path is applied automatically.
- Rename Cursor role setup to `/lbai-role-setup` and Codex plugin skill to `lbai-role-setup` (aligned with **LBAI Role Setup**).
- Show `***` masked confirmation after GitHub Token and backend API Key input so paste success is obvious.
- Streamline installer bootstrap logging and print `lbai setup-guide` at the end of install.

## 1.4.17

- Complete Windows compatibility for UTF-8 output, long paths, path assertions, source-tree plugin preflight, and Prompt Lab cleanup.
- Publish the repository-binding guidance with a fully green Ubuntu and Windows CI baseline.

## 1.4.16

- Fix the test runner's virtualenv Python discovery on Windows.
- Keep `git` available when tests exercise the Git credential fallback on GitHub-hosted runners.

## 1.4.15

- Improve GitHub authentication guidance by separating credential readiness from workspace and private-repository binding status.
- Show the exact `lbai init-workspace --repo-url <private-repo-url> --path "<workspace>"` command when an existing workspace has no `origin`.
- Add a missing `origin` remote when binding an already initialized local workspace, and report missing `read:org` scope explicitly.

## 1.4.14

- Unify Codex plugin command names with Cursor `/lbai-*` commands: **LBAI Role Setup** for init and **LBAI Self Iterate** for self-iterate; update employee docs and install next-step hints.

## 1.4.13

- Fix `install.sh` capturing `info` and `pip` stdout into the generated `lbai` launcher, which broke `lbai workspace ensure` with `File name too long`.
- Document Codex plugin command palette names (`LBAI Role Setup`, `LBAI Self Iterate`, etc.) and align `lbai-init` / `lbai-self-iterate` display names.

## 1.4.12

- Rename `lbai auth login` to `lbai github auth token` for clearer GitHub PAT configuration.

## 1.4.11

- Print numbered install steps (`[步骤 N/12]`) and per-URL download progress so users can see where install stalls.

## 1.4.10

- Auto-create and register shared workspace at `~/.lbai/workspace` during install via `lbai workspace ensure`.
- Remove `lbai init-workspace` from default install steps; use it only for optional GitHub private repo binding.

## 1.4.9

- Switch employee install commands from jsDelivr CDN to GitHub `releases/latest/download` installer assets.
- Remove jsDelivr cache purge workflow; keep ghproxy as optional GitHub mirror in docs.

## 1.4.8

- Auto-purge jsDelivr `@latest` / `@main` cache on every GitHub release so piped `@latest` installers stay current.
- Bootstrap stale piped installers using GitHub `releases/latest/download` with ghproxy fallback.
- Document fallback install URL when output lacks **安装结果汇总**.

## 1.4.7

- Print an install summary table at the end of `install.sh` / `install.ps1` showing OK / failed / skipped / warning for Git, Python, LBAI CLI, Codex CLI, Codex plugin, and other components.

## 1.4.6

- Tighten `backend_search_query_plan_v1` to `types` / `statuses` / `include_related` and reject unknown fields.
- Improve `/lbai-add-evidence` sync messaging for `PUSHED`, `NO_CHANGES`, and `PUSH_FAILED`; return non-zero exit on push failure.
- Align default task backend search plan with OKF concept types.

## 1.4.5

- Always bootstrap piped `@latest` installers from GitHub latest release before install proceeds.
- Attach `install.sh` / `install.ps1` to GitHub releases for `releases/latest/download` bootstrap.
- Keep employee install commands on jsDelivr `@latest`; do not pin version tags in docs.

## 1.4.4

- Bootstrap stale `curl | sh` installers by re-fetching the latest `install.sh` / `install.ps1` from GitHub release tags (fixes jsDelivr `@latest` cache lag).
- Add Codex CLI fallback installers via npm and GitHub release binaries when `chatgpt.com` is unreachable.
- Auto-add `~/.local/bin` to shell PATH when installing Codex via GitHub binary fallback.

## 1.4.3

- Bundle OpenAI Codex CLI installation into `install.sh` and `install.ps1`.
- Auto-configure the `lbai-internal` Codex marketplace and install `lbai-workspace` from the same release tag.
- Add `LBAI_SKIP_CODEX_CLI` and `LBAI_SKIP_CODEX_PLUGIN` opt-out flags for installer automation.

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
