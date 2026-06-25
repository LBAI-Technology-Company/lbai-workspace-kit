# LBAI Codex 企业内部插件

## 职责边界

`lbai-workspace` 插件负责 Codex 中的工作流发现、AI enrichment 和命令编排。`lbai` CLI 继续负责 GitHub/后端认证、工作区初始化、模板升级、检查和 Git 同步。

插件不会打包员工的 `role_workspace/`、`tasks/`、凭证或工作区模板副本。正式业务规则仍以员工工作区中的 `lbai_system/runner_contracts/lbai_command_contract_v1.md` 为准。

## 安装

先安装 LBAI CLI，完成认证：

```text
lbai github auth token
lbai auth backend-login
```

安装器会自动创建并注册公用工作区（默认 `~/.lbai/workspace`，写入 `~/.lbai/config.json`）。之后你在 Codex 里打开任意项目，都可以从命令面板选择 LBAI 插件命令，或在对话里使用 `$lbai-*` skill 引用；任务、证据和台账都会写入这个统一工作区。

如需绑定 private GitHub 仓库做 Git 同步：

```text
lbai init-workspace --repo-url <private-repo> --path ~/.lbai/workspace
```

如需手动切换或补注册：

```text
lbai workspace show
lbai workspace set --path /path/to/lbai-workspace-xxx
```

管理员发布固定 Git tag 后，员工只需运行 `install.sh` / `install.ps1`；安装器会自动配置 Codex marketplace 并安装 `lbai-workspace` 插件。如需手动安装或排查，可使用：

```text
codex plugin marketplace add LBAI-Technology-Company/lbai-workspace-kit --ref <release-tag>
codex plugin add lbai-workspace@lbai-internal
```

安装或升级后开启新 Codex 线程，使新 Skills 生效。

## 日常入口

**命名约定**

- **Cursor**：使用 `/lbai-*` 斜杠命令（例如 `/lbai-self-iterate`）。
- **Codex 命令面板**：使用 **LBAI …** 显示名。除岗位设定外，显示名与 slash 命令一一对应：`/lbai-new-task` → **LBAI New Task**，`/lbai-self-iterate` → **LBAI Self Iterate**。岗位设定固定显示为 **LBAI Role Setup**（合同命令仍为 `/lbai-init`）。
- **Codex 对话**：也可写 `$lbai-init`、`$lbai-new-task`、`$lbai-self-iterate` 等 skill 引用。

安装 `lbai-workspace` 插件后，Codex 命令面板会展示 8 个 LBAI 命令。选中后会注入对应 skill；也可用自然语言描述同一动作。

| Codex 命令面板 | Skill ID | Cursor 命令 | Cursor MCP tool |
|---|---|---|---|
| **LBAI Role Setup** | `lbai-init` | `/lbai-init` | `lbai_role_setup` |
| **LBAI New Task** | `lbai-new-task` | `/lbai-new-task` | `lbai_new_task` |
| **LBAI Add Evidence** | `lbai-add-evidence` | `/lbai-add-evidence` | `lbai_add_evidence` |
| **LBAI Search Artifacts** | `lbai-search-artifacts` | `/lbai-search-artifacts` | `lbai_search_artifacts` |
| **LBAI Execute Task** | `lbai-execute-task` | `/lbai-execute-task` | `lbai_execute_task` |
| **LBAI Finish Task** | `lbai-finish-task` | `/lbai-finish-task` | `lbai_finish_task` |
| **LBAI Update Kit** | `lbai-update-kit` | `/lbai-update-kit` | `lbai_update_kit` |
| **LBAI Self Iterate** | `lbai-self-iterate` | `/lbai-self-iterate` | `lbai_self_iterate` |

Cursor 继续使用 `.cursor/commands/` 里的 `/lbai-*` 斜杠命令，或使用全局 MCP server 提供的 `lbai_*` 工具（详见 [Cursor MCP 文档](CURSOR_MCP_SETUP.md)）。两种入口均路由到 registered active workspace（`~/.lbai/config.json`）。

如果你在某个 LBAI 工作区项目里打开了 Codex，项目本地的 `$lbai-*` 或 `/lbai-*` 兼容入口仍然可用；全局插件命令会把读写路由到 registered active workspace（`~/.lbai/config.json`）。

## 升级和卸载

```text
codex plugin marketplace upgrade lbai-internal
codex plugin add lbai-workspace@lbai-internal
codex plugin remove lbai-workspace
```

插件升级与工作区模板升级相互独立。插件提示版本不兼容时，在员工工作区运行：

```text
lbai update-kit
```

`lbai-workspace`、LBAI CLI 与 Workspace Kit 从 1.4.1 起使用同一版本号。当前版本为 1.4.19，要求三者均为 1.4.1 或更高版本，具体契约记录在插件的 `compatibility.json`。

## 数据和凭证

- GitHub token 保存到本机 `~/.lbai/auth/`，不得写入仓库、任务或聊天产物。
- 员工工作产物只写入当前 private workspace。
- `/lbai-add-evidence` 和 `/lbai-finish-task` 仅同步合同允许的安全范围。
- `/lbai-search-artifacts` 通过后端知识服务查询，不扫描本地资料。
- 插件 preflight 只返回认证是否可用，不输出 token 或 API key。

## 故障排查

| 状态 | 处理 |
|---|---|
| `lbai_cli_missing` | 安装 LBAI CLI 后重新打开终端 |
| `workspace_not_initialized` | 运行 `lbai init-workspace` 或 `lbai workspace set --path <lbai-workspace>` |
| `workspace_update_required` | 在工作区运行 `lbai update-kit` |
| GitHub 认证不可用 | 运行 `lbai github auth token` |
| 知识服务认证不可用 | 运行 `lbai auth backend-login` |
| 缺少 origin/upstream | 修复 private workspace 的 Git remote 和跟踪分支 |
| 插件升级后未生效 | 新建 Codex 线程 |

## 发布检查

发布 tag 前必须同步更新：

- 根目录 `VERSION`
- 插件 `plugin.json` 版本
- 插件 `CHANGELOG.md`
- 兼容版本测试

使用固定 release tag 进行内部试点，不允许员工直接安装未经验证的 `main`。
