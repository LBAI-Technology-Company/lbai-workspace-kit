#!/usr/bin/env python3
import argparse
import hashlib
import json
import select
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True

from task_utils import (
    LEADER_REVIEW_REMINDER,
    REVIEW_ALLOWED_TASK_FILES,
    REVIEW_TASK_FILES,
    is_task_dir,
    markdown_field,
    read_text,
    redact_sensitive,
    set_markdown_field,
    slugify,
    workspace_root,
)


VALID_SOURCE_KINDS = [
    'transcript',
    'feedback',
    'interview',
    'draft',
    'data_notes',
    'source',
    'notes',
    'general',
    'reference',
]

VALID_USAGE_INTENTS = ['reference', 'possible_task_input', 'task_input']
VALID_ADMISSIBILITY = ['CAPTURED', 'NEEDS_REVIEW']
ENRICHMENT_VERSION = 'evidence_enrichment_v1'
ENRICHMENT_BLOCKED_MESSAGE = (
    'AI enrichment required (--enrichment). Use Cursor or Codex desktop app; '
    'see lbai_system/prompts/evidence_enrichment_prompt_v1.md. No rule-based fallback.'
)

BRIEF_SECTIONS = [
    ('usable_facts', '可直接使用的信息'),
    ('review_limited', '待 review 后才能使用的信息'),
    ('uncertain', '不确定或只是推断的信息'),
    ('decisions', '已明确确认的决定'),
    ('missing_info', '还缺的信息'),
    ('action_items', '行动项'),
    ('blocked_signals', 'Blocked / 失败信号'),
    ('risks', '风险提示'),
    ('practical_next_step', '建议下一步'),
]

REVIEW_REMINDER = LEADER_REVIEW_REMINDER

REVIEW_FILE_CONTENT = {
    'overclaim_check.md': '# Overclaim Check\n\nReview required before external release. Do not add unapproved public, pricing, legal, investor, media, product capability, or customer promise claims.\n',
    'release_boundary_check.md': '# Release Boundary Check\n\nThis task is not approved for external release until founder or role owner review is complete.\n',
    'founder_review_needed.md': '# Founder Review Reminder\n\nRemind the employee: leader review is required before external release. This workflow does not block execution or finish.\n',
}


def run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(['git', *args], cwd=root, capture_output=True, text=True)


def git_remote_available(root: Path) -> bool:
    result = run_git(root, ['remote'])
    return result.returncode == 0 and bool(result.stdout.strip())


def git_upstream_available(root: Path) -> bool:
    result = run_git(root, ['rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'])
    return result.returncode == 0 and bool(result.stdout.strip())


def git_has_staged_changes(root: Path) -> bool:
    result = run_git(root, ['diff', '--cached', '--quiet'])
    return result.returncode == 1


def finalize_admissibility(enrichment: dict) -> tuple[str, list[str], str, bool]:
    ai_status = enrichment.get('admissibility_status', 'CAPTURED')
    ai_reasons = [str(item).strip() for item in (enrichment.get('review_reasons') or []) if str(item).strip()]
    needs_review = ai_status == 'NEEDS_REVIEW'
    status = 'NEEDS_REVIEW' if needs_review else 'CAPTURED'
    return status, ai_reasons, ai_status, needs_review


def conversion_status_for(usage_intent: str, linked_task: str) -> str:
    if linked_task:
        return 'LINKED_TO_TASK'
    if usage_intent == 'possible_task_input':
        return 'TASK_SUGGESTED'
    return 'REFERENCE_ONLY'


def next_available(path: Path) -> Path:
    if not path.exists():
        return path
    for idx in range(2, 100):
        candidate = path.with_name(f'{path.name}_{idx}')
        if not candidate.exists():
            return candidate
    raise RuntimeError(f'No available evidence folder for {path}')


def read_available_stdin() -> str:
    if sys.stdin.isatty():
        return ''
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    if not ready:
        return ''
    return sys.stdin.read().strip()


def parse_input(args: argparse.Namespace) -> tuple[str, str]:
    target = args.target_or_content or ''
    rest = ' '.join(args.content).strip()
    content = args.content_text.strip() if args.content_text else ''
    stdin_text = read_available_stdin()
    task_folder = ''

    if target.startswith('tasks/'):
        task_folder = target
        content = content or rest or stdin_text
    else:
        content = content or ' '.join([part for part in [target, rest] if part]).strip() or stdin_text

    return task_folder, content


