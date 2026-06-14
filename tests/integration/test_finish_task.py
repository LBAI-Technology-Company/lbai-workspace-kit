"""Integration tests for finish_task.py."""
from __future__ import annotations

import pytest

from tests.helpers.tool_runner import enrichment_path, parse_task_folder, run_tool

pytestmark = pytest.mark.integration


def _create_ready_task(isolated_workspace, fixtures) -> str:
    enrich = enrichment_path(fixtures, 'task_intake_open.json')
    created = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
    assert created.returncode == 0, created.output
    task_rel = parse_task_folder(created.stdout)
    task_dir = isolated_workspace / task_rel
    (task_dir / 'task_output.md').write_text(
        '# Task Output\n\n## summary\n完成用户反馈周报摘要。\n\n## categories\n- 功能问题\n- 体验问题\n- 文档问题\n\n## next_steps\n- 跟进 top3 问题\n',
        encoding='utf-8',
    )
    return task_rel


class TestFinishTask:
    def test_approve_finish_writes_review_artifacts(self, isolated_workspace, fixtures):
        task_rel = _create_ready_task(isolated_workspace, fixtures)
        enrich = enrichment_path(fixtures, 'finish_approve.json')
        result = run_tool(isolated_workspace, 'finish_task.py', task_rel, '--enrichment', str(enrich))
        # git sync may block without remote; artifacts should still be written
        task_dir = isolated_workspace / task_rel
        assert (task_dir / 'finish_review.md').exists()
        assert (task_dir / 'finish_review_enrichment.json').exists()
        review = (task_dir / 'finish_review.md').read_text(encoding='utf-8')
        assert 'APPROVE_FINISH' in review
        assert '结果：' in result.stdout
        assert '下一步：' in result.stdout
        assert 'task_status:' in result.stdout
        assert 'commit_readiness:' in result.stdout

    def test_block_finish_forces_blocked_readiness(self, isolated_workspace, fixtures):
        task_rel = _create_ready_task(isolated_workspace, fixtures)
        enrich = enrichment_path(fixtures, 'finish_block.json')
        result = run_tool(isolated_workspace, 'finish_task.py', task_rel, '--enrichment', str(enrich))
        assert 'commit_readiness: BLOCKED' in result.stdout
        ledger = (task_dir := isolated_workspace / task_rel) / 'task_ledger.md'
        assert 'BLOCKED' in ledger.read_text(encoding='utf-8') or 'commit_readiness' in ledger.read_text(encoding='utf-8')

    def test_non_task_changes_warn_but_do_not_block_commit_readiness(self, isolated_workspace, fixtures):
        task_rel = _create_ready_task(isolated_workspace, fixtures)
        extra = isolated_workspace / 'role_workspace' / 'knowledge' / 'evidence' / 'manual_test' / 'raw.md'
        extra.parent.mkdir(parents=True, exist_ok=True)
        extra.write_text('manual evidence that should be synced separately', encoding='utf-8')

        enrich = enrichment_path(fixtures, 'finish_approve.json')
        result = run_tool(isolated_workspace, 'finish_task.py', task_rel, '--enrichment', str(enrich))

        assert result.returncode != 0
        assert 'commit_readiness: READY' in result.stdout
        assert 'manual_test/raw.md' in result.stdout
        assert '仅提示，不阻断' in result.stdout

    def test_invalid_task_folder(self, isolated_workspace, fixtures):
        enrich = enrichment_path(fixtures, 'finish_approve.json')
        result = run_tool(isolated_workspace, 'finish_task.py', 'tasks/not_a_real_task', '--enrichment', str(enrich))
        assert result.returncode != 0
        assert 'BLOCKED' in result.stdout
