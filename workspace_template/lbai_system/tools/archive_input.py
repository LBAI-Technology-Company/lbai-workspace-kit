#!/usr/bin/env python3
import argparse
import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True

from task_utils import is_task_dir, read_text, redact_sensitive, set_markdown_field, unresolved_missing_inputs, workspace_root


KIND_TO_FILE = {
    'transcript': 'input_transcript.md',
    'feedback': 'input_feedback.md',
    'interview': 'input_interview.md',
    'draft': 'input_draft.md',
    'data_notes': 'input_data_notes.md',
    'source': 'input_source.md',
    'notes': 'input_notes.md',
    'general': 'input_user_provided.md',
}


def classify_kind(text: str, task_context: str = '') -> str:
    low = text.lower()
    if any(k in low for k in ['不是会议', '不是会议全文', 'not a meeting', 'not a transcript']):
        return 'general'
    if any(k in low for k in ['会议', 'meeting', 'transcript', 'action item']):
        return 'transcript'
    if any(k in low for k in ['用户反馈', '客户反馈', 'feedback', 'bug', 'complaint']):
        return 'feedback'
    if any(k in low for k in ['访谈', 'interview']):
        return 'interview'
    if any(k in low for k in ['草稿', 'draft', '文案']):
        return 'draft'
    if any(k in low for k in ['数据表', 'spreadsheet', 'csv', '指标']):
        return 'data_notes'
    if any(k in low for k in ['source', '来源', '产品说明', '官网']):
        return 'source'
    if any(k in low for k in ['notes', '笔记', '要点']):
        return 'notes'
    return 'general'


def missing_item_matches_kind(item: str, kind: str) -> bool:
    low = item.lower()
    if any(k in low for k in ['会议', 'meeting', '纪要', 'transcript', 'action item']):
        return kind in {'transcript', 'notes'}
    if any(k in low for k in ['用户反馈', '客户反馈', 'feedback', 'complaint']):
        return kind == 'feedback'
    if any(k in low for k in ['官网', '文案', 'homepage', 'website', '产品说明', 'source', '草稿', 'approved source']):
        return kind in {'source', 'draft'}
    if any(k in low for k in ['周报', 'weekly']):
        return kind in {'notes', 'data_notes', 'general'}
    return False


def next_available(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for idx in range(2, 100):
        candidate = path.with_name(f'{stem}_{idx}{suffix}')
        if not candidate.exists():
            return candidate
    raise RuntimeError(f'No available input filename for {path}')


def update_task_state(task_dir: Path, kind: str) -> str:
    remaining = unresolved_missing_inputs(task_dir)
    resolved = [item for item in remaining if missing_item_matches_kind(item, kind)]
    unresolved = [item for item in remaining if item not in resolved]
    missing = task_dir / 'missing_inputs.md'

    if not remaining:
        status = 'READY_TO_EXECUTE'
    elif unresolved:
        status = 'BLOCKED'
        missing.write_text(
            '# Missing Inputs\n\n'
            + ''.join(f'- Resolved: {item}\n' for item in resolved)
            + ''.join(f'- {item}\n' for item in unresolved)
            + f'\nSaved input kind: {kind}. The task remains blocked until the remaining missing inputs are provided.\n',
            encoding='utf-8',
        )
    else:
        status = 'READY_TO_EXECUTE'
        if missing.exists():
            missing.write_text(
                '# Missing Inputs\n\n'
                + ''.join(f'- Resolved: {item}\n' for item in resolved)
                + f'\nSaved input kind: {kind}. If more context is needed, the workspace assistant should ask for the exact missing item.\n',
                encoding='utf-8',
            )
    for name in ['task_scope.md', 'task_ledger.md']:
        path = task_dir / name
        if path.exists():
            txt = read_text(path)
            txt = set_markdown_field(txt, 'status', status)
            path.write_text(txt, encoding='utf-8')
    return status


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('task_folder')
    parser.add_argument('--kind', choices=sorted(KIND_TO_FILE.keys()) + ['auto'], default='auto')
    parser.add_argument('--content', default='')
    args = parser.parse_args()

    root = workspace_root()
    task_dir = (root / args.task_folder).resolve()
    if not is_task_dir(task_dir, root):
        print('STATUS BLOCKED')
        print('REASON task_folder must be an existing task under tasks/ with task_scope.md and task_ledger.md')
        return 1

    content = args.content or sys.stdin.read()
    if not content.strip():
        print('STATUS BLOCKED')
        print('REASON no input content provided')
        return 1

    task_context = f"{read_text(task_dir / 'task_scope.md')}\n{read_text(task_dir / 'task_ledger.md')}"
    kind = classify_kind(content, task_context) if args.kind == 'auto' else args.kind
    filename = KIND_TO_FILE[kind]
    path = next_available(task_dir / filename)
    redacted, findings = redact_sensitive(content)
    path.write_text(f"""# User Input

## source_identity
User-provided chat input

## source_kind
{kind}

## captured_at
{date.today().isoformat()}

## admissibility_status
CAPTURED

## converted_artifact_status
NOT_CONVERTED

## redacted
{"true" if findings else "false"}

## content
{redacted.strip()}
""", encoding='utf-8')
    status = update_task_state(task_dir, kind)

    print(f'SAVED {path.relative_to(root)}')
    print(f'INPUT_KIND {kind}')
    print(f'REDACTED {"true" if findings else "false"}')
    print(f'STATUS {status}')
    if status == 'READY_TO_EXECUTE':
        print(f'NEXT_STEP /lbai-execute-task {task_dir.relative_to(root)}')
    else:
        print('NEXT_STEP 请确认剩余缺失输入；资料齐全后再运行 /lbai-execute-task。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
