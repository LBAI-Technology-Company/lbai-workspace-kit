from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tests.helpers.tool_runner import enrichment_path


def run_prompt_lab(workspace: Path, *args: str) -> subprocess.CompletedProcess:
    script = workspace / 'lbai_system' / 'prompt_lab' / 'prompt_lab.py'
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=workspace,
        capture_output=True,
        text=True,
    )


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def test_prompt_lab_start_creates_isolated_records_only(isolated_workspace):
    result = run_prompt_lab(
        isolated_workspace,
        'start',
        '--run-id',
        'run_test_start',
        '--rounds',
        '1',
        '--scenarios-per-round',
        '2',
    )

    assert result.returncode == 0, result.stdout + result.stderr
    run_dir = isolated_workspace / 'prompt_lab' / 'runs' / 'run_test_start'
    assert (run_dir / 'run_manifest.json').exists()
    assert (run_dir / 'round_001' / 'scenario_inputs').is_dir()
    assert (run_dir / 'workspaces' / 'round_001_workspace').is_dir()
    assert (isolated_workspace / 'prompt_lab' / 'prompt_versions' / 'current').is_dir()
    task_entries = [path.name for path in (isolated_workspace / 'tasks').iterdir()]
    assert task_entries in ([], ['.gitkeep'])
    remote = subprocess.run(
        ['git', 'remote'],
        cwd=run_dir / 'workspaces' / 'round_001_workspace',
        capture_output=True,
        text=True,
    )
    assert remote.returncode == 0
    assert remote.stdout.strip() == ''


def test_prompt_lab_scores_and_applies_patch_to_experimental_prompt_only(isolated_workspace):
    started = run_prompt_lab(isolated_workspace, 'start', '--run-id', 'run_test_apply')
    assert started.returncode == 0, started.stdout + started.stderr
    run_dir = isolated_workspace / 'prompt_lab' / 'runs' / 'run_test_apply'
    round_dir = run_dir / 'round_001'

    evaluation = {
        'schema_version': 'prompt_lab_evaluation_v1',
        'scenario_id': 'scenario_internal_report',
        'scores': {
            'schema_compliance': 5,
            'boundary_handling': 5,
            'source_grounding': 5,
            'missing_input_handling': 5,
            'task_quality': 5,
            'finish_review_accuracy': 5,
        },
        'red_flags': [],
        'issues': [],
        'prompt_improvement_candidates': ['Make source requirements more explicit.'],
    }
    write_json(round_dir / 'evaluations' / 'scenario_internal_report.json', evaluation)

    scored = run_prompt_lab(isolated_workspace, 'score', '--run', str(run_dir), '--round', '1')
    assert scored.returncode == 0, scored.stdout + scored.stderr
    assert 'overall_score: 100.0' in scored.stdout
    assert 'round_report:' in scored.stdout
    assert (round_dir / 'round_report.md').exists()

    formal_prompt = isolated_workspace / 'lbai_system' / 'prompts' / 'task_intake_enrichment_prompt_v1.md'
    formal_before = formal_prompt.read_text(encoding='utf-8')
    patch = {
        'schema_version': 'prompt_lab_prompt_patch_v1',
        'rationale': 'A high-scoring run found a clearer intake guardrail.',
        'files': [
            {
                'prompt_file': 'task_intake_enrichment_prompt_v1.md',
                'operation': 'append_rule',
                'content': 'When source material is missing for company claims, keep the task blocked.',
            }
        ],
    }
    patch_path = round_dir / 'optimizer' / 'prompt_patch.json'
    write_json(patch_path, patch)

    applied = run_prompt_lab(
        isolated_workspace,
        'apply-prompt-patch',
        '--run',
        str(run_dir),
        '--round',
        '1',
        '--patch',
        str(patch_path),
        '--threshold',
        '80',
    )

    assert applied.returncode == 0, applied.stdout + applied.stderr
    assert 'apply_status: APPLIED' in applied.stdout
    assert 'round_report:' in applied.stdout
    experimental_prompt = isolated_workspace / 'prompt_lab' / 'prompt_versions' / 'current' / 'task_intake_enrichment_prompt_v1.md'
    assert 'When source material is missing for company claims' in experimental_prompt.read_text(encoding='utf-8')
    assert formal_prompt.read_text(encoding='utf-8') == formal_before
    assert (round_dir / 'optimizer' / 'prompt_patch.diff').exists()
    assert (round_dir / 'optimizer' / 'before_after_score.json').exists()
    assert (round_dir / 'optimizer' / 'optimizer_rationale.md').exists()
    assert (round_dir / 'prompt_before_patch_snapshot' / 'task_intake_enrichment_prompt_v1.md').exists()
    assert (round_dir / 'accepted_prompt_snapshot' / 'task_intake_enrichment_prompt_v1.md').exists()
    report = (round_dir / 'round_report.md').read_text(encoding='utf-8')
    assert '## Prompt 欠缺或 AI 犯错' in report
    assert '## 怎么修改' in report
    assert '## 原始数据索引' in report
    assert '## AI 产出记录' in report

    finalized = run_prompt_lab(isolated_workspace, 'finalize', '--run', str(run_dir))
    assert finalized.returncode == 0, finalized.stdout + finalized.stderr
    assert 'finalize_status: CLEANED' in finalized.stdout
    assert not run_dir.exists()
    assert experimental_prompt.exists()


