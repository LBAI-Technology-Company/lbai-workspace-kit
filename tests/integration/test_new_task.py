"""Integration tests for new_task.py."""
from __future__ import annotations

import json

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
        assert '## known_information' in scope
        assert 'conversation_context' in scope
        assert '## recommended_inputs' in scope
        assert (task_dir / 'recommended_inputs.md').exists()
        assert not (task_dir / 'retrieved_context.md').exists()

    def test_blocked_task_with_missing_inputs(self, isolated_workspace, fixtures):
        enrich = enrichment_path(fixtures, 'task_intake_blocked.json')
        result = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
        assert result.returncode == 0, result.output
        assert 'STATUS BLOCKED' in result.stdout
        assert 'MISSING' in result.stdout
        assert '对话框补充' in result.stdout
        task_rel = parse_task_folder(result.stdout)
        assert (isolated_workspace / task_rel / 'missing_inputs.md').exists()
        assert (isolated_workspace / task_rel / 'recommended_inputs.md').exists()
        assert not (isolated_workspace / task_rel / 'retrieved_context.md').exists()

    def test_duplicate_task_name_gets_new_folder(self, isolated_workspace, fixtures):
        enrich = enrichment_path(fixtures, 'task_intake_open.json')
        first = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
        second = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
        assert first.returncode == 0, first.output
        assert second.returncode == 0, second.output
        assert parse_task_folder(first.stdout) != parse_task_folder(second.stdout)

    def test_review_task_creates_review_files(self, isolated_workspace, fixtures):
        enrich = enrichment_path(fixtures, 'task_intake_review.json')
        result = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
        assert result.returncode == 0, result.output
        assert 'REVIEW_NEEDED true' in result.stdout
        task_rel = parse_task_folder(result.stdout)
        task_dir = isolated_workspace / task_rel
        for name in ('overclaim_check.md', 'release_boundary_check.md', 'founder_review_needed.md'):
            assert (task_dir / name).exists(), name

    def test_sensitive_known_information_is_redacted_before_write(self, isolated_workspace, fixtures):
        data = json.loads(enrichment_path(fixtures, 'task_intake_open.json').read_text(encoding='utf-8'))
        data['known_information'] = [
            {
                'summary': '客户邮箱 test@example.com，电话 13800138000',
                'source_kind': 'conversation_context',
                'source_ref': 'employee said test@example.com',
            }
        ]
        enrich = isolated_workspace / 'sensitive_task_intake.json'
        enrich.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

        result = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
        assert result.returncode == 0, result.output
        assert 'SENSITIVE_CAPTURE_STATUS REDACTED' in result.stdout
        task_rel = parse_task_folder(result.stdout)
        task_dir = isolated_workspace / task_rel
        combined = '\n'.join(
            (task_dir / name).read_text(encoding='utf-8')
            for name in ('task_scope.md', 'task_ledger.md', 'task_intake_enrichment.json')
        )
        assert 'test@example.com' not in combined
        assert '13800138000' not in combined
        assert '[SENSITIVE INFORMATION REDACTED - USE APPROVED SECURE CHANNEL]' in combined

    def test_review_reasons_auto_enable_review_needed(self, isolated_workspace, fixtures):
        data = json.loads(enrichment_path(fixtures, 'task_intake_review.json').read_text(encoding='utf-8'))
        data['review_needed'] = False
        enrich = isolated_workspace / 'review_conflict.json'
        enrich.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

        result = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
        assert result.returncode == 0, result.output
        assert 'REVIEW_NEEDED true' in result.stdout

    def test_placeholder_review_reason_does_not_block_internal_task(self, isolated_workspace, fixtures):
        data = json.loads(enrichment_path(fixtures, 'task_intake_open.json').read_text(encoding='utf-8'))
        data['review_reasons'] = ['无']
        enrich = isolated_workspace / 'placeholder_review_reason.json'
        enrich.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

        result = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
        assert result.returncode == 0, result.output
        assert 'REVIEW_NEEDED false' in result.stdout

    def test_required_task_fields_must_not_be_blank(self, isolated_workspace, fixtures):
        data = json.loads(enrichment_path(fixtures, 'task_intake_open.json').read_text(encoding='utf-8'))
        data['goal'] = '   '
        data['expected_output'] = '   '
        data['completion_conditions'] = []
        enrich = isolated_workspace / 'blank_required_fields.json'
        enrich.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

        result = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
        assert result.returncode == 2
        assert 'validation failed' in result.stdout or 'must be non-empty' in result.stdout
        assert not list((isolated_workspace / 'tasks').glob('*/task_scope.md'))

    def test_positional_description_must_match_enrichment(self, isolated_workspace, fixtures):
        enrich = enrichment_path(fixtures, 'task_intake_open.json')
        result = run_tool(isolated_workspace, 'new_task.py', '另一个任务', '--enrichment', str(enrich))
        assert result.returncode == 2
        assert 'does not match enrichment task_description' in result.stdout
        assert not list((isolated_workspace / 'tasks').glob('*/task_scope.md'))

    def test_company_process_writing_requires_source_and_audience(self, isolated_workspace, fixtures):
        data = json.loads(enrichment_path(fixtures, 'task_intake_open.json').read_text(encoding='utf-8'))
        data.update({
            'task_description': '写一篇短文介绍我公司的工作方法流程',
            'goal': '写一篇介绍公司工作方法流程的短文',
            'expected_output': 'task_output.md 包含一篇短文',
            'known_information': [
                {
                    'summary': '员工想写一篇短文介绍公司的工作方法流程',
                    'source_kind': 'conversation_context',
                    'source_ref': 'employee task request',
                }
            ],
            'missing_inputs': [],
            'recommended_inputs': ['受众是内部同事，还是可能对外发布'],
            'status': 'OPEN',
        })
        enrich = isolated_workspace / 'company_process_writing.json'
        enrich.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

        result = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
        assert result.returncode == 0, result.output
        assert 'STATUS BLOCKED' in result.stdout
        assert 'backend_evidence_search skipped:' not in result.stdout
        assert 'backend 查询结果' not in result.stdout
        assert '请补充公司工作方法/流程的来源材料或关键要点' in result.stdout
        assert '请说明这篇短文的受众和用途' in result.stdout
        task_rel = parse_task_folder(result.stdout)
        task_dir = isolated_workspace / task_rel
        missing = (task_dir / 'missing_inputs.md').read_text(encoding='utf-8')
        assert '请补充公司工作方法/流程的来源材料或关键要点' in missing
        assert '请说明这篇短文的受众和用途' in missing
