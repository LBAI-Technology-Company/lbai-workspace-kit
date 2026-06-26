"""Integration tests for resolve_current_task.py and check_task_delivery.py."""
from __future__ import annotations

import pytest

from tests.helpers.tool_runner import enrichment_path, parse_task_folder, run_tool

pytestmark = pytest.mark.integration


class TestResolveCurrentTask:
    def test_finish_resolves_open_task_without_task_output(self, isolated_workspace, fixtures):
        created = run_tool(
            isolated_workspace,
            'new_task.py',
            '--enrichment',
            str(enrichment_path(fixtures, 'task_intake_open.json')),
        )
        task_rel = parse_task_folder(created.stdout)
        task_dir = isolated_workspace / task_rel
        assert not (task_dir / 'task_output.md').exists()

        result = run_tool(isolated_workspace, 'resolve_current_task.py', 'finish')
        assert result.returncode == 0, result.output
        assert 'RESOLUTION unique' in result.stdout
        assert task_rel in result.stdout
        assert '/lbai-finish-task' in result.stdout

    def test_execute_only_resolves_open_tasks(self, isolated_workspace, fixtures):
        created = run_tool(
            isolated_workspace,
            'new_task.py',
            '--enrichment',
            str(enrichment_path(fixtures, 'task_intake_open.json')),
        )
        task_rel = parse_task_folder(created.stdout)
        result = run_tool(isolated_workspace, 'resolve_current_task.py', 'execute')
        assert result.returncode == 0, result.output
        assert task_rel in result.stdout


class TestCheckTaskDelivery:
    def test_needs_auto_execute_when_task_output_missing(self, isolated_workspace, fixtures):
        created = run_tool(
            isolated_workspace,
            'new_task.py',
            '--enrichment',
            str(enrichment_path(fixtures, 'task_intake_open.json')),
        )
        task_rel = parse_task_folder(created.stdout)
        result = run_tool(isolated_workspace, 'check_task_delivery.py', task_rel)
        assert result.returncode == 0, result.output
        assert 'auto_execute_needed: true' in result.stdout
        assert 'task_output.md missing' in result.stdout

    def test_ready_when_task_output_exists(self, isolated_workspace, fixtures):
        created = run_tool(
            isolated_workspace,
            'new_task.py',
            '--enrichment',
            str(enrichment_path(fixtures, 'task_intake_open.json')),
        )
        task_rel = parse_task_folder(created.stdout)
        output = isolated_workspace / task_rel / 'task_output.md'
        output.write_text(
            '# Task Output\n\n## summary\nDeliverable with enough content to pass delivery check.\n',
            encoding='utf-8',
        )
        result = run_tool(isolated_workspace, 'check_task_delivery.py', task_rel)
        assert result.returncode == 0, result.output
        assert 'auto_execute_needed: false' in result.stdout
        assert 'delivery_status: READY' in result.stdout

    def test_blocked_when_missing_inputs_remain(self, isolated_workspace, fixtures):
        created = run_tool(
            isolated_workspace,
            'new_task.py',
            '--enrichment',
            str(enrichment_path(fixtures, 'task_intake_blocked.json')),
        )
        task_rel = parse_task_folder(created.stdout)
        result = run_tool(isolated_workspace, 'check_task_delivery.py', task_rel)
        assert result.returncode != 0
        assert 'delivery_status: BLOCKED' in result.stdout

    def test_finish_task_blocks_without_task_output(self, isolated_workspace, fixtures):
        created = run_tool(
            isolated_workspace,
            'new_task.py',
            '--enrichment',
            str(enrichment_path(fixtures, 'task_intake_open.json')),
        )
        task_rel = parse_task_folder(created.stdout)
        result = run_tool(
            isolated_workspace,
            'finish_task.py',
            task_rel,
            '--enrichment',
            str(enrichment_path(fixtures, 'finish_block.json')),
        )
        assert result.returncode != 0
        assert 'auto_execute: BLOCKED' in result.stdout
        assert 'task_output.md missing' in result.stdout
