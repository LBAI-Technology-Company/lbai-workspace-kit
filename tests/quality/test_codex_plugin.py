"""Validate the internal Codex plugin package and marketplace metadata."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers.workspace import kit_root

pytestmark = pytest.mark.quality

ROOT = kit_root()
PLUGIN = ROOT / 'plugins' / 'lbai-workspace'
MANIFEST = PLUGIN / '.codex-plugin' / 'plugin.json'
MARKETPLACE = ROOT / '.agents' / 'plugins' / 'marketplace.json'


def test_plugin_manifest_and_marketplace_contract():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    marketplace = json.loads(MARKETPLACE.read_text(encoding='utf-8'))

    assert manifest['name'] == PLUGIN.name == 'lbai-workspace'
    assert re.fullmatch(r'\d+\.\d+\.\d+', manifest['version'])
    assert manifest['skills'] == './skills/'
    assert 'mcpServers' not in manifest
    assert 'apps' not in manifest
    assert 'hooks' not in manifest
    assert manifest['interface']['capabilities'] == ['Interactive', 'Write']
    assert len(manifest['interface']['defaultPrompt']) <= 3

    assert marketplace['name'] == 'lbai-internal'
    entry = next(item for item in marketplace['plugins'] if item['name'] == manifest['name'])
    assert entry['source'] == {'source': 'local', 'path': './plugins/lbai-workspace'}
    assert entry['policy'] == {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'}
    assert entry['category'] == 'Productivity'


def test_plugin_assets_exist_and_are_png():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    interface = manifest['interface']
    paths = [interface['composerIcon'], interface['logo'], *interface['screenshots']]
    for rel in paths:
        path = PLUGIN / rel.removeprefix('./')
        assert path.is_file(), f'missing plugin asset: {rel}'
        assert path.suffix == '.png'
        assert path.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')


def test_plugin_contains_no_employee_artifacts_or_credentials():
    forbidden_parts = {'role_workspace', 'tasks', '.lbai'}
    forbidden_names = {'.env', 'github_token', 'knowledge_service.json'}
    for path in PLUGIN.rglob('*'):
        relative = path.relative_to(PLUGIN)
        assert not forbidden_parts.intersection(relative.parts)
        assert path.name not in forbidden_names
        if path.is_file() and path.suffix in {'.md', '.json', '.py', '.yaml'}:
            text = path.read_text(encoding='utf-8')
            assert '[TODO:' not in text
            assert not re.search(r'\b(?:ghp_|sk-)[A-Za-z0-9_-]{16,}', text)


def test_plugin_version_matches_changelog():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    compatibility = json.loads((PLUGIN / 'compatibility.json').read_text(encoding='utf-8'))
    changelog = (PLUGIN / 'CHANGELOG.md').read_text(encoding='utf-8')
    assert f'## {manifest["version"]}' in changelog
    assert compatibility['plugin_version'] == manifest['version']
    assert compatibility['minimum_cli_version'] == '1.4.1'
    assert compatibility['minimum_workspace_kit_version'] == '1.4.1'
    for skill_path in (PLUGIN / 'skills').glob('*/SKILL.md'):
        text = skill_path.read_text(encoding='utf-8')
        assert f'--plugin-version {manifest["version"]}' in text
        assert f'--min-workspace-version {compatibility["minimum_workspace_kit_version"]}' in text


def test_plugin_skill_display_names():
    expected = {
        'lbai-init': 'LBAI Role Setup',
        'lbai-new-task': 'LBAI New Task',
        'lbai-add-evidence': 'LBAI Add Evidence',
        'lbai-search-artifacts': 'LBAI Search Artifacts',
        'lbai-execute-task': 'LBAI Execute Task',
        'lbai-finish-task': 'LBAI Finish Task',
        'lbai-update-kit': 'LBAI Update Kit',
        'lbai-self-iterate': 'LBAI Self Iterate',
    }
    for skill_id, display_name in expected.items():
        yaml_path = PLUGIN / 'skills' / skill_id / 'agents' / 'openai.yaml'
        text = yaml_path.read_text(encoding='utf-8')
        assert f'display_name: "{display_name}"' in text, skill_id


def test_plugin_preflight_uses_machine_readable_cli():
    env = os.environ.copy()
    env['PATH'] = f'{ROOT / "lbai_core" / "bin"}{os.pathsep}{env.get("PATH", "")}'
    result = subprocess.run(
        [sys.executable, str(PLUGIN / 'scripts' / 'preflight.py'), '--workspace', str(ROOT)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report['schema_version'] == 'lbai_plugin_preflight_v1'
    assert report['plugin_version'] == '1.4.14'
    assert report['preflight_status'] == 'READY'
