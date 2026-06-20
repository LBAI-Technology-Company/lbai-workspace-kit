"""Integration tests for add_evidence.py."""
from __future__ import annotations

import json

import pytest

from tests.helpers.tool_runner import enrichment_path, run_tool

pytestmark = pytest.mark.integration


class TestAddEvidence:
    def test_captures_evidence_with_valid_enrichment(self, isolated_workspace, fixtures):
        init_enrich = enrichment_path(fixtures, 'init_valid.json')
        init_result = run_tool(isolated_workspace, 'init_lbai.py', '--enrichment', str(init_enrich))
        assert init_result.returncode == 0, init_result.output

        enrich = enrichment_path(fixtures, 'evidence_valid.json')
        sample = fixtures / 'samples' / 'transcript_sample.md'
        content = sample.read_text(encoding='utf-8')
        result = run_tool(
            isolated_workspace,
            'add_evidence.py',
            '--enrichment',
            str(enrich),
            '--no-sync',
            '--content',
            content,
        )
        assert result.returncode == 0, result.output
        assert 'OKF_CONCEPT role_workspace/knowledge/references/' in result.stdout
        assert 'evidence_status: CAPTURED' in result.stdout
        assert 'employee_user_name: 王小明' in result.stdout
        assert 'employee_position: 内容助理' in result.stdout
        assert 'source_type: meeting_note' in result.stdout
        assert '未同步 GitHub' in result.stdout

        concept_line = next(line for line in result.stdout.splitlines() if line.startswith('OKF_CONCEPT'))
        rel = concept_line.split(' ', 1)[1].strip()
        concept = isolated_workspace / rel
        assert concept.exists()
        text = concept.read_text(encoding='utf-8')
        assert 'type: Reference' in text
        assert 'visibility: "team"' in text
        assert (isolated_workspace / 'role_workspace/knowledge/index.md').exists()
        assert (isolated_workspace / 'role_workspace/knowledge/log.md').exists()

    def test_ai_needs_review_status(self, isolated_workspace, fixtures):
        enrich = enrichment_path(fixtures, 'evidence_needs_review.json')
        result = run_tool(
            isolated_workspace,
            'add_evidence.py',
            '--enrichment',
            str(enrich),
            '--no-sync',
            '--content',
            '官网首页定价说明草稿',
        )
        assert result.returncode == 0, result.output
        assert 'evidence_status: NEEDS_REVIEW' in result.stdout
        concept_line = next(
            line for line in result.stdout.splitlines() if line.startswith('OKF_CONCEPT')
        )
        concept = isolated_workspace / concept_line.split(' ', 1)[1]
        assert 'status: draft' in concept.read_text(encoding='utf-8')

    def test_no_keyword_overlay_when_ai_captured(self, isolated_workspace, fixtures):
        """AI CAPTURED must not be upgraded by legacy keyword rules (e.g. 财务的对接)."""
        enrich = enrichment_path(fixtures, 'evidence_internal_finance_workstream.json')
        result = run_tool(
            isolated_workspace,
            'add_evidence.py',
            '--enrichment',
            str(enrich),
            '--no-sync',
            '--content',
            '并行推进产品迭代与财务的对接',
        )
        assert result.returncode == 0, result.output
        assert 'evidence_status: CAPTURED' in result.stdout
        assert 'NEEDS_REVIEW' not in result.stdout.split('evidence_status:')[1].split('\n')[0]

    def test_invalid_enrichment_blocked(self, isolated_workspace, fixtures):
        enrich = enrichment_path(fixtures, 'evidence_invalid_schema.json')
        result = run_tool(
            isolated_workspace,
            'add_evidence.py',
            '--enrichment',
            str(enrich),
            '--no-sync',
            '--content',
            'test',
        )
        assert result.returncode != 0
        assert 'BLOCKED' in result.stdout

    def test_missing_required_metadata_blocked(self, isolated_workspace, fixtures):
        enrich = enrichment_path(fixtures, 'evidence_missing_practical_next_step.json')
        result = run_tool(
            isolated_workspace,
            'add_evidence.py',
            '--enrichment',
            str(enrich),
            '--no-sync',
            '--content',
            'test',
        )
        assert result.returncode != 0
        assert 'title' in result.stdout

    def test_redacts_secrets_in_content(self, isolated_workspace, fixtures):
        enrich = enrichment_path(fixtures, 'evidence_valid.json')
        secret = 'api_key=ghp_1234567890abcdefghijklmnopqrstuvwxyz'
        result = run_tool(
            isolated_workspace,
            'add_evidence.py',
            '--enrichment',
            str(enrich),
            '--no-sync',
            '--content',
            secret,
        )
        assert result.returncode == 0, result.output
        assert 'sensitive_capture_status: REDACTED' in result.stdout

    def test_updates_okf_index_and_log(self, isolated_workspace, fixtures):
        enrich = enrichment_path(fixtures, 'evidence_valid.json')
        run_tool(
            isolated_workspace,
            'add_evidence.py',
            '--enrichment',
            str(enrich),
            '--no-sync',
            '--content',
            'ledger test content',
        )
        index = (isolated_workspace / 'role_workspace' / 'knowledge' / 'index.md').read_text(encoding='utf-8')
        log = (isolated_workspace / 'role_workspace' / 'knowledge' / 'log.md').read_text(encoding='utf-8')
        assert '用户反馈分类会议记录' in index
        assert '**Creation**' in log
        assert index.count('# References') == 1

    def test_same_content_reuses_stable_concept(self, isolated_workspace, fixtures):
        enrich = enrichment_path(fixtures, 'evidence_valid.json')
        first = run_tool(
            isolated_workspace,
            'add_evidence.py',
            '--enrichment',
            str(enrich),
            '--no-sync',
            '--content',
            'same reusable source content',
        )
        second = run_tool(
            isolated_workspace,
            'add_evidence.py',
            '--enrichment',
            str(enrich),
            '--no-sync',
            '--content',
            'same reusable source content',
        )
        first_path = next(
            line for line in first.stdout.splitlines() if line.startswith('OKF_CONCEPT')
        )
        second_path = next(
            line for line in second.stdout.splitlines() if line.startswith('OKF_CONCEPT')
        )
        assert first_path == second_path
        concepts = list(
            (isolated_workspace / 'role_workspace/knowledge/references').glob('*.md')
        )
        assert len(concepts) == 1
        index = (isolated_workspace / 'role_workspace/knowledge/index.md').read_text(
            encoding='utf-8'
        )
        assert index.count('用户反馈分类会议记录') == 1

    def test_evidence_remains_independent_from_task_inputs(self, isolated_workspace, fixtures):
        task = isolated_workspace / 'tasks' / '2026_06_10_blocked'
        task.mkdir(parents=True)
        (task / 'task_scope.md').write_text('# Task Scope\n\n## status\nBLOCKED\n', encoding='utf-8')
        (task / 'task_ledger.md').write_text('# Task Ledger\n\n## status\nBLOCKED\n', encoding='utf-8')
        (task / 'missing_inputs.md').write_text('# Missing Inputs\n\n- 客户名单确认\n', encoding='utf-8')
        enrich = enrichment_path(fixtures, 'evidence_valid.json')
        result = run_tool(
            isolated_workspace,
            'add_evidence.py',
            '--enrichment',
            str(enrich),
            '--no-sync',
            '--content',
            'tasks/2026_06_10_blocked 客户反馈样本',
        )
        assert result.returncode == 0, result.output
        assert 'related_tasks:' not in result.stdout
        assert 'linked_task:' not in result.stdout
        assert '- 客户名单确认' in (task / 'missing_inputs.md').read_text(encoding='utf-8')
        assert not (task / 'gap_record.md').exists()

    def test_unrelated_changes_do_not_hide_push_failure(self, isolated_workspace, fixtures):
        unrelated = isolated_workspace / 'tasks' / 'unrelated' / 'task_output.md'
        unrelated.parent.mkdir(parents=True, exist_ok=True)
        unrelated.write_text('unrelated draft', encoding='utf-8')

        enrich = enrichment_path(fixtures, 'evidence_valid.json')
        result = run_tool(
            isolated_workspace,
            'add_evidence.py',
            '--enrichment',
            str(enrich),
            '--content',
            'new evidence with unrelated task draft in workspace',
        )

        assert result.returncode == 3
        assert 'sync_status: PUSH_FAILED' in result.stdout
        assert 'tasks/unrelated/task_output.md' in result.stdout
        assert 'evidence_status: CAPTURED' in result.stdout
        assert 'sync_status: BLOCKED' not in result.stdout
        assert '仅提示，不阻断' in result.stdout

    def test_meeting_note_infers_occurred_at_from_content_when_unknown(self, isolated_workspace, fixtures):
        enrich = enrichment_path(fixtures, 'evidence_valid.json')
        data = json.loads(enrich.read_text(encoding='utf-8'))
        data['source_occurred_at'] = 'unknown'
        data['source_type'] = 'meeting_note'
        data['title'] = '产品周会 Mock 会议记录'
        enrich_path = isolated_workspace / 'meeting_unknown_date.json'
        enrich_path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

        result = run_tool(
            isolated_workspace,
            'add_evidence.py',
            '--enrichment',
            str(enrich_path),
            '--no-sync',
            '--content',
            '【Mock 会议记录】\n时间：2026-06-15 10:00-11:00\n决议：输出导出优化方案',
        )

        assert result.returncode == 0, result.output
        concept_line = next(line for line in result.stdout.splitlines() if line.startswith('OKF_CONCEPT'))
        rel = concept_line.split(' ', 1)[1].strip()
        concept_text = (isolated_workspace / rel).read_text(encoding='utf-8')
        assert 'effective_from: "2026-06-15"' in concept_text