def markdown_list(items: list[str]) -> str:
    cleaned = [item.strip() for item in items if item and item.strip()]
    return '\n'.join(f'- {item}' for item in cleaned) if cleaned else '- None'


def merge_markdown_list(existing: str, item: str) -> str:
    values = []
    for line in existing.splitlines():
        value = line.strip().lstrip('-').strip()
        if value and value.lower() != 'none' and value not in values:
            values.append(value)
    if item and item not in values:
        values.append(item)
    return markdown_list(values)


def merge_review_reason(existing: str, evidence_rel: str) -> str:
    addition = f'Review-sensitive linked evidence: {evidence_rel}'
    value = existing.strip()
    if not value or value.lower() in {'none', 'false'}:
        return addition
    if addition in value:
        return value
    return f'{value}\n{addition}'


def ensure_review_files(task_dir: Path):
    for name in REVIEW_TASK_FILES:
        path = task_dir / name
        if not path.exists():
            path.write_text(
                REVIEW_FILE_CONTENT.get(name, f'# {name}\n\nLeader review reminder required before external release.\n'),
                encoding='utf-8',
            )


def load_enrichment(path: Path, linked_task: str) -> tuple[dict | None, str]:
    if not path.exists():
        return None, f'enrichment file not found: {path}'
    try:
        data = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        return None, f'enrichment JSON parse error: {exc}'

    if not isinstance(data, dict):
        return None, 'enrichment must be a JSON object'
    if data.get('schema_version') != ENRICHMENT_VERSION:
        return None, f'enrichment schema_version must be {ENRICHMENT_VERSION}'

    errors = []
    for field in ('source_kind', 'usage_intent', 'admissibility_status', 'brief'):
        if field not in data:
            errors.append(f'missing required field: {field}')

    kind = data.get('source_kind')
    if kind not in VALID_SOURCE_KINDS:
        errors.append(f'invalid source_kind: {kind!r}')

    usage = data.get('usage_intent')
    if usage not in VALID_USAGE_INTENTS:
        errors.append(f'invalid usage_intent: {usage!r}')

    status = data.get('admissibility_status')
    if status not in VALID_ADMISSIBILITY:
        errors.append(f'invalid admissibility_status: {status!r}')

    brief = data.get('brief')
    if not isinstance(brief, dict):
        errors.append('brief must be an object')
    else:
        for key, _ in BRIEF_SECTIONS:
            if key not in brief:
                errors.append(f'brief missing required field: {key}')
            elif key != 'practical_next_step' and not isinstance(brief.get(key), list):
                errors.append(f'brief.{key} must be an array')
            elif key == 'practical_next_step' and not isinstance(brief.get(key), str):
                errors.append('brief.practical_next_step must be a string')

    if linked_task:
        gap = data.get('gap_analysis')
        if not isinstance(gap, dict):
            errors.append('gap_analysis is required when linking a task')
        else:
            for key in ('covers_gaps', 'remaining_gaps'):
                if key not in gap or not isinstance(gap.get(key), list):
                    errors.append(f'gap_analysis.{key} must be an array')

    if linked_task and usage != 'task_input':
        errors.append('usage_intent must be task_input when linking a task')

    if errors:
        return None, '; '.join(errors)
    return data, ''


def build_evidence_brief_from_enrichment(
    *,
    kind: str,
    enrichment: dict,
    linked_task: str,
    covered: list[str],
    remaining: list[str],
    suggestion: str,
    evidence_needs_review: bool,
    redacted: bool,
    task_status: str,
    next_step: str,
) -> str:
    brief = enrichment['brief']
    source_kind_labels = {
        'transcript': '会议记录 / 讨论转写',
        'feedback': '用户或客户反馈',
        'interview': '访谈材料',
        'draft': '草稿 / 待审内容',
        'data_notes': '数据或指标说明',
        'source': '已提供来源 / 产品说明',
        'notes': '笔记 / SOP / 日志',
        'reference': '参考资料',
        'general': '一般资料',
    }

    sections = [
        '# Evidence Brief',
        '',
        '## 资料类型',
        source_kind_labels.get(kind, kind),
        '',
    ]
    for key, heading in BRIEF_SECTIONS:
        value = brief.get(key, [])
        if key == 'practical_next_step':
            continue
        sections.extend([f'## {heading}', markdown_list(value), ''])

    sections.extend([
        '## 建议下一步',
        f'- {brief.get("practical_next_step", "None")}',
        f'- 系统下一步字段：{next_step}',
        '',
        '## 关联任务',
        linked_task or 'None',
        '',
        '## 覆盖的缺口',
        markdown_list(covered),
        '',
        '## 仍未覆盖的缺口',
        markdown_list(remaining),
        '',
        '## 任务状态',
        task_status,
        '',
        '## 任务建议',
        suggestion if suggestion not in {'None', None} else 'None',
        '',
        '## Review 状态',
        'NEEDS_REVIEW' if evidence_needs_review else 'CAPTURED',
        '',
        '## 脱敏',
        'true' if redacted else 'false',
        '',
    ])
    return '\n'.join(sections)


