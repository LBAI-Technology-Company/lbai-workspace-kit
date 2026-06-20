#!/usr/bin/env python3
"""Run the machine-readable LBAI workspace preflight without exposing credentials."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
COMPATIBILITY = json.loads((PLUGIN_ROOT / 'compatibility.json').read_text(encoding='utf-8'))
PLUGIN_VERSION = COMPATIBILITY['plugin_version']
MIN_CLI_VERSION = COMPATIBILITY['minimum_cli_version']
MIN_WORKSPACE_VERSION = COMPATIBILITY['minimum_workspace_kit_version']


def version_tuple(value: str) -> tuple[int, int, int] | None:
    parts = value.lstrip('v').split('.', 2)
    if len(parts) != 3:
        return None
    try:
        return tuple(int(part.split('-', 1)[0].split('+', 1)[0]) for part in parts)
    except ValueError:
        return None


def blocked(reason: str, next_step: str) -> int:
    print(json.dumps({
        'schema_version': 'lbai_plugin_preflight_v1',
        'plugin_version': PLUGIN_VERSION,
        'preflight_status': 'BLOCKED',
        'reason': reason,
        'next_step': next_step,
    }, ensure_ascii=False, indent=2))
    return 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--workspace',
        help='Optional explicit workspace path. Omit to resolve the registered active workspace.',
    )
    parser.add_argument('--require-backend', action='store_true')
    args = parser.parse_args()

    lbai = shutil.which('lbai')
    if not lbai:
        return blocked(
            'lbai_cli_missing',
            'Install the LBAI CLI, run lbai auth login, then run lbai init-workspace.',
        )

    command = [
        lbai,
        'doctor',
        '--json',
        '--plugin-version',
        PLUGIN_VERSION,
        '--min-workspace-version',
        MIN_WORKSPACE_VERSION,
    ]
    if args.workspace:
        command.extend(['--path', str(Path(args.workspace).expanduser().resolve())])
    if args.require_backend:
        command.append('--require-backend')
    result = subprocess.run(command, capture_output=True, text=True)
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        return blocked(
            'lbai_cli_upgrade_required',
            'Update the LBAI CLI; this plugin requires lbai doctor --json support.',
        )

    current_cli = version_tuple(str(report.get('cli_version') or ''))
    required_cli = version_tuple(MIN_CLI_VERSION)
    if not current_cli or not required_cli or current_cli < required_cli:
        return blocked(
            'lbai_cli_upgrade_required',
            f'Update the LBAI CLI to {MIN_CLI_VERSION} or later.',
        )

    report['schema_version'] = 'lbai_plugin_preflight_v1'
    report['preflight_status'] = report.get('doctor_status', 'BLOCKED')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['preflight_status'] == 'READY' else 2


if __name__ == '__main__':
    raise SystemExit(main())
