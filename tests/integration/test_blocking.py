"""Integration tests: tools must block without AI enrichment."""
from __future__ import annotations

import pytest

from tests.helpers.tool_runner import run_tool

pytestmark = pytest.mark.integration


class TestBlockingWithoutEnrichment:
    def test_add_evidence_blocks(self, isolated_workspace):
        result = run_tool(isolated_workspace, 'add_evidence.py', 'sample content')
        assert result.returncode != 0
        assert 'BLOCKED' in result.output or 'required' in result.output.lower()

    def test_new_task_blocks(self, isolated_workspace):
        result = run_tool(isolated_workspace, 'new_task.py')
        assert result.returncode != 0
        assert '--enrichment' in result.output

    def test_init_blocks(self, isolated_workspace):
        result = run_tool(isolated_workspace, 'init_lbai.py')
        assert result.returncode != 0
        assert 'BLOCKED' in result.stdout

    def test_search_blocks_without_enrichment(self, isolated_workspace):
        result = run_tool(isolated_workspace, 'search_artifacts.py')
        assert result.returncode != 0
        assert 'BLOCKED' in result.stdout

    def test_finish_blocks_without_enrichment(self, isolated_workspace):
        task = isolated_workspace / 'tasks' / '2026_06_10_test_task'
        task.mkdir(parents=True)
        (task / 'task_scope.md').write_text('# Task Scope\n\n## status\nOPEN\n', encoding='utf-8')
        (task / 'task_ledger.md').write_text('# Task Ledger\n\n## status\nOPEN\n', encoding='utf-8')
        result = run_tool(isolated_workspace, 'finish_task.py', 'tasks/2026_06_10_test_task')
        assert result.returncode != 0
        assert '--enrichment' in result.output
