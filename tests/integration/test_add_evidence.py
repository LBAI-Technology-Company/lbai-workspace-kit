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
        assert 'EVIDENCE_FOLDER role_workspace/knowledge/evidence/' in result.stdout
        assert 'evidence_status: CAPTURED' in result.stdout
        assert 'employee_user_name: 王小明' in result.stdout
        assert 'employee_position: 内容助理' in result.stdout
        assert 'source_type: meeting_note' in result.stdout
        assert '未同步 GitHub' in result.stdout

        folder_line = next(line for line in result.stdout.splitlines() if line.startswith('EVIDENCE_FOLDER'))
        rel = folder_line.split(' ', 1)[1].strip()
        evidence_dir = isolated_workspace / rel
        assert (evidence_dir / 'raw.md').exists()
        assert (evidence_dir / 'metadata.json').exists()
        assert (evidence_dir / 'evidence_enrichment.json').exists()
        metadata = (evidence_dir / 'metadata.json').read_text(encoding='utf-8')
        assert '"employee_user_name": "王小明"' in metadata
        assert '"employee_position": "内容助理"' in metadata
        assert '"backend_ingestion_status": "PENDING_GITHUB_SYNC"' in metadata
        assert not (evidence_dir / 'evidence_brief.md').exists()

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

    def test_updates_ledger(self, isolated_workspace, fixtures):
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
        ledger = (isolated_workspace / 'role_workspace' / 'ledgers' / 'EVIDENCE_LEDGER_v1.md').read_text(encoding='utf-8')
        assert 'Employee User Name' in ledger
        assert 'Employee Position' in ledger
        assert 'Source Type' in ledger
        assert 'meeting_note' in ledger
        assert '|' in ledger

    def test_legacy_ledger_rows_are_preserved_during_migration(self, isolated_workspace, fixtures):
        ledger_path = isolated_workspace / 'role_workspace' / 'ledgers' / 'EVIDENCE_LEDGER_v1.md'
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        ledger_path.write_text(
            '# EVIDENCE_LEDGER_v1\n\n'
            '| Date | Evidence ID | Source Kind | Usage Intent | Linked Task | Covers Gaps | Status | Sync Status | Next Step |\n'
            '|---|---|---|---|---|---|---|---|---|\n'
            '| 2026-06-01 | legacy_evidence | transcript | reference | None | None | CAPTURED | SYNCED | Keep legacy row |\n',
            encoding='utf-8',
        )
        enrich = enrichment_path(fixtures, 'evidence_valid.json')
        result = run_tool(
            isolated_workspace,
            'add_evidence.py',
            '--enrichment',
            str(enrich),
            '--no-sync',
            '--content',
            'new ledger migration content',
        )
        assert result.returncode == 0, result.output
        ledger = ledger_path.read_text(encoding='utf-8')
        assert 'legacy_evidence' in ledger
        assert 'Keep legacy row' in ledger
        assert 'Employee User ID' in ledger
        assert 'meeting_note' in ledger

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

    def test_unrelated_changes_do_not_block_no_sync_capture(self, isolated_workspace, fixtures):
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

        assert result.returncode == 0, result.output
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
        folder_line = next(line for line in result.stdout.splitlines() if line.startswith('EVIDENCE_FOLDER'))
        rel = folder_line.split(' ', 1)[1].strip()
        metadata = json.loads((isolated_workspace / rel / 'metadata.json').read_text(encoding='utf-8'))
        assert metadata['source_occurred_at'] == '2026-06-15'
