# /lbai-update-kit

Cursor command wrapper for the shared LBAI workflow contract.

Source override:

{{input}}

## Required behavior

Read `lbai_system/runner_contracts/lbai_command_contract_v1.md` and execute the `/lbai-update-kit` section.

普通员工通常留空，直接运行默认升级。管理员测试本地模板时，填写本地文件夹路径，例如 `/path/to/lbai-workspace-kit/workspace_template`；不要加 `local:` 前缀。

Use existing tools under `lbai_system/tools/`. Do not duplicate command logic in this adapter.

## Response format

Use the `/lbai-update-kit` response format from `lbai_system/runner_contracts/lbai_command_contract_v1.md`.
