# LBAI_WORKSPACE_KIT_RESPONSIBILITY_GAP_REGISTER_v1

| gap_id | priority | gap_name | gap_class | current_evidence | missing_artifact | owner | next_chain |
|---|---|---|---|---|---|---|---|
| GAP-01 | P1 | Agent identity lock | Scope | README and commands describe a workspace kit | Identity source and scope lock | Workspace kit owner | Scope lock |
| GAP-02 | P1 | Internal Runtime Router Agent | Runtime routing | Fixed slash commands exist | Router contract and decision table | Runtime owner | Router contract |
| GAP-03 | P0 | Workspace Bootstrap Agent | Bootstrap | Manual README setup plus command checker | Bootstrap check/fill contract and tool | Workspace kit owner | Bootstrap v1 |
| GAP-04 | P1 | Evidence-driven role world model update | Role memory | `/lbai-init` writes initial role files | Delta, version, lineage contract | Role memory owner | Role model update v1 |
| GAP-05 | P0 | Company guardrail source | Guardrail | Cursor rules contain review/sensitive boundaries | Canonical company guardrail artifacts | Company ops owner | Guardrail source |
| GAP-06 | P2 | MCP / callable skills layer | Runtime capability | Cursor skills exist | MCP/tool registry contract | Runtime owner | MCP manifest |
| GAP-07 | P0 | Structured task ledger | Ledger | Task and global ledgers are markdown-light | Canonical ledger schema | Workspace kit owner | Task Ledger v1 |
| GAP-08 | P1 | External evidence intake boundary | Evidence | `/lbai-add-evidence` captures evidence under `role_workspace/knowledge/evidence/` and links task gaps | Stronger admissibility review and role-delta conversion rules | Workspace kit owner | Evidence intake v0.6 hardening |
| GAP-09 | P2 | Domain-specific release guardrails | Domain review | Broad review files exist | Domain-specific boundaries and benchmarks | Domain owners | Domain agent specs |
| GAP-10 | P0 | GitHub Sync / Repo Hygiene Agent | Artifact ledger | Hygiene check exists; push is manual | Auto sync contract and status fields | Workspace kit owner | GitHub Sync v1 |
| GAP-11 | P1 | Runner / harness contracts | Runtime guardrail | Natural language command rules exist | Agent call and output contracts | Runtime owner | Runner contracts |
| GAP-12 | P2 | Internal adoption evidence chain | Product proof | Task folders can show real internal runs | Adoption log and sample run register | Product proof owner | Adoption evidence |

## Priority Notes

P0 gaps are required for v0.5 because they make work traceable, guardrailed, and safely pushed to the private GitHub artifact ledger.

P1 gaps define the next layer of runtime behavior but may begin as contracts before executable agents exist.

P2 gaps should not block v0.5. They are important for later product proof and domain-specific runtime expansion.
