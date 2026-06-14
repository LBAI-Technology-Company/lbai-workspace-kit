"""Integration tests for update_kit.py employee-facing output."""
from __future__ import annotations

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
