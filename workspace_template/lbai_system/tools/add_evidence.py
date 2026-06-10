#!/usr/bin/env python3
import argparse
import hashlib
import re
import select
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True

from task_utils import LEADER_REVIEW_REMINDER, REDACTION, REVIEW_ALLOWED_TASK_FILES, REVIEW_TASK_FILES, classify_risk, is_task_dir, markdown_field, read_text, redact_sensitive, set_markdown_field, slugify, unresolved_missing_inputs, workspace_root


SOURCE_KIND_FILES = {
    'transcript': ['会议', 'meeting', 'transcript', 'action item', '纪要'],
    'feedback': ['用户反馈', '客户反馈', 'feedback', 'bug', 'complaint', '投诉'],
    'interview': ['访谈', 'interview'],
    'draft': ['草稿', 'draft', '文案', 'copy'],
    'data_notes': ['数据', 'spreadsheet', 'csv', '指标', '报表'],
    'source': ['source', '来源', '产品说明', '官网', 'approved source'],
    'notes': ['notes', '笔记', '要点', 'sop', '日志', 'log'],
    'reference': ['参考', 'reference', '知识', '资料沉淀', '不创建任务', '不要创建任务'],
}

TASK_SUGGESTION_BY_KIND = {
    'transcript': '可创建会议纪要 / action items 整理任务',
    'feedback': '可创建用户反馈归类与产品问题提炼任务',
    'interview': '可创建访谈纪要与洞察整理任务',
    'draft': '可创建草稿审阅、改写或发布前检查任务',
    'data_notes': '可创建数据整理、指标解读或周报任务',
    'source': '可创建基于 approved source 的文案或说明整理任务',
    'notes': '可创建资料整理、SOP 提炼或行动项任务',
}

SOURCE_KIND_LABELS = {
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

DECISION_HINTS = [
    '决定', '确认', '已定', '批准', '同意', 'approved', 'confirmed', 'decided',
]

UNCERTAIN_HINTS = [
    '可能', '也许', '预计', '推测', '假设', '待确认', '不确定', '需要确认',
    'might', 'maybe', 'assume', 'assumption', 'tbd', 'to be confirmed',
]

MISSING_INFO_HINTS = [
    '缺', '还需要', '待补充', '未提供', '没有提供', '需要确认', '待确认',
    'missing', 'need', 'needs', 'required', 'unknown',
]

REVIEW_LIMITED_HINTS = [
    '承诺', '保证', '客户承诺', '官网', '对外', '公开发布', '价格', '报价',
    '收入', '增长', '转化率', '指标', '数据', '合规', '法律',
    'sla', 'guarantee', 'website', 'homepage', 'pricing', 'revenue',
    'conversion', 'legal', 'compliance',
]

REDACTION_SENTINEL = 'LBAI_REDACTED_PLACEHOLDER'

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


def classify_kind(text: str) -> str:
    low = text.lower()
    for kind, keywords in SOURCE_KIND_FILES.items():
        if any(keyword.lower() in low for keyword in keywords):
            return kind
    return 'general'


def usage_intent_for(kind: str, linked_task: str, text: str) -> str:
    low = text.lower()
    if linked_task:
        return 'task_input'
    if kind == 'reference' or any(k in low for k in ['只保存', '保存资料', '知识沉淀', '不创建任务', '不要创建任务', 'reference only']):
        return 'reference'
    if kind in TASK_SUGGESTION_BY_KIND:
        return 'possible_task_input'
    return 'reference'


def conversion_status_for(usage_intent: str, linked_task: str) -> str:
    if linked_task:
        return 'LINKED_TO_TASK'
    if usage_intent == 'possible_task_input':
        return 'TASK_SUGGESTED'
    return 'REFERENCE_ONLY'


def contains_redaction_marker(text: str) -> bool:
    return REDACTION in text or REDACTION_SENTINEL in text


def protect_redaction_marker(text: str) -> str:
    return text.replace(REDACTION, REDACTION_SENTINEL)


def restore_redaction_marker(text: str) -> str:
    return text.replace(REDACTION_SENTINEL, REDACTION)


def split_evidence_points(text: str, limit: int = 6) -> list[str]:
    protected = protect_redaction_marker(text).strip()
    if not protected:
        return []
    parts = []
    for line in protected.splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r'^\s*[-•]\s+', '', line)
        parts.extend(re.split(r'(?<=[。！？!?；;])\s*|(?<=[.!?;])\s+', line))
    points = []
    for part in parts:
        item = restore_redaction_marker(part.strip(' -•\t'))
        if not item:
            continue
        if len(item) > 180:
            item = item[:177].rstrip() + '...'
        if item not in points:
            points.append(item)
        if len(points) >= limit:
            break
    return points


