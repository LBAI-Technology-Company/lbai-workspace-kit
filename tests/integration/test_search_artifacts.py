"""Integration tests for search_artifacts.py."""
from __future__ import annotations

import json

import pytest

from tests.helpers.tool_runner import enrichment_path, run_tool

pytestmark = pytest.mark.integration


def _seed_evidence(isolated_workspace, fixtures):
    enrich = enrichment_path(fixtures, 'evidence_valid.json')
    run_tool(
        isolated_workspace,
        'add_evidence.py',
        '--enrichment',
        str(enrich),
        '--no-sync',
        '--content',
        'search fixture evidence about feedback taxonomy',
    )


class TestSearchArtifacts:
    def test_print_catalog(self, isolated_workspace, fixtures):
        _seed_evidence(isolated_workspace, fixtures)
        result = run_tool(isolated_workspace, 'search_artifacts.py', '--print-catalog')
        assert result.returncode == 0, result.output
        data = json.loads(result.stdout)
        assert data['schema_version'] == 'search_catalog_v1'
        assert isinstance(data['artifacts'], list)
        assert any('evidence' in a['path'] for a in data['artifacts'])

    def test_search_found(self, isolated_workspace, fixtures, write_fixture):
        _seed_evidence(isolated_workspace, fixtures)
        catalog = json.loads(
            run_tool(isolated_workspace, 'search_artifacts.py', '--print-catalog').stdout
        )
        evidence_paths = [a['path'] for a in catalog['artifacts'] if a['type'] == 'evidence']
        assert evidence_paths
        enrichment = {
            'schema_version': 'search_enrichment_v1',
            'query': '反馈分类',
            'query_interpretation': '查找与反馈分类相关的 evidence',
            'result_status': 'FOUND',
            'matches': [
                {
                    'path': evidence_paths[0],
                    'match_reason': 'brief 提到反馈分类标准',
                    'suggested_use': '作为周报任务输入',
                    'preview': '分类标准讨论',
                }
            ],
            'next_step': '可在 new-task 时引用该 evidence',
        }
        path = write_fixture('search_found.json', enrichment)
        result = run_tool(isolated_workspace, 'search_artifacts.py', '--enrichment', str(path))
        assert result.returncode == 0, result.output
        assert 'artifact 查询结果：FOUND' in result.stdout
        assert evidence_paths[0] in result.stdout

    def test_search_no_match(self, isolated_workspace, write_fixture):
        enrichment = {
            'schema_version': 'search_enrichment_v1',
            'query': '不存在的主题 xyz',
            'result_status': 'NO_MATCH',
            'matches': [],
            'next_step': '改用 add-evidence 录入新材料',
        }
        path = write_fixture('search_no_match.json', enrichment)
        result = run_tool(isolated_workspace, 'search_artifacts.py', '--enrichment', str(path))
        assert result.returncode == 0, result.output
        assert 'NO_MATCH' in result.stdout

    def test_invalid_path_blocked(self, isolated_workspace, write_fixture):
        enrichment = {
            'schema_version': 'search_enrichment_v1',
            'query': 'test',
            'result_status': 'FOUND',
            'matches': [
                {
                    'path': 'tasks/nonexistent_task',
                    'match_reason': 'x',
                    'suggested_use': 'x',
                    'preview': 'x',
                }
            ],
            'next_step': 'x',
        }
        path = write_fixture('search_bad_path.json', enrichment)
        result = run_tool(isolated_workspace, 'search_artifacts.py', '--enrichment', str(path))
        assert result.returncode != 0
        assert 'BLOCKED' in result.stdout
