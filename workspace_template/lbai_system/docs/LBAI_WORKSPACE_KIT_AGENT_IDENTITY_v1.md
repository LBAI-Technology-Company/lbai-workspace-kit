# LBAI_WORKSPACE_KIT_AGENT_IDENTITY_v1

## Identity

`lbai-workspace-kit` is the LBAI employee workspace bootstrap substrate and internal work runtime foundation.

Its core function is to let capable models work stably inside company rules, evidence boundaries, task processes, and delivery standards.

It provides:

- Cursor and Codex project adapter structure
- Employee role memory
- Formal task folders
- Task ledger and repo artifact hygiene
- Guardrail sources for internal work
- Minimal contracts for future company-defined agents

## Not This

`lbai-workspace-kit` is not:

- The full LBAI internal work runtime agent system
- A full autonomous agent
- A public-facing product
- Any public-facing product
- A replacement for founder, owner, legal, security, finance, or hiring review

## Version Positioning

v0.1 was an employee Cursor workspace kit.

v0.5 is an internal work runtime foundation. It adds canonical guardrails, structured ledgers, bootstrap checks, safe GitHub sync, template updates, role workspace defaults, a local status dashboard, and a project-local Codex adapter while preserving the low-friction employee command surface.

## Employee Command Surface

Daily employee work should remain simple:

```text
/lbai-new-task
/lbai-add-evidence
/lbai-search-artifacts
/lbai-execute-task
/lbai-finish-task
```

Role setup or later role changes use:

```text
/lbai-init
```

Runtime foundation files under `lbai_system/` are maintained by the company, not by employees during daily task work.
