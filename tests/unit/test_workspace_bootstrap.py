"""Unit tests for personal-repo-first workspace bootstrap."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'lbai_core'))

from lbai.workspace_bootstrap import inspect_remote_repo  # noqa: E402
from lbai.workspace_config import is_workspace  # noqa: E402


def git(cwd: Path, *args: str) -> None:
    subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True, text=True)


def init_repo(path: Path, *, message: str, filename: str, content: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    git(path, 'init', '-b', 'main')
    git(path, 'config', 'user.email', 'lbai-test@example.com')
    git(path, 'config', 'user.name', 'LBAI Test')
    (path / filename).write_text(content, encoding='utf-8')
    git(path, 'add', filename)
    git(path, 'commit', '-m', message)


def test_inspect_remote_repo_states(tmp_path: Path):
    bare = tmp_path / 'remote.git'
    git(tmp_path, 'init', '--bare', str(bare))
    assert inspect_remote_repo(str(bare)) == 'empty'

    seed_work = tmp_path / 'seed_work'
    init_repo(seed_work, message='readme only', filename='README.md', content='# hello\n')
    git(seed_work, 'remote', 'add', 'origin', str(bare))
    git(seed_work, 'push', '-u', 'origin', 'main')
    assert inspect_remote_repo(str(bare)) == 'seedable'

    template_root = Path(__file__).resolve().parents[2] / 'workspace_template'
    lbai_work = tmp_path / 'lbai_work'
    shutil.copytree(
        template_root,
        lbai_work,
        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store', '.git'),
    )
    git(lbai_work, 'init', '-b', 'main')
    git(lbai_work, 'config', 'user.email', 'lbai-test@example.com')
    git(lbai_work, 'config', 'user.name', 'LBAI Test')
    git(lbai_work, 'add', '-A')
    git(lbai_work, 'commit', '-m', 'seed lbai workspace')
    bare2 = tmp_path / 'lbai-remote.git'
    git(tmp_path, 'init', '--bare', str(bare2))
    git(lbai_work, 'remote', 'add', 'origin', str(bare2))
    git(lbai_work, 'push', '-u', 'origin', 'main')
    assert inspect_remote_repo(str(bare2)) == 'lbai_workspace'

    clone_dir = tmp_path / 'cloned'
    subprocess.run(['git', 'clone', str(bare2), str(clone_dir)], check=True, capture_output=True, text=True)
    assert is_workspace(clone_dir)
