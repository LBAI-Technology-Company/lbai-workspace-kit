"""Integration tests for new_task.py."""
from __future__ import annotations

import pytest

from tests.helpers.tool_runner import enrichment_path, parse_task_folder, run_tool

pytestmark = pytest.mark.integration


class TestNewTask:
    def test_open_task_created(self, isolated_workspace, fixtures):
        enrich = enrichment_path(fixtures, 'task_intake_open.json')
        result = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
        assert result.returncode == 0, result.output
        assert 'TASK_FOLDER tasks/' in result.stdout
        assert 'STATUS OPEN' in result.stdout
        assert 'REVIEW_NEEDED false' in result.stdout

        task_rel = parse_task_folder(result.stdout)
        task_dir = isolated_workspace / task_rel
        assert (task_dir / 'task_scope.md').exists()
        assert (task_dir / 'task_slot.md').exists()
        assert (task_dir / 'task_ledger.md').exists()
        assert (task_dir / 'task_intake_enrichment.json').exists()
        scope = (task_dir / 'task_scope.md').read_text(encoding='utf-8')
        assert '整理用户反馈周报' in scope
        assert '## status\nOPEN' in scope

    def test_blocked_task_with_missing_inputs(self, isolated_workspace, fixtures):
        enrich = enrichment_path(fixtures, 'task_intake_blocked.json')
        result = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
        assert result.returncode == 0, result.output
        assert 'STATUS BLOCKED' in result.stdout
        assert 'MISSING' in result.stdout
        task_rel = parse_task_folder(result.stdout)
        assert (isolated_workspace / task_rel / 'missing_inputs.md').exists()

    def test_review_task_creates_review_files(self, isolated_workspace, fixtures):
        enrich = enrichment_path(fixtures, 'task_intake_review.json')
        result = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
        assert result.returncode == 0, result.output
        assert 'REVIEW_NEEDED true' in result.stdout
        task_rel = parse_task_folder(result.stdout)
        task_dir = isolated_workspace / task_rel
        for name in ('overclaim_check.md', 'release_boundary_check.md', 'founder_review_needed.md'):
            assert (task_dir / name).exists(), name
