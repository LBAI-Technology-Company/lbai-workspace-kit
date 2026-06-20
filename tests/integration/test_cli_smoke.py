"""CLI smoke tests for cross-platform Python invocation."""
from __future__ import annotations

import os
import json
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


def test_cli_doctor_json_contract(tmp_path):
    workspace = create_isolated_workspace(tmp_path)
    result = run_cli(
        'doctor',
        '--json',
        '--path',
        str(workspace),
        '--plugin-version',
        '1.4.12',
        '--min-workspace-version',
        '1.4.1',
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report['schema_version'] == 'lbai_doctor_v1'
    assert report['cli_version'] == '1.4.12'
    assert report['workspace_kit_version'] == '1.4.12'
    assert report['workspace_valid'] is True
    assert report['required_files']['status'] == 'READY'
    assert report['git']['origin_configured'] is True
    assert report['git']['upstream_configured'] is True
    assert report['plugin_version'] == '1.4.12'
    assert report['compatibility']['status'] == 'READY'
    assert report['doctor_status'] == 'READY'


def test_cli_doctor_json_reports_workspace_update(tmp_path):
    workspace = create_isolated_workspace(tmp_path)
    metadata_path = workspace / '.lbai' / 'workspace.json'
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    metadata['workspaceKitVersion'] = '1.3.0'
    metadata_path.write_text(json.dumps(metadata), encoding='utf-8')

    result = run_cli(
        'doctor',
        '--json',
        '--path',
        str(workspace),
        '--min-workspace-version',
        '1.4.1',
    )
    assert result.returncode == 2
    report = json.loads(result.stdout)
    assert report['compatibility']['reason'] == 'workspace_update_required'
    assert any('lbai update-kit' in step for step in report['next_steps'])


def test_cli_doctor_json_requires_backend_only_when_requested(tmp_path):
    workspace = create_isolated_workspace(tmp_path)
    home = tmp_path / 'empty_lbai_home'
    result = run_cli(
        'doctor',
        '--json',
        '--path',
        str(workspace),
        '--require-backend',
        env_extra={'LBAI_HOME': str(home)},
    )
    assert result.returncode == 2
    report = json.loads(result.stdout)
    assert report['knowledge_service']['status'] == 'NEEDS_AUTH'
    assert report['authentication']['knowledge_service_available'] is False
    assert any('backend-login' in step for step in report['next_steps'])


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
            '--identity-token',
            'test.identity.signature',
            env_extra={'LBAI_HOME': str(home)},
        )
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'backend_key_check: OK' in result.stdout
    assert requests and requests[0]['path'] == '/v1/knowledge/search'
    headers = {key.lower(): value for key, value in requests[0]['headers'].items()}
    assert headers.get('x-lbai-api-key') == 'test_backend_api_key'
    assert headers.get('x-lbai-identity-token') == 'test.identity.signature'
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
            '--identity-token',
            'test.identity.signature',
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
        '--identity-token',
        'test.identity.signature',
        '--no-verify',
        env_extra={'LBAI_HOME': str(home)},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'backend_key_check: SKIPPED' in result.stdout
    assert (home / 'auth' / 'knowledge_service.json').exists()


def path_without_gh() -> str:
    parts = []
    for part in os.environ.get('PATH', '').split(':'):
        if part and not (Path(part) / 'gh').exists():
            parts.append(part)
    return ':'.join(parts)


def import_workspace_cli():
    workspace_core = str(kit_root() / 'lbai_core')
    for key in list(sys.modules):
        if key == 'lbai' or key.startswith('lbai.'):
            del sys.modules[key]
    while workspace_core in sys.path:
        sys.path.remove(workspace_core)
    sys.path.insert(0, workspace_core)
    import lbai.cli as cli_module

    return cli_module


def test_git_credential_sync_roundtrip(tmp_path, monkeypatch):
    home = tmp_path / 'lbai_home'
    cred_store = tmp_path / 'git-credentials'
    gitconfig = tmp_path / 'gitconfig'
    gitconfig.write_text(
        f'[credential "https://github.com"]\n\thelper = store --file={cred_store}\n',
        encoding='utf-8',
    )
    monkeypatch.setenv('LBAI_HOME', str(home))
    monkeypatch.setenv('GIT_CONFIG_GLOBAL', str(gitconfig))
    monkeypatch.setenv('GIT_CONFIG_SYSTEM', '/dev/null')
    monkeypatch.setenv('PATH', path_without_gh())
    sys.path.insert(0, str(kit_root() / 'lbai_core'))
    from lbai.cli import auth_token_path, git_credential_password, sync_git_credentials

    token = 'lbai_test_github_token'
    auth_token_path().parent.mkdir(parents=True, exist_ok=True)
    auth_token_path().write_text(token + '\n', encoding='utf-8')

    ok, message = sync_git_credentials(token)
    assert ok, message
    assert git_credential_password() == token


