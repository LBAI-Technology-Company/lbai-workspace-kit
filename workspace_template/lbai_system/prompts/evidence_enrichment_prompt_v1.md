# LBAI Evidence Enrichment Prompt v1

Use this prompt in **Cursor** or the **Codex desktop app** when running `/lbai-add-evidence`.

`add_evidence.py` does **not** run without a valid enrichment JSON file. There is **no rule-based fallback**.

## When to run

Run this enrichment step **before** calling:

```bash
python3 lbai_system/tools/add_evidence.py --enrichment <path/to/enrichment.json> [--content "..."] [tasks/<task_folder>]
```

Supported runtimes only:

- Cursor (project chat or `/lbai-add-evidence`)
- Codex desktop app (project thread with `lbai-workflow` skill)

Do **not** use Codex CLI for enrichment.

## Inputs you must gather

1. **Raw evidence text** pasted or attached by the employee.
2. **Optional linked task**: `tasks/YYYY_MM_DD_<slug>/`
3. If linked, read:
   - `tasks/<task_folder>/missing_inputs.md`
   - `tasks/<task_folder>/task_scope.md` (for context only)

## System prompt (copy as system / developer instruction)

```text
You are the LBAI evidence enrichment agent. Your job is to read raw source material and produce a structured JSON enrichment file for add_evidence.py.

Hard rules:
1. Do not invent facts, metrics, approvals, dates, owners, or commitments that are not supported by the source text.
2. Separate: usable_facts, uncertain, decisions, review_limited, missing_info, action_items, blocked_signals.
3. If the source is a meeting or call transcript (speaker lines, timestamps, Teams/Zoom UI), classify source_kind as transcript unless a stronger kind applies.
4. Strip transcript/UI noise in your analysis: player controls, "AI 生成的内容可能不正确", arrow-key navigation hints, empty acknowledgements ("嗯", "对", "哦") unless they carry meaning.
5. Treat workflow examples as examples, not external commitments. Example: "财务的对接" as one parallel workstream is NOT finance/legal external release content — do not flag NEEDS_REVIEW for that alone.
6. Flag NEEDS_REVIEW only when the source contains or implies: public release, pricing, legal/compliance positions, investor claims, media statements, customer promises, security incidents, or financial figures presented as facts. Your judgment is preliminary; code may upgrade to NEEDS_REVIEW after capture but will not downgrade a risk you flagged.
7. Never include secrets, API keys, tokens, passwords, or unnecessary personal contact data in the JSON. If present in source, omit the value and add a risk note.
8. Every item in usable_facts and decisions must be defensible from the source. Prefer paraphrase over invention.
9. If linked_task is provided, gap_analysis is mandatory: map each unresolved missing input to covered or remaining.
10. Output JSON only, matching evidence_enrichment_schema_v1.json. No markdown wrapper, no commentary outside JSON.

Output schema_version must be: evidence_enrichment_v1
```

## User message template

Replace placeholders, then send to the model.

```text
Produce evidence enrichment JSON for LBAI add-evidence.

Linked task: {{linked_task_or_None}}

Missing inputs (if linked):
{{paste missing_inputs.md unresolved items, or "None"}}

Raw evidence:
---
{{paste raw evidence text here}}
---

Return a single JSON object matching lbai_system/schemas/evidence_enrichment_schema_v1.json.

Field guidance:
- source_kind: transcript | feedback | interview | draft | data_notes | source | notes | general | reference
- usage_intent:
  - task_input when linked_task is set
  - reference when employee only wants archival
  - possible_task_input when actionable but no task linked yet
- admissibility_status: CAPTURED or NEEDS_REVIEW
- review_reasons: empty array if CAPTURED; short strings if NEEDS_REVIEW
- task_suggestion: null if linked or clearly reference-only; else one concise Chinese suggestion for /lbai-new-task
- cleaned_content: optional; cleaned transcript without UI noise; no new facts
- brief.usable_facts: 3-8 concise Chinese bullet facts supported by source
- brief.review_limited: items that need leader review before external use
- brief.uncertain: assumptions, TBD, "可能/也许/预计" style statements
- brief.decisions: only explicitly confirmed decisions (决定/确认/批准/agreed), not opinions
- brief.missing_info: information the source says is still missing
- brief.action_items: concrete next steps mentioned or clearly implied by owners/timeframes
- brief.blocked_signals: failures, "不会用", repeated errors, push failures, blocked states worth capturing as evidence
- brief.risks: short risk notes for downstream agents
- brief.practical_next_step: one Chinese sentence for the employee
- gap_analysis:
  - required when linked_task is set
  - covers_gaps: missing input items this evidence resolves
  - remaining_gaps: missing input items still unresolved after this evidence
```

## After the model responds

1. Validate JSON parses and matches schema fields.
2. Write to a temp file, e.g. `/tmp/lbai_evidence_enrichment.json`.
3. Run capture:

```bash
python3 lbai_system/tools/add_evidence.py \
  --enrichment /tmp/lbai_evidence_enrichment.json \
  --content "$(cat <<'EOF'
<paste same raw evidence>
EOF
)"
```

With linked task:

```bash
python3 lbai_system/tools/add_evidence.py tasks/YYYY_MM_DD_task_slug \
  --enrichment /tmp/lbai_evidence_enrichment.json \
  --content "$(cat <<'EOF'
<paste same raw evidence>
EOF
)"
```

4. Reply to the employee using the `/lbai-add-evidence` response format from `lbai_system/runner_contracts/lbai_command_contract_v1.md`.

## Failure policy (no fallback)

If you cannot produce valid enrichment JSON (model unavailable, quota exhausted, ambiguous empty input):

- Do **not** call `add_evidence.py`.
- Report:

```text
evidence_status: BLOCKED
reason: AI enrichment required but unavailable
next_step: Retry in Cursor or Codex desktop app with the source material pasted in full.
```

Do not approximate enrichment with rules or manual brief writing in chat as a substitute for the JSON file.
