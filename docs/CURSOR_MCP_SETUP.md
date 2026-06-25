# LBAI Cursor MCP 服务器

## 职责边界

`lbai-workspace` MCP server 负责 Cursor 中的工具发现和命令转发。每个 MCP tool 都是对现有 `lbai` CLI 子命令的薄封装。`lbai` CLI 继续负责 GitHub/后端认证、工作区初始化、模板升级、检查、版本对齐和 Git 同步。

MCP server 不会打包员工的 `role_workspace/`、`tasks/`、凭证或工作区模板副本。正式业务规则仍以员工工作区中的 `lbai_system/runner_contracts/lbai_command_contract_v1.md` 为准。

## 安装

先安装 LBAI CLI，完成认证：

```text
lbai github auth token
lbai auth backend-login   # 可选，用于知识搜索
```

安装器 (`install.sh` / `install.ps1`) 会自动在 `~/.cursor/mcp.json` 中注册 `lbai-workspace` MCP server。全局注册后，在 Cursor 中打开任意项目，agent 工具列表中即可看到 `lbai_*` 工具；任务、证据和台账都会路由到 registered active workspace（`~/.lbai/config.json`）。

如需手动安装或排查，将以下块合并到 `~/.cursor/mcp.json`（不存在则新建）：

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

- `<venv-python>`：安装器 venv 中的 Python（通常 `~/.lbai/venv/bin/python3`，Windows 上为 `~\.lbai\venv\Scripts\python.exe`）。
- `<kit>`：lbai-workspace-kit 源码根目录（通常 `~/.lbai/kit`）。

写入后重启 Cursor，使 MCP server 生效。跳过自动安装：

```text
LBAI_SKIP_CURSOR_MCP=1 install.sh
```

## 日常入口

**命名约定**

MCP tool 名称使用 `lbai_` 前缀，保持与 CLI 子命令和 Codex skill 一致的命名空间。

| MCP tool | CLI 子命令 | Cursor 命令 | Codex 命令面板 |
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

Cmd/Ctrl+L 打开 Cursor agent 后，输入自然语言需求，或点击工具列表中的 `lbai_*` 工具。需要 `enrichment_json` 的工具请先按 `lbai_system/schemas/<name>_schema_v1.json` 生成 enrichment 对象，再调用 tool。

如果你在某个 LBAI 工作区项目里打开了 Cursor，项目本地的 `/.cursor/commands/lbai-*.md` 斜杠命令仍然可用；MCP tool 会把读写路由到 registered active workspace（`~/.lbai/config.json`）。

## 升级和卸载

安装器升级 kit 版本后重跑 `install.sh` / `install.ps1` 即自动更新 MCP server 注册（`mcp.json` 中的 `args` 路径已指向新版 `mcp_server.py`）。

```text
lbai update-kit                 # 升级工作流模板（不覆盖 MCP server 本身）
```

卸载：删除 `~/.cursor/mcp.json` 中的 `lbai-workspace` 条目并重启 Cursor，或删除整个 `mcp.json`（如需清理其他 MCP server 请只删 `lbai-workspace` 条目）。验证健康状态：

```text
lbai doctor --json              # checks.cursor_mcp 注册后显示 READY
```

## 故障排查

| 症状 | 解决 |
|---|---|
| agent 中看不到 `lbai_*` 工具 | 修改 `mcp.json` 后重启 Cursor |
| `lbai_cli_missing` | 重装 LBAI CLI，重开终端 |
| `workspace_not_initialized` | `lbai init-workspace` 或 `lbai workspace set --path <ws>` |
| `workspace_update_required` | 在工作区内运行 `lbai update-kit` |
| GitHub 认证不可用 | `lbai github auth token` |
| 知识服务不可用 | `lbai auth backend-login` |
