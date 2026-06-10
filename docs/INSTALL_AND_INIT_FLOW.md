# Install And Init Flow

## Public Install Command

Employee install command:

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/LBAI-Technology-Company/lbai-workspace-kit@v0.1.4/install.sh | sh
source ~/.zshrc
lbai auth login
lbai init-workspace
```

The installer downloads the release package through internal mirrors when needed. Employees only need the one command above.

## Authentication

Do not pass tokens as command-line arguments.

Good:

```bash
lbai auth login
```

Avoid:

```bash
lbai init-workspace --github-token ghp_xxx
```

## Existing Repo Flow

The selected MVP path is:

```text
Use an existing private GitHub repo.
```

`lbai init-workspace` should ask for:

- Existing private repo URL
- Local workspace folder path

Example interactive result:

```text
GitHub repo URL: https://github.com/LBAI-Technology-Company/lbai-workspace-zhangsan.git
Local folder path: ~/LBAI/lbai-workspace-zhangsan
```

## Init Steps

```text
1. Read GitHub authentication from `lbai auth login`, `GITHUB_TOKEN`, `GH_TOKEN`, or GitHub CLI credential state.
2. Clone the private repo into the selected local path, or use an existing local Git repo.
3. Copy files from `workspace_template/`.
4. Overwrite company-managed paths.
5. Fill missing employee default paths without overwriting existing `role_workspace/` or `tasks/` files.
6. Write workspace version metadata.
7. Stage only initialized template files.
8. Commit with a clear initialization message.
9. Push to the existing private repo unless `--no-push` is used.
10. Run `lbai doctor`.
```

Recommended initialization commit:

```text
chore(lbai): initialize workspace kit
```

## Local-Only Fallback

If GitHub authentication or repo access fails, the current CLI stops and reports the blocked reason. A later convenience feature may offer local-only initialization and a separate reconnect command.

```text
Create local workspace without GitHub sync now?
```

That reconnect command is not implemented in the current MVP.
