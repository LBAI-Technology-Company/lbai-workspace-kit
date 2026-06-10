# external_evidence_schema_v1

External evidence and reference material are saved first under:

```text
role_workspace/knowledge/evidence/YYYY_MM_DD_<source_kind>_<short_hash>/
```

The folder name must not include raw evidence content. Use source kind plus a short non-reversible hash or sequence id.

Each evidence folder must contain:

```text
input.md
evidence_metadata.md
evidence_brief.md
```

`evidence_brief.md` is a short employee-readable summary. It should separate usable source-supported information from uncertain or inferred information, list confirmed decisions when present, surface missing information and review risks, show linked task gap coverage, and give the safest next step in plain language. It is an aid for use and search, not a separate source of truth.

Task-local `input_*.md` files are legacy fallback artifacts only. New user-provided material should be captured through `/lbai-add-evidence` and linked back to a task when applicable.

## Required Metadata

Each `evidence_metadata.md` file should include:

- `source_identity`: who or what provided the source
- `source_kind`: transcript, feedback, interview, draft, data_notes, source, notes, general, or reference
- `captured_at`: local capture date
- `admissibility_status`: `CAPTURED`, `NEEDS_REVIEW`, `ADMITTED`, or `REJECTED`
- `converted_artifact_status`: `REFERENCE_ONLY`, `TASK_SUGGESTED`, `LINKED_TO_TASK`, `CONVERTED_TO_TASK_OUTPUT`, or `CONVERTED_TO_ROLE_DELTA`
- `usage_intent`: reference, possible_task_input, or task_input
- `linked_task`: task folder or `None`
- `covers_gaps`: covered task gaps or `None`
- `remaining_gaps`: remaining task gaps or `None`
- `redacted`: `true` or `false`
- `sensitive_capture_status`: `NONE` or `REDACTED`
- `sync_status`: `PUSHED`, `PUSH_FAILED`, `BLOCKED`, `NOT_SYNCED`, or `NO_CHANGES`
- `evidence_brief`: path to the generated `evidence_brief.md`

## Boundary

Captured evidence is not company state by itself. It becomes usable task state only after it is saved as an artifact, checked for admissibility and sensitive data, linked to the relevant task or ledger, and safely synced when possible.

Reference-only evidence must not directly update `ROLE_WORLD_MODEL_v1.md`. If evidence should change role memory, create or approve a separate role-delta task.
