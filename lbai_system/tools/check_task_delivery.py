#!/usr/bin/env python3
"""Report whether /lbai-finish-task should run the auto-execute phase before finish review."""
import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from task_utils import (
    is_task_dir,
    task_needs_auto_execute,
    task_output_delivery_reasons,
    unresolved_missing_inputs,
    workspace_root,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('task_folder')
    args = parser.parse_args()

    root = workspace_root()
    task_dir = (root / args.task_folder).resolve()
    if not is_task_dir(task_dir, root):
        print('auto_execute_needed: false')
        print('delivery_status: BLOCKED')
        print('reason: task_folder must be an existing task under tasks/ with task_scope.md and task_ledger.md')
        print('next_step: 运行 /lbai-new-task 创建任务，或提供正确的 tasks/<task_folder>。')
        return 1

    missing = unresolved_missing_inputs(task_dir)
    if missing:
        print('auto_execute_needed: false')
        print('delivery_status: BLOCKED')
        print('missing_inputs:')
        for item in missing:
            print(f'- {item}')
        print(
            'next_step: 在对话补充缺失决策或上下文；/lbai-finish-task 会先用 archive_input 关闭缺口，'
            '再自动生成交付物。'
        )
        return 1

    reasons = task_output_delivery_reasons(task_dir)
    needed = task_needs_auto_execute(task_dir)
    print(f'auto_execute_needed: {"true" if needed else "false"}')
    print(f'delivery_status: {"NEEDS_DELIVERY" if needed else "READY"}')
    if reasons:
        print('reasons:')
        for reason in reasons:
            print(f'- {reason}')
    if needed:
        print(
            'next_step: /lbai-finish-task 先走 auto-execute：'
            'prepare_execute_task.py → 按 execute_task_plan_prompt 写 execution_plan.md + task_output.md。'
        )
    else:
        print('next_step: task_output.md 已就绪；/lbai-finish-task 直接进入 finish review。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
