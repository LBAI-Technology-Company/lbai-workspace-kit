# LBAI_WORK_RUNTIME_RULES_V2

## Core Acceptance Standard

The workflow runtime exists to:

```text
让聪明模型在公司规则、证据边界、任务流程、交付标准里稳定工作。
```

No model output becomes a company work product unless it preserves company rules, evidence boundaries, task lifecycle state, and artifact delivery requirements.

## Core Runtime Split

- AI chat is for exploration, clarification, and execution slot generation.
- Cursor or Codex is the employee workspace execution runtime.
- GitHub is the durable private artifact ledger.
- Chat output is not a final company work product until it is converted into repo artifacts.

## Formal Work Rule

Every formal task should produce or update a task folder under `tasks/`.

Formal task completion requires:

- Task contract files
- Output artifact
- Task ledger update
- Guardrail check
- Private GitHub sync when safe

## Evidence Rule

Meeting transcripts, founder updates, customer feedback, and pasted chat content are external evidence.

External evidence must be captured, structured or adjudicated, and admitted into a repo artifact before becoming role memory, company state, or public-facing content.

Task outputs must distinguish facts, assumptions, uncertainty, recommendations, and next steps.

Success data, metrics, benchmarks, customer evidence, case results, market claims, performance claims, product capability claims, pricing claims, legal positions, approvals, and company commitments must trace to task inputs, approved references, or explicitly cited external sources when browsing is allowed.

Do not fabricate evidence-like details to make a work product appear complete.

If feasibility cannot be verified from available information, label the recommendation as an assumption and include the validation step.

## Review Rule

Review-required work may be pushed to the private GitHub artifact ledger as draft or waiting-review evidence.

Private GitHub sync does not mean public approval, legal approval, release approval, or founder approval.
