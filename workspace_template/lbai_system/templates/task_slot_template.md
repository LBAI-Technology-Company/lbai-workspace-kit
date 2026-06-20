# Task Slot

## allowed_sources

- This task folder
- Linked OKF Concepts under `role_workspace/knowledge/`
- Legacy task-local `input_*.md` when present
- Role world model files under `role_workspace/world_model/`
- Company guardrails under `lbai_system/company_guardrails/`

## forbidden_actions

- Do not invent missing source facts
- Do not fabricate data, metrics, benchmarks, customer evidence, case results, product capabilities, pricing, legal positions, approvals, or company commitments
- Do not write sensitive information
- Do not generate unauthorized public claims
- Do not mark review-required work as approved

## execution_standard

- Treat the output as internal company work, not casual chat
- Separate facts, assumptions, uncertainty, recommendations, and next steps
- Cite or name the source for success data, market claims, performance claims, and customer claims
- If feasibility is not verified, label the recommendation as an assumption and provide the validation step
- If required information is missing, state the exact missing material or decision

## output_path

## required_outputs

- `task_output.md`
- `task_ledger.md`

## completion_conditions

- Required input exists
- `task_output.md` generated
- `/lbai-finish-task` updates ledgers and commit readiness
