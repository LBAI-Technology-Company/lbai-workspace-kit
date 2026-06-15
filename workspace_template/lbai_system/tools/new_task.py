#!/usr/bin/env python3
import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True

from enrichment_utils import load_json_file, resolve_enrichment_path, validate_with_schema
from role_memory_backend import retrieve_role_memory_context
from search_backend import search_backend
from task_utils import LEADER_REVIEW_REMINDER, redact_sensitive, today_slugged_task_dir, workspace_root, write_if_missing


ROOT = workspace_root()
ENRICHMENT_VERSION = 'task_intake_enrichment_v1'
BLOCKED_MESSAGE = (
    'AI enrichment required (--enrichment). Use Cursor or Codex desktop app; '
    'see lbai_system/prompts/task_intake_enrichment_prompt_v1.md'
)
TERMINAL_NEXT_STEP = (
    '请在 Cursor 或 Codex 桌面 App 中打开本工作区，输入 /lbai-new-task；'
    '高级用户可提供 --enrichment <json_path>。'
)
REVIEW_REQUIRED_HINTS = (
    'public',
    'website',
    'external',
    'pricing',
    'legal',
    'compliance',
    'investor',
    'media',
    'customer promise',
    'finance-sensitive',
    'security-sensitive',
    '官网',
    '外部发布',
    '定价',
    '价格',
    '合规',
    '法务',
    '法律',
    '投资人',
    '媒体',
    '客户承诺',
    '财务敏感',
    '安全敏感',
)
NO_REVIEW_REASON_VALUES = {'none', 'n/a', 'na', '无', '无需', '不需要', 'none.'}
COMPANY_FACT_HINTS = (
    '公司',
    '我司',
    '企业',
    '产品',
    '服务',
    '客户',
    '案例',
    '业务',
    '工作方法',
    '方法流程',
    '工作流程',
    '流程',
    '制度',
    '规范',
)
WRITING_HINTS = (
    '写',
    '撰写',
    '介绍',
    '说明',
    '短文',
    '文章',
    '文案',
    '材料',
    '官网',
    '对外',
    '发布',
)
SOURCE_KINDS_WITH_TRACEABLE_COMPANY_FACTS = {'company_knowledge', 'linked_evidence', 'external_source'}
CONVERSATION_SOURCE_FACT_MARKERS = ('包括', '分为', '步骤', '流程是', '方法是', '先', '再', '最后', '核心', '原则', '机制')
COMPANY_SOURCE_MISSING_INPUT = '请补充公司工作方法/流程的来源材料或关键要点。'
AUDIENCE_MISSING_INPUT = '请说明这篇短文的受众和用途：内部同事阅读，还是可能对外发布。'


def clean_review_reasons(data: dict) -> list[str]:
    reasons = []
    for item in data.get('review_reasons') or []:
        reason = str(item).strip()
        if reason and reason.lower() not in NO_REVIEW_REASON_VALUES:
            reasons.append(reason)
    return reasons


def validate_intake(root: Path, data: dict) -> str | None:
    err = validate_with_schema(root, data, 'task_intake_enrichment_schema_v1.json')
    if err:
        return err
    if not isinstance(data['missing_inputs'], list):
        return 'missing_inputs must be an array'
    if not isinstance(data['known_information'], list):
        return 'known_information must be an array'
    if not isinstance(data['recommended_inputs'], list):
        return 'recommended_inputs must be an array'
    if not isinstance(data['completion_conditions'], list):
        return 'completion_conditions must be an array'
    if not str(data.get('task_description', '')).strip():
        return 'task_description must be non-empty'
    if not str(data.get('goal', '')).strip():
        return 'goal must be non-empty'
    if not str(data.get('expected_output', '')).strip():
        return 'expected_output must be non-empty'
    if not [str(item).strip() for item in data['completion_conditions'] if str(item).strip()]:
        return 'completion_conditions must contain at least one non-empty item'
    return None


