#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from task_utils import task_status, workspace_root


def task_dirs(root: Path) -> list[Path]:
    tasks_root = root / 'tasks'
    if not tasks_root.exists():
        return []
    return sorted(
        [p for p in tasks_root.iterdir() if p.is_dir() and (p / 'task_scope.md').exists()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def candidates(root: Path, command: str) -> list[Path]:
    dirs = task_dirs(root)
    if command == 'execute':
        return [p for p in dirs if task_status(p) in {'OPEN', 'READY_TO_EXECUTE'}]
    if command == 'finish':
        return [p for p in dirs if (p / 'task_output.md').exists() or task_status(p) in {'COMPLETED', 'WAITING_REVIEW'}]
    return dirs


def command_name(command: str) -> str:
    if command == 'execute':
        return 'lbai-execute-task'
    if command == 'finish':
        return 'lbai-finish-task'
    return f'lbai-{command}-task'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['execute', 'finish'])
    args = parser.parse_args()

    root = workspace_root()
    matches = candidates(root, args.command)

    if not matches:
        print('RESOLUTION none')
        print(f'NEXT_STEP 请先运行 /lbai-new-task 创建任务，或提供明确任务目录。')
        return 2
    if len(matches) == 1:
        print('RESOLUTION unique')
        print(f'TASK_FOLDER {matches[0].relative_to(root)}')
        print(f'NEXT_STEP /{command_name(args.command)} {matches[0].relative_to(root)}')
        return 0

    print('RESOLUTION ambiguous')
    print('CANDIDATES')
    for idx, path in enumerate(matches, start=1):
        print(f'{idx}. {path.relative_to(root)} ({task_status(path)})')
    print('NEXT_STEP 请回复任务编号或完整任务目录。')
    return 3


if __name__ == '__main__':
    raise SystemExit(main())
