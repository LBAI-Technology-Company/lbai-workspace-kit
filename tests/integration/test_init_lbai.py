"""Integration tests for init_lbai.py."""
from __future__ import annotations

import pytest

from tests.helpers.tool_runner import enrichment_path, run_tool

pytestmark = pytest.mark.integration


class TestInitLbai:
    def test_print_questions(self, isolated_workspace):
        result = run_tool(isolated_workspace, 'init_lbai.py', '--print-questions')
        assert result.returncode == 0
        assert '岗位名称' in result.stdout
        assert '主要职责' in result.stdout

    def test_valid_enrichment_updates_role_files(self, isolated_workspace, fixtures):
        enrich = enrichment_path(fixtures, 'init_valid.json')
        result = run_tool(isolated_workspace, 'init_lbai.py', '--enrichment', str(enrich))
        assert result.returncode == 0, result.output
        assert 'STATUS UPDATED' in result.stdout
        world = (isolated_workspace / 'role_workspace' / 'world_model' / 'ROLE_WORLD_MODEL_v1.md').read_text(encoding='utf-8')
        assert '内容助理' in world
        archive = list((isolated_workspace / 'role_workspace' / 'archive').glob('init_enrichment_*.json'))
        assert archive

    def test_missing_sections_blocked(self, isolated_workspace, fixtures):
        enrich = enrichment_path(fixtures, 'init_missing_sections.json')
        result = run_tool(isolated_workspace, 'init_lbai.py', '--enrichment', str(enrich))
        assert result.returncode != 0
        assert 'BLOCKED' in result.stdout
        assert 'missing required sections' in result.stdout
