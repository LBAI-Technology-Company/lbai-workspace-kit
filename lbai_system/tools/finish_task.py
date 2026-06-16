#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True

from enrichment_utils import load_json_file, resolve_enrichment_path, validate_with_schema
from task_utils import REQUIRED_TASK_FILES, LEADER_REVIEW_REMINDER, is_task_dir, markdown_field, prompt_lab_isolated_mode, read_text, review_required, set_markdown_field, task_status, unresolved_missing_inputs, workspace_root


ENRICHMENT_VERSION = 'finish_review_enrichment_v1'
BLOCKED_MESSAGE = (
    'AI finish review required (--enrichment). Use Cursor or Codex desktop app; '
    'see lbai_system/prompts/finish_review_enrichment_prompt_v1.md'
)


def validate_finish_review(root: Path, data: dict) -> str | None:
    err = validate_with_schema(root, data, 'finish_review_enrichment_schema_v1.json')
    if err:
        return err
    if data['finish_verdict'] not in {'APPROVE_FINISH', 'BLOCK_FINISH'}:
        return 'invalid finish_verdict'
    return None


def write_finish_review_artifact(task_dir: Path, data: dict):
    (task_dir / 'finish_review_enrichment.json').write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )
    summary = str(data.get('completeness_summary', '')).strip()
    gaps = data.get('gaps') or []
    risks = data.get('overclaim_risks') or []
    notes = data.get('review_notes') or []
    (task_dir / 'finish_review.md').write_text(
        '# Finish Review\n\n'
        f'## finish_verdict\n{data["finish_verdict"]}\n\n'
        f'## completeness_summary\n{summary}\n\n'
        f'## gaps\n' + ('\n'.join(f'- {item}' for item in gaps) if gaps else '- None') + '\n\n'
        f'## overclaim_risks\n' + ('\n'.join(f'- {item}' for item in risks) if risks else '- None') + '\n\n'
        f'## review_notes\n' + ('\n'.join(f'- {item}' for item in notes) if notes else '- None') + '\n\n'
        f'## next_step\n{data.get("next_step", "None")}\n',
        encoding='utf-8',
    )


def write_role_memory_feedback(root: Path, task_dir: Path, data: dict) -> list[str]:
    candidates = data.get('role_memory_feedback_candidates') or []
    if not candidates:
        return []
    task_rel = str(task_dir.relative_to(root))
    feedback_id = f'fb_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}_{task_dir.name}'
    payload = {
        'schema_version': 'role_memory_feedback_v1',
        'feedback_id': feedback_id,
        'source_task': task_rel,
        'confirmed_by_user': True,
        'created_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'feedback_items': candidates[:3],
        'note': 'Feedback candidate for backend aggregation. Not a local authoritative role rule.',
    }
    json_path = task_dir / 'role_memory_feedback.json'
    md_path = task_dir / 'role_memory_feedback.md'
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = [
        '# Role Memory Feedback',
        '',
        'These are feedback candidates for backend aggregation, not local authoritative role rules.',
        '',
        '## feedback_items',
    ]
    for item in candidates[:3]:
        lines.append(f'- {item.get("title", item.get("type", "feedback"))}: {item.get("content", "")}')
    lines.append('')
    md_path.write_text('\n'.join(lines), encoding='utf-8')
    return [json_path.name, md_path.name]


def run_pre_commit_check(root: Path, task_folder: str) -> tuple[int, str]:
    script = Path(__file__).resolve().with_name('hygiene_check.py')
    result = subprocess.run(
        [sys.executable, str(script), task_folder],
        cwd=root,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout + result.stderr


def parse_commit_readiness(output: str) -> str:
    for line in output.splitlines():
        if line.startswith('commit_readiness:'):
            return line.split(':', 1)[1].strip()
    return 'NEEDS_MANUAL_CHECK'


def run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ['git', *args],
        cwd=root,
        capture_output=True,
        text=True,
    )


