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
        assert 'task_output_sections' in result.stdout
        assert 'task_output.md' in result.stdout

        plan = isolated_workspace / task_rel / 'execution_plan.md'
        assert plan.exists()
        text = plan.read_text(encoding='utf-8')
        assert '## artifacts_to_read' in text
        assert '## task_output_sections' in text
        assert not (isolated_workspace / task_rel / 'retrieved_context.md').exists()

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
        assert '对话框补充' in result.stdout

    def test_chat_clarifications_can_resolve_missing_inputs(self, isolated_workspace, fixtures):
        created = run_tool(
            isolated_workspace,
            'new_task.py',
            '--enrichment',
            str(enrichment_path(fixtures, 'task_intake_blocked.json')),
        )
        task_rel = parse_task_folder(created.stdout)

        first = run_tool(
            isolated_workspace,
            'archive_input.py',
            task_rel,
            '--resolves',
            '客户名单确认',
            '--content',
            '客户名单已确认：A 公司、B 公司。',
        )
        assert first.returncode == 0, first.output
        assert 'STATUS BLOCKED' in first.stdout

        second = run_tool(
            isolated_workspace,
            'archive_input.py',
            task_rel,
            '--resolves',
            '完整访谈转写文本',
            '--content',
            '访谈转写文本：客户提到交付节奏、培训和售后响应。',
        )
        assert second.returncode == 0, second.output
        assert 'STATUS OPEN' in second.stdout

        result = run_tool(isolated_workspace, 'prepare_execute_task.py', task_rel)
        assert result.returncode == 0, result.output
        assert 'execute_status: READY' in result.stdout

    def test_chat_input_without_resolves_does_not_clear_missing_inputs(self, isolated_workspace, fixtures):
        created = run_tool(
            isolated_workspace,
            'new_task.py',
            '--enrichment',
            str(enrichment_path(fixtures, 'task_intake_blocked.json')),
        )
        task_rel = parse_task_folder(created.stdout)
        saved = run_tool(
            isolated_workspace,
            'archive_input.py',
            task_rel,
            '--content',
            '访谈转写文本的风格先保持简洁。',
        )
        assert saved.returncode == 0, saved.output
        assert 'STATUS BLOCKED' in saved.stdout

        result = run_tool(isolated_workspace, 'prepare_execute_task.py', task_rel)
        assert result.returncode != 0
        assert 'execute_status: BLOCKED' in result.stdout
