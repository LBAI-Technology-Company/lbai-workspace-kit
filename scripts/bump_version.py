#!/usr/bin/env python3
"""Bump the LBAI Workspace Kit version across every version-bearing file.

The kit records its version in many places that must stay aligned. Releases are
cut manually and `.lbai/workspace.json` has drifted in the past because it was
forgotten. This script is the single atomic writer so that drift cannot recur.

Usage:
    python3 scripts/bump_version.py <new_version>        # apply the bump
    python3 scripts/bump_version.py <new_version> --verify
    python3 scripts/bump_version.py --verify             # check current alignment

Files updated (plugin_version / installer / __version__ / workspaceKitVersion):
    VERSION
    lbai_core/lbai/__init__.py
    .lbai/workspace.json
    workspace_template/.lbai/workspace.json
    plugins/lbai-workspace/compatibility.json
    plugins/lbai-workspace/.codex-plugin/plugin.json
    install.sh
    install.ps1
    plugins/lbai-workspace/skills/*/SKILL.md   (--plugin-version only)

Deliberately NOT touched:
    compatibility.json minimum_cli_version / minimum_workspace_kit_version
        (intentional compatibility floor, pinned by test_codex_plugin.py)
    SKILL.md --min-workspace-version
        (mirrors the compatibility floor above)
    plugins/lbai-workspace/CHANGELOG.md
        (human-authored semantic release notes; the script only reminds you)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_RE = re.compile(r'^\d+\.\d+\.\d+$')

VERSION_FILE = ROOT / 'VERSION'
INIT_FILE = ROOT / 'lbai_core' / 'lbai' / '__init__.py'
WORKSPACE_JSON = ROOT / '.lbai' / 'workspace.json'
TEMPLATE_WORKSPACE_JSON = ROOT / 'workspace_template' / '.lbai' / 'workspace.json'
COMPATIBILITY_JSON = ROOT / 'plugins' / 'lbai-workspace' / 'compatibility.json'
PLUGIN_JSON = ROOT / 'plugins' / 'lbai-workspace' / '.codex-plugin' / 'plugin.json'
INSTALL_SH = ROOT / 'install.sh'
INSTALL_PS1 = ROOT / 'install.ps1'
SKILLS_DIR = ROOT / 'plugins' / 'lbai-workspace' / 'skills'


def version_tuple(value: str) -> tuple[int, int, int]:
    return tuple(int(part) for part in value.split('.'))  # type: ignore[return-value]


def read_current_version() -> str:
    return VERSION_FILE.read_text(encoding='utf-8').strip()


def set_text_file(path: Path, content: str) -> bool:
    """Write text only when it differs; return True if changed."""
    if path.read_text(encoding='utf-8') == content:
        return False
    path.write_text(content, encoding='utf-8')
    return True


def bump_plain(path: Path, version: str) -> bool:
    return set_text_file(path, f'{version}\n')


def bump_regex(path: Path, pattern: str, replacement: str) -> bool:
    text = path.read_text(encoding='utf-8')
    new_text, count = re.subn(pattern, replacement, text)
    if count == 0:
        raise RuntimeError(f'{path}: pattern not matched: {pattern}')
    return set_text_file(path, new_text)


def bump_json_field(path: Path, field: str, version: str) -> bool:
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get(field) == version:
        return False
    data[field] = version
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return True


def bump_install_sh(version: str) -> bool:
    return bump_regex(INSTALL_SH, r'INSTALLER_VERSION="[^"]*"', f'INSTALLER_VERSION="{version}"')


def bump_install_ps1(version: str) -> bool:
    return bump_regex(INSTALL_PS1, r'\$InstallerVersion = "[^"]*"', f'$InstallerVersion = "{version}"')


def bump_init(version: str) -> bool:
    return bump_regex(INIT_FILE, r'__version__\s*=\s*"[^"]*"', f'__version__ = "{version}"')


def bump_skill_files(version: str) -> list[Path]:
    changed: list[Path] = []
    for skill_md in sorted(SKILLS_DIR.glob('*/SKILL.md')):
        text = skill_md.read_text(encoding='utf-8')
        new_text, count = re.subn(
            r'--plugin-version \d+\.\d+\.\d+',
            f'--plugin-version {version}',
            text,
        )
        if count == 0:
            raise RuntimeError(f'{skill_md}: --plugin-version not found')
        if new_text != text:
            skill_md.write_text(new_text, encoding='utf-8')
            changed.append(skill_md)
    return changed


def collect_alignment() -> list[tuple[str, str]]:
    """Return (label, current_value) for every version-bearing location."""
    rows: list[tuple[str, str]] = []
    rows.append(('VERSION', read_current_version()))
    init = re.search(r'__version__\s*=\s*"([^"]*)"', INIT_FILE.read_text(encoding='utf-8'))
    rows.append(('lbai_core/__init__.py __version__', init.group(1) if init else 'MISSING'))
    rows.append(('.lbai/workspace.json workspaceKitVersion',
                 json.loads(WORKSPACE_JSON.read_text(encoding='utf-8')).get('workspaceKitVersion', 'MISSING')))
    rows.append(('template workspace.json workspaceKitVersion',
                 json.loads(TEMPLATE_WORKSPACE_JSON.read_text(encoding='utf-8')).get('workspaceKitVersion', 'MISSING')))
    compat = json.loads(COMPATIBILITY_JSON.read_text(encoding='utf-8'))
    rows.append(('compatibility.json plugin_version', compat.get('plugin_version', 'MISSING')))
    plugin = json.loads(PLUGIN_JSON.read_text(encoding='utf-8'))
    rows.append(('plugin.json version', plugin.get('version', 'MISSING')))
    sh = re.search(r'INSTALLER_VERSION="([^"]*)"', INSTALL_SH.read_text(encoding='utf-8'))
    rows.append(('install.sh INSTALLER_VERSION', sh.group(1) if sh else 'MISSING'))
    ps1 = re.search(r'\$InstallerVersion = "([^"]*)"', INSTALL_PS1.read_text(encoding='utf-8'))
    rows.append(('install.ps1 InstallerVersion', ps1.group(1) if ps1 else 'MISSING'))
    skill_versions: set[str] = set()
    for skill_md in sorted(SKILLS_DIR.glob('*/SKILL.md')):
        m = re.search(r'--plugin-version (\d+\.\d+\.\d+)', skill_md.read_text(encoding='utf-8'))
        skill_versions.add(m.group(1) if m else 'MISSING')
    rows.append(('SKILL.md --plugin-version (8 files)',
                 ', '.join(sorted(skill_versions)) if len(skill_versions) == 1
                 else f'MIXED: {sorted(skill_versions)}'))
    return rows


def apply_bump(version: str) -> int:
    changed: list[str] = []
    if bump_plain(VERSION_FILE, version):
        changed.append(str(VERSION_FILE.relative_to(ROOT)))
    if bump_init(version):
        changed.append(str(INIT_FILE.relative_to(ROOT)))
    if bump_json_field(WORKSPACE_JSON, 'workspaceKitVersion', version):
        changed.append(str(WORKSPACE_JSON.relative_to(ROOT)))
    if bump_json_field(TEMPLATE_WORKSPACE_JSON, 'workspaceKitVersion', version):
        changed.append(str(TEMPLATE_WORKSPACE_JSON.relative_to(ROOT)))
    if bump_json_field(COMPATIBILITY_JSON, 'plugin_version', version):
        changed.append(str(COMPATIBILITY_JSON.relative_to(ROOT)))
    if bump_json_field(PLUGIN_JSON, 'version', version):
        changed.append(str(PLUGIN_JSON.relative_to(ROOT)))
    if bump_install_sh(version):
        changed.append(str(INSTALL_SH.relative_to(ROOT)))
    if bump_install_ps1(version):
        changed.append(str(INSTALL_PS1.relative_to(ROOT)))
    for skill_md in bump_skill_files(version):
        changed.append(str(skill_md.relative_to(ROOT)))

    print(f'Bumped to {version}.')
    if changed:
        print('Changed files:')
        for path in changed:
            print(f'  - {path}')
    else:
        print('No files changed (already at target version).')
    print()
    print('Reminder: add a "## <version>" entry to '
          'plugins/lbai-workspace/CHANGELOG.md with the semantic changes,')
    print('then commit and push. Do not bump minimum_* fields in compatibility.json.')
    return 0


def verify(target: str | None) -> int:
    rows = collect_alignment()
    versions = {value for _, value in rows if value not in {'MISSING'} and not value.startswith('MIXED')}
    print('Version alignment check:')
    for label, value in rows:
        marker = '  ' if (target is None or value == target) else '!!'
        print(f'{marker} {label}: {value}')
    print()
    misaligned = [value for value in versions if target is not None and value != target]
    mixed = [value for _, value in rows if value.startswith('MIXED') or value == 'MISSING']
    if target is not None:
        if not misaligned and not mixed:
            print(f'OK: all locations report {target}.')
            return 0
        print(f'MISALIGNED: expected {target}, found {sorted(misaligned + mixed)}')
        return 1
    if len(versions) == 1 and not mixed:
        print(f'OK: all locations aligned at {next(iter(versions))}.')
        return 0
    print(f'MISALIGNED: found distinct values {sorted(versions)}{sorted(mixed)}')
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('version', nargs='?', help='Target version, e.g. 1.4.20.')
    parser.add_argument('--verify', action='store_true',
                        help='Only check alignment; with a version arg, check it matches everywhere.')
    args = parser.parse_args()

    if args.verify:
        return verify(args.version)

    if not args.version:
        parser.error('version is required (or pass --verify).')
    if not VERSION_RE.match(args.version):
        parser.error(f'invalid version format: {args.version} (expected X.Y.Z)')
    current = read_current_version()
    if version_tuple(args.version) <= version_tuple(current):
        parser.error(f'new version {args.version} must be greater than current {current}')
    return apply_bump(args.version)


if __name__ == '__main__':
    raise SystemExit(main())