def git_remote_available(root: Path) -> bool:
    result = run_git(root, ['remote'])
    return result.returncode == 0 and bool(result.stdout.strip())


def git_upstream_available(root: Path) -> bool:
    result = run_git(root, ['rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'])
    return result.returncode == 0 and bool(result.stdout.strip())


def git_has_staged_changes(root: Path) -> bool:
    result = run_git(root, ['diff', '--cached', '--quiet'])
    return result.returncode == 1


def git_add_task_artifacts(root: Path, task_folder: str) -> tuple[bool, str]:
    paths = [task_folder, 'role_workspace/ledgers/TASK_LEDGER_v1.md']
    add_result = run_git(root, ['add', '-A', '--', *paths])
    if add_result.returncode != 0:
        return False, f'git add failed: {(add_result.stdout + add_result.stderr).strip()}'
    return True, ''


def commit_task_artifacts(root: Path, task_folder: str, commit_message: str) -> tuple[bool, str]:
    ok, detail = git_add_task_artifacts(root, task_folder)
    if not ok:
        return False, detail
    if git_has_staged_changes(root):
        commit_result = run_git(root, ['commit', '-m', commit_message])
        if commit_result.returncode != 0:
            return False, f'git commit failed: {(commit_result.stdout + commit_result.stderr).strip()}'
        return True, commit_message
    return True, 'No local changes to commit'


def push_current(root: Path) -> tuple[bool, str]:
    push_result = run_git(root, ['push'])
    if push_result.returncode != 0:
        return False, f'git push failed: {(push_result.stdout + push_result.stderr).strip()}'
    return True, 'git push completed'


def reset_last_commit_keep_changes(root: Path) -> tuple[bool, str]:
    reset_result = run_git(root, ['reset', '--mixed', 'HEAD~1'])
    if reset_result.returncode != 0:
        return False, f'git reset failed while rolling back sync-status commit: {(reset_result.stdout + reset_result.stderr).strip()}'
    return True, 'sync-status commit rolled back'


def determine_task_status(task_dir: Path) -> str:
    missing = [name for name in REQUIRED_TASK_FILES if not (task_dir / name).exists()]
    if missing:
        return 'BLOCKED'
    if unresolved_missing_inputs(task_dir):
        return 'BLOCKED'
    current_status = task_status(task_dir)
    if current_status == 'BLOCKED':
        return 'BLOCKED'
    return 'COMPLETED'


def update_task_ledger(task_dir: Path, status: str, commit_readiness: str):
    path = task_dir / 'task_ledger.md'
    txt = read_text(path) or '# Task Ledger\n'
    txt = set_markdown_field(txt, 'status', status)
    txt = set_markdown_field(txt, 'commit_readiness', commit_readiness)
    txt = set_markdown_field(txt, 'last_finished_at', date.today().isoformat())
    path.write_text(txt, encoding='utf-8')


def non_placeholder(value: str) -> str:
    value = value.strip()
    if not value or value.startswith('<') or 'derived from' in value.lower():
        return ''
    return value


def task_goal(task_dir: Path) -> str:
    scope = read_text(task_dir / 'task_scope.md')
    ledger = read_text(task_dir / 'task_ledger.md')
    return (
        non_placeholder(markdown_field(scope, 'goal'))
        or non_placeholder(markdown_field(scope, 'task_name'))
        or non_placeholder(markdown_field(ledger, 'task_name'))
        or task_dir.name
    )


def list_task_artifacts(task_dir: Path) -> list[str]:
    return sorted(p.name for p in task_dir.iterdir() if p.is_file())


def markdown_list_items(value: str) -> list[str]:
    items = []
    for line in value.splitlines():
        item = line.strip().lstrip('-').strip()
        if item and item.lower() != 'none' and item not in items:
            items.append(item)
    return items


