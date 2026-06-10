# GitHub Token Policy

## Principle

GitHub tokens are authentication material. They must not be written into workspace artifacts.

Forbidden storage locations:

```text
AGENTS.md
README.md
.env
role_workspace/
tasks/
evidence artifacts
task artifacts
shell history
command-line arguments
logs
```

## Recommended MVP

`lbai auth login` should prompt securely:

```text
Paste GitHub token:
```

The input should not echo in the terminal.

Prefer storage in:

- macOS Keychain
- Windows Credential Manager
- Linux Secret Service
- GitHub CLI credential store, if `gh` is installed

If secure OS storage is not implemented in the first internal prototype, use a clearly marked local developer-only fallback outside the workspace and document that it is temporary.

## Required Token Capability

For the selected existing-repo flow, the token needs access to:

- Read the public `lbai-workspace-kit` repo.
- Clone the employee private workspace repo.
- Commit and push to the employee private workspace repo.

If GitHub CLI is available, prefer:

```bash
gh auth login
lbai auth doctor
```

Then `lbai` can rely on Git credential state rather than storing a token directly.

## User Experience

The initializer should not ask for the token in the same prompt as repo URL and path. Authentication is a separate step:

```bash
lbai auth login
lbai init-workspace
```

This keeps secrets out of initialization logs and makes troubleshooting clearer.