def normalize_intake(data: dict) -> dict:
    normalized = dict(data)
    missing_inputs = [str(item).strip() for item in normalized.get('missing_inputs') or [] if str(item).strip()]
    normalized['missing_inputs'] = missing_inputs
    normalized['status'] = 'BLOCKED' if missing_inputs else 'OPEN'

    review_reasons = clean_review_reasons(normalized)
    review_text = ' '.join(
        [
            str(normalized.get('task_description') or ''),
            str(normalized.get('goal') or ''),
            str(normalized.get('expected_output') or ''),
            str(normalized.get('execution_notes') or ''),
            *review_reasons,
        ]
    ).lower()
    if review_reasons or any(hint in review_text for hint in REVIEW_REQUIRED_HINTS):
        normalized['review_needed'] = True
    return normalized


def add_missing_input(data: dict, item: str) -> None:
    missing_inputs = data.setdefault('missing_inputs', [])
    existing = {str(value).strip() for value in missing_inputs}
    if item not in existing:
        missing_inputs.append(item)


def task_needs_company_fact_source(data: dict) -> bool:
    text = ' '.join(
        str(data.get(key) or '')
        for key in ('task_description', 'goal', 'expected_output')
    ).lower()
    return any(hint in text for hint in COMPANY_FACT_HINTS) and any(hint in text for hint in WRITING_HINTS)


def has_traceable_company_fact_source(data: dict) -> bool:
    for item in data.get('known_information') or []:
        if not isinstance(item, dict):
            continue
        summary = str(item.get('summary') or '').strip()
        source_kind = str(item.get('source_kind') or '').strip()
        if summary and source_kind in SOURCE_KINDS_WITH_TRACEABLE_COMPANY_FACTS:
            return True
        if summary and source_kind == 'conversation_context' and any(marker in summary for marker in CONVERSATION_SOURCE_FACT_MARKERS):
            return True
    return False


def has_audience_or_usage(data: dict) -> bool:
    text = ' '.join(
        [
            str(data.get('task_description') or ''),
            str(data.get('goal') or ''),
            str(data.get('expected_output') or ''),
            ' '.join(str(item.get('summary') or '') for item in data.get('known_information') or [] if isinstance(item, dict)),
        ]
    )
    return any(
        hint in text
        for hint in ('内部', '对外', '官网', '客户', '同事', '负责人', '投资人', '媒体', '发布', '培训', '入职', '销售', '市场')
    )


def apply_intake_guardrails(data: dict) -> dict:
    guarded = dict(data)
    guarded['missing_inputs'] = list(guarded.get('missing_inputs') or [])
    if task_needs_company_fact_source(guarded):
        if not has_traceable_company_fact_source(guarded):
            add_missing_input(guarded, COMPANY_SOURCE_MISSING_INPUT)
        if not has_audience_or_usage(guarded):
            add_missing_input(guarded, AUDIENCE_MISSING_INPUT)
    guarded['missing_inputs'] = [str(item).strip() for item in guarded.get('missing_inputs') or [] if str(item).strip()]
    guarded['status'] = 'BLOCKED' if guarded['missing_inputs'] else 'OPEN'
    return guarded


def backend_search_query_plan(data: dict) -> dict:
    query = ' '.join(
        str(data.get(key) or '').strip()
        for key in ('task_description', 'goal', 'expected_output')
        if str(data.get(key) or '').strip()
    )
    return {
        'schema_version': 'backend_search_query_plan_v1',
        'query': query,
        'keywords': [keyword for keyword in ('公司', '工作方法', '工作流程', '流程', '方法') if keyword in query],
        'concepts': ['company_workflow', 'work_method', 'process'],
        'prefer_status': ['CAPTURED', 'NEEDS_REVIEW'],
        'limit': 5,
    }


