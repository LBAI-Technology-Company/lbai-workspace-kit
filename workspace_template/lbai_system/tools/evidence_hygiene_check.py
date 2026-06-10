#!/usr/bin/env python3
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from task_utils import REVIEW_ALLOWED_TASK_FILES, SENSITIVE_PATTERNS, is_task_dir, read_text, workspace_root


TEMP_PATTERNS = ['.DS_Store', '__pycache__', 'node_modules', '.env', '.pem', '.key', '.log']
ALLOWED_LEDGER = 'role_workspace/ledgers/EVIDENCE_LEDGER_v1.md'


def run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(['git', *args], cwd=root, capture_output=True, text=True)


def changed_files(root: Path) -> tuple[list[str], bool]:
    result = run_git(root, ['-c', 'core.quotePath=false', 'status', '--porcelain', '--untracked-files=all'])
    if result.returncode != 0:
        return [], False
    files = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if ' -> ' in path:
            path = path.split(' -> ', 1)[1].strip()
        files.append(path)
    return files, True


def task_allowed_paths(root: Path, task_folder: str, allow_review_files: bool) -> set[str]:
    if not task_folder:
        return set()
    task_dir = (root / task_folder).resolve()
    if not is_task_dir(task_dir, root):
        return set()
    allowed = {
        'missing_inputs.md',
        'task_scope.md',
        'task_slot.md',
        'task_ledger.md',
        'gap_record.md',
    }
    if allow_review_files:
        allowed.update(REVIEW_ALLOWED_TASK_FILES)
    return {str((task_dir / name).relative_to(root)) for name in allowed}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('evidence_folder')
    parser.add_argument('--linked-task', default='')
    parser.add_argument('--allow-review-files', action='store_true')
    args = parser.parse_args()

    root = workspace_root()
    evidence_dir = (root / args.evidence_folder).resolve()
    try:
        evidence_rel = str(evidence_dir.relative_to(root))
    except ValueError:
        print('commit_readiness: BLOCKED')
        print('reason: evidence_folder must be inside the workspace')
        return 1

    allowed_prefix = evidence_rel + '/'
    allowed_files = {ALLOWED_LEDGER}
    allowed_files.update(task_allowed_paths(root, args.linked_task, args.allow_review_files))

    files, git_ok = changed_files(root)
    relevant_files = []
    unsafe_changes = []
    if git_ok:
        for changed in files:
            if changed.startswith(allowed_prefix) or changed in allowed_files:
                relevant_files.append(changed)
            else:
                unsafe_changes.append(changed)

    if evidence_dir.exists():
        for path in evidence_dir.rglob('*'):
            if path.is_file():
                rel = str(path.relative_to(root))
                if rel not in relevant_files:
                    relevant_files.append(rel)
    if (root / ALLOWED_LEDGER).exists() and ALLOWED_LEDGER not in relevant_files:
        relevant_files.append(ALLOWED_LEDGER)

    temp = []
    sensitive = []
    for rel in sorted(set(relevant_files)):
        path = root / rel
        if any(pattern in rel for pattern in TEMP_PATTERNS):
            temp.append(rel)
        if path.exists() and path.is_file():
            text = read_text(path)
            for pattern in SENSITIVE_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                    sensitive.append(f'{rel}: {pattern}')

    blocked = bool(unsafe_changes or temp or sensitive or not evidence_dir.exists())
    print('# LBAI Evidence 提交前检查结果')
    print(f'workspace_root: {root}')
    print(f'evidence_folder: {args.evidence_folder}')
    print('')
    print('## 相关文件')
    for item in sorted(set(relevant_files)) or ['None']:
        print(f'- {item}')
    print('')
    print('## 非允许范围变更')
    for item in unsafe_changes or ['无']:
        print(f'- {item}')
    print('')
    print('## 临时文件')
    for item in temp or ['无']:
        print(f'- {item}')
    print('')
    print('## 敏感信息')
    for item in sensitive or ['未发现']:
        print(f'- {item}')
    print('')
    if blocked:
        print('commit_readiness: BLOCKED')
        if not evidence_dir.exists():
            print('reason: evidence_folder does not exist')
        return 1
    print('commit_readiness: READY')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
