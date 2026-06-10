"""Integration tests for add_evidence.py."""
from __future__ import annotations

import pytest

from tests.helpers.tool_runner import enrichment_path, run_tool

pytestmark = pytest.mark.integration


class TestAddEvidence:
    def test_captures_evidence_with_valid_enrichment(self, isolated_workspace, fixtures):
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
        assert 'source_kind: transcript' in result.stdout

        folder_line = next(line for line in result.stdout.splitlines() if line.startswith('EVIDENCE_FOLDER'))
        rel = folder_line.split(' ', 1)[1].strip()
        evidence_dir = isolated_workspace / rel
        assert (evidence_dir / 'input.md').exists()
        assert (evidence_dir / 'evidence_brief.md').exists()
        assert (evidence_dir / 'evidence_metadata.md').exists()
        assert (evidence_dir / 'evidence_enrichment.json').exists()

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

    def test_missing_practical_next_step_blocked(self, isolated_workspace, fixtures):
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
        assert 'practical_next_step' in result.stdout

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
        assert 'transcript' in ledger
        assert '|' in ledger
