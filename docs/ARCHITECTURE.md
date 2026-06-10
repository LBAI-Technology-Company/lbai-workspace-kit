# Architecture

## Decision

Use one public repository for the first phase:

```text
lbai-workspace-kit
```

This repository contains installer planning, CLI core planning, workspace template planning, and upgrade planning.

## Why One Repository

The current project is not considered sensitive. Splitting installer, core, and template into three repositories would add avoidable operational overhead.

One repository is easier to maintain because:

- One public URL can install the kit.
- One version controls installer, core, and template compatibility.
- `/lbai-update-kit` can fetch from the same release source.
- There is no cross-repo permission or release coordination problem.
- The team can split repositories later if sensitive logic or stricter release governance appears.

## Logical Modules

Even with one repository, keep clear directory boundaries:

```text
install.sh           macOS / Linux installer entry
install.ps1          Windows installer entry
lbai_core/           installable CLI and workflow core
workspace_template/  files copied into employee private repos
docs/                planning and operating documentation
```

## Runtime Model

```text
Employee terminal
  -> install.sh or install.ps1
  -> lbai CLI
  -> init-workspace
  -> employee private GitHub repo
  -> Codex/Cursor project adapters
  -> /lbai-* daily workflow
```

Codex and Cursor remain the model execution environments. The `lbai` CLI owns deterministic workflow state, checks, templates, ledgers, and safe sync.

## Non-Goals For Stage 1

- No Cursor extension.
- No Codex plugin marketplace package.
- No GitHub Enterprise dependency.
- No custom install domain requirement.
- No standalone LLM agent runtime.

