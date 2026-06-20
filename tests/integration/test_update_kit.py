"""Integration tests for update_kit.py employee-facing output."""
from __future__ import annotations

import importlib.util
import json
import sys

import pytest

from tests.helpers.tool_runner import run_tool
from tests.helpers.workspace import template_root

pytestmark = pytest.mark.integration


class TestUpdateKit:
    def test_dry_run_prints_contract_summary_and_legacy_status(self, isolated_workspace):
        result = run_tool(isolated_workspace, 'update_kit.py', '--source', str(template_root()), '--dry-run')

        assert result.returncode == 0, result.output
        assert '工作流更新完成：DRY_RUN' in result.stdout
        assert 'commit_readiness: READY' in result.stdout
        assert 'git_status: SKIPPED' in result.stdout
        assert 'GitHub 同步：skipped: dry-run only' in result.stdout
        assert 'kit_update_status: DRY_RUN' in result.stdout
        assert 'cli_core_update: DRY_RUN' in result.stdout

    def test_skip_core_update_flag(self, isolated_workspace):
        result = run_tool(
            isolated_workspace,
            'update_kit.py',
            '--source',
            str(template_root()),
            '--dry-run',
            '--skip-core-update',
        )

        assert result.returncode == 0, result.output
        assert 'cli_core_update: SKIPPED' in result.stdout
        assert 'cli_core_detail: --skip-core-update' in result.stdout

    def test_auth_update_preserves_identity_token(self, tmp_path, monkeypatch):
        monkeypatch.setenv('LBAI_HOME', str(tmp_path / 'lbai_home'))
        tools_dir = template_root() / 'lbai_system' / 'tools'
        sys.path.insert(0, str(tools_dir))
        try:
            spec = importlib.util.spec_from_file_location(
                'update_kit_auth_test', tools_dir / 'update_kit.py'
            )
            assert spec and spec.loader
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        finally:
            sys.path.remove(str(tools_dir))

        auth_path = module.knowledge_service_auth_path()
        auth_path.parent.mkdir(parents=True)
        auth_path.write_text(
            json.dumps(
                {
                    'schema_version': 'knowledge_service_auth_v1',
                    'api_key': 'old-key',
                    'identity_token': 'signed.identity.token',
                    'identity_header': 'X-LBAI-Identity-Token',
                }
            ),
            encoding='utf-8',
        )
        module.write_knowledge_service_auth('new-key')
        stored = json.loads(auth_path.read_text(encoding='utf-8'))
        assert stored['api_key'] == 'new-key'
        assert stored['identity_token'] == 'signed.identity.token'
