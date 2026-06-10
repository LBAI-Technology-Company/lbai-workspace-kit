#!/usr/bin/env python3
import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True

from enrichment_utils import load_json_file, resolve_enrichment_path, validate_with_schema
from task_utils import LEADER_REVIEW_REMINDER, today_slugged_task_dir, workspace_root, write_if_missing


ROOT = workspace_root()
ENRICHMENT_VERSION = 'task_intake_enrichment_v1'
BLOCKED_MESSAGE = (
    'AI enrichment required (--enrichment). Use Cursor or Codex desktop app; '
    'see lbai_system/prompts/task_intake_enrichment_prompt_v1.md'
)


def validate_intake(root: Path, data: dict) -> str | None:
    err = validate_with_schema(root, data, 'task_intake_enrichment_schema_v1.json')
    if err:
        return err
    if data['status'] not in {'OPEN', 'BLOCKED'}:
        return 'invalid status'
    if not isinstance(data['missing_inputs'], list):
        return 'missing_inputs must be an array'
    if not isinstance(data['completion_conditions'], list):
        return 'completion_conditions must be an array'
    if not str(data.get('task_description', '')).strip():
        return 'task_description must be non-empty'
    if data['status'] == 'OPEN' and data['missing_inputs']:
        return 'status OPEN requires empty missing_inputs'
    if data['status'] == 'BLOCKED' and not data['missing_inputs']:
        return 'status BLOCKED requires missing_inputs'
    return None


def finalize_review(data: dict) -> tuple[bool, str, list[str]]:
    review_needed = bool(data.get('review_needed'))
    reasons = [str(item).strip() for item in (data.get('review_reasons') or []) if str(item).strip()]
    review_reason = '; '.join(reasons) if reasons else (
        'Review required' if review_needed else 'Internal or low-risk task based on AI intake'
    )
    return review_needed, review_reason, reasons


def markdown_list(items: list[str]) -> str:
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    return '\n'.join(f'- {item}' for item in cleaned) if cleaned else '- None'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('task_description', nargs='*')
    parser.add_argument('--owner', default='<owner>')
    parser.add_argument('--enrichment', required=True)
    args = parser.parse_args()

    enrichment_path = resolve_enrichment_path(ROOT, args.enrichment)
    data, error = load_json_file(enrichment_path)
    if data is None:
        print('TASK_FOLDER unresolved')
        print('STATUS BLOCKED')
        print(f'reason: {error or BLOCKED_MESSAGE}')
        print(f'NEXT_STEP {BLOCKED_MESSAGE}')
        return 2

    validation_error = validate_intake(ROOT, data)
    if validation_error:
        print('TASK_FOLDER unresolved')
        print('STATUS BLOCKED')
        print(f'reason: {validation_error}')
        print(f'NEXT_STEP {BLOCKED_MESSAGE}')
        return 2

    task_description = str(data['task_description']).strip()
    goal = str(data['goal']).strip()
    expected_output = str(data['expected_output']).strip()
    missing_inputs = [str(item).strip() for item in data['missing_inputs'] if str(item).strip()]
    status = data['status']
    completion_conditions = [str(item).strip() for item in data['completion_conditions'] if str(item).strip()]
    execution_notes = str(data.get('execution_notes') or '').strip()
    review_needed, review_reason, _ = finalize_review(data)
    risk_level = 'high' if review_needed else 'low'

    task_dir = today_slugged_task_dir(ROOT, task_description)
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
{'Missing input from employee via /lbai-add-evidence' if missing_inputs else 'Run /lbai-execute-task'}

## next_step
{f'请直接粘贴缺失输入，工作区助手应使用 /lbai-add-evidence {task_dir.relative_to(ROOT)} 保存为 evidence 并更新缺口状态。' if missing_inputs else f'Run /lbai-execute-task {task_dir.relative_to(ROOT)}.'}
""", ROOT)

    (task_dir / 'task_intake_enrichment.json').write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )

    if missing_inputs:
        write_if_missing(task_dir / 'missing_inputs.md', '# Missing Inputs\n\n' + '\n'.join(f'- {item}\n' for item in missing_inputs) + '\n', ROOT)

    if review_needed:
        write_if_missing(task_dir / 'overclaim_check.md', '# Overclaim Check\n\nReview required. Do not add unapproved public, pricing, legal, investor, media, product capability, or customer promise claims.\n', ROOT)
        write_if_missing(task_dir / 'release_boundary_check.md', '# Release Boundary Check\n\nThis task is not approved for public release until founder or role owner review is complete.\n', ROOT)
        write_if_missing(task_dir / 'founder_review_needed.md', '# Founder Review Reminder\n\nRemind the employee: leader review is required before external release. This workflow does not block execution or finish.\n', ROOT)

    print(f'TASK_FOLDER {task_dir.relative_to(ROOT)}')
    print(f'STATUS {status}')
    print(f'REVIEW_NEEDED {str(review_needed).lower()}')
    if review_needed:
        print(f'leader_review_reminder: {LEADER_REVIEW_REMINDER}')
    if missing_inputs:
        print('MISSING ' + '; '.join(missing_inputs))
        print(f'NEXT_STEP 请直接粘贴缺失输入，工作区助手应使用 /lbai-add-evidence {task_dir.relative_to(ROOT)} 保存为 evidence 并更新缺口状态。')
    else:
        print(f'NEXT_STEP /lbai-execute-task {task_dir.relative_to(ROOT)}')


if __name__ == '__main__':
    raise SystemExit(main() or 0)