def points_with_hints(points: list[str], hints: list[str], limit: int = 4) -> list[str]:
    matches = []
    for point in points:
        low = point.lower()
        if any(hint.lower() in low for hint in hints):
            matches.append(point)
        if len(matches) >= limit:
            break
    return matches


def review_risk_summary(evidence_needs_review: bool, kind: str, text: str) -> list[str]:
    risks = []
    if evidence_needs_review:
        risks.append('涉及对外发布、价格、法律、财务、投资人、媒体、客户承诺或安全等 review 边界，使用前需要负责人 review。')
    if kind == 'draft':
        risks.append('这是草稿类资料，不能默认视为已批准版本。')
    low = text.lower()
    if any(term in low for term in ['指标', '数据', '增长', 'revenue', '收入', 'conversion', '转化率']):
        risks.append('包含数据或指标表述时，后续输出需要保留来源或验证口径。')
    return risks


def next_step_sentence(linked_task: str, task_status: str, remaining: list[str], suggestion: str, evidence_needs_review: bool) -> str:
    if evidence_needs_review:
        if linked_task and remaining:
            return '资料已保存，但存在 review 风险；先补齐剩余缺口，并在对外使用前负责人 review。'
        if linked_task:
            return '资料已保存并可辅助当前任务，但对外使用前需要负责人 review。'
        return '资料已保存为参考；如要用于对外内容或正式承诺，先负责人 review。'
    if linked_task and task_status == 'READY_TO_EXECUTE':
        return f'资料已覆盖当前必需缺口，下一步可运行 /lbai-execute-task {linked_task}。'
    if linked_task and remaining:
        return '资料已关联当前任务，但还需要补齐剩余缺口后再执行。'
    if suggestion != 'None':
        return '资料已保存为参考；如要推进成正式工作，请用 /lbai-new-task 明确创建任务。'
    return '资料已保存为参考，不会自动创建任务。'


def build_evidence_brief(
    *,
    kind: str,
    redacted_text: str,
    linked_task: str,
    covered: list[str],
    remaining: list[str],
    suggestion: str,
    evidence_needs_review: bool,
    redacted: bool,
    task_status: str,
    next_step: str,
) -> str:
    points = split_evidence_points(redacted_text)
    uncertain = points_with_hints(points, UNCERTAIN_HINTS)
    missing_info = points_with_hints(points, MISSING_INFO_HINTS)
    review_limited = points_with_hints(points, REVIEW_LIMITED_HINTS)
    decisions = [
        point for point in points_with_hints(points, DECISION_HINTS)
        if not contains_redaction_marker(point)
        if point not in uncertain and point not in missing_info
    ]
    restricted = evidence_needs_review or kind == 'draft' or redacted
    if restricted:
        usable_heading = '仅可内部参考的信息'
        usable = [
            point for point in points
            if point not in missing_info
            and point not in review_limited
            and not contains_redaction_marker(point)
        ]
    else:
        usable_heading = '可直接使用的信息'
        usable = [
            point for point in points
            if point not in uncertain
            and point not in missing_info
            and point not in review_limited
            and not contains_redaction_marker(point)
        ]
    risks = review_risk_summary(evidence_needs_review, kind, redacted_text)
    if redacted:
        risks.insert(0, '已检测并脱敏敏感信息；仓库内只能流转脱敏版本，原始内容必须使用批准的安全渠道。')
    if not risks:
        risks.append('未发现明显敏感或对外发布风险。')

    practical_next = next_step_sentence(linked_task, task_status, remaining, suggestion, evidence_needs_review)

    return (
        '# Evidence Brief\n\n'
        '## 资料类型\n'
        f'{SOURCE_KIND_LABELS.get(kind, kind)}\n\n'
        f'## {usable_heading}\n'
        f'{markdown_list(usable[:5])}\n\n'
        '## 待 review 后才能使用的信息\n'
        f'{markdown_list(review_limited if restricted else [])}\n\n'
        '## 不确定或只是推断的信息\n'
        f'{markdown_list(uncertain)}\n\n'
        '## 已明确确认的决定\n'
        f'{markdown_list(decisions)}\n\n'
        '## 还缺的信息\n'
        f'{markdown_list(missing_info or remaining)}\n\n'
        '## 风险提示\n'
        f'{markdown_list(risks)}\n\n'
        '## 关联任务\n'
        f'{linked_task or "None"}\n\n'
        '## 覆盖的缺口\n'
        f'{markdown_list(covered)}\n\n'
        '## 仍未覆盖的缺口\n'
        f'{markdown_list(remaining)}\n\n'
        '## 建议下一步\n'
        f'- {practical_next}\n'
        f'- 系统下一步字段：{next_step}\n'
    )