def test_prompt_lab_run_tool_forces_no_sync_for_syncing_tools(isolated_workspace):
    started = run_prompt_lab(isolated_workspace, 'start', '--run-id', 'run_test_no_sync')
    assert started.returncode == 0, started.stdout + started.stderr
    workspace = isolated_workspace / 'prompt_lab' / 'runs' / 'run_test_no_sync' / 'workspaces' / 'round_001_workspace'
    fake_tool = workspace / 'lbai_system' / 'tools' / 'add_evidence.py'
    fake_tool.write_text(
        'import sys\nprint("ARGS " + " ".join(sys.argv[1:]))\n',
        encoding='utf-8',
    )
    output = isolated_workspace / 'prompt_lab' / 'runs' / 'run_test_no_sync' / 'round_001' / 'tool_outputs' / 'fake_add_evidence.json'

    result = run_prompt_lab(
        isolated_workspace,
        'run-tool',
        '--workspace',
        str(workspace),
        '--tool',
        'add_evidence.py',
        '--output',
        str(output),
        '--',
        '--enrichment',
        'mock.json',
    )

    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(output.read_text(encoding='utf-8'))
    assert '--no-sync' in data['extra_args']
    assert '--no-sync' in data['stdout']
    assert data['extra_args'][0] != '--'


def test_prompt_lab_run_tool_strips_leading_double_dash(isolated_workspace):
    started = run_prompt_lab(isolated_workspace, 'start', '--run-id', 'run_test_strip_dash')
    assert started.returncode == 0, started.stdout + started.stderr
    workspace = isolated_workspace / 'prompt_lab' / 'runs' / 'run_test_strip_dash' / 'workspaces' / 'round_001_workspace'
    fake_tool = workspace / 'lbai_system' / 'tools' / 'new_task.py'
    fake_tool.write_text(
        'import sys\nprint("ARGS " + " ".join(sys.argv[1:]))\n',
        encoding='utf-8',
    )
    output = isolated_workspace / 'prompt_lab' / 'runs' / 'run_test_strip_dash' / 'round_001' / 'tool_outputs' / 'strip_dash.json'

    result = run_prompt_lab(
        isolated_workspace,
        'run-tool',
        '--workspace',
        str(workspace),
        '--tool',
        'new_task.py',
        '--output',
        str(output),
        '--',
        '--enrichment',
        'mock.json',
    )

    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(output.read_text(encoding='utf-8'))
    assert data['extra_args'][0] == '--enrichment'
    assert '--' not in data['extra_args']
    assert 'ARGS --enrichment mock.json' in data['stdout']


def test_prompt_lab_run_tool_rejects_employee_workspace(isolated_workspace):
    result = run_prompt_lab(
        isolated_workspace,
        'run-tool',
        '--workspace',
        str(isolated_workspace),
        '--tool',
        'new_task.py',
        '--output',
        'prompt_lab/runs/blocked.json',
        '--',
        '--enrichment',
        'mock.json',
    )

    assert result.returncode == 2
    assert 'tool_status: BLOCKED' in result.stdout
    assert 'prompt_lab/runs/' in result.stdout


