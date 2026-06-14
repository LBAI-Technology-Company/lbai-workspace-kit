# external_evidence_schema_v1

External evidence and reference material are saved first under:

```text
role_workspace/knowledge/evidence/YYYY_MM_DD_<source_type>_<short_hash>/
```

The folder name must not include raw evidence content. Use source type plus a short non-reversible hash or sequence id.

Each new evidence folder must contain:

```text
raw.md
metadata.json
evidence_enrichment.json
```

`evidence_enrichment.json` is the AI-generated metadata enrichment produced in Cursor or the Codex desktop app before capture. `add_evidence.py` requires it via `--enrichment` and does not provide a rule-based fallback.

Prompt: `lbai_system/prompts/evidence_enrichment_prompt_v1.md`

Schema: `lbai_system/schemas/evidence_enrichment_schema_v1.json`

Legacy folders may contain `input.md`, `evidence_metadata.md`, or `evidence_brief.md`. Backend ingestion may read them for migration compatibility, but employee-side search must not use local fallback and new captures should not create them.

Task-local `input_*.md` files are legacy fallback artifacts only. New user-provided material should be captured through `/lbai-add-evidence` and related back to a task when applicable.

## Required Metadata

Each `metadata.json` file should include:

- `schema_version`: `employee_evidence_metadata_v1`
- `evidence_id`: evidence folder id
- `title`: short human-readable title
- `source_type`: meeting_note, chat_record, customer_feedback, interview, draft, data_note, policy, reference, task_material, or general
- `source_origin`: where the material came from
- `source_occurred_at`: source event date/time or `unknown`
- `submitted_at`: capture timestamp
- `submitted_by`: employee id from `.lbai/workspace.json`
- `submitted_by_display_name`: optional display name
- `submitted_by_email`: optional email
- `employee_user_name`: role profile name from `/lbai-init`
- `employee_position`: role profile position from `/lbai-init`
- `source_visibility`: private, team, or company
- `related_objects`: optional business objects
- `content_files`: raw content files, normally `raw.md`
- `content_hash`: sha256 hash of redacted content
- `sensitive_scan_status`: passed or redacted
- `redacted`: true or false
- `backend_ingestion_status`: normally `PENDING_GITHUB_SYNC`
- `backend_ingestion_hint`: backend handling hint

## Boundary

Captured evidence is not company state by itself. The employee client only saves redacted source material and metadata to GitHub. Backend services later ingest, extract facts, resolve conflicts, and return evidence packs.

Reference-only evidence must not directly update `ROLE_WORLD_MODEL_v1.md`. If evidence should change role memory, create or approve a separate role feedback or task flow.