def append_backend_company_knowledge(data: dict, backend_data: dict) -> int:
    pack = backend_data.get('evidence_pack') or []
    if not isinstance(pack, list):
        return 0
    known_information = data.setdefault('known_information', [])
    added = 0
    for item in pack[:5]:
        if not isinstance(item, dict):
            continue
        source = item.get('source') or {}
        source_ref = ''
        if isinstance(source, dict):
            source_ref = str(source.get('path') or source.get('id') or '').strip()
        summary = str(
            item.get('evidence_text')
            or item.get('value')
            or item.get('subject')
            or item.get('event_id')
            or ''
        ).strip()
        if not summary:
            continue
        known_information.append({
            'summary': summary,
            'source_kind': 'company_knowledge',
            'source_ref': source_ref or 'backend_evidence_search',
        })
        added += 1
    return added


def enrich_with_backend_company_knowledge(root: Path, data: dict) -> tuple[dict, str]:
    if not task_needs_company_fact_source(data) or has_traceable_company_fact_source(data):
        return data, ''
    backend_data, _ = search_backend(root, backend_search_query_plan(data))
    if backend_data is None:
        return data, ''
    enriched = dict(data)
    enriched['known_information'] = list(data.get('known_information') or [])
    added = append_backend_company_knowledge(enriched, backend_data)
    return enriched, f'backend_evidence_search_used: {added}' if added else ''


def sanitize_for_artifacts(value):
    if isinstance(value, str):
        redacted, findings = redact_sensitive(value)
        return redacted.strip(), findings
    if isinstance(value, list):
        cleaned = []
        findings = []
        for item in value:
            sanitized, item_findings = sanitize_for_artifacts(item)
            findings.extend(item_findings)
            cleaned.append(sanitized)
        return cleaned, findings
    if isinstance(value, dict):
        cleaned = {}
        findings = []
        for key, item in value.items():
            sanitized, item_findings = sanitize_for_artifacts(item)
            findings.extend(item_findings)
            cleaned[key] = sanitized
        return cleaned, findings
    return value, []


def finalize_review(data: dict) -> tuple[bool, str, list[str]]:
    review_needed = bool(data.get('review_needed'))
    reasons = clean_review_reasons(data)
    review_reason = '; '.join(reasons) if reasons else (
        'Review required' if review_needed else 'Internal or low-risk task based on AI intake'
    )
    return review_needed, review_reason, reasons


def markdown_list(items: list[str]) -> str:
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    return '\n'.join(f'- {item}' for item in cleaned) if cleaned else '- None'


def known_information_markdown(items: list[dict]) -> str:
    rows = []
    for item in items or []:
        summary = str(item.get('summary') or '').strip()
        if not summary:
            continue
        source_kind = str(item.get('source_kind') or 'unknown').strip()
        source_ref = str(item.get('source_ref') or '').strip()
        suffix = f' ({source_kind}: {source_ref})' if source_ref else f' ({source_kind})'
        rows.append(f'- {summary}{suffix}')
    return '\n'.join(rows) if rows else '- None'


def next_step_for_missing(task_rel: str) -> str:
    return (
        '请直接在对话框补充必要信息；如果补充的是原始资料、会议纪要、客户材料或可复用来源，'
        f'再使用 /lbai-add-evidence {task_rel} 归档。'
    )


