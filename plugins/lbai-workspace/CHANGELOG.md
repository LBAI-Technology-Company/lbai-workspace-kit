# Changelog

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