def source_artifacts_for_task(task_dir: Path) -> list[str]:
    task_scope = read_text(task_dir / 'task_scope.md')
    task_ledger = read_text(task_dir / 'task_ledger.md')
    evidence = markdown_list_items(markdown_field(task_scope, 'evidence_artifacts'))
    evidence.extend(item for item in markdown_list_items(markdown_field(task_ledger, 'evidence_artifacts')) if item not in evidence)

    artifacts = list_task_artifacts(task_dir)
    legacy_inputs = [name for name in artifacts if name.startswith('input_')]
    sources = evidence + [name for name in legacy_inputs if name not in evidence]
    return sources or ['task description from task_scope.md']


def update_structured_task_ledger(
    task_dir: Path,
    status: str,
    commit_readiness: str,
    git_status: str,
    blocked_reason: str,
    next_dependency: str,
):
    path = task_dir / 'task_ledger.md'
    txt = read_text(path) or '# Task Ledger\n'
    task_id = task_dir.name
    artifacts = list_task_artifacts(task_dir)
    sources = source_artifacts_for_task(task_dir)
    outputs = [
        name for name in artifacts
        if name in {
            'task_output.md',
            'execution_plan.md',
            'finish_review.md',
            'finish_review_enrichment.json',
            'overclaim_check.md',
            'release_boundary_check.md',
            'founder_review_needed.md',
            'role_memory_feedback.json',
            'role_memory_feedback.md',
        }
    ]
    if not outputs:
        outputs = ['None']
    fields = {
        'task_id': task_id,
        'task_goal': task_goal(task_dir),
        'source_artifacts': '\n'.join(f'- {item}' for item in sources),
        'agents_or_tools_used': '\n'.join([
            '- /lbai-finish-task',
            '- lbai_system/tools/finish_task.py',
            '- lbai_system/tools/hygiene_check.py',
        ]),
        'outputs_created': '\n'.join(f'- {item}' for item in outputs),
        'status': status,
        'blocked_reason': blocked_reason or 'None',
        'commit_readiness': commit_readiness,
        'git_status': git_status,
        'next_dependency': next_dependency,
        'next_step': next_dependency,
        'last_finished_at': date.today().isoformat(),
        'leader_review_reminder': LEADER_REVIEW_REMINDER if review_required(task_dir) else 'None',
    }
    for field, value in fields.items():
        txt = set_markdown_field(txt, field, value)
    path.write_text(txt, encoding='utf-8')


def update_global_ledger(root: Path, task_folder: str, status: str, commit_readiness: str, git_status: str, next_dependency: str):
    path = root / 'role_workspace' / 'ledgers' / 'TASK_LEDGER_v1.md'
    path.parent.mkdir(parents=True, exist_ok=True)
    txt = read_text(path)
    if not txt.strip():
        txt = '# TASK_LEDGER_v1\n\n| Date | Task ID | Task Goal | Status | Review Needed | Commit Readiness | Git Status | Source Artifacts | Outputs Created | Next Dependency |\n|---|---|---|---|---|---|---|---|---|---|\n'
    elif '| Task ID |' not in txt:
        legacy = txt.strip()
        txt = '# TASK_LEDGER_v1\n\n| Date | Task ID | Task Goal | Status | Review Needed | Commit Readiness | Git Status | Source Artifacts | Outputs Created | Next Dependency |\n|---|---|---|---|---|---|---|---|---|---|\n\n## Legacy Rows Before Structured Ledger\n\n' + legacy + '\n'
    task_name = Path(task_folder).name
    task_dir = root / task_folder
    review = 'Yes' if review_required(task_dir) else 'No'
    sources = '; '.join(source_artifacts_for_task(task_dir))
    line = f'| {date.today().isoformat()} | {task_name} | {task_goal(task_dir)} | {status} | {review} | {commit_readiness} | {git_status} | {sources} | `{task_folder}/` | {next_dependency} |'
    lines = [existing for existing in txt.splitlines() if f'| {task_name} |' not in existing]
    lines.append(line)
    path.write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')