def unique_task_dir(base_dir: Path) -> Path:
    if not base_dir.exists():
        return base_dir
    for idx in range(2, 100):
        candidate = base_dir.with_name(f'{base_dir.name}_{idx}')
        if not candidate.exists():
            return candidate
    raise RuntimeError(f'No available task directory for {base_dir}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('task_description', nargs='*')
    parser.add_argument('--owner', default='<owner>')
    parser.add_argument('--enrichment', default='')
    args = parser.parse_args()

    if not args.enrichment:
        print('TASK_FOLDER unresolved')
        print('STATUS BLOCKED')
        print(f'reason: {BLOCKED_MESSAGE}')
        print(f'NEXT_STEP {TERMINAL_NEXT_STEP}')
        return 2

    enrichment_path = resolve_enrichment_path(ROOT, args.enrichment)
    data, error = load_json_file(enrichment_path)
    if data is None:
        print('TASK_FOLDER unresolved')
        print('STATUS BLOCKED')
        print(f'reason: {error or BLOCKED_MESSAGE}')
        print(f'NEXT_STEP {TERMINAL_NEXT_STEP}')
        return 2

    validation_error = validate_intake(ROOT, data)
    if validation_error:
        print('TASK_FOLDER unresolved')
        print('STATUS BLOCKED')
        print(f'reason: {validation_error}')
        print(f'NEXT_STEP {TERMINAL_NEXT_STEP}')
        return 2

    data = normalize_intake(data)
    data, backend_search_detail = enrich_with_backend_company_knowledge(ROOT, data)
    data = apply_intake_guardrails(data)
    data, sensitive_findings = sanitize_for_artifacts(data)

    task_description = str(data['task_description']).strip()
    provided_description = ' '.join(args.task_description).strip()
    if provided_description and provided_description != task_description:
        print('TASK_FOLDER unresolved')
        print('STATUS BLOCKED')
        print('reason: task_description argument does not match enrichment task_description')
        print('NEXT_STEP 重新生成与命令输入一致的 task intake enrichment JSON，或不要传入额外 task_description 参数。')
        return 2
    goal = str(data['goal']).strip()
    expected_output = str(data['expected_output']).strip()
    missing_inputs = [str(item).strip() for item in data['missing_inputs'] if str(item).strip()]
    recommended_inputs = [
        str(item).strip()
        for item in data.get('recommended_inputs', [])
        if str(item).strip()
    ]
    known_information = data.get('known_information') or []
    status = data['status']
    completion_conditions = [str(item).strip() for item in data['completion_conditions'] if str(item).strip()]
    execution_notes = str(data.get('execution_notes') or '').strip()
    review_needed, review_reason, _ = finalize_review(data)
    risk_level = 'high' if review_needed else 'low'

    task_dir = unique_task_dir(today_slugged_task_dir(ROOT, task_description))
    task_id = task_dir.name

    write_if_missing(task_dir / 'task_scope.md', f"""# Task Scope

## task_id
{task_id}

## task_name
{task_description}

## goal
{goal}

## owner
{args.owner}

## inputs_available
- Task intake enrichment: {enrichment_path.name}

## known_information
{known_information_markdown(known_information)}

## recommended_inputs
{markdown_list(recommended_inputs)}

## input_capture_policy
- Direct clarifications and decisions may be provided in chat and saved as task-local context.
- Use /lbai-add-evidence only for source materials that should be archived as reusable evidence.

## inputs_missing
{markdown_list(missing_inputs)}

## expected_output
{expected_output}

## completion_conditions
{markdown_list(completion_conditions)}

## execution_notes
{execution_notes or 'None'}

## risk_level
{risk_level}

## review_needed
{str(review_needed).lower()}

## review_reason
{review_reason}

## leader_review_reminder
{LEADER_REVIEW_REMINDER if review_needed else 'None'}

## sensitive_info_expected
false

## status
{status}

""", ROOT)

    write_if_missing(task_dir / 'task_slot.md', f"""# Task Slot

## task_id
{task_id}

## allowed_sources
- This task folder
- Task-local chat clarifications saved in this task folder
- Linked evidence saved under role_workspace/knowledge/evidence/
- Legacy task-local input_*.md when present
- Role world model files under role_workspace/world_model/
- Company guardrails under lbai_system/company_guardrails/

## forbidden_actions
- Do not invent missing source facts
- Do not fabricate data, metrics, benchmarks, customer evidence, case results, product capabilities, pricing, legal positions, approvals, or company commitments
- Do not write sensitive information
- Do not generate unauthorized public claims
- Do not mark review-required work as approved

## execution_standard
- Treat the output as internal company work, not casual chat
- Use conversation clarifications as task-local context; do not treat them as archived evidence unless captured through /lbai-add-evidence
- Separate facts, assumptions, uncertainty, recommendations, and next steps
- Cite or name the source for success data, market claims, performance claims, and customer claims
- If feasibility is not verified, label the recommendation as an assumption and provide the validation step
- If required information is missing, state the exact missing material or decision

## output_path
{task_dir.relative_to(ROOT)}/task_output.md

## required_outputs
- task_output.md
- task_ledger.md

## completion_conditions
{markdown_list(completion_conditions)}

## completion_conditions_source
task intake enrichment
""", ROOT)

    write_if_missing(task_dir / 'task_ledger.md', f"""# Task Ledger

## task_id
{task_id}

## date
{date.today().isoformat()}

## task_name
{task_description}

## task_goal
{goal}

## source_artifacts
- Task intake enrichment: {enrichment_path.name}

## agents_or_tools_used
- /lbai-new-task
- lbai_system/tools/new_task.py

## outputs_created
- task_scope.md
- task_slot.md
- task_ledger.md
- task_intake_enrichment.json

## status
{status}

## blocked_reason
{'; '.join(missing_inputs) if missing_inputs else 'None'}

## known_information
{known_information_markdown(known_information)}

## recommended_inputs
{markdown_list(recommended_inputs)}

## owner
{args.owner}

## review_needed
{str(review_needed).lower()}

## leader_review_reminder
{LEADER_REVIEW_REMINDER if review_needed else 'None'}

## commit_readiness
UNKNOWN

## git_status
NOT_SYNCED

## next_dependency
{'Missing input from employee' if missing_inputs else 'Run /lbai-execute-task'}

## next_step
{next_step_for_missing(str(task_dir.relative_to(ROOT))) if missing_inputs else f'Run /lbai-execute-task {task_dir.relative_to(ROOT)}.'}
""", ROOT)

    (task_dir / 'task_intake_enrichment.json').write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )

    if missing_inputs:
        write_if_missing(
            task_dir / 'missing_inputs.md',
            '# Missing Inputs\n\n'
            'Only blocking gaps belong in this file. Recommended context belongs in recommended_inputs.md.\n\n'
            + '\n'.join(f'- {item}\n' for item in missing_inputs)
            + '\n',
            ROOT,
        )

    if recommended_inputs:
        write_if_missing(
            task_dir / 'recommended_inputs.md',
            '# Recommended Inputs\n\n'
            'These inputs improve quality but do not block /lbai-execute-task.\n\n'
            + '\n'.join(f'- {item}\n' for item in recommended_inputs)
            + '\n',
            ROOT,
        )

    if review_needed:
        write_if_missing(task_dir / 'overclaim_check.md', '# Overclaim Check\n\nReview required. Do not add unapproved public, pricing, legal, investor, media, product capability, or customer promise claims.\n', ROOT)
        write_if_missing(task_dir / 'release_boundary_check.md', '# Release Boundary Check\n\nThis task is not approved for public release until founder or role owner review is complete.\n', ROOT)
        write_if_missing(task_dir / 'founder_review_needed.md', '# Founder Review Reminder\n\nRemind the employee: leader review is required before external release. This workflow does not block execution or finish.\n', ROOT)

    role_memory_detail = retrieve_role_memory_context(ROOT, task_dir, f'{task_description}\n{goal}\n{expected_output}')

    print(f'TASK_FOLDER {task_dir.relative_to(ROOT)}')
    print(f'STATUS {status}')
    print(f'REVIEW_NEEDED {str(review_needed).lower()}')
    if backend_search_detail:
        print(backend_search_detail)
    if role_memory_detail and 'role_memory_context: FOUND' in role_memory_detail:
        print(role_memory_detail)
    if sensitive_findings:
        print('SENSITIVE_CAPTURE_STATUS REDACTED')
    if review_needed:
        print(f'leader_review_reminder: {LEADER_REVIEW_REMINDER}')
    if missing_inputs:
        print('MISSING ' + '; '.join(missing_inputs))
        print(f'NEXT_STEP {next_step_for_missing(str(task_dir.relative_to(ROOT)))}')
    else:
        if recommended_inputs:
            print('RECOMMENDED ' + '; '.join(recommended_inputs))
        print(f'NEXT_STEP /lbai-execute-task {task_dir.relative_to(ROOT)}')


if __name__ == '__main__':
    raise SystemExit(main() or 0)
