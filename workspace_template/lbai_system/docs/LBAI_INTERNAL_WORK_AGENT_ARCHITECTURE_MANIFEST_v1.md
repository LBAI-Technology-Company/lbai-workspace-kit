# LBAI_INTERNAL_WORK_AGENT_ARCHITECTURE_MANIFEST_v1

## Purpose

This manifest defines the intended company-agent architecture for `lbai-workspace-kit` v0.5. v0.5 contains contracts and minimal tools only. It does not claim to be a complete MCP or autonomous runtime.

## Core Function

```text
让聪明模型在公司规则、证据边界、任务流程、交付标准里稳定工作。
```

The architecture should be evaluated by whether it keeps model behavior inside those four controls, not by whether it adds more general AI features.

## Agent Layers

| layer | agent | purpose | input sources | output artifacts | hard blocks |
|---|---|---|---|---|---|
| 1 | Internal Runtime Router Agent | Choose the next company capability when the employee is unsure | User request, task state, role memory, guardrails | Router decision | Ambiguous request, missing source, unsafe action |
| 2 | Workspace Bootstrap Agent | Check and repair workspace structure without overwriting employee work | Repo tree, Git status, command files | Bootstrap report | Non-workspace root, conflicting files, missing Git context needing human setup |
| 3 | Role World Model Update Agent | Convert approved evidence into role model deltas | Current role world model, evidence artifacts, guardrails | Delta, version artifact, lineage | Untrusted evidence, unsupported claim, review-required change |
| 4 | Task Ledger Agent | Admit task state into structured ledgers | Task folder, source artifacts, outputs, Git status | Task ledger entry and global ledger row | Missing task contract, missing output, unsafe source |
| 5 | GitHub Sync / Repo Hygiene Agent | Commit and push safe workspace artifacts | Git status, hygiene check, task ledger | Commit, push status | Sensitive info, temp files, non-task changes, no upstream |
| 6 | Company Guardrail Agent | Apply source, review, public claim, and sensitive data boundaries | Company guardrail files, task scope, output | Guardrail decision | Public claim without source, sensitive data, review-required finalization |
| 7 | Domain-specific Agents | Add website, support bot, PR, finance, hiring, or legal-specific checks | Domain sources and benchmark sets | Domain reports | Missing benchmark/source, forbidden claims |

## Router Decisions

Allowed router outputs:

- `call_workspace_bootstrap_agent`
- `call_role_world_model_update_agent`
- `call_task_ledger_agent`
- `call_github_sync_agent`
- `call_company_guardrail_agent`
- `call_domain_specific_agent`
- `block_and_request_source`

Router outputs must be executable decisions, not general advice.

## Artifact Rule

Formal work must land in repo artifacts before it is treated as company state:

```text
external evidence -> adjudication/structuring -> task artifact -> ledger -> private GitHub sync
```
