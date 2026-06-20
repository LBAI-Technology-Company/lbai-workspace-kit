"""End-to-end pipeline across init → task → evidence → search → finish."""
from __future__ import annotations

import json

import pytest

from tests.helpers.backend_server import backend_search_server
from tests.helpers.tool_runner import enrichment_path, parse_task_folder, run_tool, write_backend_auth

pytestmark = pytest.mark.e2e


class TestFullPipeline:
    def test_init_new_task_evidence_search_finish(self, isolated_workspace, fixtures, write_fixture):
        # 1. init role
        init_result = run_tool(
            isolated_workspace,
            'init_lbai.py',
            '--enrichment',
            str(enrichment_path(fixtures, 'init_valid.json')),
        )
        assert init_result.returncode == 0, init_result.output

        # 2. new task (blocked — missing inputs)
        blocked_intake = dict(load_json(fixtures, 'task_intake_blocked.json'))
        blocked_path = write_fixture('pipeline_blocked_intake.json', blocked_intake)
        task_result = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(blocked_path))
        assert task_result.returncode == 0, task_result.output
        assert 'STATUS BLOCKED' in task_result.stdout
        task_rel = parse_task_folder(task_result.stdout)

        # 3. add an independent OKF knowledge concept
        knowledge_metadata = dict(load_json(fixtures, 'evidence_task_independent.json'))
        metadata_path = write_fixture('pipeline_knowledge_metadata.json', knowledge_metadata)
        ev_result = run_tool(
            isolated_workspace,
            'add_evidence.py',
            '--enrichment',
            str(metadata_path),
            '--no-sync',
            '--content',
            '用户反馈样本：登录慢、文档缺失、导出失败。',
        )
        assert ev_result.returncode == 0, ev_result.output
        assert 'linked_task:' not in ev_result.stdout

        # 4. search backend returns context
        config_path = isolated_workspace / '.lbai' / 'workspace.json'
        query_plan = {
            'schema_version': 'backend_search_query_plan_v1',
            'query': '用户反馈',
            'keywords': ['用户反馈'],
            'entity_types': ['evidence'],
            'limit': 5,
        }
        search_path = write_fixture('pipeline_search.json', query_plan)
        payload = {
            'schema_version': 'knowledge_search_response_v1',
            'status': 'FOUND',
            'results': [
                {
                    'concept_uid': 'kn_pipeline_feedback',
                    'concept_id': 'references/pipeline-feedback',
                    'type': 'Reference',
                    'title': '用户反馈样本',
                    'description': '用户反馈样本',
                    'facts': [{'statement': '登录慢、文档缺失、导出失败。'}],
                    'source': {'repo_id': 'repo', 'path': 'role_workspace/knowledge/references/pipeline-feedback.md', 'commit_sha': 'abc'},
                    'reason': 'backend matched linked evidence',
                    'score': 0.9,
                }
            ],
            'trace': {},
            'diagnostics': [],
        }
        with backend_search_server(payload) as (base_url, _requests):
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                json.dumps(
                    {
                        'employee_identity': {'employee_user_id': 'employee-test'},
                        'knowledge_service': {
                            'enabled': True,
                            'base_url': base_url,
                            'workspace_repo_id': 'test-workspace',
                            'search_timeout_seconds': 2,
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding='utf-8',
            )
            write_backend_auth(isolated_workspace)
            search_result = run_tool(isolated_workspace, 'search_artifacts.py', '--enrichment', str(search_path))
        assert search_result.returncode == 0, search_result.output
        assert 'artifact 查询结果：FOUND' in search_result.stdout

        # 5. simulate execute — write output
        task_dir = isolated_workspace / task_rel
        (task_dir / 'task_output.md').write_text(
            '# Task Output\n\n## summary\n汇总 Q2 访谈与反馈样本。\n',
            encoding='utf-8',
        )

        # 6. finish with approve
        finish_result = run_tool(
            isolated_workspace,
            'finish_task.py',
            task_rel,
            '--enrichment',
            str(enrichment_path(fixtures, 'finish_approve.json')),
        )
        assert (task_dir / 'finish_review.md').exists()
        assert 'task_status:' in finish_result.stdout


def load_json(fixtures, name: str) -> dict:
    return json.loads((fixtures / 'enrichments' / name).read_text(encoding='utf-8'))
