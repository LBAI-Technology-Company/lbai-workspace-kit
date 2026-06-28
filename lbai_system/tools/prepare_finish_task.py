#!/usr/bin/env python3
"""Prepare /lbai-finish-task: resolve task folder or signal retroactive intake."""
import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from resolve_current_task import candidates
from task_utils import is_task_dir, task_status, workspace_root


AUTO_INTAKE_NEXT_STEP = (
    '从当前对话读取任务描述、决策与上下文，按 lbai_system/prompts/task_intake_enrichment_prompt_v1.md '
    '生成 task intake enrichment JSON（known_information 优先使用 conversation_context），'
    '运行 python3 lbai_system/tools/new_task.py --enrichment <json_path> 补建任务，'
    '然后继续 /lbai-finish-task：archive_input → check_task_delivery → auto-execute → finish review。'
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('task_folder', nargs='?', default='')
    args = parser.parse_args()

    root = workspace_root()

    if args.task_folder.strip():
        task_dir = (root / args.task_folder.strip()).resolve()
        if not is_task_dir(task_dir, root):
            print('resolution: invalid')
            print('auto_intake_needed: false')
            print(
                'next_step: 提供 tasks/ 下已有任务目录，或省略参数让系统自动解析/补建任务。'
            )
            return 1
        rel = task_dir.relative_to(root)
        print('resolution: explicit')
        print('auto_intake_needed: false')
        print(f'task_folder: {rel}')
        print(f'task_status: {task_status(task_dir)}')
        print(f'next_step: /lbai-finish-task {rel}')
        return 0

    matches = candidates(root, 'finish')
    if not matches:
        print('resolution: none')
        print('auto_intake_needed: true')
        print(f'next_step: {AUTO_INTAKE_NEXT_STEP}')
        return 0

    if len(matches) == 1:
        rel = matches[0].relative_to(root)
        print('resolution: unique')
        print('auto_intake_needed: false')
        print(f'task_folder: {rel}')
        print(f'task_status: {task_status(matches[0])}')
        print(f'next_step: /lbai-finish-task {rel}')
        return 0

    print('resolution: ambiguous')
    print('auto_intake_needed: false')
    print('candidates:')
    for idx, path in enumerate(matches, start=1):
        print(f'{idx}. {path.relative_to(root)} ({task_status(path)})')
    print('next_step: 请回复任务编号或完整任务目录；若以上都不是今天的工作，请省略参数重试以触发补建任务。')
    return 3


if __name__ == '__main__':
    raise SystemExit(main())
