"""Personal-repo-first workspace bootstrap helpers."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from lbai.workspace_config import is_workspace


RemoteRepoState = str  # empty | lbai_workspace | seedable | unreachable


def inspect_remote_repo(repo_url: str, env: dict[str, str] | None = None) -> RemoteRepoState:
    ls = _capture(['git', 'ls-remote', '--heads', repo_url], env=env)
    if ls.returncode != 0:
        return 'unreachable'
    if not ls.stdout.strip():
        return 'empty'
    branches = [
        line.rsplit('refs/heads/', 1)[-1].strip()
        for line in ls.stdout.splitlines()
        if 'refs/heads/' in line
    ]
    branch = 'main' if 'main' in branches else branches[0]

    with tempfile.TemporaryDirectory(prefix='lbai-remote-inspect-') as tmp:
        tmp_path = Path(tmp)
        clone = _run(
            ['git', 'clone', '--depth', '1', '--branch', branch, repo_url, str(tmp_path)],
            env=env,
        )
        if clone.returncode != 0:
            return 'unreachable'
        if is_workspace(tmp_path):
            return 'lbai_workspace'
        return 'seedable'


def clone_personal_repo(local_path: Path, repo_url: str, env: dict[str, str] | None = None) -> tuple[bool, str]:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    if local_path.exists():
        shutil.rmtree(local_path)
    clone = _run(['git', 'clone', repo_url, str(local_path)], env=env)
    if clone.returncode != 0:
        detail = (clone.stdout + clone.stderr).strip()
        return False, f'git clone failed: {detail}'
    if not is_workspace(local_path):
        return False, 'remote repo is not a valid LBAI workspace'
    return True, 'cloned personal repo'


def pull_personal_repo(local_path: Path, repo_url: str, env: dict[str, str] | None = None) -> tuple[bool, str]:
    from lbai.git_sync import pull_remote_before_push

    remote = _set_origin(local_path, repo_url)
    if remote.returncode != 0:
        return False, 'failed to configure Git remote origin'
    branch = _current_branch(local_path)
    ok, detail = pull_remote_before_push(local_path, branch=branch, env=env)
    if not ok:
        return False, detail
    if not is_workspace(local_path):
        return False, 'local workspace is missing required LBAI files after pull'
    return True, detail


def clone_raw_repo(local_path: Path, repo_url: str, env: dict[str, str] | None = None) -> tuple[bool, str]:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    if local_path.exists():
        shutil.rmtree(local_path)
    clone = _run(['git', 'clone', repo_url, str(local_path)], env=env)
    if clone.returncode != 0:
        detail = (clone.stdout + clone.stderr).strip()
        return False, f'git clone failed: {detail}'
    return True, 'cloned remote repo'


def restore_from_personal_repo(local_path: Path, repo_url: str, env: dict[str, str] | None = None) -> tuple[bool, str]:
    if local_path.exists() and (local_path / '.git').exists() and is_workspace(local_path):
        origin = _origin_url(local_path)
        if origin == repo_url.strip():
            return pull_personal_repo(local_path, repo_url, env=env)
    return clone_personal_repo(local_path, repo_url, env=env)


def _run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    import os

    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(cmd, cwd=cwd, env=merged, text=True)


def _capture(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    import os

    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(cmd, cwd=cwd, env=merged, text=True, capture_output=True)


def _current_branch(root: Path) -> str:
    result = _capture(['git', 'branch', '--show-current'], cwd=root)
    return result.stdout.strip() or 'main'


def _origin_url(root: Path) -> str:
    result = _capture(['git', 'remote', 'get-url', 'origin'], cwd=root)
    if result.returncode != 0:
        return ''
    return result.stdout.strip()


def _set_origin(root: Path, repo_url: str) -> subprocess.CompletedProcess:
    if _origin_url(root):
        return _run(['git', 'remote', 'set-url', 'origin', repo_url], cwd=root)
    return _run(['git', 'remote', 'add', 'origin', repo_url], cwd=root)
