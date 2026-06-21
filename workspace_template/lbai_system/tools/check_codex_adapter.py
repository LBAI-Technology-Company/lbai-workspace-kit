#!/usr/bin/env python3
from pathlib import Path


REQUIRED_FILES = [
    Path('AGENTS.md'),
    Path('lbai_system/runner_contracts/lbai_command_contract_v1.md'),
    Path('lbai_system/codex/skills/lbai-workflow/SKILL.md'),
    Path('.agents/skills/lbai-role-setup/SKILL.md'),
    Path('.agents/skills/lbai-add-evidence/SKILL.md'),
    Path('.agents/skills/lbai-search-artifacts/SKILL.md'),
    Path('.agents/skills/lbai-new-task/SKILL.md'),
    Path('.agents/skills/lbai-execute-task/SKILL.md'),
    Path('.agents/skills/lbai-finish-task/SKILL.md'),
    Path('.agents/skills/lbai-update-kit/SKILL.md'),
    Path('.agents/skills/lbai-self-iterate/SKILL.md'),
]

REQUIRED_COMMANDS = [
    '/lbai-role-setup',
    '/lbai-add-evidence',
    '/lbai-search-artifacts',
    '/lbai-new-task',
    '/lbai-execute-task',
    '/lbai-finish-task',
    '/lbai-update-kit',
    '/lbai-self-iterate',
]

REQUIRED_AGENTS_REFERENCES = [
    '.agents/skills/',
    'lbai_system/codex/skills/lbai-workflow/SKILL.md',
    'lbai_system/runner_contracts/lbai_command_contract_v1.md',
    '~/.codex/skills/',
]


def read(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return ''


def main() -> int:
    missing_files = [path for path in REQUIRED_FILES if not path.exists()]
    agents = read(Path('AGENTS.md'))
    contract = read(Path('lbai_system/runner_contracts/lbai_command_contract_v1.md'))
    skill = read(Path('lbai_system/codex/skills/lbai-workflow/SKILL.md'))
    command_skills = {
        command: read(Path(f'.agents/skills/{command.lstrip("/")}/SKILL.md'))
        for command in REQUIRED_COMMANDS
    }

    missing_commands = [
        command for command in REQUIRED_COMMANDS
        if command not in agents or command not in contract or command not in skill
    ]
    missing_agents_refs = [ref for ref in REQUIRED_AGENTS_REFERENCES if ref not in agents]
    missing_skill_refs = [
        ref for ref in [
            'AGENTS.md',
            'lbai_system/runner_contracts/lbai_command_contract_v1.md',
            'lbai_system/tools/',
        ]
        if ref not in skill
    ]
    missing_command_skill_refs = [
        command for command, text in command_skills.items()
        if command not in text
        or 'AGENTS.md' not in text
        or 'lbai_system/runner_contracts/lbai_command_contract_v1.md' not in text
        or 'lbai_system/tools/' not in text
    ]

    print('# LBAI Codex 适配检查')
    print('')
    print('## 必需文件')
    if missing_files:
        for path in missing_files:
            print(f'- 缺少 {path.as_posix()}')
    else:
        print('- 无缺失')

    print('')
    print('## 命令覆盖')
    if missing_commands:
        for command in missing_commands:
            print(f'- 缺少 {command}')
    else:
        print('- 八个 /lbai-* 命令均已覆盖')

    print('')
    print('## AGENTS.md 引用')
    if missing_agents_refs:
        for ref in missing_agents_refs:
            print(f'- 缺少 {ref}')
    else:
        print('- Codex 项目级适配引用完整')

    print('')
    print('## Skill 引用')
    if missing_skill_refs:
        for ref in missing_skill_refs:
            print(f'- 缺少 {ref}')
    else:
        print('- Skill 指向共享契约和核心工具')

    print('')
    print('## .agents 命令入口')
    if missing_command_skill_refs:
        for command in missing_command_skill_refs:
            print(f'- {command} 入口未完整指向 AGENTS、共享契约和核心工具')
    else:
        print('- 八个 .agents 命令入口均为薄适配')

    print('')
    if missing_files or missing_commands or missing_agents_refs or missing_skill_refs or missing_command_skill_refs:
        print('STATUS BLOCKED')
        print('NEXT_STEP 补齐 Codex 项目级适配文件、.agents 命令入口、共享命令契约或 AGENTS.md 引用。')
        return 1

    print('STATUS OK')
    print('NEXT_STEP 在 Codex 打开本项目后，可输入 /lbai-add-evidence、/lbai-search-artifacts、/lbai-new-task 等命令触发项目级 LBAI 工作流。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
