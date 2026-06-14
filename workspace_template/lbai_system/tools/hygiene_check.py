#!/usr/bin/env python3
import argparse
import re
import subprocess
from pathlib import Path
import sys
from typing import Optional

sys.dont_write_bytecode = True

from task_utils import REQUIRED_TASK_FILES, REVIEW_TASK_FILES, SENSITIVE_PATTERNS, is_task_dir, read_text, review_required, RECOMMENDED_TASK_FILES

TEMP_PATTERNS = ['.DS_Store', '__pycache__', 'node_modules', '.env', '.pem', '.key', '.log']
ALLOWED_TASK_COMMIT_PREFIXES = ('tasks/',)
ALLOWED_TASK_COMMIT_FILES = {'role_workspace/ledgers/TASK_LEDGER_v1.md'}

def git_root() -> Optional[Path]:
    try:
        out = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True, stderr=subprocess.DEVNULL).strip()
        return Path(out)
    except Exception:
        return None

def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, shell=True)

def changed_files(root: Path):
    r = run('git -c core.quotePath=false status --porcelain --untracked-files=all', root)
    if r.returncode != 0:
        return [], False
    files=[]
    for line in r.stdout.splitlines():
        if line.strip():
            path = line[3:].strip()
            if ' -> ' in path:
                path = path.split(' -> ', 1)[1].strip()
            files.append(path)
    return files, True

def task_files(root: Path, task_path: Path):
    if not task_path.exists():
        return []
    files = []
    for p in task_path.rglob('*'):
        if p.is_file():
            try:
                files.append(str(p.relative_to(root)))
            except ValueError:
                pass
    return sorted(files)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('task_folder', nargs='?', default='')
    args = parser.parse_args()

    git_available = True
    root = git_root()
    if root is None:
        git_available = False
        root = Path.cwd()

    task_path = (root / args.task_folder).resolve() if args.task_folder else None
    if not task_path:
        print('# LBAI 提交前检查结果')
        print(f'workspace_root: {root}')
        print(f'git_available: {git_available}')
        print('task_folder: ')
        print('')
        print('commit_readiness: NEEDS_MANUAL_CHECK')
        print('reason: 请提供具体任务目录，例如 python3 lbai_system/tools/hygiene_check.py tasks/<task_folder>')
        return 2
    if not is_task_dir(task_path, root):
        print('commit_readiness: BLOCKED')
        print('reason: task_folder must be an existing task under tasks/ with task_scope.md and task_ledger.md')
        return 1

    files, git_ok = changed_files(root) if git_available else ([], False)
    missing=[]
    for name in REQUIRED_TASK_FILES:
        if not (task_path/name).exists():
            missing.append(str((task_path/name).relative_to(root)))

    needs_review = review_required(task_path) if task_path and task_path.exists() else False
    missing_review=[]
    if needs_review and task_path:
        for name in REVIEW_TASK_FILES:
            if not (task_path/name).exists():
                missing_review.append(str((task_path/name).relative_to(root)))

    recommended_missing=[]
    if (task_path / 'task_output.md').exists():
        for name in RECOMMENDED_TASK_FILES:
            if not (task_path / name).exists():
                recommended_missing.append(str((task_path / name).relative_to(root)))

    sensitive=[]
    temp=[]
    unsafe_changes=[]
    relevant_files=[]
    rel_task = str(task_path.relative_to(root))
    all_task_files = task_files(root, task_path)
    relevant_files = sorted(set(all_task_files + ['role_workspace/ledgers/TASK_LEDGER_v1.md']))
    if git_ok:
        for f in files:
            if f.startswith(rel_task + '/') or f in ALLOWED_TASK_COMMIT_FILES:
                continue
            if any(f.startswith(prefix) for prefix in ALLOWED_TASK_COMMIT_PREFIXES):
                unsafe_changes.append(f)
                continue
            unsafe_changes.append(f)

    for f in relevant_files:
        p=root/f
        if p.exists() and any(pattern in f for pattern in TEMP_PATTERNS):
            temp.append(f)
        if p.exists() and p.is_file():
            txt=read_text(p)
            for pat in SENSITIVE_PATTERNS:
                if re.search(pat, txt, re.IGNORECASE):
                    sensitive.append(f'{f}: {pat}')

    blocked = bool(missing or missing_review or sensitive or temp)
    print('# LBAI 提交前检查结果')
    print(f'workspace_root: {root}')
    print(f'git_available: {git_available}')
    print(f'task_folder: {args.task_folder}')
    print('')
    print('## 相关文件')
    for f in relevant_files or []: print(f'- {f}')
    if not relevant_files: print('- None')
    print('')
    print('## 必需文件')
    for m in missing: print(f'- {m}')
    if not missing: print('- 齐全')
    print('')
    print('## 需审核')
    print('是' if needs_review else '否')
    if needs_review:
        print('')
        print('## 缺少的审核文件')
        for m in missing_review: print(f'- {m}')
        if not missing_review: print('- 无')
    print('')
    print('## 推荐文件（非阻断）')
    for m in recommended_missing:
        print(f'- 缺少 {m}（/lbai-execute-task 应先写 execution_plan.md）')
    if not recommended_missing:
        print('- 无')
    print('')
    print('## 敏感信息')
    for s in sensitive: print(f'- {s}')
    if not sensitive: print('- 未发现')
    print('')
    print('## 临时或不安全文件')
    for t in temp: print(f'- {t}')
    if not temp: print('- 无')
    print('')
    print('## 非本任务变更（仅提示，不阻断）')
    for u in unsafe_changes: print(f'- {u}')
    if not unsafe_changes: print('- 无')
    if unsafe_changes:
        print('这些文件不会被 /lbai-finish-task 自动提交；请在对应流程中单独处理。')
    print('')
    if blocked:
        print('commit_readiness: BLOCKED')
        return 1
    if not git_available:
        print('commit_readiness: NEEDS_MANUAL_CHECK')
        print('reason: 当前目录不是 Git 仓库。已完成本地任务文件检查，但无法确认 Git 状态。')
        return 2
    print('commit_readiness: READY')
    print('')
    if args.task_folder:
        slug=Path(args.task_folder).name
        print('自动 GitHub 同步:')
        print(f'通过 /lbai-finish-task 自动提交任务结果、推送、再追加 sync-status 提交。task commit message: docs(lbai): finish {slug}')
    return 0

if __name__ == '__main__':
    sys.exit(main())