def test_prompt_lab_run_tool_rejects_unlisted_tool(isolated_workspace):
    started = run_prompt_lab(isolated_workspace, 'start', '--run-id', 'run_test_allowlist')
    assert started.returncode == 0, started.stdout + started.stderr
    workspace = isolated_workspace / 'prompt_lab' / 'runs' / 'run_test_allowlist' / 'workspaces' / 'round_001_workspace'
    output = isolated_workspace / 'prompt_lab' / 'runs' / 'run_test_allowlist' / 'round_001' / 'tool_outputs' / 'blocked.json'

    result = run_prompt_lab(
        isolated_workspace,
        'run-tool',
        '--workspace',
        str(workspace),
        '--tool',
        'update_kit.py',
        '--output',
        str(output),
    )

    assert result.returncode == 2
    assert 'unsupported tool for Prompt Lab' in result.stdout


def test_prompt_lab_score_rejects_run_outside_prompt_lab(isolated_workspace):
    result = run_prompt_lab(
        isolated_workspace,
        'score',
        '--run',
        'tasks',
        '--round',
        '1',
    )

    assert result.returncode == 2
    assert 'score_status: BLOCKED' in result.stdout
    assert 'prompt_lab/runs/' in result.stdout


def _write_minimal_round_completion(round_dir: Path) -> None:
    write_json(round_dir / 'optimizer' / 'apply_result.json', {
        'schema_version': 'prompt_lab_apply_result_v1',
        'apply_status': 'SKIPPED',
        'reason': 'test setup',
    })


def test_prompt_lab_advance_round_creates_next_workspace(isolated_workspace):
    started = run_prompt_lab(
        isolated_workspace,
        'start',
        '--run-id',
        'run_test_advance',
        '--rounds',
        '2',
    )
    assert started.returncode == 0, started.stdout + started.stderr
    run_dir = isolated_workspace / 'prompt_lab' / 'runs' / 'run_test_advance'
    _write_minimal_round_completion(run_dir / 'round_001')

    advanced = run_prompt_lab(
        isolated_workspace,
        'advance-round',
        '--run',
        str(run_dir.relative_to(isolated_workspace)),
    )
    assert advanced.returncode == 0, advanced.stdout + advanced.stderr
    assert 'advance_round_status: OK' in advanced.stdout
    assert 'current_round: 2/2' in advanced.stdout

    manifest = json.loads((run_dir / 'run_manifest.json').read_text(encoding='utf-8'))
    assert manifest['current_round'] == 2
    assert (run_dir / 'workspaces' / 'round_002_workspace').is_dir()

    _write_minimal_round_completion(run_dir / 'round_002')
    blocked = run_prompt_lab(
        isolated_workspace,
        'advance-round',
        '--run',
        str(run_dir.relative_to(isolated_workspace)),
    )
    assert blocked.returncode == 2
    assert 'already at final round' in blocked.stdout


def test_prompt_lab_advance_round_rejects_invalid_apply_result(isolated_workspace):
    started = run_prompt_lab(isolated_workspace, 'start', '--run-id', 'run_test_invalid_apply')
    assert started.returncode == 0, started.stdout + started.stderr
    run_dir = isolated_workspace / 'prompt_lab' / 'runs' / 'run_test_invalid_apply'
    (run_dir / 'round_001' / 'optimizer' / 'apply_result.json').write_text('{}', encoding='utf-8')

    blocked = run_prompt_lab(
        isolated_workspace,
        'advance-round',
        '--run',
        str(run_dir.relative_to(isolated_workspace)),
    )

    assert blocked.returncode == 2
    assert 'schema_version must be prompt_lab_apply_result_v1' in blocked.stdout


