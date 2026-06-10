#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True

from task_utils import SENSITIVE_PATTERNS, git_root, read_text


DEFAULT_REPO = 'LBAI-Technology-Company/lbai-workspace-kit'
DEFAULT_SOURCE = f'github-release:{DEFAULT_REPO}:latest'
MANAGED_DIRS = [Path('.cursor'), Path('.agents'), Path('lbai_system')]
MANAGED_FILES = [
    Path('.gitignore'),
    Path('AGENTS.md'),
    Path('README.md'),
    Path('workspace_dashboard.html'),
]
EMPLOYEE_ARTIFACT_DIRS = [Path('role_workspace'), Path('tasks')]
REQUIRED_SOURCE_PATHS = [Path('.cursor'), Path('lbai_system')]
KIT_TEMPLATE_DIR = Path('workspace_template')
TEMP_NAMES = {'.DS_Store', '__pycache__'}
TEMP_SUFFIXES = {'.pyc', '.pyo', '.log'}


def run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(['git', *args], cwd=root, capture_output=True, text=True)


def rel(path: Path) -> str:
    return path.as_posix()


def is_managed(path: str) -> bool:
    p = Path(path)
    if p in MANAGED_FILES:
        return True
    return any(p == d or d in p.parents for d in MANAGED_DIRS)


def is_employee_artifact(path: str) -> bool:
    p = Path(path)
    return any(p == d or d in p.parents for d in EMPLOYEE_ARTIFACT_DIRS)


def parse_status_paths(output: str) -> list[str]:
    paths = []
    for line in output.splitlines():
        if not line.strip():
            continue
        value = line[3:].strip()
        if ' -> ' in value:
            old, new = value.split(' -> ', 1)
            paths.extend([old.strip(), new.strip()])
        else:
            paths.append(value)
    return paths


def git_status_paths(root: Path) -> tuple[list[str], bool]:
    result = run_git(root, ['-c', 'core.quotePath=false', 'status', '--porcelain', '--untracked-files=all'])
    if result.returncode != 0:
        return [], False
    return parse_status_paths(result.stdout), True


def managed_status_paths(root: Path) -> tuple[list[str], bool]:
    paths, ok = git_status_paths(root)
    return sorted({p for p in paths if is_managed(p)}), ok


def dirty_managed_paths(root: Path) -> list[str]:
    paths, ok = managed_status_paths(root)
    if not ok:
        return ['Git status could not be read']
    return paths


def employee_artifact_status_paths(root: Path) -> list[str]:
    paths, ok = git_status_paths(root)
    if not ok:
        return []
    return sorted({p for p in paths if is_employee_artifact(p)})


def print_employee_artifact_note(root: Path):
    items = employee_artifact_status_paths(root)
    print_list('employee_artifact_changes_not_in_kit_update:', items)
    if items:
        print('employee_artifact_policy: /lbai-update-kit does not stage role_workspace/ or tasks/. Sync them through /lbai-add-evidence or /lbai-finish-task when appropriate.')


def source_from_arg(value: str | None) -> str:
    if value:
        return value
    if os.environ.get('LBAI_WORKSPACE_KIT_SOURCE'):
        return os.environ['LBAI_WORKSPACE_KIT_SOURCE']
    return DEFAULT_SOURCE


def parse_github_release_source(source: str) -> tuple[str, str] | None:
    prefix = 'github-release:'
    if not source.startswith(prefix):
        return None
    value = source[len(prefix):]
    parts = value.split(':', 1)
    repo = parts[0].strip()
    tag = parts[1].strip() if len(parts) == 2 and parts[1].strip() else 'latest'
    if '/' not in repo:
        return None
    return repo, tag