REVIEW_REMINDER = LEADER_REVIEW_REMINDER

REVIEW_FILE_CONTENT = {
    'overclaim_check.md': '# Overclaim Check\n\nReview required before external release. Do not add unapproved public, pricing, legal, investor, media, product capability, or customer promise claims.\n',
    'release_boundary_check.md': '# Release Boundary Check\n\nThis task is not approved for external release until founder or role owner review is complete.\n',
    'founder_review_needed.md': '# Founder Review Reminder\n\nRemind the employee: leader review is required before external release. This workflow does not block execution or finish.\n',
}


def review_needed(kind: str, text: str) -> bool:
    _, needs_review, _ = classify_risk(text)
    return needs_review


def missing_item_matches_kind(item: str, kind: str) -> bool:
    low = item.lower()
    if any(k in low for k in ['会议', 'meeting', '纪要', 'transcript', 'action item']):
        return kind in {'transcript', 'notes'}
    if any(k in low for k in ['用户反馈', '客户反馈', 'feedback', 'complaint']):
        return kind == 'feedback'
    if any(k in low for k in ['访谈', 'interview']):
        return kind == 'interview'
    if any(k in low for k in ['官网', '文案', 'homepage', 'website', '产品说明', 'source', '草稿', 'approved source']):
        return kind in {'source', 'draft'}
    if any(k in low for k in ['周报', 'weekly', '数据', '指标']):
        return kind in {'notes', 'data_notes', 'general'}
    return False


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
    return '\n'.join(f'- {item}' for item in items) if items else '- None'


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
            path.write_text(REVIEW_FILE_CONTENT.get(name, f'# {name}\n\nLeader review reminder required before external release.\n'), encoding='utf-8')


