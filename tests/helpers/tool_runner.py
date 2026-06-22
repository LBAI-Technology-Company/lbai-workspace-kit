"""Run lbai_system tools via subprocess inside an isolated workspace."""
from __future__ import annotations

import subprocess
import sys
import os
import json
import stat
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ToolResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        return self.stdout + self.stderr

    def line(self, prefix: str) -> str | None:
        for line in self.stdout.splitlines():
            if line.startswith(prefix):
                return line.split(':', 1)[-1].strip() if ':' in line else line[len(prefix):].strip()
        return None


def parse_task_folder(stdout: str) -> str:
    for line in stdout.splitlines():
        if line.startswith('TASK_FOLDER '):
            return line.split(' ', 1)[1].strip()
    raise AssertionError(f'TASK_FOLDER not found in output:\n{stdout}')


def run_tool(workspace: Path, script_name: str, *args: str, input_text: str | None = None) -> ToolResult:
    script = workspace / 'lbai_system' / 'tools' / script_name
    if not script.exists():
        raise FileNotFoundError(script)
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['LBAI_HOME'] = str(workspace / '.lbai_home')
    proc = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        input=input_text,
        env=env,
    )
    return ToolResult(proc.returncode, proc.stdout, proc.stderr)


def write_backend_auth(
    workspace: Path,
    api_key: str = 'test_backend_api_key',
    api_key_header: str = 'X-LBAI-API-Key',
    workspace_repo_id: str = '',
) -> Path:
    path = workspace / '.lbai_home' / 'auth' / 'knowledge_service.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                'schema_version': 'knowledge_service_auth_v1',
                'api_key': api_key,
                'api_key_header': api_key_header,
                'workspace_repo_id': workspace_repo_id,
                'created_at': '2026-06-14T00:00:00+00:00',
            },
            ensure_ascii=False,
            indent=2,
        )
        + '\n',
        encoding='utf-8',
    )
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return path


def enrichment_path(fixtures_root: Path, name: str) -> Path:
    return fixtures_root / 'enrichments' / name