def next_dependency_for(status: str, commit_readiness: str, git_status: str, leader_review_reminder: bool = False) -> str:
    if status == 'BLOCKED':
        return '先补齐缺失任务文件或缺失输入，再重新运行 /lbai-finish-task。'
    if git_status == 'PUSH_FAILED':
        return '检查网络、权限或 Git 冲突后，重新运行 /lbai-finish-task。'
    if commit_readiness == 'BLOCKED':
        return (
            '查看下方提交前检查结果。若出现“非本任务变更”，请先用对应流程同步或提交这些内容：'
            '/lbai-add-evidence 处理资料、/lbai-init 处理岗位记忆、/lbai-update-kit 处理工作流文件；'
            '也可以移走临时文件后重试 /lbai-finish-task。'
        )
    if git_status == 'BLOCKED':
        return '配置 Git remote/upstream 或处理同步阻塞后，重新运行 /lbai-finish-task。'
    if git_status == 'COMMITTED':
        return '任务已本地提交，之后需要同步到 private GitHub。'
    if leader_review_reminder and status == 'COMPLETED':
        return LEADER_REVIEW_REMINDER
    if git_status == 'PUSHED':
        return 'private GitHub 任务记录已同步。'
    return '请在工作区根目录重新运行 /lbai-finish-task。'


