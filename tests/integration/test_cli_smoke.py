"""CLI smoke tests for cross-platform Python invocation."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers.backend_server import backend_search_server
from tests.helpers.workspace import create_isolated_workspace, kit_root

pytestmark = pytest.mark.integration


def run_cli(*args: str, cwd: Path | None = None, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env['PYTHONPATH'] = str(kit_root() / 'lbai_core')
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, '-m', 'lbai.cli', *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
    )


def test_cli_version():
    result = run_cli('--version')
    assert result.returncode == 0
    assert 'lbai' in result.stdout


def test_cli_doctor_on_isolated_workspace(tmp_path):
    workspace = create_isolated_workspace(tmp_path)
    result = run_cli('doctor', '--path', str(workspace))
    assert result.returncode == 0
    assert 'doctor_status: READY' in result.stdout


def test_cli_new_task_without_enrichment_shows_friendly_hint(tmp_path, monkeypatch):
    workspace = create_isolated_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    result = run_cli('new-task', '整理用户反馈')
    assert result.returncode == 2
    combined = result.stdout + result.stderr
    assert '/lbai-new-task' in combined
    assert 'Cursor' in combined or 'Codex' in combined


def test_cli_backend_login_verifies_and_stores_key_outside_workspace(tmp_path):
    home = tmp_path / 'lbai_home'
    with backend_search_server() as (base_url, requests):
        result = run_cli(
            'auth',
            'backend-login',
            '--api-key',
            'test_backend_api_key',
            '--base-url',
            base_url,
            env_extra={'LBAI_HOME': str(home)},
        )
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'backend_key_check: OK' in result.stdout
    assert requests and requests[0]['path'] == '/v1/search/evidence'
    headers = {key.lower(): value for key, value in requests[0]['headers'].items()}
    assert headers.get('x-lbai-api-key') == 'test_backend_api_key'
    auth_file = home / 'auth' / 'knowledge_service.json'
    assert auth_file.exists()
    text = auth_file.read_text(encoding='utf-8')
    assert 'test_backend_api_key' in text


def test_cli_backend_login_rejects_invalid_key(tmp_path):
    home = tmp_path / 'lbai_home'
    with backend_search_server(status=401, raw_body='{"error":"unauthorized"}') as (base_url, _requests):
        result = run_cli(
            'auth',
            'backend-login',
            '--api-key',
            'bad_backend_api_key',
            '--base-url',
            base_url,
            env_extra={'LBAI_HOME': str(home)},
        )
    assert result.returncode == 2
    assert 'backend_key_check: FAILED HTTP_401' in result.stdout
    assert 'backend_auth_status: BLOCKED' in result.stdout
    assert not (home / 'auth' / 'knowledge_service.json').exists()


def test_cli_backend_login_no_verify_can_store_offline(tmp_path):
    home = tmp_path / 'lbai_home'
    result = run_cli(
        'auth',
        'backend-login',
        '--api-key',
        'offline_backend_api_key',
        '--no-verify',
        env_extra={'LBAI_HOME': str(home)},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'backend_key_check: SKIPPED' in result.stdout
    assert (home / 'auth' / 'knowledge_service.json').exists()


def test_cli_self_iterate_starts_prompt_lab(tmp_path):
    workspace = create_isolated_workspace(tmp_path)
    result = run_cli('self-iterate', '--rounds', '1', '--scenarios-per-round', '1', cwd=workspace)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'prompt_lab_status: STARTED' in result.stdout
    assert 'prompt_lab_next_step:' in result.stdout
