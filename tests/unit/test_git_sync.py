"""Unit tests for git_sync_utils pull-before-push behavior."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parents[2] / 'lbai_system' / 'tools'
sys.path.insert(0, str(TOOLS_DIR))

from git_sync_utils import pull_remote_before_push, push_with_remote_sync  # noqa: E402


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError((result.stdout + result.stderr).strip())
    return result


def init_repo(path: Path, *, message: str, filename: str, content: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    git(path, 'init', '-b', 'main', check=False)
    git(path, 'config', 'user.email', 'lbai-test@example.com')
    git(path, 'config', 'user.name', 'LBAI Test')
    (path / filename).write_text(content, encoding='utf-8')
    git(path, 'add', filename)
    git(path, 'commit', '-m', message)


def test_pull_merges_unrelated_histories(tmp_path: Path):
    bare = tmp_path / 'remote.git'
    git(tmp_path, 'init', '--bare', str(bare))

    remote_work = tmp_path / 'remote_work'
    init_repo(remote_work, message='remote seed', filename='README.md', content='remote readme\n')
    git(remote_work, 'remote', 'add', 'origin', str(bare))
    git(remote_work, 'push', '-u', 'origin', 'main')

    local = tmp_path / 'local'
    init_repo(local, message='local seed', filename='AGENTS.md', content='# local workspace\n')
    git(local, 'remote', 'add', 'origin', str(bare))

    ok, detail = pull_remote_before_push(local)
    assert ok, detail
    assert 'unrelated' in detail

    log = git(local, 'log', '--oneline', '--decorate').stdout
    assert 'remote seed' in log
    assert 'local seed' in log


def test_push_with_remote_sync_rebases_before_push(tmp_path: Path):
    bare = tmp_path / 'remote.git'
    git(tmp_path, 'init', '--bare', str(bare))

    remote_work = tmp_path / 'remote_work'
    init_repo(remote_work, message='remote seed', filename='README.md', content='remote readme\n')
    git(remote_work, 'remote', 'add', 'origin', str(bare))
    git(remote_work, 'push', '-u', 'origin', 'main')

    local = tmp_path / 'local'
    git(tmp_path, 'clone', str(bare), str(local))
    (local / 'tasks' / 'note.md').parent.mkdir(parents=True)
    (local / 'tasks' / 'note.md').write_text('local task\n', encoding='utf-8')
    git(local, 'add', 'tasks/note.md')
    git(local, 'commit', '-m', 'local task commit')

    git(remote_work, 'checkout', 'main')
    (remote_work / 'role_workspace' / 'note.md').parent.mkdir(parents=True)
    (remote_work / 'role_workspace' / 'note.md').write_text('remote role note\n', encoding='utf-8')
    git(remote_work, 'add', 'role_workspace/note.md')
    git(remote_work, 'commit', '-m', 'remote role commit')
    git(remote_work, 'push', 'origin', 'main')

    ok, pull_status, detail = push_with_remote_sync(local)
    assert ok, detail
    assert 'rebased' in pull_status or 'merged' in pull_status

    assert (local / 'tasks' / 'note.md').exists()
    assert (local / 'role_workspace' / 'note.md').exists()
