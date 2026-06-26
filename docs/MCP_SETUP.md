# LBAI MCP 服务器配置

## 职责边界

`lbai-workspace` MCP server 通过 **stdio** 协议暴露 8 个 LBAI 工作流 + `lbai_doctor` 健康检查。每个 MCP tool 都是对 `lbai` CLI 子命令的薄封装；业务规则仍以 active workspace 中的 `lbai_system/runner_contracts/lbai_command_contract_v1.md` 为准。

MCP server **不打包**员工的 `role_workspace/`、`tasks/`、凭证或工作区模板。读写一律路由到 `~/.lbai/config.json` 注册的 active workspace（与 Codex 插件相同）。

## 前置条件

```bash
lbai github auth token
lbai bind-github          # 或 lbai init-workspace
lbai auth backend-login   # 可选，知识搜索
```

## 通用 server 配置块

所有支持 **stdio MCP** 的客户端，都使用同一套 `lbai-workspace` 条目。将下列 JSON **合并**到对应客户端的配置文件（保留已有其他 server 条目）：

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

路径占位符（安装 `install.sh` / `install.ps1` 后的默认值）：

| 占位符 | macOS / Linux | Windows |
|--------|---------------|---------|
| `<venv-python>` | `~/.lbai/venv/bin/python3` | `%USERPROFILE%\.lbai\venv\Scripts\python.exe` |
| `<kit>` | `~/.lbai/kit` | `%USERPROFILE%\.lbai\kit` |

macOS 示例（请按本机用户名替换）：

```json
{
  "mcpServers": {
    "lbai-workspace": {
      "command": "/Users/you/.lbai/venv/bin/python3",
      "args": ["/Users/you/.lbai/kit/cursor_plugin/mcp_server.py"],
      "env": { "PYTHONPATH": "/Users/you/.lbai/kit/lbai_core" }
    }
  }
}
```

写入后**重启客户端**，使 MCP server 生效。

## 各 AI 工具配置文件位置

| AI 工具 | 配置文件 | 安装器是否自动写入 |
|---------|----------|-------------------|
| **Cursor** | `~/.cursor/mcp.json` | ✅ `install.sh` / `install.ps1` 自动注册 |
| **Claude Desktop** | macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`<br>Windows: `%APPDATA%\Claude\claude_desktop_config.json`<br>Linux: `~/.config/Claude/claude_desktop_config.json` | ❌ 手动合并 |
| **Windsurf** | `~/.codeium/windsurf/mcp_config.json` | ❌ 手动合并 |
| **Cline**（VS Code 扩展） | macOS: `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`<br>Windows: `%APPDATA%\Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json` | ❌ 手动合并 |
| **VS Code**（原生 MCP） | 项目级：`.vscode/mcp.json`（根键为 `servers`，部分版本为 `mcpServers`） | ❌ 手动合并 |
| **Claude Code** | 项目级：`.mcp.json`；或 CLI：`claude mcp add-json lbai-workspace '<json>'` | ❌ 手动 |

**Cursor 跳过自动安装：**

```bash
LBAI_SKIP_CURSOR_MCP=1 install.sh
```

**Claude Desktop 快捷入口：** Settings → Developer → Edit Config（会自动创建/打开配置文件）。

**Windsurf 快捷入口：** Cascade 面板 → MCP → Configure。

## MCP 工具一览

| MCP tool | CLI 子命令 | 对应 Cursor 斜杠命令 |
|----------|-----------|---------------------|
| `lbai_role_setup` | `lbai init --enrichment` | `/lbai-role-setup` |
| `lbai_new_task` | `lbai new-task --enrichment` | `/lbai-new-task` |
| `lbai_add_evidence` | `lbai add-evidence --enrichment` | `/lbai-add-evidence` |
| `lbai_search_artifacts` | `lbai search-artifacts --enrichment` | `/lbai-search-artifacts` |
| `lbai_execute_task` | `lbai execute-task` | `/lbai-execute-task` |
| `lbai_finish_task` | `lbai finish-task --enrichment` | `/lbai-finish-task` |
| `lbai_update_kit` | `lbai update-kit` | `/lbai-update-kit` |
| `lbai_self_iterate` | `lbai self-iterate` | `/lbai-self-iterate` |
| `lbai_doctor` | `lbai doctor --json` | — |

需要 `enrichment_json` 的工具：Agent 先按 active workspace 内 `lbai_system/schemas/*_schema_v1.json` 生成 JSON，再作为 tool 参数传入（与 Codex 插件 skill 契约相同）。

Codex 命令面板对照见 [Codex 插件文档](CODEX_PLUGIN_INTERNAL_MARKETPLACE.md#日常入口)。

## 与 Codex 插件的关系

| 维度 | MCP（任意 MCP 客户端） | Codex `lbai-workspace` 插件 |
|------|------------------------|----------------------------|
| 业务逻辑 | `lbai` CLI → `lbai_system/tools/` | 同左 |
| 工作区路由 | `~/.lbai/config.json` | 同左 |
| 触发方式 | 结构化 MCP tool call | Skill 引导 + 命令面板 |
| AI enrichment | Agent 生成 JSON → `--enrichment` | 同左 |

MCP 与 Codex 插件是同一套工作流的两种适配层；产物路径与格式一致。

## 升级与卸载

```bash
# 升级 kit 后重跑安装器，Cursor 的 mcp.json 会自动更新路径
install.sh   # 或 install.ps1

lbai update-kit   # 仅升级工作区模板，不覆盖 MCP server 本身
```

卸载：从对应客户端配置文件中删除 `lbai-workspace` 条目并重启客户端。

验证（Cursor 用户）：

```bash
lbai doctor --json   # checks.cursor_mcp 在 Cursor 注册后显示 READY（advisory）
```

## 故障排查

| 症状 | 处理 |
|------|------|
| 看不到 `lbai_*` 工具 | 检查 JSON 语法；修改配置后重启客户端 |
| `lbai_cli_missing` | 重装 LBAI CLI，重开终端 |
| `workspace_not_initialized` | `lbai bind-github` 或 `lbai workspace set --path <ws>` |
| `workspace_update_required` | 在工作区内运行 `lbai update-kit` |
| GitHub 认证不可用 | `lbai github auth token` |
| 知识服务不可用 | `lbai auth backend-login` |

Cursor 专项说明见 [Cursor MCP 文档](CURSOR_MCP_SETUP.md)。
