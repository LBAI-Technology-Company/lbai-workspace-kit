#!/usr/bin/env python3
import json
from pathlib import Path


EXPECTED = {
    'lbai-add-evidence.md',
    'lbai-search-artifacts.md',
    'lbai-init.md',
    'lbai-new-task.md',
    'lbai-execute-task.md',
    'lbai-finish-task.md',
    'lbai-update-kit.md',
}

STALE = {
    'init-lbai.md',
    'new-task.md',
    'execute-task.md',
    'finish-task.md',
}


def load_manifest_commands() -> set[str]:
    manifest = Path('lbai_system') / 'adapters' / 'commands_manifest.json'
    if not manifest.exists():
        return EXPECTED
    data = json.loads(manifest.read_text(encoding='utf-8'))
    return {item['name'] for item in data.get('commands', [])}


def main():
    expected = load_manifest_commands() or EXPECTED
    cursor_command_dir = Path('.cursor') / 'commands'
    system_command_dir = Path('lbai_system') / 'cursor' / 'commands'
    cursor_existing = {p.name for p in cursor_command_dir.glob('*.md')} if cursor_command_dir.exists() else set()
    system_existing = {p.name for p in system_command_dir.glob('*.md')} if system_command_dir.exists() else set()
    cursor_missing = sorted(expected - cursor_existing)
    system_missing = sorted(expected - system_existing)
    cursor_stale = sorted(STALE & cursor_existing)
    system_stale = sorted(STALE & system_existing)
    drift = []

    print('# LBAI Cursor 命令配置检查')
    print('')
    print('## 期望命令')
    for name in sorted(expected):
        print(f'- .cursor/commands/{name}')
        print(f'- lbai_system/cursor/commands/{name}')
    print('')
    print('## 缺少的新命令')
    if cursor_missing or system_missing:
        for name in cursor_missing:
            print(f'- .cursor/commands/{name}')
        for name in system_missing:
            print(f'- lbai_system/cursor/commands/{name}')
    else:
        print('- 无')
    print('')
    print('## 需要删除的旧命令')
    if cursor_stale or system_stale:
        for name in cursor_stale:
            print(f'- .cursor/commands/{name}')
        for name in system_stale:
            print(f'- lbai_system/cursor/commands/{name}')
    else:
        print('- 无')
    print('')
    print('## 内容一致性')
    for name in sorted(expected):
        cursor_path = cursor_command_dir / name
        system_path = system_command_dir / name
        if not cursor_path.exists() or not system_path.exists():
            continue
        if cursor_path.read_text(encoding='utf-8') != system_path.read_text(encoding='utf-8'):
            drift.append(name)
            print(f'- DRIFT {name}')
    if not drift:
        print('- 无')
    print('')
    if cursor_missing or system_missing or cursor_stale or system_stale or drift:
        print('STATUS BLOCKED')
        print('NEXT_STEP 删除旧命令文件，确认 .cursor/commands/ 和 lbai_system/cursor/commands/ 都包含七个 lbai- 命令文件且内容一致，然后重启 Cursor 或 Reload Window。')
        return 1
    print('STATUS OK')
    print('NEXT_STEP 在 Cursor 输入 /lbai 应该能看到 /lbai-init、/lbai-add-evidence、/lbai-search-artifacts、/lbai-new-task、/lbai-execute-task、/lbai-finish-task、/lbai-update-kit。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
