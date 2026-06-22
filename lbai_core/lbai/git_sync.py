"""Fetch and integrate remote commits before workspace Git push."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


def run_git(root: Path, args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        ['git', *args],
        cwd=root,
        env=merged,
        text=True,
        capture_output=True,
    )


def current_branch(root: Path) -> str:
    result = run_git(root, ['branch', '--show-current'])
    return result.stdout.strip() or 'main'


def origin_configured(root: Path) -> bool:
    result = run_git(root, ['remote', 'get-url', 'origin'])
    return result.returncode == 0 and bool(result.stdout.strip())


def pull_remote_before_push(
    root: Path,
    branch: str | None = None,
    env: dict[str, str] | None = None,
) -> tuple[bool, str]:
    if not origin_configured(root):
        return True, 'no origin configured; skipping pull'

    branch = branch or current_branch(root)
    remote_ref = f'origin/{branch}'

    fetch = run_git(root, ['fetch', 'origin'], env=env)
    if fetch.returncode != 0:
        detail = (fetch.stdout + fetch.stderr).strip()
        return False, f'git fetch failed: {detail}'

    verify = run_git(root, ['rev-parse', '--verify', remote_ref], env=env)
    if verify.returncode != 0:
        return True, f'{remote_ref} does not exist yet; nothing to pull'

    merge_base = run_git(root, ['merge-base', 'HEAD', remote_ref], env=env)
    if merge_base.returncode != 0:
        pull = run_git(
            root,
            [
                'pull',
                '--no-rebase',
                'origin',
                branch,
                '--allow-unrelated-histories',
                '--no-edit',
            ],
            env=env,
        )
        if pull.returncode != 0:
            detail = (pull.stdout + pull.stderr).strip()
            return False, f'git pull --allow-unrelated-histories failed: {detail}'
        return True, 'merged unrelated remote history'

    behind = run_git(root, ['rev-list', '--count', f'HEAD..{remote_ref}'], env=env)
    behind_count = int((behind.stdout.strip() or '0') if behind.returncode == 0 else '0')
    if behind_count == 0:
        return True, 'already up to date with remote'

    pull = run_git(root, ['pull', '--rebase', 'origin', branch], env=env)
    if pull.returncode != 0:
        pull = run_git(root, ['pull', '--no-rebase', 'origin', branch, '--no-edit'], env=env)
        if pull.returncode != 0:
            detail = (pull.stdout + pull.stderr).strip()
            return False, f'git pull failed: {detail}'
        return True, f'merged {behind_count} remote commit(s)'

    return True, f'rebased onto {behind_count} remote commit(s)'


def push_with_remote_sync(
    root: Path,
    branch: str | None = None,
    env: dict[str, str] | None = None,
    *,
    set_upstream: bool = False,
) -> tuple[bool, str, str]:
    branch = branch or current_branch(root)
    pull_ok, pull_detail = pull_remote_before_push(root, branch=branch, env=env)
    if not pull_ok:
        return False, 'PULL_FAILED', pull_detail

    if set_upstream:
        push = run_git(root, ['push', '-u', 'origin', branch], env=env)
    else:
        push = run_git(root, ['push'], env=env)

    if push.returncode != 0:
        detail = (push.stdout + push.stderr).strip()
        return False, 'PUSH_FAILED', detail

    return True, pull_detail, 'git push completed'