def update_task_gap_state(
    root: Path,
    task_folder: str,
    evidence_rel: str,
    evidence_needs_review: bool,
    covered: list[str],
    remaining: list[str],
) -> tuple[list[str], list[str], str, str]:
    if not task_folder:
        return [], [], 'NO_LINKED_TASK', 'None'

    task_dir = (root / task_folder).resolve()
    if not is_task_dir(task_dir, root):
        return [], [], 'INVALID_LINKED_TASK', 'None'

    if not remaining:
        status = 'READY_TO_EXECUTE'
    else:
        status = 'BLOCKED'

    missing_path = task_dir / 'missing_inputs.md'
    missing_path.write_text(
        '# Missing Inputs\n\n'
        + ''.join(f'- Resolved: {item} (covered by {evidence_rel})\n' for item in covered)
        + ''.join(f'- {item}\n' for item in remaining)
        + '\n',
        encoding='utf-8',
    )

    ready = status == 'READY_TO_EXECUTE'
    blocked_reason = 'None' if ready else '; '.join(remaining) if remaining else 'Missing input from employee'
    leader_review_reminder = REVIEW_REMINDER if evidence_needs_review else 'None'
    next_dependency = f'Run /lbai-execute-task {task_folder}' if ready else 'Missing input from employee'
    next_step = f'/lbai-execute-task {task_folder}' if ready else f'Provide remaining missing inputs with /lbai-add-evidence {task_folder}.'
    if evidence_needs_review:
        ensure_review_files(task_dir)

    scope_path = task_dir / 'task_scope.md'
    if scope_path.exists():
        txt = read_text(scope_path)
        txt = set_markdown_field(txt, 'status', status)
        txt = set_markdown_field(txt, 'inputs_available', merge_markdown_list(markdown_field(txt, 'inputs_available'), f'Evidence: {evidence_rel}'))
        txt = set_markdown_field(txt, 'inputs_missing', markdown_list(remaining))
        txt = set_markdown_field(txt, 'evidence_artifacts', merge_markdown_list(markdown_field(txt, 'evidence_artifacts'), evidence_rel))
        txt = set_markdown_field(txt, 'remaining_gaps', markdown_list(remaining))
        if evidence_needs_review:
            txt = set_markdown_field(txt, 'review_needed', 'true')
            txt = set_markdown_field(txt, 'review_reason', merge_review_reason(markdown_field(txt, 'review_reason'), evidence_rel))
            txt = set_markdown_field(txt, 'leader_review_reminder', leader_review_reminder)
        scope_path.write_text(txt, encoding='utf-8')

    ledger_path = task_dir / 'task_ledger.md'
    if ledger_path.exists():
        txt = read_text(ledger_path)
        txt = set_markdown_field(txt, 'status', status)
        if evidence_needs_review:
            txt = set_markdown_field(txt, 'review_needed', 'true')
            txt = set_markdown_field(txt, 'review_reason', merge_review_reason(markdown_field(txt, 'review_reason'), evidence_rel))
            txt = set_markdown_field(txt, 'leader_review_reminder', leader_review_reminder)
        txt = set_markdown_field(txt, 'source_artifacts', merge_markdown_list(markdown_field(txt, 'source_artifacts'), evidence_rel))
        txt = set_markdown_field(txt, 'blocked_reason', blocked_reason)
        txt = set_markdown_field(txt, 'next_dependency', next_dependency)
        txt = set_markdown_field(txt, 'next_step', next_step)
        txt = set_markdown_field(txt, 'evidence_artifacts', merge_markdown_list(markdown_field(txt, 'evidence_artifacts'), evidence_rel))
        txt = set_markdown_field(txt, 'remaining_gaps', markdown_list(remaining))
        ledger_path.write_text(txt, encoding='utf-8')

    gap_record = task_dir / 'gap_record.md'
    gap_record.write_text(
        '# Gap Record\n\n'
        f'## latest_evidence\n{evidence_rel}\n\n'
        f'## covers_gaps\n{markdown_list(covered)}\n\n'
        f'## remaining_gaps\n{markdown_list(remaining)}\n\n'
        f'## leader_review_reminder\n{leader_review_reminder}\n\n'
        f'## status\n{status}\n',
        encoding='utf-8',
    )
    return covered, remaining, status, leader_review_reminder


