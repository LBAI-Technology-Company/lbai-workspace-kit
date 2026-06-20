"""Ensure Cursor adapter files stay in sync with canonical lbai_system copies."""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.workspace import template_root

pytestmark = pytest.mark.quality

COMMANDS = [
    'lbai-add-evidence.md',
    'lbai-search-artifacts.md',
    'lbai-init.md',
    'lbai-new-task.md',
    'lbai-execute-task.md',
    'lbai-finish-task.md',
    'lbai-update-kit.md',
    'lbai-self-iterate.md',
]

MANIFEST = template_root() / 'lbai_system' / 'adapters' / 'commands_manifest.json'
PLUGIN_SKILLS = Path(__file__).resolve().parents[2] / 'plugins' / 'lbai-workspace' / 'skills'


def command_pairs():
    cursor_dir = template_root() / '.cursor' / 'commands'
    system_dir = template_root() / 'lbai_system' / 'cursor' / 'commands'
    for name in COMMANDS:
        yield name, cursor_dir / name, system_dir / name


@pytest.mark.parametrize('name,cursor_path,system_path', list(command_pairs()))
def test_cursor_command_files_match(name, cursor_path, system_path):
    assert cursor_path.exists(), f'missing .cursor command: {name}'
    assert system_path.exists(), f'missing lbai_system command: {name}'
    assert cursor_path.read_text(encoding='utf-8') == system_path.read_text(encoding='utf-8')


def test_commands_manifest_lists_all_commands():
    import json

    data = json.loads(MANIFEST.read_text(encoding='utf-8'))
    listed = {item['name'] for item in data['commands']}
    assert listed == set(COMMANDS)


def test_commands_manifest_has_routing_metadata():
    import json

    data = json.loads(MANIFEST.read_text(encoding='utf-8'))
    required = {
        'name',
        'slug',
        'tool',
        'category',
        'display_order',
        'prompt',
        'schema',
        'requires_enrichment',
        'mutates',
        'backend_required',
    }
    for item in data['commands']:
        assert required <= set(item), f'manifest command missing metadata: {item}'
    search = next(item for item in data['commands'] if item['slug'] == '/lbai-search-artifacts')
    assert search['backend_required'] is True
    assert search['mutates'] is False
    assert search['prompt'] == 'backend_search_query_plan_prompt_v1.md'
    assert search['schema'] == 'backend_search_query_plan_schema_v1.json'


def test_codex_plugin_skills_cover_command_surface():
    plugin_skills = {path.parent.name for path in PLUGIN_SKILLS.glob('*/SKILL.md')}
    expected = {name.removesuffix('.md') for name in COMMANDS}
    assert plugin_skills == expected


def test_codex_plugin_skills_delegate_to_workspace_contract_and_cli():
    for skill_path in PLUGIN_SKILLS.glob('*/SKILL.md'):
        text = skill_path.read_text(encoding='utf-8')
        assert 'lbai_system/runner_contracts/lbai_command_contract_v1.md' in text
        assert 'lbai ' in text
        assert 'lbai doctor --json' in text
        assert '[TODO:' not in text
