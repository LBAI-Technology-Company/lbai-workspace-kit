"""Integration tests for prepare_execute_task.py."""
from __future__ import annotations

import pytest

from tests.helpers.tool_runner import enrichment_path, parse_task_folder, run_tool

pytestmark = pytest.mark.integration


class TestPrepareExecuteTask:
    def test_writes_execution_plan_for_open_task(self, isolated_workspace, fixtures):
        created = run_tool(
            isolated_workspace,
            'new_task.py',
            '--enrichment',
            str(enrichment_path(fixtures, 'task_intake_open.json')),
        )
        task_rel = parse_task_folder(created.stdout)
        result = run_tool(isolated_workspace, 'prepare_execute_task.py', task_rel)
        assert result.returncode == 0, result.output
        assert 'execute_status: READY' in result.stdout
        assert 'execution_plan:' in result.stdout

        plan = isolated_workspace / task_rel / 'execution_plan.md'
        assert plan.exists()
        text = plan.read_text(encoding='utf-8')
        assert '## artifacts_to_read' in text
        assert '## task_output_sections' in text

    def test_blocks_when_missing_inputs_remain(self, isolated_workspace, fixtures):
        created = run_tool(
            isolated_workspace,
            'new_task.py',
            '--enrichment',
            str(enrichment_path(fixtures, 'task_intake_blocked.json')),
        )
        task_rel = parse_task_folder(created.stdout)
        result = run_tool(isolated_workspace, 'prepare_execute_task.py', task_rel)
        assert result.returncode != 0
        assert 'execute_status: BLOCKED' in result.stdout
        assert '/lbai-add-evidence' in result.stdout
