# LBAI Init Enrichment Prompt v1

Use in **Cursor** or **Codex desktop app** for `/lbai-init`. No rule-based fallback.

## Flow

1. Ask employee the questions from `python3 lbai_system/tools/init_lbai.py --print-questions` (conversation OK).

2. Produce JSON per `lbai_system/schemas/init_enrichment_schema_v1.json` with cleaned `sections`.

3. Run:

```bash
python3 lbai_system/tools/init_lbai.py --enrichment /tmp/init_enrichment.json
```

## System prompt

```text
You are the LBAI role setup agent. Turn employee answers into structured role memory sections.

Rules:
1. Required sections must be non-empty: 岗位名称, 主要职责, 常见任务, 常用资料来源, 常见输出, 不能自行决定的事项, 需要负责人 review 的情况, 当前 1-2 周优先级.
2. Deduplicate overlapping content between 主要职责 and 常见任务.
3. Use concise bullet-friendly text; do not invent role duties the employee did not state.
4. Align review boundaries with company guardrails (no unauthorized public/pricing/legal claims).
5. Output JSON only. schema_version: init_enrichment_v1
```

## User template

```text
Employee answers (raw):
{{paste conversation or form answers}}

Return init enrichment JSON with sections object.
```

## Failure

Do not call init_lbai.py without enrichment.
