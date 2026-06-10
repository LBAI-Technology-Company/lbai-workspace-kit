"""CLI smoke tests for cross-platform Python invocation."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers.workspace import create_isolated_workspace, kit_root

pytestmark = pytest.mark.integration


def run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env['PYTHONPATH'] = str(kit_root() / 'lbai_core')
    return subprocess.run(
        [sys.executable, '-m', 'lbai.cli', *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
    )


def test_cli_version():
    result = run_cli('--version')
    assert result.returncode == 0
    assert 'lbai' in result.stdout


def test_cli_doctor_on_isolated_workspace(tmp_path):
    workspace = create_isolated_workspace(tmp_path)
    result = run_cli('doctor', '--path', str(workspace))
    assert result.returncode == 0
    assert 'doctor_status: READY' in result.stdout


def test_cli_new_task_without_enrichment_shows_friendly_hint(tmp_path, monkeypatch):
    workspace = create_isolated_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    result = run_cli('new-task', '整理用户反馈')
    assert result.returncode == 2
    combined = result.stdout + result.stderr
    assert '/lbai-new-task' in combined
    assert 'Cursor' in combined or 'Codex' in combined
