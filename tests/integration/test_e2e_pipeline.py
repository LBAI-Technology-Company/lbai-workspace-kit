"""End-to-end pipeline across init → task → evidence → search → finish."""
from __future__ import annotations

import json

import pytest

from tests.helpers.tool_runner import enrichment_path, parse_task_folder, run_tool

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

        # 3. add evidence linked to task
        linked = dict(load_json(fixtures, 'evidence_task_linked.json'))
        linked_path = write_fixture('pipeline_linked_evidence.json', linked)
        ev_result = run_tool(
            isolated_workspace,
            'add_evidence.py',
            task_rel,
            '--enrichment',
            str(linked_path),
            '--no-sync',
            '--content',
            '用户反馈样本：登录慢、文档缺失、导出失败。',
        )
        assert ev_result.returncode == 0, ev_result.output
        assert f'linked_task: {task_rel}' in ev_result.stdout

        # 4. search catalog includes new evidence
        catalog = json.loads(run_tool(isolated_workspace, 'search_artifacts.py', '--print-catalog').stdout)
        paths = [a['path'] for a in catalog['artifacts']]
        assert any('knowledge/evidence' in p for p in paths)

        folder_line = next(line for line in ev_result.stdout.splitlines() if line.startswith('EVIDENCE_FOLDER'))
        evidence_path_str = folder_line.split(' ', 1)[1].strip()
        search_enrichment = {
            'schema_version': 'search_enrichment_v1',
            'query': '用户反馈',
            'result_status': 'FOUND',
            'matches': [
                {
                    'path': evidence_path_str,
                    'match_reason': '刚录入的反馈 evidence',
                    'suggested_use': '继续执行任务',
                    'preview': '登录慢、文档缺失',
                }
            ],
            'next_step': 'execute task',
        }
        search_path = write_fixture('pipeline_search.json', search_enrichment)
        search_result = run_tool(isolated_workspace, 'search_artifacts.py', '--enrichment', str(search_path))
        assert search_result.returncode == 0, search_result.output
        assert 'FOUND' in search_result.stdout

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
