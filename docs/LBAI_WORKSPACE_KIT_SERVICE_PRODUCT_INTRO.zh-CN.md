# LBAI Workspace Kit + Service 产品介绍

## 一句话说明

LBAI Workspace Kit 是面向员工 AI 办公的工作区套件；它把 Cursor、Codex 这类模型放进公司规则、知识边界、任务流程和交付标准里工作。后端知识 service 以 OKF Markdown 为唯一知识源，负责版本、校验、权限和检索。

## 适合会议开场的介绍

我们现在做的不是一个单纯的 AI 聊天工具，而是一套“员工 AI 办公工作区”。

员工每天会把会议纪要、客户反馈、项目材料、制度文件、任务输出放进 Cursor 或 Codex。如果没有工作区约束，这些内容很容易只停留在聊天里，无法追踪、复盘和复用。LBAI Workspace Kit 的作用，就是把这些工作变成标准化任务和 OKF 知识，并安全同步到员工自己的 private GitHub workspace。

员工端保持轻量。员工先安装 `lbai` CLI，初始化自己的 workspace，然后在 Cursor 或 Codex 里使用 `/lbai-*` 命令完成日常工作，包括初始化岗位信息、保存资料、创建任务、执行任务、完成收尾、搜索历史证据和更新 kit。

Workspace Kit 主要解决三件事：

1. 把聊天里的正式工作转成可追踪任务。
2. 把会议纪要、反馈、制度、项目材料沉淀为可读、可 Diff、可链接的 OKF Concept。
3. 在交付前检查来源、敏感信息、review 边界和交付质量，并同步到 private GitHub。

后端知识 service 的定位，是把多个员工 workspace 中持续产生的 OKF Concept 同步成公司级可检索知识。后端通过 GitHub webhook 或定时同步读取完整 Bundle，校验 frontmatter、链接和 UID，再建立 revision、section、原子事实、全文索引、向量索引和关系图。

当员工搜索公司知识时，Cursor/Codex 先生成 `backend_search_query_plan_v1` 查询计划，员工端调用后端 `POST /v1/knowledge/search`。后端返回可追溯的 Concept、section、fact、citation 和 Git commit 来源。

整个闭环是：员工把资料保存为 OKF Concept，GitHub 同步到后端，后端原子发布并建立混合索引，员工任务检索可追溯知识，AI 基于知识完成任务，结果再回到 workspace。

## 当前落地口径

- 已落地：`lbai` CLI、workspace 模板、Cursor/Codex `/lbai-*` 工作流、资料和任务落盘、GitHub 同步、后端检索调用契约。
- 已对齐：员工端 `/lbai-search-artifacts` 只调用后端知识服务，不回退本地搜索。
- 已落地：repo 同步、OKF 校验、原子事实、结构化数据库、权限过滤、冲突检测、管理后台和混合检索。

## 核心对象

- 员工命令：`/lbai-init`、`/lbai-add-evidence`、`/lbai-search-artifacts`、`/lbai-new-task`、`/lbai-execute-task`、`/lbai-finish-task`、`/lbai-update-kit`、`/lbai-self-iterate`。
- 员工 workspace：`.lbai/workspace.json` 保存员工技术身份和后端配置；`role_workspace/knowledge/` 保存 OKF；`tasks/` 保存任务过程和结果。
- 后端 API：`POST /v1/knowledge/search` 返回 `knowledge_search_response_v1`。
- 知识对象：Concept、Revision、Section、Fact、Link 和 Citation。

## 讲图顺序

1. 先讲左侧员工入口：安装 CLI，打开 Cursor/Codex，使用 `/lbai-*`。
2. 再讲中间 workspace kit：任务、资料、台账、交付检查、GitHub 同步。
3. 然后讲右侧 service：同步、解析、抽取、校验、入库、检索。
4. 最后讲底部闭环：资料沉淀、证据检索、任务执行、交付检查、知识回流。
