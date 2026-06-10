# router_contract_v1

## Purpose

Return the next executable company capability when the employee is unsure how to proceed.

## Allowed Decisions

- `call_workspace_bootstrap_agent`
- `call_role_world_model_update_agent`
- `call_task_ledger_agent`
- `call_github_sync_agent`
- `call_company_guardrail_agent`
- `call_domain_specific_agent`
- `block_and_request_source`

## Rule

The router returns decisions, not broad advice.

If source material is missing or the request is ambiguous, return `block_and_request_source` with the exact missing input.