def ensure_ledger(root: Path) -> Path:
    path = root / 'role_workspace' / 'ledgers' / 'EVIDENCE_LEDGER_v1.md'
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or not read_text(path).strip():
        path.write_text(
            '# EVIDENCE_LEDGER_v1\n\n'
            '| Date | Evidence ID | Source Kind | Usage Intent | Linked Task | Covers Gaps | Status | Sync Status | Next Step |\n'
            '|---|---|---|---|---|---|---|---|---|\n',
            encoding='utf-8',
        )
    return path


def update_ledger(root: Path, evidence_id: str, kind: str, usage_intent: str, linked_task: str, covered: list[str], status: str, sync_status: str, next_step: str):
    path = ensure_ledger(root)
    txt = read_text(path)
    line = (
        f'| {date.today().isoformat()} | {evidence_id} | {kind} | {usage_intent} | '
        f'{linked_task or "None"} | {"; ".join(covered) if covered else "None"} | {status} | {sync_status} | {next_step} |'
    )
    lines = [existing for existing in txt.splitlines() if f'| {evidence_id} |' not in existing]
    lines.append(line)
    path.write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')


def run_hygiene(root: Path, evidence_rel: str, linked_task: str, allow_review_files: bool = False) -> tuple[str, str]:
    script = Path(__file__).resolve().with_name('evidence_hygiene_check.py')
    args = ['python3', str(script), evidence_rel, '--linked-task', linked_task]
    if allow_review_files:
        args.append('--allow-review-files')
    result = subprocess.run(args, cwd=root, capture_output=True, text=True)
    output = result.stdout + result.stderr
    readiness = 'BLOCKED'
    for line in output.splitlines():
        if line.startswith('commit_readiness:'):
            readiness = line.split(':', 1)[1].strip()
            break
    return readiness, output


def sync_paths(root: Path, evidence_rel: str, linked_task: str, message: str, include_review_files: bool = False) -> tuple[str, str]:
    if not git_remote_available(root):
        return 'BLOCKED', 'MISSING_GITHUB_REMOTE: no Git remote configured'
    if not git_upstream_available(root):
        return 'BLOCKED', 'MISSING_GIT_UPSTREAM: current branch has no upstream'

    paths = [evidence_rel, 'role_workspace/ledgers/EVIDENCE_LEDGER_v1.md']
    if linked_task:
        paths.extend([
            f'{linked_task}/missing_inputs.md',
            f'{linked_task}/task_scope.md',
            f'{linked_task}/task_slot.md',
            f'{linked_task}/task_ledger.md',
            f'{linked_task}/gap_record.md',
        ])
        if include_review_files:
            paths.extend(f'{linked_task}/{name}' for name in REVIEW_ALLOWED_TASK_FILES)
    paths = [path for path in paths if (root / path).exists()]
    add_result = run_git(root, ['add', '-A', '--', *paths])
    if add_result.returncode != 0:
        return 'BLOCKED', f'git add failed: {(add_result.stdout + add_result.stderr).strip()}'
    if not git_has_staged_changes(root):
        return 'NO_CHANGES', 'No local changes to commit'
    commit_result = run_git(root, ['commit', '-m', message])
    if commit_result.returncode != 0:
        return 'BLOCKED', f'git commit failed: {(commit_result.stdout + commit_result.stderr).strip()}'
    push_result = run_git(root, ['push'])
    if push_result.returncode != 0:
        return 'PUSH_FAILED', f'git push failed: {(push_result.stdout + push_result.stderr).strip()}'
    return 'PUSHED', 'git push completed'


