#!/usr/bin/env python3
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from task_utils import workspace_root


REQUIRED_DIRS = [
    '.cursor/commands',
    '.cursor/rules',
    'lbai_system/company_guardrails',
    'lbai_system/codex/skills/lbai-workflow',
    'lbai_system/cursor/commands',
    'lbai_system/cursor/rules',
    'lbai_system/cursor/skills',
    'lbai_system/docs',
    'lbai_system/runner_contracts',
    'lbai_system/schemas',
    'lbai_system/templates',
    'lbai_system/templates/role_workspace/archive',
    'lbai_system/templates/role_workspace/knowledge/evidence',
    'lbai_system/templates/role_workspace/knowledge/references',
    'lbai_system/templates/role_workspace/ledgers',
    'lbai_system/templates/role_workspace/world_model',
    'lbai_system/templates/role_workspace/world_model/versions',
    'lbai_system/tools',
    'role_workspace/archive',
    'role_workspace/knowledge/evidence',
    'role_workspace/knowledge/references',
    'role_workspace/ledgers',
    'role_workspace/world_model',
    'role_workspace/world_model/versions',
    'tasks',
]

OLD_COMMANDS = [
    '.cursor/commands/new-task.md',
    '.cursor/commands/execute-task.md',
    '.cursor/commands/finish-task.md',
    '.cursor/commands/init.md',
    '.cursor/commands/init-lbai.md',
    '.cursor/commands/update-kit.md',
]

LOADER_TEMPLATE = 'lbai_system/templates/lbai_loader_template.mdc'
ROLE_TEMPLATE_DIR = Path('lbai_system/templates/role_workspace')
ROLE_TEMPLATE_FILES = [
    Path('archive/.gitkeep'),
    Path('ledgers/BLOCKED_ITEMS_v1.md'),
    Path('ledgers/DECISION_LEDGER_v1.md'),
    Path('ledgers/EVIDENCE_LEDGER_v1.md'),
    Path('ledgers/TASK_LEDGER_v1.md'),
    Path('knowledge/evidence/.gitkeep'),
    Path('knowledge/references/.gitkeep'),
    Path('world_model/ROLE_BOUNDARY_v1.md'),
    Path('world_model/ROLE_CURRENT_PRIORITIES_v1.md'),
    Path('world_model/ROLE_WORLD_MODEL_v1.md'),
    Path('world_model/versions/.gitkeep'),
]
COMMAND_FILES = [
    'lbai-add-evidence.md',
    'lbai-search-artifacts.md',
    'lbai-init.md',
    'lbai-new-task.md',
    'lbai-execute-task.md',
    'lbai-finish-task.md',
    'lbai-update-kit.md',
]

REQUIRED_FILES = [
    'lbai_system/runner_contracts/lbai_command_contract_v1.md',
    'lbai_system/codex/skills/lbai-workflow/SKILL.md',
]


def run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(['git', *args], cwd=root, capture_output=True, text=True)


def has_git_remote(root: Path) -> bool:
    result = run_git(root, ['remote'])
    return result.returncode == 0 and bool(result.stdout.strip())


def has_git_upstream(root: Path) -> bool:
    result = run_git(root, ['rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'])
    return result.returncode == 0 and bool(result.stdout.strip())


def write_if_missing(root: Path, path: Path, content: str, repair: bool, created: list[str], missing: list[str]):
    if path.exists():
        return
    rel = str(path.relative_to(root))
    missing.append(rel)
    if repair:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        created.append(rel)


def copy_command_if_missing(root: Path, name: str, repair: bool, created: list[str], missing: list[str]):
    src = root / 'lbai_system' / 'cursor' / 'commands' / name
    dst = root / '.cursor' / 'commands' / name
    if dst.exists():
        return
    missing.append(str(dst.relative_to(root)))
    if repair and src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        created.append(str(dst.relative_to(root)))


