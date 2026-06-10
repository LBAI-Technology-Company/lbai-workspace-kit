"""Run lbai_system tools via subprocess inside an isolated workspace."""
from __future__ import annotations

import subprocess
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
    proc = subprocess.run(
        ['python3', str(script), *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        input=input_text,
    )
    return ToolResult(proc.returncode, proc.stdout, proc.stderr)


def enrichment_path(fixtures_root: Path, name: str) -> Path:
    return fixtures_root / 'enrichments' / name
