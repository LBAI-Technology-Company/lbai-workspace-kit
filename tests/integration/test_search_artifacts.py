"""Integration tests for backend-only search_artifacts.py."""
from __future__ import annotations

import json

import pytest

from tests.helpers.backend_server import backend_search_server
from tests.helpers.tool_runner import enrichment_path, run_tool, write_backend_auth

pytestmark = pytest.mark.integration


def write_backend_config(workspace, base_url: str, *, enabled: bool = True):
    config_path = workspace / '.lbai' / 'workspace.json'
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                'employee_identity': {'employee_user_id': 'employee-test'},
                'knowledge_service': {
                    'enabled': enabled,
                    'base_url': base_url,
                    'api_key_header': 'X-LBAI-API-Key',
                    'workspace_repo_id': 'test-workspace',
                    'search_timeout_seconds': 2,
                },
            },
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )


def write_query_plan(write_fixture, name: str = 'backend_query_plan.json'):
    query_plan = {
        'schema_version': 'backend_search_query_plan_v1',
        'query': 'feedback taxonomy',
        'keywords': ['feedback', 'taxonomy'],
        'concepts': [],
        'entity_types': ['evidence'],
        'prefer_status': ['confirmed'],
        'limit': 5,
    }
    return write_fixture(name, query_plan)


class TestSearchArtifacts:
    def test_backend_found_is_rendered_directly(self, isolated_workspace, write_fixture):
        payload = {
            'schema_version': 'knowledge_search_response_v1',
            'status': 'FOUND',
            'results': [
                {
                    'concept_uid': 'kn_feedback',
                    'concept_id': 'references/feedback',
                    'type': 'Reference',
                    'title': '用户反馈分类',
                    'description': '客户反馈分类知识',
                    'facts': [{'statement': '反馈分为登录、导出、文档三类。'}],
                    'source': {'repo_id': 'repo', 'path': 'role_workspace/knowledge/references/feedback.md', 'commit_sha': 'abc'},
                    'reason': 'backend semantic match',
                    'score': 0.9,
                }
            ],
            'trace': {},
            'diagnostics': [],
        }
        with backend_search_server(payload) as (base_url, requests):
            write_backend_config(isolated_workspace, base_url)
            write_backend_auth(isolated_workspace)
            result = run_tool(isolated_workspace, 'search_artifacts.py', '--enrichment', str(write_query_plan(write_fixture)))

        assert result.returncode == 0, result.output
        assert 'artifact 查询结果：FOUND' in result.stdout
        assert 'source: backend' in result.stdout
        assert 'kn_feedback' in result.stdout
        assert '用户反馈分类' in result.stdout
        assert requests and requests[0]['path'] == '/v1/knowledge/search'
        headers = {key.lower(): value for key, value in requests[0]['headers'].items()}
        assert headers.get('x-lbai-api-key') == 'test_backend_api_key'
        assert requests[0]['body']['query'] == 'feedback taxonomy'

    def test_backend_no_match_is_rendered_directly(self, isolated_workspace, write_fixture):
        payload = {
            'schema_version': 'knowledge_search_response_v1',
            'status': 'NO_MATCH',
            'results': [],
            'trace': {},
            'diagnostics': [],
        }
        with backend_search_server(payload) as (base_url, _requests):
            write_backend_config(isolated_workspace, base_url)
            write_backend_auth(isolated_workspace)
            result = run_tool(isolated_workspace, 'search_artifacts.py', '--enrichment', str(write_query_plan(write_fixture, 'no_match_plan.json')))

        assert result.returncode == 0, result.output
        assert 'artifact 查询结果：NO_MATCH' in result.stdout
        assert 'matches:\n- None' in result.stdout
        assert '可补充或调整 OKF 概念' in result.stdout

    def test_disabled_backend_renders_error_without_local_fallback(self, isolated_workspace, fixtures, write_fixture):
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
        write_backend_config(isolated_workspace, '', enabled=False)

        result = run_tool(isolated_workspace, 'search_artifacts.py', '--enrichment', str(write_query_plan(write_fixture, 'disabled_plan.json')))

        assert result.returncode == 0
        assert 'artifact 查询结果：ERROR' in result.stdout
        assert 'knowledge_service.disabled' in result.stdout
        assert 'search fixture evidence' not in result.stdout
        assert 'local_fallback' not in result.stdout

    def test_backend_request_error_is_rendered(self, isolated_workspace, write_fixture):
        write_backend_config(isolated_workspace, 'http://127.0.0.1:1')
        write_backend_auth(isolated_workspace)

        result = run_tool(isolated_workspace, 'search_artifacts.py', '--enrichment', str(write_query_plan(write_fixture, 'error_plan.json')))

        assert result.returncode == 0
        assert 'artifact 查询结果：ERROR' in result.stdout
        assert 'backend_error:' in result.stdout
        assert 'local_fallback' not in result.stdout

    def test_backend_error_status_is_rendered(self, isolated_workspace, write_fixture):
        payload = {
            'schema_version': 'knowledge_search_response_v1',
            'status': 'ERROR',
            'results': [],
            'trace': {},
            'diagnostics': [],
            'error': 'INDEX_REBUILDING',
        }
        with backend_search_server(payload) as (base_url, _requests):
            write_backend_config(isolated_workspace, base_url)
            write_backend_auth(isolated_workspace)
            result = run_tool(isolated_workspace, 'search_artifacts.py', '--enrichment', str(write_query_plan(write_fixture, 'backend_error_status_plan.json')))

        assert result.returncode == 0
        assert 'artifact 查询结果：ERROR' in result.stdout
        assert 'INDEX_REBUILDING' in result.stdout

    def test_invalid_backend_response_is_rendered(self, isolated_workspace, write_fixture):
        with backend_search_server({'schema_version': 'wrong'}) as (base_url, _requests):
            write_backend_config(isolated_workspace, base_url)
            write_backend_auth(isolated_workspace)
            result = run_tool(isolated_workspace, 'search_artifacts.py', '--enrichment', str(write_query_plan(write_fixture, 'invalid_backend_response_plan.json')))

        assert result.returncode == 0
        assert 'artifact 查询结果：ERROR' in result.stdout
        assert 'backend_error:' in result.stdout

    def test_invalid_query_plan_blocks(self, isolated_workspace, write_fixture):
        path = write_fixture('invalid_backend_query_plan.json', {'schema_version': 'backend_search_query_plan_v1'})

        result = run_tool(isolated_workspace, 'search_artifacts.py', '--enrichment', str(path))

        assert result.returncode != 0
        assert 'artifact 查询结果：BLOCKED' in result.stdout
        assert 'query' in result.stdout

    def test_print_catalog_is_not_supported(self, isolated_workspace):
        result = run_tool(isolated_workspace, 'search_artifacts.py', '--print-catalog')

        assert result.returncode != 0
        assert 'search_catalog_v1' not in result.stdout
