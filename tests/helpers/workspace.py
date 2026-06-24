"""Create isolated LBAI workspaces for integration tests (never touches kit repo state)."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

IGNORE = shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store', '.git')


def kit_root() -> Path:
    return Path(__file__).resolve().parents[2]


def template_root() -> Path:
    return kit_root() / 'workspace_template'


def fixtures_root() -> Path:
    return Path(__file__).resolve().parents[1] / 'fixtures'


def create_isolated_workspace(base_dir: Path, *, initial_commit: bool = True) -> Path:
    """Copy workspace_template into a fresh directory and init a local git repo."""
    workspace = base_dir / 'lbai_test_workspace'
    if workspace.exists():
        shutil.rmtree(workspace)
    shutil.copytree(template_root(), workspace, ignore=IGNORE)

    contract = workspace / 'lbai_system' / 'runner_contracts' / 'lbai_command_contract_v1.md'
    if not contract.exists():
        raise FileNotFoundError(f'missing runner contract in template: {contract}')

    subprocess.run(['git', 'init'], cwd=workspace, check=True, capture_output=True, text=True)
    subprocess.run(['git', 'config', 'user.email', 'lbai-test@example.com'], cwd=workspace, check=True)
    subprocess.run(['git', 'config', 'user.name', 'LBAI Test'], cwd=workspace, check=True)

    if initial_commit:
        employee_paths = ['.gitignore', 'role_workspace', 'tasks', 'prompt_lab']
        existing = [p for p in employee_paths if (workspace / p).exists()]
        subprocess.run(['git', 'add', '-A', '--', *existing], cwd=workspace, check=True, capture_output=True, text=True)
        subprocess.run(
            ['git', 'commit', '-m', 'test: isolated workspace seed'],
            cwd=workspace,
            check=True,
            capture_output=True,
            text=True,
        )
        # Stub remote/upstream so bootstrap and finish preconditions can be tested without network.
        subprocess.run(
            ['git', 'remote', 'add', 'origin', 'https://example.com/lbai-test-workspace.git'],
            cwd=workspace,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(['git', 'branch', '-M', 'main'], cwd=workspace, check=True, capture_output=True, text=True)
        subprocess.run(['git', 'update-ref', 'refs/remotes/origin/main', 'HEAD'], cwd=workspace, check=True)
        subprocess.run(
            ['git', 'branch', '--set-upstream-to=origin/main', 'main'],
            cwd=workspace,
            check=True,
            capture_output=True,
            text=True,
        )
    return workspace


def tools_dir(workspace: Path) -> Path:
    return workspace / 'lbai_system' / 'tools'