def github_token_from_git_credentials() -> tuple[str | None, str]:
    for env_name in ['LBAI_GITHUB_TOKEN', 'GH_TOKEN', 'GITHUB_TOKEN']:
        token = os.environ.get(env_name, '').strip()
        if token:
            return token, f'environment variable {env_name}'

    try:
        result = subprocess.run(
            ['git', 'credential', 'fill'],
            input='protocol=https\nhost=github.com\n\n',
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as exc:
        return None, f'git credential lookup failed: {exc}'

    if result.returncode != 0:
        detail = (result.stdout + result.stderr).strip()
        return None, f'git credential lookup failed: {detail or "no detail"}'

    values = {}
    for line in result.stdout.splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip()
    token = values.get('password', '')
    if token:
        return token, 'Git credential manager'
    return None, 'no GitHub token found in Git credential manager'


def github_request(url: str, token: str | None = None) -> urllib.request.Request:
    headers = {
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'lbai-update-kit',
        'X-GitHub-Api-Version': '2022-11-28',
    }
    if token:
        headers['Authorization'] = f'Bearer {token}'
    return urllib.request.Request(url, headers=headers)


def github_api_json(url: str, token: str | None = None) -> dict:
    with urllib.request.urlopen(github_request(url, token), timeout=30) as response:
        return json.loads(response.read().decode('utf-8'))


def download_github_url(url: str, target: Path, token: str | None = None):
    with urllib.request.urlopen(github_request(url, token), timeout=60) as response:
        with target.open('wb') as handle:
            shutil.copyfileobj(response, handle)


def resolve_latest_release_tag(repo: str) -> tuple[str | None, str]:
    details = []
    if shutil.which('gh'):
        result = subprocess.run(
            ['gh', 'api', f'repos/{repo}/releases/latest', '--jq', '.tag_name'],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip(), ''
        details.append((result.stdout + result.stderr).strip() or 'gh api returned no release tag')

    token, token_source = github_token_from_git_credentials()
    if token:
        try:
            payload = github_api_json(f'https://api.github.com/repos/{repo}/releases/latest', token)
            tag = str(payload.get('tag_name', '')).strip()
            if tag:
                return tag, ''
            details.append(f'{token_source} returned no release tag')
        except Exception as exc:
            details.append(f'{token_source} API lookup failed: {exc}')
    else:
        details.append(token_source)

    try:
        response = urllib.request.urlopen(github_request(f'https://github.com/{repo}/releases/latest'), timeout=30)
        final_url = response.geturl().rstrip('/')
        tag = final_url.rsplit('/', 1)[-1]
        if tag and tag != 'latest':
            return tag, ''
    except Exception as exc:  # pragma: no cover - depends on local network/auth setup
        details.append(f'public release redirect failed: {exc}')
    return None, 'Could not resolve latest release tag; ' + '; '.join(item for item in details if item)


def release_archive_root(unpack_root: Path) -> Path:
    entries = [path for path in unpack_root.iterdir() if path.is_dir()]
    if len(entries) == 1:
        return entries[0]
    return unpack_root


def has_required_source_paths(source_root: Path) -> bool:
    return all((source_root / path).exists() for path in REQUIRED_SOURCE_PATHS)


def kit_template_root(source_root: Path) -> Path:
    if has_required_source_paths(source_root):
        return source_root
    nested = source_root / KIT_TEMPLATE_DIR
    if nested.is_dir() and has_required_source_paths(nested):
        return nested
    return source_root


def materialize_release_source(source: str, temp_root: Path) -> tuple[Path | None, str, str]:
    parsed = parse_github_release_source(source)
    if not parsed:
        return None, f'Invalid GitHub release source: {source}', 'unknown'
    repo, tag = parsed
    if tag == 'latest':
        resolved_tag, detail = resolve_latest_release_tag(repo)
        if not resolved_tag:
            return None, f'Failed to resolve latest GitHub release for {repo}: {detail}', 'unknown'
        tag = resolved_tag

    archive_dir = temp_root / 'release-archive'
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f'{repo.replace("/", "-")}-{tag}.zip'

    download_details = []
    if shutil.which('gh'):
        result = subprocess.run(
            ['gh', 'release', 'download', tag, '--repo', repo, '--archive=zip', '--dir', str(archive_dir)],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            candidates = sorted(archive_dir.glob('*.zip'))
            if candidates:
                archive_path = candidates[0]
        else:
            detail = (result.stdout + result.stderr).strip()
            download_details.append(f'gh release download failed: {detail or "no detail"}')

    if not archive_path.exists():
        token, token_source = github_token_from_git_credentials()
        if token:
            url = f'https://api.github.com/repos/{repo}/zipball/{tag}'
            try:
                download_github_url(url, archive_path, token)
            except Exception as exc:  # pragma: no cover - depends on local network/auth setup
                download_details.append(f'{token_source} archive download failed: {exc}')
        else:
            download_details.append(token_source)

    if not archive_path.exists():
        url = f'https://github.com/{repo}/archive/refs/tags/{tag}.zip'
        try:
            download_github_url(url, archive_path)
        except Exception as exc:  # pragma: no cover - depends on local network/auth setup
            download_details.append(f'public archive download failed: {exc}')

    if not archive_path.exists():
        return None, (
            f'Failed to download GitHub release archive {repo}@{tag}. '
            'Make sure the employee has access to lbai-workspace-kit and has run the README Git token setup. '
            + '; '.join(item for item in download_details if item)
        ), 'unknown'

    unpack_root = temp_root / 'release-unpacked'
    unpack_root.mkdir(parents=True, exist_ok=True)
    try:
        shutil.unpack_archive(str(archive_path), str(unpack_root))
    except Exception as exc:
        return None, f'Failed to unpack GitHub release archive {repo}@{tag}: {exc}', 'unknown'
    archive_root = release_archive_root(unpack_root)
    source_version = kit_version_from_tree(archive_root)
    if source_version == 'unknown':
        source_version = normalize_version(tag)
    return kit_template_root(archive_root), f'github-release:{repo}:{tag}', source_version


def materialize_source(source: str, temp_root: Path) -> tuple[Path | None, str, str]:
    if source.startswith('github-release:'):
        return materialize_release_source(source, temp_root)

    local = Path(source).expanduser()
    if local.exists():
        resolved = kit_template_root(local.resolve())
        return resolved, f'local:{resolved}', kit_version_from_tree(resolved)

    target = temp_root / 'lbai-workspace-kit'
    clone = subprocess.run(
        ['git', 'clone', '--depth', '1', source, str(target)],
        capture_output=True,
        text=True,
    )
    if clone.returncode != 0:
        detail = (clone.stdout + clone.stderr).strip()
        return None, f'Failed to clone workflow kit source: {detail}', 'unknown'
    resolved = kit_template_root(target)
    return resolved, source, kit_version_from_tree(resolved)


def validate_source(source_root: Path) -> list[str]:
    missing = []
    for path in REQUIRED_SOURCE_PATHS:
        if not (source_root / path).exists():
            missing.append(rel(path))
    return missing


def normalize_version(value: str) -> str:
    return value.strip().lstrip('v')


def workspace_kit_version(root: Path) -> str:
    metadata_path = root / '.lbai' / 'workspace.json'
    if metadata_path.exists():
        try:
            data = json.loads(metadata_path.read_text(encoding='utf-8'))
            version = str(data.get('workspaceKitVersion', '')).strip()
            if version:
                return normalize_version(version)
        except (json.JSONDecodeError, OSError):
            pass
    legacy_path = root / 'lbai_system' / 'VERSION'
    if legacy_path.exists():
        value = read_text(legacy_path).strip()
        if value:
            return normalize_version(value)
    return 'unknown'


def kit_version_from_tree(source_root: Path) -> str:
    for candidate in [source_root, *source_root.parents]:
        version_file = candidate / 'VERSION'
        if not version_file.is_file():
            continue
        if (candidate / 'workspace_template').is_dir() or candidate.name == 'workspace_template':
            value = read_text(version_file).strip()
            if value:
                return normalize_version(value)
    return 'unknown'


def write_workspace_kit_version(root: Path, version: str) -> None:
    version = normalize_version(version)
    metadata_path = root / '.lbai' / 'workspace.json'
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, object] = {}
    if metadata_path.exists():
        try:
            data = json.loads(metadata_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            data = {}
    data['workspaceKitVersion'] = version
    data.setdefault('coreVersionRequired', '>=0.1.0')
    data.setdefault('templateSource', DEFAULT_REPO)
    data.setdefault(
        'managedPaths',
        [rel(path) for path in MANAGED_DIRS + MANAGED_FILES],
    )
    metadata_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def remove_path(path: Path):
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def ignore_temp(_dir: str, names: list[str]) -> set[str]:
    ignored = set()
    for name in names:
        if is_temp_name(name):
            ignored.add(name)
    return ignored


def is_temp_name(name: str) -> bool:
    return name in TEMP_NAMES or any(name.endswith(suffix) for suffix in TEMP_SUFFIXES)


def is_temp_path(path: Path) -> bool:
    return any(is_temp_name(part) for part in path.parts) or is_temp_name(path.name)


def sync_managed_paths(root: Path, source_root: Path, dry_run: bool) -> list[str]:
    touched = []
    for directory in MANAGED_DIRS:
        src = source_root / directory
        dst = root / directory
        if not src.exists():
            continue
        touched.append(rel(directory) + '/')
        if dry_run:
            continue
        remove_path(dst)
        shutil.copytree(src, dst, ignore=ignore_temp)

    for file_path in MANAGED_FILES:
        src = source_root / file_path
        dst = root / file_path
        touched.append(rel(file_path))
        if dry_run:
            continue
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        else:
            remove_path(dst)
    return touched


def changed_managed_files(root: Path) -> list[str]:
    paths, ok = managed_status_paths(root)
    if not ok:
        return []
    files = []
    for path in paths:
        absolute = root / path
        if absolute.is_file():
            files.append(path)
    return sorted(files)


def post_update_changed_files(root: Path) -> list[str]:
    files = changed_managed_files(root)
    metadata = '.lbai/workspace.json'
    status = run_git(root, ['status', '--porcelain', '--', metadata])
    if status.stdout.strip() and metadata not in files:
        files.append(metadata)
    return sorted(files)


def source_managed_files(source_root: Path) -> list[str]:
    files = []
    for directory in MANAGED_DIRS:
        base = source_root / directory
        if not base.exists():
            continue
        for path in base.rglob('*'):
            relative = path.relative_to(source_root)
            if is_temp_path(relative):
                continue
            if path.is_file():
                files.append(rel(relative))
    for file_path in MANAGED_FILES:
        if (source_root / file_path).is_file():
            files.append(rel(file_path))
    return sorted(set(files))


def hygiene_findings(root: Path, paths: list[str]) -> list[str]:
    findings = []
    for path in paths:
        p = root / path
        if any(part in TEMP_NAMES for part in p.parts) or any(path.endswith(suffix) for suffix in TEMP_SUFFIXES):
            findings.append(f'{path}: temporary file')
            continue
        if not p.exists() or not p.is_file():
            continue
        text = read_text(p)
        for pattern in SENSITIVE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                findings.append(f'{path}: sensitive pattern {pattern}')
    return findings


def git_remote_available(root: Path) -> bool:
    result = run_git(root, ['remote'])
    return result.returncode == 0 and bool(result.stdout.strip())


def git_upstream_available(root: Path) -> bool:
    result = run_git(root, ['rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'])
    return result.returncode == 0 and bool(result.stdout.strip())


def git_has_staged_changes(root: Path) -> bool:
    result = run_git(root, ['diff', '--cached', '--quiet'])
    return result.returncode == 1


def stage_managed(root: Path) -> tuple[bool, str]:
    paths = [rel(p) for p in MANAGED_DIRS + MANAGED_FILES] + ['.lbai/workspace.json']
    result = run_git(root, ['add', '-A', '--', *paths])
    if result.returncode != 0:
        return False, (result.stdout + result.stderr).strip()
    return True, ''


def commit_managed(root: Path, message: str) -> tuple[bool, str]:
    ok, detail = stage_managed(root)
    if not ok:
        return False, f'git add failed: {detail}'
    if not git_has_staged_changes(root):
        return True, 'No managed changes to commit'
    result = run_git(root, ['commit', '-m', message])
    if result.returncode != 0:
        return False, f'git commit failed: {(result.stdout + result.stderr).strip()}'
    return True, message


def push_current(root: Path) -> tuple[bool, str]:
    result = run_git(root, ['push'])
    if result.returncode != 0:
        return False, f'git push failed: {(result.stdout + result.stderr).strip()}'
    return True, 'git push completed'


def print_list(title: str, items: list[str]):
    print(title)
    if items:
        for item in items:
            print(f'- {item}')
    else:
        print('- 无')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', help='lbai-workspace-kit release source, Git URL, or local folder. Employees usually leave this empty.')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be synced without changing files.')
    parser.add_argument('--no-commit', action='store_true', help='Update files but do not create a git commit.')
    parser.add_argument('--no-push', action='store_true', help='Commit locally but skip git push.')
    parser.add_argument('--overwrite-managed', action='store_true', help='Overwrite local changes in managed workflow files after employee confirmation.')
    parser.add_argument('--allow-dirty-managed', action='store_true', help='Admin override: update even if managed files are dirty.')
    args = parser.parse_args()

    root = git_root() or Path.cwd()
    before_version = workspace_kit_version(root)
    source = source_from_arg(args.source)
    overwrite_managed = args.overwrite_managed or args.allow_dirty_managed

    pre_dirty = dirty_managed_paths(root)
    if pre_dirty and not overwrite_managed:
        print('kit_update_status: BLOCKED')
        print('commit_readiness: BLOCKED')
        print('git_status: BLOCKED')
        print('reason: managed workflow files have local changes; employee confirmation is required before overwrite')
        print('overwrite_confirmation_required: true')
        print_list('dirty_managed_files:', pre_dirty)
        print_employee_artifact_note(root)
        print('employee_choices:')
        print('- 覆盖升级: discard local changes in the listed workflow files and continue updating')
        print('- 暂不升级: keep local changes and stop')
        return 1

    if not args.no_commit and not args.no_push:
        if not git_remote_available(root):
            print('kit_update_status: BLOCKED')
            print('commit_readiness: BLOCKED')
            print('git_status: BLOCKED')
            print('reason: MISSING_GITHUB_REMOTE: no Git remote configured')
            return 1
        if not git_upstream_available(root):
            print('kit_update_status: BLOCKED')
            print('commit_readiness: BLOCKED')
            print('git_status: BLOCKED')
            print('reason: MISSING_GIT_UPSTREAM: current branch has no upstream')
            return 1

    with tempfile.TemporaryDirectory(prefix='lbai-kit-update-') as temp_name:
        source_root, source_label, source_version = materialize_source(source, Path(temp_name))
        if source_root is None:
            print('kit_update_status: BLOCKED')
            print('commit_readiness: BLOCKED')
            print('git_status: BLOCKED')
            print(f'reason: {source_label}')
            return 1

        missing = validate_source(source_root)
        if missing:
            print('kit_update_status: BLOCKED')
            print('commit_readiness: BLOCKED')
            print('git_status: BLOCKED')
            print('reason: workflow kit source is missing required paths')
            print_list('missing_source_paths:', missing)
            return 1

        source_findings = hygiene_findings(source_root, source_managed_files(source_root))
        if source_findings:
            print('kit_update_status: BLOCKED')
            print('commit_readiness: BLOCKED')
            print('git_status: BLOCKED')
            print('reason: workflow kit source contains sensitive or temporary managed files')
            print_list('findings:', source_findings)
            return 1

        source_version = source_version if source_version != 'unknown' else kit_version_from_tree(source_root)
        touched = sync_managed_paths(root, source_root, args.dry_run)
        if not args.dry_run:
            write_workspace_kit_version(root, source_version)

    if args.dry_run:
        print('kit_update_status: DRY_RUN')
        print('commit_readiness: READY')
        print('git_status: SKIPPED')
        print(f'workspace_root: {root}')
        print(f'source: {source_label}')
        print(f'workspace_kit_version: {before_version}')
        print(f'release_version: {source_version}')
        print_list('managed_paths_to_sync:', touched)
        print_employee_artifact_note(root)
        return 0

    after_version = workspace_kit_version(root)
    changed_files = post_update_changed_files(root)
    findings = hygiene_findings(root, changed_files)
    if findings:
        print('kit_update_status: BLOCKED')
        print('commit_readiness: BLOCKED')
        print('git_status: BLOCKED')
        print('reason: managed workflow update introduced sensitive or temporary files')
        print_list('findings:', findings)
        return 1

    if not changed_files:
        print('kit_update_status: NO_CHANGES')
        print('commit_readiness: READY')
        print('git_status: NO_CHANGES')
        print(f'workspace_root: {root}')
        print(f'source: {source_label}')
        print(f'workspace_kit_version: {after_version}')
        print_list('updated_paths:', [])
        print_employee_artifact_note(root)
        return 0

    if args.no_commit:
        print('kit_update_status: UPDATED')
        print('commit_readiness: READY')
        print('git_status: COMMIT_SKIPPED')
        print(f'workspace_root: {root}')
        print(f'source: {source_label}')
        print(f'previous_version: {before_version}')
        print(f'workspace_kit_version: {after_version}')
        if pre_dirty and overwrite_managed:
            print_list('overwritten_local_changes:', pre_dirty)
        print_list('updated_paths:', changed_files)
        print_employee_artifact_note(root)
        return 0

    message = f'chore(lbai): update workflow kit to {source_version}'
    commit_ok, commit_detail = commit_managed(root, message)
    if not commit_ok:
        print('kit_update_status: UPDATED')
        print('commit_readiness: BLOCKED')
        print('git_status: BLOCKED')
        print(f'reason: {commit_detail}')
        print_list('updated_paths:', changed_files)
        print_employee_artifact_note(root)
        return 1

    if args.no_push:
        print('kit_update_status: UPDATED')
        print('commit_readiness: READY')
        print('git_status: COMMITTED')
        print(f'workspace_root: {root}')
        print(f'source: {source_label}')
        print(f'previous_version: {before_version}')
        print(f'workspace_kit_version: {after_version}')
        print(f'commit_message: {commit_detail}')
        print('github_sync: skipped_by_flag')
        if pre_dirty and overwrite_managed:
            print_list('overwritten_local_changes:', pre_dirty)
        print_list('updated_paths:', changed_files)
        print_employee_artifact_note(root)
        return 0

    push_ok, push_detail = push_current(root)
    if not push_ok:
        print('kit_update_status: UPDATED')
        print('commit_readiness: READY')
        print('git_status: PUSH_FAILED')
        print(f'reason: {push_detail}')
        print_list('updated_paths:', changed_files)
        print_employee_artifact_note(root)
        return 3

    print('kit_update_status: UPDATED')
    print('commit_readiness: READY')
    print('git_status: PUSHED')
    print(f'workspace_root: {root}')
    print(f'source: {source_label}')
    print(f'previous_version: {before_version}')
    print(f'workspace_kit_version: {after_version}')
    print(f'commit_message: {commit_detail}')
    print('github_sync: completed')
    if pre_dirty and overwrite_managed:
        print_list('overwritten_local_changes:', pre_dirty)
    print_list('updated_paths:', changed_files)
    print_employee_artifact_note(root)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
