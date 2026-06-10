# Workspace Template Boundary

This directory contains the files copied into each employee private workspace.

Company-managed files:

```text
AGENTS.md
README.md
.gitignore
.cursor/
.agents/
lbai_system/
workspace_dashboard.html
```

Employee-owned files initialized only when missing:

```text
role_workspace/
tasks/
```

`lbai update-kit` may overwrite company-managed files from this template. It must not overwrite existing employee-owned `role_workspace/` or `tasks/` content.
