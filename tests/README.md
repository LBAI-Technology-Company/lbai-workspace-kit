# LBAI Workspace Kit — 测试套件

独立测试目录，**不会修改** `workspace_template/` 或仓库内真实 `role_workspace/`、`tasks/`。所有集成测试在临时 git 工作区中运行。

## 快速运行

```bash
# 安装依赖并运行全部测试
bash tests/run_tests.sh

# 或手动
python3 -m pip install -r tests/requirements-test.txt
python3 -m pytest tests/ -c tests/pytest.ini -v
```

## 目录结构

```
tests/
├── conftest.py              # pytest fixtures（隔离工作区）
├── fixtures/
│   ├── enrichments/         # 模拟 AI 产出的 JSON（非真实 Agent 调用）
│   └── samples/             # 样例输入文本
├── helpers/
│   ├── workspace.py         # 复制 template + git init
│   └── tool_runner.py       # subprocess 调用 tools
├── unit/                    # enrichment_utils、task_utils、schema 校验
├── integration/             # 各 lbai 命令工具
├── quality/                 # prompt/schema/contract/bootstrap 完整性
└── run_tests.sh
```

## 覆盖范围

| 类别 | 覆盖内容 |
|------|----------|
| **阻断** | 无 `--enrichment` 时 add/search/new/finish/init 均 BLOCKED |
| **add-evidence** | 落盘、ledger、AI NEEDS_REVIEW、无关键词 overlay、脱敏、非法 schema |
| **new-task** | OPEN / BLOCKED / review 文件 |
| **init** | `--print-questions`、role 文件更新、缺 section 阻断 |
| **search** | catalog 导出、FOUND / NO_MATCH、非法 path |
| **finish** | review 产物、BLOCK_FINISH → commit_readiness |
| **e2e** | init → blocked task → linked evidence → search → finish |
| **quality** | prompt/schema 存在、runner contract、bootstrap、hygiene |

## 设计原则

1. **隔离**：`tmp_path` 下复制 `workspace_template`，`git init` 后执行，测完自动删除。
2. **无 AI 依赖**：enrichment JSON 来自 `fixtures/`，测的是**代码路径与校验逻辑**，不是 LLM 质量。
3. **无网络**：默认 `--no-sync`（add-evidence）或无 remote（finish 允许 git BLOCKED）。
4. **可扩展**：新增命令时添加 fixture + `integration/test_*.py` 即可。

## 按标记运行

```bash
python3 -m pytest tests/ -c tests/pytest.ini -m unit
python3 -m pytest tests/ -c tests/pytest.ini -m integration
python3 -m pytest tests/ -c tests/pytest.ini -m e2e
python3 -m pytest tests/ -c tests/pytest.ini -m quality
```

## 与真实插件的关系

- 测试读取 **`workspace_template/lbai_system/tools/`** 中的真实工具代码。
- 不调用 Cursor/Codex API；Agent 行为需人工或单独 E2E 验证。
- 若修改 tool CLI 或 schema，同步更新 `tests/fixtures/enrichments/` 与对应用例。