def test_prompt_lab_apply_patch_rolls_back_on_partial_failure(isolated_workspace):
    started = run_prompt_lab(isolated_workspace, 'start', '--run-id', 'run_test_rollback')
    assert started.returncode == 0, started.stdout + started.stderr
    run_dir = isolated_workspace / 'prompt_lab' / 'runs' / 'run_test_rollback'
    round_dir = run_dir / 'round_001'

    evaluation = {
        'schema_version': 'prompt_lab_evaluation_v1',
        'scenario_id': 'scenario_internal_report',
        'scores': {
            'schema_compliance': 5,
            'boundary_handling': 5,
            'source_grounding': 5,
            'missing_input_handling': 5,
            'task_quality': 5,
            'finish_review_accuracy': 5,
        },
        'red_flags': [],
        'issues': [],
        'prompt_improvement_candidates': [],
    }
    write_json(round_dir / 'evaluations' / 'scenario_internal_report.json', evaluation)
    scored = run_prompt_lab(isolated_workspace, 'score', '--run', str(run_dir), '--round', '1')
    assert scored.returncode == 0, scored.stdout + scored.stderr

    experimental_prompt = isolated_workspace / 'prompt_lab' / 'prompt_versions' / 'current' / 'task_intake_enrichment_prompt_v1.md'
    before = experimental_prompt.read_text(encoding='utf-8')
    patch = {
        'schema_version': 'prompt_lab_prompt_patch_v1',
        'rationale': 'Test rollback on second-file failure.',
        'files': [
            {
                'prompt_file': 'task_intake_enrichment_prompt_v1.md',
                'operation': 'append_rule',
                'content': 'First change should roll back with the failed second change.',
            },
            {
                'prompt_file': 'evidence_enrichment_prompt_v1.md',
                'operation': 'replace_text',
                'find': 'THIS_STRING_DOES_NOT_EXIST',
                'replace': 'noop',
            },
        ],
    }
    patch_path = round_dir / 'optimizer' / 'prompt_patch.json'
    write_json(patch_path, patch)

    blocked = run_prompt_lab(
        isolated_workspace,
        'apply-prompt-patch',
        '--run',
        str(run_dir),
        '--round',
        '1',
        '--patch',
        str(patch_path),
        '--threshold',
        '80',
    )

    assert blocked.returncode == 1, blocked.stdout + blocked.stderr
    assert 'apply_status: BLOCKED' in blocked.stdout
    assert experimental_prompt.read_text(encoding='utf-8') == before


def test_prompt_lab_run_tool_rejects_search_artifacts(isolated_workspace):
    started = run_prompt_lab(isolated_workspace, 'start', '--run-id', 'run_test_search_blocked')
    assert started.returncode == 0, started.stdout + started.stderr
    workspace = isolated_workspace / 'prompt_lab' / 'runs' / 'run_test_search_blocked' / 'workspaces' / 'round_001_workspace'
    output = isolated_workspace / 'prompt_lab' / 'runs' / 'run_test_search_blocked' / 'round_001' / 'tool_outputs' / 'blocked_search.json'

    result = run_prompt_lab(
        isolated_workspace,
        'run-tool',
        '--workspace',
        str(workspace),
        '--tool',
        'search_artifacts.py',
        '--output',
        str(output),
    )

    assert result.returncode == 2
    assert 'unsupported tool for Prompt Lab' in result.stdout


