"""Verify employee Git sync boundaries after template-local-only policy."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.helpers.tool_runner import enrichment_path, parse_task_folder, run_tool
from tests.helpers.workspace import template_root

pytestmark = pytest.mark.integration

TEMPLATE_IGNORED = [
    'AGENTS.md',
    'README.md',
    '.cursor/commands/lbai-new-task.md',
    '.agents/skills/lbai-new-task/SKILL.md',
    'lbai_system/tools/finish_task.py',
    'workspace_dashboard.html',
    '.lbai/workspace.json',
]

USER_TRACKED = [
    'role_workspace/world_model/ROLE_WORLD_MODEL_v1.md',
    'role_workspace/ledgers/TASK_LEDGER_v1.md',
    'role_workspace/knowledge/index.md',
]


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ['git', '-c', 'core.quotePath=false', *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


def load_update_kit_module():
    import importlib.util
    import sys

    tools_dir = template_root() / 'lbai_system' / 'tools'
    sys.path.insert(0, str(tools_dir))
    try:
        spec = importlib.util.spec_from_file_location('update_kit_boundary_test', tools_dir / 'update_kit.py')
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(tools_dir))


class TestGitSyncBoundary:
    def test_gitignore_blocks_template_paths_but_not_user_data(self, isolated_workspace):
        for rel in TEMPLATE_IGNORED:
            path = isolated_workspace / rel
            assert path.exists(), f'missing fixture path: {rel}'
            result = subprocess.run(
                ['git', 'check-ignore', '-q', rel],
                cwd=isolated_workspace,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f'expected ignored template path: {rel}'

        for rel in USER_TRACKED:
            path = isolated_workspace / rel
            assert path.exists(), f'missing fixture path: {rel}'
            result = subprocess.run(
                ['git', 'check-ignore', '-q', rel],
                cwd=isolated_workspace,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 1, f'user data must not be ignored: {rel}'

    def test_initial_commit_tracks_user_data_not_template(self, isolated_workspace):
        tracked = git(isolated_workspace, 'ls-files').stdout.splitlines()
        tracked_set = set(tracked)

        assert any(p.startswith('role_workspace/') for p in tracked_set)
        assert '.gitignore' in tracked_set
        assert not any(p.startswith('lbai_system/') for p in tracked_set)
        assert not any(p.startswith('.cursor/') for p in tracked_set)
        assert not any(p.startswith('.agents/') for p in tracked_set)
        assert 'AGENTS.md' not in tracked_set
        assert 'README.md' not in tracked_set

    def test_finish_stages_only_task_and_task_ledger(self, isolated_workspace, fixtures):
        enrich = enrichment_path(fixtures, 'task_intake_open.json')
        created = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
        assert created.returncode == 0, created.output
        task_rel = parse_task_folder(created.stdout)
        task_dir = isolated_workspace / task_rel
        (task_dir / 'task_output.md').write_text('# Task Output\n\nDone.\n', encoding='utf-8')

        marker = isolated_workspace / 'lbai_system' / 'tools' / 'boundary_marker.txt'
        marker.write_text('must-not-stage', encoding='utf-8')

        import importlib.util
        import sys

        tools_dir = isolated_workspace / 'lbai_system' / 'tools'
        sys.path.insert(0, str(tools_dir))
        try:
            spec = importlib.util.spec_from_file_location('finish_task_boundary_test', tools_dir / 'finish_task.py')
            assert spec and spec.loader
            finish_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(finish_module)
            ok, detail = finish_module.git_add_task_artifacts(isolated_workspace, task_rel)
        finally:
            sys.path.remove(str(tools_dir))
        assert ok, detail

        staged = git(isolated_workspace, 'diff', '--cached', '--name-only').stdout.splitlines()
        allowed = {
            'role_workspace/ledgers/TASK_LEDGER_v1.md',
        }
        bad = [
            s for s in staged
            if s not in allowed and s != task_rel and not s.startswith(task_rel + '/')
        ]
        assert not bad, f'unexpected staged paths: {bad}; staged={staged}; task_rel={task_rel}'
        assert 'lbai_system/tools/boundary_marker.txt' not in staged

    def test_migrate_untrack_keeps_gitignore_tracked(self, isolated_workspace):
        module = load_update_kit_module()
        # Simulate legacy repo that tracked template files.
        git(isolated_workspace, 'add', '-f', 'lbai_system/tools/finish_task.py', 'AGENTS.md')
        git(isolated_workspace, 'commit', '-m', 'test: legacy template tracking')

        status, detail = module.migrate_stop_tracking_managed_paths(isolated_workspace, push=False)
        assert status == 'COMMITTED', detail

        tracked = set(git(isolated_workspace, 'ls-files').stdout.splitlines())
        assert '.gitignore' in tracked
        assert 'AGENTS.md' not in tracked
        assert not any(p.startswith('lbai_system/') for p in tracked)
        assert any(p.startswith('role_workspace/') for p in tracked)

    def test_update_kit_does_not_stage_template_files(self, isolated_workspace):
        module = load_update_kit_module()
        untrack_targets = set(module.managed_paths_to_untrack())
        assert '.gitignore' not in untrack_targets
        assert 'lbai_system' in untrack_targets or any(p.startswith('lbai_system') for p in untrack_targets)
        assert '.lbai' in untrack_targets
