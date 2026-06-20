#!/usr/bin/env python3
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from task_utils import SENSITIVE_PATTERNS, read_text, workspace_root


TEMP_PATTERNS = ['.DS_Store', '__pycache__', 'node_modules', '.env', '.pem', '.key', '.log']
ALLOWED_FILES = {
    'role_workspace/knowledge/index.md',
    'role_workspace/knowledge/log.md',
}


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('concept_path')
    args = parser.parse_args()

    root = workspace_root()
    concept_path = (root / args.concept_path).resolve()
    try:
        concept_rel = str(concept_path.relative_to(root))
    except ValueError:
        print('commit_readiness: BLOCKED')
        print('reason: concept_path must be inside the workspace')
        return 1

    allowed_files = set(ALLOWED_FILES)

    files, git_ok = changed_files(root)
    relevant_files = []
    unsafe_changes = []
    if git_ok:
        for changed in files:
            if changed == concept_rel or changed in allowed_files:
                relevant_files.append(changed)
            else:
                unsafe_changes.append(changed)

    if concept_path.is_file():
        relevant_files.append(concept_rel)
    for allowed in ALLOWED_FILES:
        if (root / allowed).exists() and allowed not in relevant_files:
            relevant_files.append(allowed)

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

    blocked = bool(temp or sensitive or not concept_path.is_file())
    print('# LBAI OKF Concept 提交前检查结果')
    print(f'workspace_root: {root}')
    print(f'concept_path: {args.concept_path}')
    print('')
    print('## 相关文件')
    for item in sorted(set(relevant_files)) or ['None']:
        print(f'- {item}')
    print('')
    print('## 非本次知识变更（仅提示，不阻断）')
    for item in unsafe_changes or ['无']:
        print(f'- {item}')
    if unsafe_changes:
        print('这些文件不会被 /lbai-add-evidence 自动提交；请在对应流程中单独处理。')
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
        if not concept_path.is_file():
            print('reason: concept_path must be an existing Markdown file')
        return 1
    print('commit_readiness: READY')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
