"""Validate the Cursor MCP plugin package and tool definitions."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers.workspace import kit_root

pytestmark = pytest.mark.quality

ROOT = kit_root()
CURSOR_PLUGIN = ROOT / 'cursor_plugin'
MANIFEST = CURSOR_PLUGIN / 'manifest.json'
MCP_SERVER = CURSOR_PLUGIN / 'mcp_server.py'
TOOLS_MODULE = CURSOR_PLUGIN / 'tools.py'
COMPATIBILITY = ROOT / 'plugins' / 'lbai-workspace' / 'compatibility.json'


def test_cursor_manifest_schema():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))

    assert manifest['name'] == 'lbai-workspace'
    assert re.fullmatch(r'\d+\.\d+\.\d+', manifest['version'])
    assert manifest['entrypoint'] == './mcp_server.py'
    assert manifest['transport'] == 'stdio'
    assert 'mcpServers' not in manifest
    assert 'apps' not in manifest
    assert 'hooks' not in manifest
    assert manifest['interface']['displayName'] == 'LBAI Workspace'
    assert manifest['interface']['composerIcon'] == './assets/icon.png'
    assert manifest['interface']['logo'] == './assets/logo.png'


def test_cursor_manifest_version_matches_compatibility():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    compatibility = json.loads(COMPATIBILITY.read_text(encoding='utf-8'))
    assert manifest['version'] == compatibility['plugin_version'], (
        'cursor_plugin/manifest.json version must match compatibility.json plugin_version'
    )


def test_assets_exist_and_are_png():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    interface = manifest['interface']
    paths = [interface['composerIcon'], interface['logo']]
    for rel in paths:
        path = CURSOR_PLUGIN / rel.removeprefix('./')
        assert path.is_file(), f'missing cursor plugin asset: {rel}'
        assert path.suffix == '.png'
        assert path.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')


def test_plugin_contains_no_employee_artifacts_or_credentials():
    forbidden_parts = {'role_workspace', 'tasks', '.lbai'}
    forbidden_names = {'.env', 'github_token', 'knowledge_service.json'}
    for path in CURSOR_PLUGIN.rglob('*'):
        relative = path.relative_to(CURSOR_PLUGIN)
        assert not forbidden_parts.intersection(relative.parts)
        assert path.name not in forbidden_names
        if path.is_file() and path.suffix in {'.md', '.json', '.py'}:
            text = path.read_text(encoding='utf-8')
            assert '[TODO:' not in text
            assert not re.search(r'\b(?:ghp_|sk-)[A-Za-z0-9_-]{16,}', text)


def test_tools_module_is_importable():
    """Verify tools.py is valid Python and exports the expected list."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('tools', str(TOOLS_MODULE))
    tools_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tools_mod)

    expected = {
        'lbai_role_setup',
        'lbai_new_task',
        'lbai_add_evidence',
        'lbai_search_artifacts',
        'lbai_execute_task',
        'lbai_finish_task',
        'lbai_update_kit',
        'lbai_self_iterate',
        'lbai_doctor',
    }
    assert set(tools_mod.tool_names()) == expected

    for tool in tools_mod.TOOLS:
        assert 'name' in tool
        assert 'description' in tool
        assert 'cli' in tool
        assert 'inputSchema' in tool
        assert isinstance(tool['cli'], list)
        assert isinstance(tool['inputSchema'], dict)


def test_mcp_server_initialize_and_list_tools():
    """Smoke test the MCP server protocol (initialize + tools/list)."""
    input_lines = (
        '{"jsonrpc":"2.0","id":1,"method":"initialize"}\n'
        '{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n'
    )
    result = subprocess.run(
        [sys.executable, str(MCP_SERVER)],
        input=input_lines,
        capture_output=True,
        text=True,
        env={**dict(__import__('os').environ), 'PYTHONPATH': str(ROOT / 'lbai_core') + ':' + str(CURSOR_PLUGIN)},
    )
    assert result.returncode == 0, result.stderr
    lines = [l for l in result.stdout.strip().split('\n') if l.strip()]
    assert len(lines) >= 2

    init_resp = json.loads(lines[0])
    assert init_resp['id'] == 1
    assert 'result' in init_resp
    assert init_resp['result']['serverInfo']['name'] == 'lbai-workspace'
    assert 'capabilities' in init_resp['result']

    list_resp = json.loads(lines[1])
    assert list_resp['id'] == 2
    tools = list_resp['result']['tools']
    assert len(tools) == 9
    names = {t['name'] for t in tools}
    assert 'lbai_doctor' in names
    assert 'lbai_role_setup' in names
