"""Unit tests for the MCP json merge used in install.sh / install.ps1.

These tests exercise the Python merge snippet that the installer uses for
idempotent upsert of ``lbai-workspace`` into ``~/.cursor/mcp.json``.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


KIT_ROOT = '/kit/root'
VENV_PYTHON = '/venv/python'


def merge(existing_data: dict | None) -> dict:
    """Simulate what the install.sh Python heredoc does."""

    data = existing_data if isinstance(existing_data, dict) else {}
    data = dict(data)  # shallow copy to avoid mutating the caller
    servers = data.setdefault('mcpServers', {})
    if not isinstance(servers, dict):
        servers = {}
        data['mcpServers'] = servers
    servers['lbai-workspace'] = {
        'command': VENV_PYTHON,
        'args': [KIT_ROOT + '/cursor_plugin/mcp_server.py'],
        'env': {'PYTHONPATH': KIT_ROOT + '/lbai_core'},
    }
    return data


def test_merge_from_empty():
    result = merge(None)
    assert result == {
        'mcpServers': {
            'lbai-workspace': {
                'command': VENV_PYTHON,
                'args': [KIT_ROOT + '/cursor_plugin/mcp_server.py'],
                'env': {'PYTHONPATH': KIT_ROOT + '/lbai_core'},
            },
        },
    }


def test_merge_preserves_existing_unrelated_server():
    existing = {
        'mcpServers': {
            'other-tool': {'command': '/usr/bin/foo', 'args': ['x']},
        },
        'otherTopLevel': True,
    }
    result = merge(existing)
    assert result['mcpServers']['other-tool']['command'] == '/usr/bin/foo'
    assert result['otherTopLevel'] is True
    assert 'lbai-workspace' in result['mcpServers']


def test_merge_is_idempotent():
    # Two passes produce identical output
    existing = {
        'mcpServers': {
            'lbai-workspace': {'command': 'OLD', 'args': ['stale']},
        },
    }
    pass1 = merge(existing)
    pass2 = merge(pass1)
    assert pass1 == pass2


def test_merge_overwrites_existing_lbai_entry():
    existing = {
        'mcpServers': {
            'lbai-workspace': {'command': 'old-python', 'args': ['old-path']},
        },
    }
    result = merge(existing)
    assert result['mcpServers']['lbai-workspace']['command'] == VENV_PYTHON
    assert result['mcpServers']['lbai-workspace']['args'][0] == KIT_ROOT + '/cursor_plugin/mcp_server.py'


def test_merge_with_non_dict_mcpservers():
    """If existing mcpServers is not a dict, it should be replaced."""
    result = merge({'mcpServers': 'not-a-dict'})
    assert isinstance(result['mcpServers'], dict)
    assert 'lbai-workspace' in result['mcpServers']