def update_task_gap_state(root: Path, task_folder: str, kind: str, evidence_rel: str, evidence_needs_review: bool) -> tuple[list[str], list[str], str, str]:
    if not task_folder:
        return [], [], 'NO_LINKED_TASK', 'None'
    task_dir = (root / task_folder).resolve()
    if not is_task_dir(task_dir, root):
        return [], [], 'INVALID_LINKED_TASK', 'None'

    remaining = unresolved_missing_inputs(task_dir)
    covered = [item for item in remaining if missing_item_matches_kind(item, kind)]
    unresolved = [item for item in remaining if item not in covered]
    if not remaining:
        status = 'READY_TO_EXECUTE'
    elif not unresolved:
        status = 'READY_TO_EXECUTE'
    else:
        status = 'BLOCKED'

    missing_path = task_dir / 'missing_inputs.md'
    if remaining or unresolved:
        missing_path.write_text(
            '# Missing Inputs\n\n'
            + ''.join(f'- Resolved: {item} (covered by {evidence_rel})\n' for item in covered)
            + ''.join(f'- {item}\n' for item in unresolved)
            + '\n',
            encoding='utf-8',
        )

    ready = status == 'READY_TO_EXECUTE'
    blocked_reason = 'None' if ready else '; '.join(unresolved) if unresolved else 'Missing input from employee'
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
        txt = set_markdown_field(txt, 'inputs_missing', markdown_list(unresolved))
        txt = set_markdown_field(txt, 'evidence_artifacts', merge_markdown_list(markdown_field(txt, 'evidence_artifacts'), evidence_rel))
        txt = set_markdown_field(txt, 'remaining_gaps', markdown_list(unresolved))
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
        txt = set_markdown_field(txt, 'remaining_gaps', markdown_list(unresolved))
        ledger_path.write_text(txt, encoding='utf-8')

    gap_record = task_dir / 'gap_record.md'
    gap_record.write_text(
        '# Gap Record\n\n'
        f'## latest_evidence\n{evidence_rel}\n\n'
        f'## covers_gaps\n{markdown_list(covered)}\n\n'
        f'## remaining_gaps\n{markdown_list(unresolved)}\n\n'
        f'## leader_review_reminder\n{leader_review_reminder}\n\n'
        f'## status\n{status}\n',
        encoding='utf-8',
    )
    return covered, unresolved, status, leader_review_reminder


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
    result = subprocess.run(
        args,
        cwd=root,
        capture_output=True,
        text=True,
    )
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('target_or_content', nargs='?')
    parser.add_argument('content', nargs='*')
    parser.add_argument('--content', dest='content_text', default='')
    parser.add_argument('--kind', choices=['auto', *VALID_SOURCE_KINDS], default='auto')
    parser.add_argument('--no-sync', action='store_true', help='Create evidence artifacts without committing or pushing.')
    args = parser.parse_args()

    root = workspace_root()
    linked_task, content = parse_input(args)
    if not content.strip():
        print('evidence_status: BLOCKED')
        print('sync_status: BLOCKED')
        print('reason: no evidence content provided')
        print('next_step: 请粘贴资料，或使用 /lbai-add-evidence <资料内容>。')
        return 1

    if linked_task and not is_task_dir((root / linked_task).resolve(), root):
        print('evidence_status: BLOCKED')
        print('sync_status: BLOCKED')
        print('reason: linked task must be an existing task folder under tasks/')
        return 1

    kind = classify_kind(content) if args.kind == 'auto' else args.kind
    usage_intent = usage_intent_for(kind, linked_task, content)
    converted_status = conversion_status_for(usage_intent, linked_task)
    admissibility_status = 'NEEDS_REVIEW' if review_needed(kind, content) else 'CAPTURED'
    redacted, findings = redact_sensitive(content)
    sensitive_capture_status = 'REDACTED' if findings else 'NONE'
    suggestion = TASK_SUGGESTION_BY_KIND.get(kind, '可作为背景资料保存；如需执行，请明确创建任务。') if not linked_task and usage_intent == 'possible_task_input' else 'None'

    content_hash = hashlib.sha256(redacted.encode('utf-8')).hexdigest()[:10]
    base_slug = slugify(f'{kind}_{content_hash}')[:64]
    evidence_dir = next_available(root / 'role_workspace' / 'knowledge' / 'evidence' / f'{date.today().strftime("%Y_%m_%d")}_{base_slug}')
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (root / 'role_workspace' / 'knowledge' / 'references').mkdir(parents=True, exist_ok=True)
    evidence_rel = str(evidence_dir.relative_to(root))
    evidence_id = evidence_dir.name

    input_path = evidence_dir / 'input.md'
    input_path.write_text(
        '# Evidence Input\n\n'
        f'## source_identity\nUser-provided command input\n\n'
        f'## source_kind\n{kind}\n\n'
        f'## captured_at\n{date.today().isoformat()}\n\n'
        f'## content\n{redacted.strip()}\n',
        encoding='utf-8',
    )

    evidence_needs_review = admissibility_status == 'NEEDS_REVIEW'
    covered, remaining, task_status, gap_review_reminder = update_task_gap_state(root, linked_task, kind, evidence_rel, evidence_needs_review)
    leader_review_reminder = gap_review_reminder if gap_review_reminder != 'None' else (REVIEW_REMINDER if evidence_needs_review else 'None')
    if linked_task and task_status == 'READY_TO_EXECUTE':
        next_step = f'/lbai-execute-task {linked_task}'
    elif linked_task:
        next_step = 'Provide remaining missing inputs before /lbai-execute-task.'
    elif suggestion != 'None':
        next_step = 'Keep as reference, or confirm a task with /lbai-new-task.'
    else:
        next_step = 'Evidence saved as reference. No task was created.'
    sync_status = 'NOT_SYNCED'

    brief_path = evidence_dir / 'evidence_brief.md'
    brief_path.write_text(
        build_evidence_brief(
            kind=kind,
            redacted_text=redacted,
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

    metadata_path = evidence_dir / 'evidence_metadata.md'
    metadata_path.write_text(
        '# Evidence Metadata\n\n'
        f'## source_identity\nUser-provided command input\n\n'
        f'## source_kind\n{kind}\n\n'
        f'## captured_at\n{date.today().isoformat()}\n\n'
        f'## admissibility_status\n{admissibility_status}\n\n'
        f'## converted_artifact_status\n{converted_status}\n\n'
        f'## usage_intent\n{usage_intent}\n\n'
        f'## linked_task\n{linked_task or "None"}\n\n'
        f'## covers_gaps\n{markdown_list(covered)}\n\n'
        f'## remaining_gaps\n{markdown_list(remaining)}\n\n'
        f'## redacted\n{"true" if findings else "false"}\n\n'
        f'## sensitive_capture_status\n{sensitive_capture_status}\n\n'
        f'## sync_status\n{sync_status}\n\n'
        f'## leader_review_reminder\n{leader_review_reminder}\n\n'
        f'## task_suggestion\n{suggestion}\n\n'
        f'## evidence_brief\n{evidence_rel}/evidence_brief.md\n',
        encoding='utf-8',
    )

    evidence_status = admissibility_status
    update_ledger(root, evidence_rel, kind, usage_intent, linked_task, covered, evidence_status, sync_status, next_step)

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
        update_ledger(root, evidence_rel, kind, usage_intent, linked_task, covered, evidence_status, sync_status, next_step)
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