def test_prompt_lab_start_full_lifecycle_chain_mode(isolated_workspace):
    result = run_prompt_lab(
        isolated_workspace,
        'start',
        '--run-id',
        'run_test_full_chain',
        '--chain-mode',
        'full_lifecycle',
        '--focus',
        'meeting_to_finish',
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'chain_mode: full_lifecycle' in result.stdout
    manifest = json.loads(
        (isolated_workspace / 'prompt_lab' / 'runs' / 'run_test_full_chain' / 'run_manifest.json').read_text(encoding='utf-8')
    )
    assert manifest['chain_mode'] == 'full_lifecycle'
    assert (isolated_workspace / 'prompt_lab' / 'runs' / 'run_test_full_chain' / 'round_001' / 'chain_outputs').is_dir()


def test_prompt_lab_next_step_full_lifecycle_shows_chain_instructions(isolated_workspace):
    started = run_prompt_lab(
        isolated_workspace,
        'start',
        '--run-id',
        'run_test_full_chain_next',
        '--chain-mode',
        'full_lifecycle',
    )
    assert started.returncode == 0, started.stdout + started.stderr
    nxt = run_prompt_lab(
        isolated_workspace,
        'next-step',
        '--run',
        'prompt_lab/runs/run_test_full_chain_next',
    )
    assert nxt.returncode == 0, nxt.stdout + nxt.stderr
    assert 'chain_mode: full_lifecycle' in nxt.stdout
    assert 'write-task-artifact' in nxt.stdout
    assert 'prepare_execute_task.py' in nxt.stdout


def test_prompt_lab_write_task_artifact_copies_mock_output(isolated_workspace, fixtures):
    started = run_prompt_lab(isolated_workspace, 'start', '--run-id', 'run_test_write_artifact')
    assert started.returncode == 0, started.stdout + started.stderr
    run_dir = isolated_workspace / 'prompt_lab' / 'runs' / 'run_test_write_artifact'
    workspace = run_dir / 'workspaces' / 'round_001_workspace'
    enrich = enrichment_path(fixtures, 'task_intake_open.json')
    created = run_prompt_lab(
        isolated_workspace,
        'run-tool',
        '--workspace',
        str(workspace),
        '--tool',
        'new_task.py',
        '--output',
        str(run_dir / 'round_001' / 'tool_outputs' / 'create_task.json'),
        '--',
        '--enrichment',
        str(enrich),
    )
    assert created.returncode == 0, created.stdout + created.stderr
    created_data = json.loads((run_dir / 'round_001' / 'tool_outputs' / 'create_task.json').read_text(encoding='utf-8'))
    task_rel = next(
        line.split(' ', 1)[1].strip()
        for line in created_data['stdout'].splitlines()
        if line.startswith('TASK_FOLDER ')
    )
    chain_dir = run_dir / 'round_001' / 'chain_outputs' / 'demo_scenario'
    chain_dir.mkdir(parents=True, exist_ok=True)
    mock_output = chain_dir / 'task_output.md'
    mock_output.write_text('# Task Output\n\n## summary\nMock deliverable from meeting action.\n', encoding='utf-8')
    result = run_prompt_lab(
        isolated_workspace,
        'write-task-artifact',
        '--workspace',
        str(workspace.relative_to(isolated_workspace)),
        '--task',
        task_rel,
        '--artifact',
        'task_output.md',
        '--source',
        str(mock_output.relative_to(isolated_workspace)),
        '--output',
        str(run_dir / 'round_001' / 'tool_outputs' / 'demo_task_output.json'),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'artifact_status: OK' in result.stdout
    assert (workspace / task_rel / 'task_output.md').exists()


def test_prompt_lab_write_task_artifact_rejects_source_outside_chain_outputs(isolated_workspace, fixtures):
    started = run_prompt_lab(isolated_workspace, 'start', '--run-id', 'run_test_write_artifact_source_boundary')
    assert started.returncode == 0, started.stdout + started.stderr
    run_dir = isolated_workspace / 'prompt_lab' / 'runs' / 'run_test_write_artifact_source_boundary'
    workspace = run_dir / 'workspaces' / 'round_001_workspace'
    enrich = enrichment_path(fixtures, 'task_intake_open.json')
    created = run_prompt_lab(
        isolated_workspace,
        'run-tool',
        '--workspace',
        str(workspace),
        '--tool',
        'new_task.py',
        '--output',
        str(run_dir / 'round_001' / 'tool_outputs' / 'create_task.json'),
        '--',
        '--enrichment',
        str(enrich),
    )
    assert created.returncode == 0, created.stdout + created.stderr
    created_data = json.loads((run_dir / 'round_001' / 'tool_outputs' / 'create_task.json').read_text(encoding='utf-8'))
    task_rel = next(
        line.split(' ', 1)[1].strip()
        for line in created_data['stdout'].splitlines()
        if line.startswith('TASK_FOLDER ')
    )
    outside = run_dir / 'round_001' / 'tool_outputs' / 'private_output.md'
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text('# Private\n\nDo not copy this file.\n', encoding='utf-8')

    result = run_prompt_lab(
        isolated_workspace,
        'write-task-artifact',
        '--workspace',
        str(workspace.relative_to(isolated_workspace)),
        '--task',
        task_rel,
        '--artifact',
        'task_output.md',
        '--source',
        str(outside.relative_to(isolated_workspace)),
        '--output',
        str(run_dir / 'round_001' / 'tool_outputs' / 'blocked_task_output.json'),
    )

    assert result.returncode == 2
    assert 'artifact_status: BLOCKED' in result.stdout
    assert 'chain_outputs' in result.stdout
    assert not (workspace / task_rel / 'task_output.md').exists()


def test_prompt_lab_run_tool_allows_prepare_execute_task(isolated_workspace, fixtures):
    started = run_prompt_lab(isolated_workspace, 'start', '--run-id', 'run_test_prepare')
    assert started.returncode == 0, started.stdout + started.stderr
    run_dir = isolated_workspace / 'prompt_lab' / 'runs' / 'run_test_prepare'
    workspace = run_dir / 'workspaces' / 'round_001_workspace'
    enrich = enrichment_path(fixtures, 'task_intake_open.json')
    created = run_prompt_lab(
        isolated_workspace,
        'run-tool',
        '--workspace',
        str(workspace),
        '--tool',
        'new_task.py',
        '--output',
        str(run_dir / 'round_001' / 'tool_outputs' / 'create_task.json'),
        '--',
        '--enrichment',
        str(enrich),
    )
    assert created.returncode == 0, created.stdout + created.stderr
    created_data = json.loads((run_dir / 'round_001' / 'tool_outputs' / 'create_task.json').read_text(encoding='utf-8'))
    task_rel = next(
        line.split(' ', 1)[1].strip()
        for line in created_data['stdout'].splitlines()
        if line.startswith('TASK_FOLDER ')
    )
    output = run_dir / 'round_001' / 'tool_outputs' / 'prepare.json'
    result = run_prompt_lab(
        isolated_workspace,
        'run-tool',
        '--workspace',
        str(workspace),
        '--tool',
        'prepare_execute_task.py',
        '--output',
        str(output),
        '--',
        task_rel,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(output.read_text(encoding='utf-8'))
    assert data['returncode'] == 0
    assert 'execute_status: READY' in data['stdout']
    assert (workspace / task_rel / 'execution_plan.md').exists()


def test_prompt_lab_start_auto_uses_mock_without_real_context(isolated_workspace):
    result = run_prompt_lab(
        isolated_workspace,
        'start',
        '--run-id',
        'run_test_context_mock',
        '--context-mode',
        'auto',
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert 'context_mode: mock' in result.stdout
    manifest = json.loads(
        (isolated_workspace / 'prompt_lab' / 'runs' / 'run_test_context_mock' / 'run_manifest.json').read_text(
            encoding='utf-8'
        )
    )
    assert manifest['effective_context_mode'] == 'mock'


def test_prompt_lab_start_real_task_blocks_without_creating_run(isolated_workspace):
    result = run_prompt_lab(
        isolated_workspace,
        'start',
        '--run-id',
        'run_test_missing_real_context',
        '--context-mode',
        'real_task',
    )

    assert result.returncode == 2
    assert '--context-mode real_task was requested' in result.stdout
    assert not (isolated_workspace / 'prompt_lab' / 'runs' / 'run_test_missing_real_context').exists()


def test_prompt_lab_start_auto_uses_real_task_context_when_available(isolated_workspace):
    task_dir = isolated_workspace / 'tasks' / 'task_real_context'
    task_dir.mkdir(parents=True)
    (task_dir / 'task_scope.md').write_text('# Task Scope\n\nPrepare renewal memo.\n', encoding='utf-8')
    (task_dir / 'task_ledger.md').write_text('# Task Ledger\n\nstatus: OPEN\n', encoding='utf-8')

    result = run_prompt_lab(
        isolated_workspace,
        'start',
        '--run-id',
        'run_test_context_real',
        '--context-mode',
        'auto',
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert 'context_mode: real_task' in result.stdout
    run_dir = isolated_workspace / 'prompt_lab' / 'runs' / 'run_test_context_real'
    manifest = json.loads((run_dir / 'run_manifest.json').read_text(encoding='utf-8'))
    assert manifest['effective_context_mode'] == 'real_task'
    assert (run_dir / 'real_task_context' / 'context.md').exists()
    isolated_task = run_dir / 'workspaces' / 'round_001_workspace' / 'tasks' / 'task_real_context'
    assert (isolated_task / 'task_scope.md').exists()
    tracked = subprocess.run(
        ['git', 'ls-files', 'tasks/task_real_context/task_scope.md'],
        cwd=run_dir / 'workspaces' / 'round_001_workspace',
        capture_output=True,
        text=True,
    )
    assert tracked.returncode == 0
    assert tracked.stdout.strip() == ''


def test_prompt_lab_score_writes_admin_handoff_outbox(isolated_workspace):
    started = run_prompt_lab(isolated_workspace, 'start', '--run-id', 'run_test_admin_outbox')
    assert started.returncode == 0, started.stdout + started.stderr
    run_dir = isolated_workspace / 'prompt_lab' / 'runs' / 'run_test_admin_outbox'
    round_dir = run_dir / 'round_001'
    write_json(round_dir / 'evaluations' / 'scenario_feedback.json', {
        'schema_version': 'prompt_lab_evaluation_v1',
        'scenario_id': 'scenario_feedback',
        'scores': {
            'schema_compliance': 5,
            'boundary_handling': 5,
            'source_grounding': 4,
            'missing_input_handling': 4,
            'task_quality': 4,
            'finish_review_accuracy': 5,
        },
        'red_flags': [],
        'issues': ['Task intake missed the requested reviewer.'],
        'prompt_improvement_candidates': ['Require reviewer extraction when the source names an approver.'],
    })

    scored = run_prompt_lab(isolated_workspace, 'score', '--run', str(run_dir), '--round', '1')

    assert scored.returncode == 0, scored.stdout + scored.stderr
    assert 'admin_summary:' in scored.stdout
    assert (round_dir / 'admin_report.md').exists()
    outbox = isolated_workspace / 'prompt_lab' / 'admin_feedback' / 'outbox' / 'run_test_admin_outbox' / 'round_001'
    assert (outbox / 'admin_report.md').exists()
    summary = json.loads((outbox / 'admin_summary.json').read_text(encoding='utf-8'))
    assert summary['problems'] == ['Task intake missed the requested reviewer.']
    assert summary['optimization_plan'] == ['Require reviewer extraction when the source names an approver.']
    assert summary['handoff_status'] == 'READY'


def test_prompt_lab_real_task_outbox_redacts_until_handoff_safe(isolated_workspace):
    task_dir = isolated_workspace / 'tasks' / 'task_sensitive_context'
    task_dir.mkdir(parents=True)
    (task_dir / 'task_scope.md').write_text('# Task Scope\n\nPrepare ACME renewal memo.\n', encoding='utf-8')
    (task_dir / 'task_ledger.md').write_text('# Task Ledger\n\nstatus: OPEN\n', encoding='utf-8')
    started = run_prompt_lab(
        isolated_workspace,
        'start',
        '--run-id',
        'run_test_redaction_required',
        '--context-mode',
        'real_task',
    )
    assert started.returncode == 0, started.stdout + started.stderr
    run_dir = isolated_workspace / 'prompt_lab' / 'runs' / 'run_test_redaction_required'
    round_dir = run_dir / 'round_001'
    write_json(round_dir / 'evaluations' / 'scenario_sensitive.json', {
        'schema_version': 'prompt_lab_evaluation_v1',
        'scenario_id': 'scenario_sensitive',
        'scores': {
            'schema_compliance': 5,
            'boundary_handling': 5,
            'source_grounding': 4,
            'missing_input_handling': 4,
            'task_quality': 4,
            'finish_review_accuracy': 5,
        },
        'red_flags': [],
        'issues': ['ACME renewal memo exposed the project codename.'],
        'prompt_improvement_candidates': ['Mention ACME only after admin redaction.'],
        'sensitive_content_present': True,
        'admin_handoff_safe': False,
        'redaction_notes': ['Remove customer and project names before admin handoff.'],
    })

    scored = run_prompt_lab(isolated_workspace, 'score', '--run', str(run_dir), '--round', '1')

    assert scored.returncode == 0, scored.stdout + scored.stderr
    outbox = isolated_workspace / 'prompt_lab' / 'admin_feedback' / 'outbox' / 'run_test_redaction_required' / 'round_001'
    summary = json.loads((outbox / 'admin_summary.json').read_text(encoding='utf-8'))
    assert summary['handoff_status'] == 'BLOCKED_REDACTION_REQUIRED'
    assert summary['problems'] == []
    assert summary['optimization_plan'] == []
    report = (outbox / 'admin_report.md').read_text(encoding='utf-8')
    assert 'ACME' not in report
    assert 'BLOCKED_REDACTION_REQUIRED' in report
