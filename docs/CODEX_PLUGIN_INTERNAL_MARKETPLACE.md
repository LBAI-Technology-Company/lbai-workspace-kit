# LBAI Codex 企业内部插件

## 职责边界

`lbai-workspace` 插件负责 Codex 中的工作流发现、AI enrichment 和命令编排。`lbai` CLI 继续负责 GitHub/后端认证、工作区初始化、模板升级、检查和 Git 同步。

插件不会打包员工的 `role_workspace/`、`tasks/`、凭证或工作区模板副本。正式业务规则仍以员工工作区中的 `lbai_system/runner_contracts/lbai_command_contract_v1.md` 为准。

## 安装

先安装 LBAI CLI，完成认证和工作区初始化：

```text
lbai auth login
lbai auth backend-login
lbai init-workspace
```

`init-workspace` 会自动把该工作区注册为本机默认 active workspace（写入 `~/.lbai/config.json`）。之后你在 Codex 里打开任意项目，都可以调用 `$lbai-workspace:*` 或 `/lbai-*`；任务、证据和台账都会写入这个统一工作区。

如需手动切换或补注册：

```text
lbai workspace show
lbai workspace set --path /path/to/lbai-workspace-xxx
```

管理员发布固定 Git tag 后，在 Codex 中安装 Marketplace 和插件：

```text
codex plugin marketplace add LBAI-Technology-Company/lbai-workspace-kit --ref <release-tag>
codex plugin add lbai-workspace@lbai-internal
```

安装或升级后开启新 Codex 线程，使新 Skills 生效。

## 日常入口

安装插件后，Codex 会以插件命名空间展示 Skills，例如 `$lbai-workspace:lbai-init`、`$lbai-workspace:lbai-new-task` 和 `$lbai-workspace:lbai-finish-task`，也可用自然语言触发。项目内原有 `$lbai-*` 或 `/lbai-*` 兼容入口继续保留。

Cursor 原有 `/lbai-*` 命令保持不变。

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

`lbai-workspace`、LBAI CLI 与 Workspace Kit 从 1.4.1 起使用同一版本号。当前版本为 1.4.2，要求三者均为 1.4.1 或更高版本，具体契约记录在插件的 `compatibility.json`。

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
| GitHub 认证不可用 | 运行 `lbai auth login` |
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