def copy_role_defaults_if_missing(root: Path, repair: bool, created: list[str], missing: list[str]):
    missing_templates = []
    for template_file in ROLE_TEMPLATE_FILES:
        src = root / ROLE_TEMPLATE_DIR / template_file
        dst = root / 'role_workspace' / template_file
        if not src.exists():
            missing_templates.append(str(src.relative_to(root)))
            continue
        if dst.exists():
            continue
        missing.append(str(dst.relative_to(root)))
        if repair:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            created.append(str(dst.relative_to(root)))
    return missing_templates


def loader_template_content(root: Path) -> str:
    template = root / LOADER_TEMPLATE
    if template.exists():
        return template.read_text(encoding='utf-8')
    return '# LBAI Cursor Project Loader\n\nFollow `lbai_system/runner_contracts/lbai_command_contract_v1.md` and `lbai_system/cursor/rules/` for this workspace.\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-only', action='store_true', help='Report missing bootstrap items without creating them.')
    args = parser.parse_args()
    repair = not args.check_only
    root = workspace_root()

    created: list[str] = []
    missing: list[str] = []
    old_commands = [path for path in OLD_COMMANDS if (root / path).exists()]

    for rel in REQUIRED_DIRS:
        path = root / rel
        if not path.exists():
            missing.append(rel)
            if repair:
                path.mkdir(parents=True, exist_ok=True)
                created.append(rel)

    for rel in REQUIRED_FILES:
        path = root / rel
        if not path.exists():
            missing.append(rel)

    missing_templates = copy_role_defaults_if_missing(root, repair, created, missing)
    write_if_missing(root, root / 'tasks' / '.gitkeep', '', repair, created, missing)

    write_if_missing(root, root / '.cursor' / 'rules' / 'lbai-loader.mdc', loader_template_content(root), repair, created, missing)
    for name in COMMAND_FILES:
        copy_command_if_missing(root, name, repair, created, missing)

    remote_ok = has_git_remote(root)
    upstream_ok = has_git_upstream(root)

    if old_commands:
        status = 'OLD_COMMANDS_DETECTED'
    elif missing_templates:
        status = 'BOOTSTRAP_BLOCKED'
    elif any(item in missing for item in REQUIRED_FILES):
        status = 'BOOTSTRAP_BLOCKED'
    elif not remote_ok:
        status = 'MISSING_GITHUB_REMOTE'
    elif not upstream_ok:
        status = 'MISSING_GIT_UPSTREAM'
    elif created:
        status = 'BOOTSTRAP_REPAIRED'
    elif missing and args.check_only:
        status = 'BOOTSTRAP_BLOCKED'
    else:
        status = 'BOOTSTRAP_COMPLETED'

    print(f'bootstrap_status: {status}')
    print(f'workspace_root: {root}')
    print(f'git_remote: {"present" if remote_ok else "missing"}')
    print(f'git_upstream: {"present" if upstream_ok else "missing"}')
    print('created:')
    for item in created or ['None']:
        print(f'- {item}')
    print('missing:')
    for item in missing or ['None']:
        print(f'- {item}')
    print('missing_source_templates:')
    for item in missing_templates or ['None']:
        print(f'- {item}')
    print('old_commands:')
    for item in old_commands or ['None']:
        print(f'- {item}')
    if old_commands:
        print('next_step: 删除旧命令文件后重启 Cursor 或 Reload Window。')
    elif missing_templates:
        print('next_step: 公司默认岗位模板缺失，请管理员重新发布完整 lbai-workspace-kit。')
    elif not remote_ok:
        print('next_step: 添加 GitHub remote 后重新运行 bootstrap check。')
    elif not upstream_ok:
        print('next_step: 设置当前分支 upstream 后重新运行 bootstrap check。')
    else:
        print('next_step: 可以使用 /lbai-init、/lbai-add-evidence、/lbai-search-artifacts 或 /lbai-new-task。')
    return 0 if status in {'BOOTSTRAP_COMPLETED', 'BOOTSTRAP_REPAIRED'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