def test_cli_github_auth_token_stores_token(tmp_path, monkeypatch):
    home = tmp_path / 'lbai_home'
    cred_store = tmp_path / 'git-credentials'
    gitconfig = tmp_path / 'gitconfig'
    gitconfig.write_text(
        f'[credential "https://github.com"]\n\thelper = store --file={cred_store}\n',
        encoding='utf-8',
    )
    monkeypatch.setenv('LBAI_HOME', str(home))
    monkeypatch.setenv('GIT_CONFIG_GLOBAL', str(gitconfig))
    monkeypatch.setenv('GIT_CONFIG_SYSTEM', '/dev/null')
    monkeypatch.setenv('PATH', path_without_gh())
    cli_module = import_workspace_cli()
    import argparse

    monkeypatch.setattr(cli_module.getpass, 'getpass', lambda _prompt: 'lbai_github_auth_token_test')
    rc = cli_module.github_auth_token(argparse.Namespace())
    assert rc == 0
    assert cli_module.auth_token_path().read_text(encoding='utf-8').strip() == 'lbai_github_auth_token_test'
    assert cred_store.exists()
    assert 'lbai_github_auth_token_test' in cred_store.read_text(encoding='utf-8')


def test_cli_auth_login_removed(tmp_path):
    home = tmp_path / 'lbai_home'
    home.mkdir()
    result = run_cli('auth', 'login', env_extra={'LBAI_HOME': str(home)})
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "invalid choice: 'login'" in combined
    assert '已更名' not in combined


def test_cli_auth_doctor_reports_git_credential_sync(tmp_path, monkeypatch):
    home = tmp_path / 'lbai_home'
    cred_store = tmp_path / 'git-credentials'
    gitconfig = tmp_path / 'gitconfig'
    gitconfig.write_text(
        f'[credential "https://github.com"]\n\thelper = store --file={cred_store}\n',
        encoding='utf-8',
    )
    monkeypatch.setenv('LBAI_HOME', str(home))
    monkeypatch.setenv('GIT_CONFIG_GLOBAL', str(gitconfig))
    monkeypatch.setenv('GIT_CONFIG_SYSTEM', '/dev/null')
    monkeypatch.setenv('PATH', path_without_gh())
    token = 'lbai_doctor_sync_token'
    auth_dir = home / 'auth'
    auth_dir.mkdir(parents=True)
    (auth_dir / 'github_token').write_text(token + '\n', encoding='utf-8')

    sys.path.insert(0, str(kit_root() / 'lbai_core'))
    from lbai.cli import sync_git_credentials

    sync_git_credentials(token)
    result = run_cli(
        'auth',
        'doctor',
        env_extra={
            'LBAI_HOME': str(home),
            'GIT_CONFIG_GLOBAL': str(gitconfig),
            'GIT_CONFIG_SYSTEM': '/dev/null',
            'PATH': path_without_gh(),
        },
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'git_credential_sync: ok' in result.stdout
    assert 'auth_status: READY' in result.stdout


def test_cli_doctor_resolves_active_workspace_from_external_project(tmp_path):
    workspace = create_isolated_workspace(tmp_path)
    home = tmp_path / 'lbai_home'
    external = tmp_path / 'other_project'
    external.mkdir()

    set_result = run_cli(
        'workspace',
        'set',
        '--path',
        str(workspace),
        env_extra={'LBAI_HOME': str(home)},
    )
    assert set_result.returncode == 0, set_result.stdout + set_result.stderr
    assert 'workspace_set_status: READY' in set_result.stdout

    result = run_cli('doctor', '--json', cwd=external, env_extra={'LBAI_HOME': str(home)})
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report['resolution_source'] == 'active_workspace'
    assert Path(report['workspace_root']) == workspace.resolve()
    assert report['source_project_path'] == str(external.resolve())


def test_cli_workspace_show_reports_active_workspace(tmp_path):
    workspace = create_isolated_workspace(tmp_path)
    home = tmp_path / 'lbai_home'
    set_result = run_cli(
        'workspace',
        'set',
        '--path',
        str(workspace),
        env_extra={'LBAI_HOME': str(home)},
    )
    assert set_result.returncode == 0

    result = run_cli('workspace', 'show', '--json', env_extra={'LBAI_HOME': str(home)})
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload['active_workspace'] == str(workspace.resolve())
    assert payload['configured_active_workspace_valid'] is True


def test_cli_workspace_ensure_creates_shared_workspace(tmp_path):
    home = tmp_path / 'lbai-home'
    result = run_cli('workspace', 'ensure', env_extra={'LBAI_HOME': str(home)})
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'workspace_ensure_status: READY' in result.stdout

    workspace = home / 'workspace'
    assert (workspace / 'AGENTS.md').is_file()
    assert (workspace / 'tasks').is_dir()

    config = json.loads((home / 'config.json').read_text(encoding='utf-8'))
    assert config['active_workspace'] == str(workspace.resolve())


def test_cli_self_iterate_starts_prompt_lab(tmp_path):
    workspace = create_isolated_workspace(tmp_path)
    result = run_cli('self-iterate', '--rounds', '1', '--scenarios-per-round', '1', cwd=workspace)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'prompt_lab_status: STARTED' in result.stdout
    assert 'prompt_lab_next_step:' in result.stdout