def employee_summary(status: str, commit_readiness: str, git_status: str, sync_detail: str, next_dependency: str) -> tuple[str, str]:
    if commit_readiness == 'READY' and status != 'BLOCKED' and git_status == 'PUSHED':
        return '任务已完成，并已同步到 private GitHub。', '可以继续下一个任务。'
    if sync_detail.startswith('MISSING_GITHUB_REMOTE'):
        return '任务已本地更新，但还没有配置 GitHub remote，暂未同步。', '先配置 private repo remote，或运行 lbai doctor 查看工作区状态。'
    if sync_detail.startswith('MISSING_GIT_UPSTREAM'):
        return '任务已本地更新，但当前分支没有 upstream，暂未同步。', '设置 upstream 后重新运行 /lbai-finish-task。'
    if git_status == 'PUSH_FAILED':
        return '任务已本地提交，但推送 GitHub 失败。', '检查网络、权限或冲突后重新运行 /lbai-finish-task。'
    if status == 'BLOCKED':
        return '任务还不能完成。', next_dependency
    if commit_readiness == 'BLOCKED':
        return '任务文件已更新，但提交前检查未通过。', next_dependency
    return '任务已本地更新，但同步状态需要处理。', next_dependency


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('task_folder')
    parser.add_argument('--enrichment', required=True)
    parser.add_argument('--no-sync', action='store_true', help='Write finish artifacts without committing or pushing.')
    args = parser.parse_args()
    if prompt_lab_isolated_mode():
        args.no_sync = True

    root = workspace_root()
    task_dir = (root / args.task_folder).resolve()
    if not is_task_dir(task_dir, root):
        print('task_status: BLOCKED')
        print('commit_readiness: BLOCKED')
        print('reason: task_folder must be an existing task under tasks/ with task_scope.md and task_ledger.md')
        return 1

    enrichment_path = resolve_enrichment_path(root, args.enrichment)
    review_data, review_error = load_json_file(enrichment_path)
    if review_data is None:
        print('task_status: BLOCKED')
        print('commit_readiness: BLOCKED')
        print(f'reason: {review_error or BLOCKED_MESSAGE}')
        print(f'next_step: {BLOCKED_MESSAGE}')
        return 1
    validation_error = validate_finish_review(root, review_data)
    if validation_error:
        print('task_status: BLOCKED')
        print('commit_readiness: BLOCKED')
        print(f'reason: {validation_error}')
        print(f'next_step: {BLOCKED_MESSAGE}')
        return 1

    write_finish_review_artifact(task_dir, review_data)
    role_memory_files = write_role_memory_feedback(root, task_dir, review_data)
    ai_finish_blocked = review_data['finish_verdict'] == 'BLOCK_FINISH'

    status = determine_task_status(task_dir)
    needs_leader_review_reminder = review_required(task_dir)
    check_code, check_output = run_pre_commit_check(root, args.task_folder)
    commit_readiness = parse_commit_readiness(check_output)
    sync_detail = ''

    if status == 'BLOCKED' and commit_readiness == 'READY':
        commit_readiness = 'BLOCKED'
        sync_detail = 'Task status is BLOCKED; resolve missing inputs or required files before GitHub sync.'

    if ai_finish_blocked:
        commit_readiness = 'BLOCKED'
        gap_text = '; '.join(str(item) for item in review_data.get('gaps') or []) or review_data.get('completeness_summary', '')
        sync_detail = f'AI finish review blocked: {gap_text}'

    skip_git_sync = (
        args.no_sync
        and commit_readiness == 'READY'
        and status != 'BLOCKED'
        and not ai_finish_blocked
    )

    if skip_git_sync:
        git_status = 'NOT_SYNCED'
        sync_detail = 'Sync skipped by --no-sync.'
        next_dependency = next_dependency_for(status, commit_readiness, git_status, needs_leader_review_reminder)
        update_structured_task_ledger(task_dir, status, commit_readiness, git_status, sync_detail, next_dependency)
        update_global_ledger(root, args.task_folder, status, commit_readiness, git_status, next_dependency)
    elif commit_readiness == 'READY' and status != 'BLOCKED' and not ai_finish_blocked:
        if not git_remote_available(root):
            commit_readiness = 'BLOCKED'
            sync_detail = 'MISSING_GITHUB_REMOTE: no Git remote configured'
        elif not git_upstream_available(root):
            commit_readiness = 'BLOCKED'
            sync_detail = 'MISSING_GIT_UPSTREAM: current branch has no upstream'

    if skip_git_sync:
        pass
    elif commit_readiness != 'READY' or status == 'BLOCKED':
        git_status = 'BLOCKED'
        sync_detail = sync_detail or 'Auto sync blocked by task status, hygiene check, or Git sync precondition.'
        if sync_detail.startswith(('MISSING_GITHUB_REMOTE', 'MISSING_GIT_UPSTREAM')):
            next_dependency = 'Configure GitHub remote/upstream and rerun /lbai-finish-task.'
        else:
            next_dependency = next_dependency_for(status, commit_readiness, git_status, needs_leader_review_reminder)
        update_structured_task_ledger(task_dir, status, commit_readiness, git_status, sync_detail, next_dependency)
        update_global_ledger(root, args.task_folder, status, commit_readiness, git_status, next_dependency)
    else:
        git_status = 'COMMITTED'
        next_dependency = next_dependency_for(status, commit_readiness, git_status, needs_leader_review_reminder)
        update_structured_task_ledger(task_dir, status, commit_readiness, git_status, 'None', next_dependency)
        update_global_ledger(root, args.task_folder, status, commit_readiness, git_status, next_dependency)

        check_code, check_output = run_pre_commit_check(root, args.task_folder)
        commit_readiness = parse_commit_readiness(check_output)
        if commit_readiness != 'READY':
            git_status = 'BLOCKED'
            sync_detail = 'Auto sync blocked after ledger update by hygiene check.'
            next_dependency = next_dependency_for(status, commit_readiness, git_status, needs_leader_review_reminder)
            update_structured_task_ledger(task_dir, status, commit_readiness, git_status, sync_detail, next_dependency)
            update_global_ledger(root, args.task_folder, status, commit_readiness, git_status, next_dependency)
        else:
            task_commit_message = f'docs(lbai): finish {Path(args.task_folder).name}'
            rel_task_folder = str(task_dir.relative_to(root))
            commit_ok, sync_detail = commit_task_artifacts(root, rel_task_folder, task_commit_message)
            if not commit_ok:
                git_status = 'BLOCKED'
                next_dependency = 'Resolve local Git commit failure and rerun /lbai-finish-task.'
                update_structured_task_ledger(task_dir, status, commit_readiness, git_status, sync_detail, next_dependency)
                update_global_ledger(root, args.task_folder, status, commit_readiness, git_status, next_dependency)
            else:
                push_ok, push_detail = push_current(root)
                if not push_ok:
                    git_status = 'PUSH_FAILED'
                    sync_detail = f'git push failed after task commit: {push_detail}'
                    next_dependency = next_dependency_for(status, commit_readiness, git_status, needs_leader_review_reminder)
                    update_structured_task_ledger(task_dir, status, commit_readiness, git_status, sync_detail, next_dependency)
                    update_global_ledger(root, args.task_folder, status, commit_readiness, git_status, next_dependency)
                else:
                    git_status = 'PUSHED'
                    next_dependency = next_dependency_for(status, commit_readiness, git_status, needs_leader_review_reminder)
                    update_structured_task_ledger(task_dir, status, commit_readiness, git_status, 'None', next_dependency)
                    update_global_ledger(root, args.task_folder, status, commit_readiness, git_status, next_dependency)

                    sync_commit_message = f'chore(lbai): sync-status {Path(args.task_folder).name}'
                    sync_commit_ok, sync_commit_detail = commit_task_artifacts(root, rel_task_folder, sync_commit_message)
                    if not sync_commit_ok:
                        git_status = 'PUSH_FAILED'
                        sync_detail = f'sync-status commit failed after task push: {sync_commit_detail}'
                        next_dependency = 'Resolve local Git sync-status commit failure and rerun /lbai-finish-task.'
                        update_structured_task_ledger(task_dir, status, commit_readiness, git_status, sync_detail, next_dependency)
                        update_global_ledger(root, args.task_folder, status, commit_readiness, git_status, next_dependency)
                    else:
                        sync_push_ok, sync_push_detail = push_current(root)
                        if not sync_push_ok:
                            reset_last_commit_keep_changes(root)
                            git_status = 'PUSH_FAILED'
                            sync_detail = f'sync-status push failed after task push: {sync_push_detail}'
                            next_dependency = next_dependency_for(status, commit_readiness, git_status, needs_leader_review_reminder)
                            update_structured_task_ledger(task_dir, status, commit_readiness, git_status, sync_detail, next_dependency)
                            update_global_ledger(root, args.task_folder, status, commit_readiness, git_status, next_dependency)
                        else:
                            sync_detail = f'{task_commit_message}; {sync_commit_message}'

    summary, employee_next_step = employee_summary(status, commit_readiness, git_status, sync_detail, next_dependency)
    print(f'结果：{summary}')
    print(f'下一步：{employee_next_step}')
    print(f'task_status: {status}')
    print(f'commit_readiness: {commit_readiness}')
    print(f'git_status: {git_status}')
    print('updated:')
    print(f'- {args.task_folder}/task_ledger.md')
    print(f'- {args.task_folder}/finish_review.md')
    print(f'- {args.task_folder}/finish_review_enrichment.json')
    for name in role_memory_files:
        print(f'- {args.task_folder}/{name}')
    print('- role_workspace/ledgers/TASK_LEDGER_v1.md')
    if commit_readiness == 'READY' and status != 'BLOCKED' and git_status == 'PUSHED':
        print('auto_git_sync: completed')
        print(f'detail: {sync_detail}')
    elif skip_git_sync and git_status == 'NOT_SYNCED':
        print('auto_git_sync: skipped')
        print(f'detail: {sync_detail}')
    else:
        print('auto_git_sync: blocked_or_failed')
        print(f'detail: {sync_detail}')
    print('提交前检查结果:')
    print(check_output.strip())
    if needs_leader_review_reminder:
        print(f'leader_review_reminder: {LEADER_REVIEW_REMINDER}')
    if commit_readiness == 'READY' and status != 'BLOCKED' and git_status == 'PUSHED':
        return 0
    if skip_git_sync and git_status == 'NOT_SYNCED':
        return 0
    if git_status == 'PUSH_FAILED':
        return 3
    if commit_readiness == 'NEEDS_MANUAL_CHECK':
        return 2
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