def block(reason: str, next_step: str) -> int:
    print('evidence_status: BLOCKED')
    print('sync_status: BLOCKED')
    print(f'reason: {reason}')
    print(f'next_step: {next_step}')
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('target_or_content', nargs='?')
    parser.add_argument('content', nargs='*')
    parser.add_argument('--content', dest='content_text', default='')
    parser.add_argument('--enrichment', required=True, help='Path to AI-generated evidence enrichment JSON (required).')
    parser.add_argument('--no-sync', action='store_true', help='Create evidence artifacts without committing or pushing.')
    args = parser.parse_args()

    root = workspace_root()
    linked_task, content = parse_input(args)
    enrichment_path = Path(args.enrichment).expanduser()
    if not enrichment_path.is_absolute():
        enrichment_path = (root / enrichment_path).resolve()

    enrichment, enrichment_error = load_enrichment(enrichment_path, linked_task)
    if enrichment is None:
        return block(enrichment_error or ENRICHMENT_BLOCKED_MESSAGE, ENRICHMENT_BLOCKED_MESSAGE)

    if not content.strip():
        return block('no evidence content provided', 'Paste source material and rerun with AI enrichment via Cursor or Codex desktop app.')

    if linked_task and not is_task_dir((root / linked_task).resolve(), root):
        return block('linked task must be an existing task folder under tasks/', f'Check task folder path: {linked_task}')

    kind = enrichment['source_kind']
    usage_intent = enrichment['usage_intent']
    redacted, findings = redact_sensitive(content)
    admissibility_status, review_reasons, ai_admissibility_status, evidence_needs_review = finalize_admissibility(
        enrichment,
    )
    converted_status = conversion_status_for(usage_intent, linked_task)
    sensitive_capture_status = 'REDACTED' if findings else 'NONE'
    suggestion = enrichment.get('task_suggestion') or 'None'
    if suggestion in {None, ''}:
        suggestion = 'None'

    gap = enrichment.get('gap_analysis') or {}
    covered = [item for item in gap.get('covers_gaps', []) if item and str(item).strip()]
    remaining = [item for item in gap.get('remaining_gaps', []) if item and str(item).strip()]

    content_hash = hashlib.sha256(redacted.encode('utf-8')).hexdigest()[:10]
    base_slug = slugify(f'{kind}_{content_hash}')[:64]
    evidence_dir = next_available(root / 'role_workspace' / 'knowledge' / 'evidence' / f'{date.today().strftime("%Y_%m_%d")}_{base_slug}')
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (root / 'role_workspace' / 'knowledge' / 'references').mkdir(parents=True, exist_ok=True)
    evidence_rel = str(evidence_dir.relative_to(root))
    evidence_id = evidence_dir.name

    cleaned = enrichment.get('cleaned_content', '').strip()
    input_body = cleaned if cleaned else redacted.strip()
    input_path = evidence_dir / 'input.md'
    input_path.write_text(
        '# Evidence Input\n\n'
        f'## source_identity\nUser-provided command input\n\n'
        f'## source_kind\n{kind}\n\n'
        f'## captured_at\n{date.today().isoformat()}\n\n'
        f'## enrichment_source\n{enrichment_path.name}\n\n'
        f'## content\n{input_body}\n',
        encoding='utf-8',
    )
    (evidence_dir / 'evidence_enrichment.json').write_text(
        json.dumps(enrichment, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )

    covered, remaining, task_status, gap_review_reminder = update_task_gap_state(
        root,
        linked_task,
        evidence_rel,
        evidence_needs_review,
        covered,
        remaining,
    )
    leader_review_reminder = gap_review_reminder if gap_review_reminder != 'None' else (REVIEW_REMINDER if evidence_needs_review else 'None')

    if linked_task and task_status == 'READY_TO_EXECUTE':
        next_step = f'/lbai-execute-task {linked_task}'
    elif linked_task:
        next_step = f'Provide remaining missing inputs with /lbai-add-evidence {linked_task}.'
    elif suggestion != 'None':
        next_step = 'Keep as reference, or confirm a task with /lbai-new-task.'
    else:
        next_step = 'Evidence saved as reference. No task was created.'

    brief_path = evidence_dir / 'evidence_brief.md'
    brief_path.write_text(
        build_evidence_brief_from_enrichment(
            kind=kind,
            enrichment=enrichment,
            linked_task=linked_task,
            covered=covered,
            remaining=remaining,
            suggestion=suggestion,
            evidence_needs_review=evidence_needs_review,
            redacted=bool(findings),
            task_status=task_status,
            next_step=next_step,
        ),
        encoding='utf-8',
    )

    review_reasons = review_reasons or []
    metadata_path = evidence_dir / 'evidence_metadata.md'
    metadata_path.write_text(
        '# Evidence Metadata\n\n'
        f'## source_identity\nUser-provided command input\n\n'
        f'## source_kind\n{kind}\n\n'
        f'## captured_at\n{date.today().isoformat()}\n\n'
        f'## ai_admissibility_status\n{ai_admissibility_status}\n\n'
        f'## admissibility_status\n{admissibility_status}\n\n'
        f'## converted_artifact_status\n{converted_status}\n\n'
        f'## usage_intent\n{usage_intent}\n\n'
        f'## linked_task\n{linked_task or "None"}\n\n'
        f'## covers_gaps\n{markdown_list(covered)}\n\n'
        f'## remaining_gaps\n{markdown_list(remaining)}\n\n'
        f'## redacted\n{"true" if findings else "false"}\n\n'
        f'## sensitive_capture_status\n{sensitive_capture_status}\n\n'
        f'## sync_status\nNOT_SYNCED\n\n'
        f'## leader_review_reminder\n{leader_review_reminder}\n\n'
        f'## review_reasons\n{markdown_list(review_reasons)}\n\n'
        f'## task_suggestion\n{suggestion}\n\n'
        f'## enrichment_artifact\n{evidence_rel}/evidence_enrichment.json\n\n'
        f'## evidence_brief\n{evidence_rel}/evidence_brief.md\n',
        encoding='utf-8',
    )

    evidence_status = admissibility_status
    sync_status = 'NOT_SYNCED'
    update_ledger(root, evidence_id, kind, usage_intent, linked_task, covered, evidence_status, sync_status, next_step)

    hygiene_output = ''
    sync_detail = 'Sync skipped by --no-sync.' if args.no_sync else ''
    if not args.no_sync:
        readiness, hygiene_output = run_hygiene(root, evidence_rel, linked_task, evidence_needs_review)
        if readiness != 'READY':
            sync_status = 'BLOCKED'
            sync_detail = 'Evidence sync blocked by hygiene check.'
        else:
            sync_status, sync_detail = sync_paths(root, evidence_rel, linked_task, f'docs(lbai): add evidence {evidence_id}', evidence_needs_review)
        metadata_text = read_text(metadata_path)
        metadata_path.write_text(set_markdown_field(metadata_text, 'sync_status', sync_status), encoding='utf-8')
        update_ledger(root, evidence_id, kind, usage_intent, linked_task, covered, evidence_status, sync_status, next_step)
        if sync_status == 'PUSHED':
            readiness, hygiene_output = run_hygiene(root, evidence_rel, linked_task, evidence_needs_review)
            if readiness == 'READY':
                sync_status_2, sync_detail_2 = sync_paths(root, evidence_rel, linked_task, f'chore(lbai): sync-evidence {evidence_id}', evidence_needs_review)
                if sync_status_2 == 'PUSHED':
                    sync_status = sync_status_2
                    sync_detail = f'{sync_detail}; {sync_detail_2}'
                elif sync_status_2 != 'NO_CHANGES':
                    sync_detail = f'{sync_detail}; sync status update not pushed: {sync_detail_2}'
            else:
                sync_detail = f'{sync_detail}; sync status update blocked by hygiene check.'

    print(f'EVIDENCE_FOLDER {evidence_rel}')
    print(f'evidence_brief: {evidence_rel}/evidence_brief.md')
    print(f'evidence_status: {evidence_status}')
    print(f'source_kind: {kind}')
    print(f'converted_artifact_status: {converted_status}')
    print(f'sensitive_capture_status: {sensitive_capture_status}')
    print(f'linked_task: {linked_task or "None"}')
    print('covers_gaps:')
    for item in covered or ['None']:
        print(f'- {item}')
    print('remaining_gaps:')
    for item in remaining or ['None']:
        print(f'- {item}')
    print(f'task_suggestion: {suggestion}')
    print(f'sync_status: {sync_status}')
    print(f'sync_detail: {sync_detail}')
    if leader_review_reminder != 'None':
        print(f'leader_review_reminder: {leader_review_reminder}')
    if hygiene_output.strip():
        print('hygiene_check:')
        print(hygiene_output.strip())
    print(f'next_step: {next_step}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
