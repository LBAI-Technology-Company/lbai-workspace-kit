#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from task_utils import is_task_dir, read_text, review_required, task_status, unresolved_missing_inputs, workspace_root


def markdown_list(items: list[str]) -> str:
    return '\n'.join(f'- {item}' for item in items) if items else '- None'


def markdown_bullets_from_file(path: Path) -> list[str]:
    items = []
    for line in read_text(path).splitlines():
        stripped = line.strip()
        if not stripped.startswith('-'):
            continue
        value = stripped.lstrip('-').strip()
        if value and value.lower() != 'none':
            items.append(value)
    return items


def existing_evidence_refs(task_dir: Path) -> list[str]:
    refs: list[str] = []
    for filename in ('task_scope.md', 'task_ledger.md', 'gap_record.md'):
        text = read_text(task_dir / filename)
        for line in text.splitlines():
            value = line.strip().lstrip('-').strip()
            if value.startswith('role_workspace/knowledge/') and value.endswith('.md') and value not in refs:
                refs.append(value)
    return refs


def role_context_refs(root: Path) -> list[str]:
    refs = []
    for rel in (
        'role_workspace/world_model/ROLE_WORLD_MODEL_v1.md',
        'role_workspace/world_model/ROLE_BOUNDARY_v1.md',
    ):
        if (root / rel).exists():
            refs.append(rel)
    return refs


def build_plan_template(root: Path, task_dir: Path) -> str:
    task_rel = str(task_dir.relative_to(root))
    artifacts = [
        f'{task_rel}/task_scope.md',
        f'{task_rel}/task_slot.md',
        f'{task_rel}/task_ledger.md',
    ]
    if (task_dir / 'missing_inputs.md').exists():
        artifacts.append(f'{task_rel}/missing_inputs.md')
    if (task_dir / 'recommended_inputs.md').exists():
        artifacts.append(f'{task_rel}/recommended_inputs.md')
    artifacts.extend(existing_evidence_refs(task_dir))
    artifacts.extend(role_context_refs(root))

    review_reminder = (
        '需要负责人 review：对外发布、官网、定价、合规、投资人、媒体、客户承诺等内容不要自行定稿。'
        if review_required(task_dir)
        else 'None'
    )

    return (
        '# Execution Plan\n\n'
        f'## task_folder\n{task_rel}\n\n'
        f'## task_status\n{task_status(task_dir)}\n\n'
        f'## artifacts_to_read\n{markdown_list(artifacts)}\n\n'
        '## facts_from_sources\n'
        '- TODO: 从 task_scope、task_slot、linked OKF Concepts、岗位上下文和用户明确提供的后端搜索结果中提取可验证事实和岗位执行偏好。\n\n'
        '## assumptions\n'
        '- TODO: 只写必要假设；不能把假设写成事实。\n\n'
        '## task_output_sections\n'
        '1. summary\n'
        '2. findings_or_deliverable\n'
        '3. next_steps\n\n'
        '## missing_inputs\n'
        f'{markdown_list(unresolved_missing_inputs(task_dir))}\n\n'
        '## recommended_inputs\n'
        f'{markdown_list(markdown_bullets_from_file(task_dir / "recommended_inputs.md"))}\n\n'
        '## forbidden\n'
        '- 不要编造未提供的数据、客户承诺、报价、发布时间或负责人。\n'
        '- 不要绕过 task_slot.md 的范围。\n\n'
        f'## review_reminder\n- {review_reminder}\n'
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('task_folder')
    parser.add_argument('--force', action='store_true', help='Rewrite existing execution_plan.md.')
    args = parser.parse_args()

    root = workspace_root()
    task_dir = (root / args.task_folder).resolve()
    if not is_task_dir(task_dir, root):
        print('execute_status: BLOCKED')
        print('reason: task_folder must be an existing task under tasks/ with task_scope.md and task_ledger.md')
        print('next_step: 运行 /lbai-new-task 创建任务，或提供正确的 tasks/<task_folder>。')
        return 1

    missing = unresolved_missing_inputs(task_dir)
    if missing:
        print('execute_status: BLOCKED')
        print(f'task_folder: {task_dir.relative_to(root)}')
        print('missing_inputs:')
        for item in missing:
            print(f'- {item}')
        print(
            'next_step: 请先在对话框补充必要信息；如果补充的是原始资料、会议纪要、客户材料或可复用来源，'
            f'再使用 /lbai-add-evidence {task_dir.relative_to(root)} 归档。'
        )
        return 1

    plan_path = task_dir / 'execution_plan.md'
    if plan_path.exists() and not args.force:
        detail = 'existing execution_plan.md kept'
    else:
        plan_path.write_text(build_plan_template(root, task_dir), encoding='utf-8')
        detail = 'execution_plan.md written'

    print('execute_status: READY')
    print(f'task_folder: {task_dir.relative_to(root)}')
    print(f'execution_plan: {plan_path.relative_to(root)}')
    print(f'detail: {detail}')
    print(
        'next_step: 在 Cursor 或 Codex 桌面 App 中读取 execution_plan.md，'
        '按 task_output_sections 写入 task_output.md；确认 task_output.md 已生成后运行 /lbai-finish-task。'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
