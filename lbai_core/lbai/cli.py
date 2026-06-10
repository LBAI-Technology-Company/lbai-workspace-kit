#!/usr/bin/env python3
import argparse
import getpass
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


MANAGED_PATHS = [
    'AGENTS.md',
    'README.md',
    '.gitignore',
    '.cursor',
    '.agents',
    'lbai_system',
    'workspace_dashboard.html',
]

EMPLOYEE_DEFAULT_PATHS = [
    'role_workspace',
    'tasks',
]

COMMAND_TO_TOOL = {
    'init': 'init_lbai.py',
    'new-task': 'new_task.py',
    'add-evidence': 'add_evidence.py',
    'search-artifacts': 'search_artifacts.py',
    'finish-task': 'finish_task.py',
}


def kit_root() -> Path:
    if os.environ.get('LBAI_KIT_ROOT'):
        return Path(os.environ['LBAI_KIT_ROOT']).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def template_root() -> Path:
    return kit_root() / 'workspace_template'


def lbai_home() -> Path:
    return Path(os.environ.get('LBAI_HOME', '~/.lbai')).expanduser()


def auth_token_path() -> Path:
    return lbai_home() / 'auth' / 'github_token'


def read_token() -> str:
    if os.environ.get('GITHUB_TOKEN'):
        return os.environ['GITHUB_TOKEN'].strip()
    if os.environ.get('GH_TOKEN'):
        return os.environ['GH_TOKEN'].strip()
    path = auth_token_path()
    if path.exists():
        return path.read_text(encoding='utf-8').strip()
    return ''


def run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None, check: bool = False) -> subprocess.CompletedProcess:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    result = subprocess.run(cmd, cwd=cwd, env=merged_env, text=True)
    if check and result.returncode != 0:
        raise SystemExit(result.returncode)
    return result


def capture(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(cmd, cwd=cwd, env=merged_env, text=True, capture_output=True)


def is_workspace(path: Path) -> bool:
    return (
        (path / 'AGENTS.md').exists()
        and (path / 'lbai_system' / 'runner_contracts' / 'lbai_command_contract_v1.md').exists()
        and (path / 'role_workspace').exists()
        and (path / 'tasks').exists()
    )


def find_workspace(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for path in [current, *current.parents]:
        if is_workspace(path):
            return path
    print('ERROR: current directory is not an LBAI workspace.', file=sys.stderr)
    print('NEXT_STEP: run this command inside a workspace or run lbai init-workspace first.', file=sys.stderr)
    raise SystemExit(2)


def copy_path(src: Path, dst: Path, overwrite: bool) -> None:
    if not src.exists():
        return
    if dst.exists():
        if not overwrite:
            return
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
    else:
        shutil.copy2(src, dst)


def copy_template_into_workspace(workspace: Path, overwrite_managed: bool) -> list[str]:
    src_root = template_root()
    if not src_root.exists():
        print(f'ERROR: workspace_template not found: {src_root}', file=sys.stderr)
        raise SystemExit(2)

    changed = []
    for rel in MANAGED_PATHS:
        src = src_root / rel
        dst = workspace / rel
        before = snapshot_path(dst)
        copy_path(src, dst, overwrite=overwrite_managed)
        if snapshot_path(dst) != before:
            changed.append(rel)

    for rel in EMPLOYEE_DEFAULT_PATHS:
        src = src_root / rel
        dst = workspace / rel
        before = snapshot_path(dst)
        copy_missing_tree(src, dst)
        if snapshot_path(dst) != before:
            changed.append(rel)

    metadata_path = workspace / '.lbai' / 'workspace.json'
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        'workspaceKitVersion': read_version(),
        'coreVersionRequired': '>=0.1.0',
        'templateSource': 'LBAI-Technology-Company/lbai-workspace-kit',
        'managedPaths': MANAGED_PATHS,
    }
    old = metadata_path.read_text(encoding='utf-8') if metadata_path.exists() else ''
    new = json.dumps(metadata, ensure_ascii=False, indent=2) + '\n'
    if old != new:
        metadata_path.write_text(new, encoding='utf-8')
        changed.append('.lbai/workspace.json')

    return sorted(set(changed))


def snapshot_path(path: Path) -> str:
    if not path.exists():
        return 'MISSING'
    if path.is_file():
        try:
            return f'FILE:{path.stat().st_size}:{path.stat().st_mtime_ns}'
        except OSError:
            return 'FILE'
    count = 0
    newest = 0
    for item in path.rglob('*'):
        if item.is_file():
            count += 1
            try:
                newest = max(newest, item.stat().st_mtime_ns)
            except OSError:
                pass
    return f'DIR:{count}:{newest}'


def copy_missing_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    if src.is_file():
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return
    for item in src.rglob('*'):
        rel = item.relative_to(src)
        target = dst / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def read_version() -> str:
    version_file = kit_root() / 'VERSION'
    if version_file.exists():
        return version_file.read_text(encoding='utf-8').strip()
    return '0.1.0'


def lbai_bin_path() -> Path:
    return lbai_home() / 'bin' / 'lbai'


def lbai_kit_install_path() -> Path:
    return lbai_home() / 'kit'


def uninstall(args: argparse.Namespace) -> int:
    home = lbai_home()
    kit_dir = lbai_kit_install_path()
    bin_path = lbai_bin_path()
    token_path = auth_token_path()

    removed = []
    for path in [kit_dir, bin_path]:
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            removed.append(str(path))

    if args.purge_auth and token_path.exists():
        token_path.unlink()
        removed.append(str(token_path))
        auth_dir = token_path.parent
        if auth_dir.exists() and not any(auth_dir.iterdir()):
            auth_dir.rmdir()
            removed.append(str(auth_dir))

    if not removed:
        print('uninstall_status: NO_CHANGES')
        print(f'lbai_home: {home}')
        print('reason: no installed kit or lbai command found')
        return 0

    print('uninstall_status: REMOVED')
    print(f'lbai_home: {home}')
    print('removed:')
    for item in removed:
        print(f'- {item}')
    if not args.purge_auth and token_path.exists():
        print('kept:')
        print(f'- {token_path}')
        print('note: GitHub token kept for reinstall. Use --purge-auth to delete it.')
    print('not_removed:')
    print('- employee workspace folders')
    print('- employee private GitHub repos')
    print('next_step: remove ~/.lbai/bin from PATH if install.sh added it to your shell rc')
    return 0


def auth_login(_args: argparse.Namespace) -> int:
    print('GitHub token will be saved outside the workspace.')
    print('Do not paste this token into README, .env, role_workspace, tasks, or chat artifacts.')
    token = getpass.getpass('Paste GitHub token: ').strip()
    if not token:
        print('auth_status: BLOCKED')
        print('reason: empty token')
        return 2
    path = auth_token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(token + '\n', encoding='utf-8')
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    print('auth_status: SAVED')
    print(f'token_store: {path}')
    print('next_step: lbai init-workspace')
    return 0


def auth_doctor(_args: argparse.Namespace) -> int:
    token = read_token()
    gh = shutil.which('gh')
    gh_authenticated = False
    print('auth_check:')
    print(f'- token_available: {"yes" if token else "no"}')
    print(f'- gh_available: {"yes" if gh else "no"}')
    if gh:
        result = capture(['gh', 'auth', 'status'])
        gh_authenticated = result.returncode == 0
        print(f'- gh_auth_status: {"ok" if gh_authenticated else "not_authenticated"}')
    if token or gh_authenticated:
        print('auth_status: READY')
        return 0
    print('auth_status: BLOCKED')
    print('next_step: lbai auth login')
    return 2


def git_env_with_token() -> tuple[dict[str, str], tempfile.TemporaryDirectory | None]:
    token = read_token()
    if not token:
        return {}, None
    tmp = tempfile.TemporaryDirectory(prefix='lbai-askpass-')
    script = Path(tmp.name) / 'askpass.sh'
    script.write_text(
        '#!/usr/bin/env sh\n'
        'case "$1" in\n'
        '  *Username*) printf "%s\\n" "x-access-token" ;;\n'
        f'  *) printf "%s\\n" "{token}" ;;\n'
        'esac\n',
        encoding='utf-8',
    )
    script.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    return {'GIT_ASKPASS': str(script), 'GIT_TERMINAL_PROMPT': '0'}, tmp


def init_workspace(args: argparse.Namespace) -> int:
    repo_url = args.repo_url or input('GitHub repo URL: ').strip()
    local_path_raw = args.path or input('Local folder path: ').strip()
    if not repo_url or not local_path_raw:
        print('init_status: BLOCKED')
        print('reason: repo URL and local path are required')
        return 2

    local_path = Path(local_path_raw).expanduser().resolve()
    env, tmp = git_env_with_token()
    try:
        if local_path.exists() and any(local_path.iterdir()):
            if not (local_path / '.git').exists():
                print('init_status: BLOCKED')
                print(f'reason: local path exists and is not a git repo: {local_path}')
                return 2
            print(f'using_existing_repo: {local_path}')
        else:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            result = run(['git', 'clone', repo_url, str(local_path)], env=env)
            if result.returncode != 0:
                print('init_status: BLOCKED')
                print('reason: git clone failed')
                print('next_step: check repo URL, token permissions, or run gh auth login')
                return result.returncode or 2

        if (local_path / '.git').exists():
            run(['git', 'remote', 'set-url', 'origin', repo_url], cwd=local_path)

        changed = copy_template_into_workspace(local_path, overwrite_managed=True)

        if not args.no_commit:
            stage_paths = [p for p in [*MANAGED_PATHS, *EMPLOYEE_DEFAULT_PATHS, '.lbai/workspace.json'] if (local_path / p).exists()]
            run(['git', 'add', '--', *stage_paths], cwd=local_path)
            status = capture(['git', 'status', '--porcelain'], cwd=local_path)
            if status.stdout.strip():
                commit = run(['git', 'commit', '-m', 'chore(lbai): initialize workspace kit'], cwd=local_path)
                if commit.returncode != 0:
                    print('git_status: COMMIT_FAILED')
                elif not args.no_push:
                    push = run(['git', 'push', '-u', 'origin', current_branch(local_path)], cwd=local_path, env=env)
                    print(f'git_status: {"PUSHED" if push.returncode == 0 else "PUSH_FAILED"}')
            else:
                print('git_status: NO_CHANGES')
        else:
            print('git_status: COMMIT_SKIPPED')

        doctor_code = doctor(argparse.Namespace(path=str(local_path), allow_missing_upstream=args.no_commit or args.no_push))
        print('init_status: READY' if doctor_code == 0 else 'init_status: NEEDS_REVIEW')
        print(f'workspace_path: {local_path}')
        print(f'next_step: cd {local_path} && lbai doctor')
        print('changed:')
        for item in changed or ['None']:
            print(f'- {item}')
        return 0 if doctor_code == 0 else doctor_code
    finally:
        if tmp:
            tmp.cleanup()


def current_branch(cwd: Path) -> str:
    result = capture(['git', 'branch', '--show-current'], cwd=cwd)
    return result.stdout.strip() or 'main'


def doctor(args: argparse.Namespace) -> int:
    root = Path(args.path).expanduser().resolve() if args.path else find_workspace()
    print('# LBAI doctor')
    print(f'workspace_root: {root}')
    if not is_workspace(root):
        print('workspace_status: BLOCKED')
        print('reason: missing AGENTS.md, lbai_system, role_workspace, or tasks')
        return 2

    checks = [
        ('bootstrap', ['python3', 'lbai_system/tools/bootstrap_check.py']),
        ('codex_adapter', ['python3', 'lbai_system/tools/check_codex_adapter.py']),
        ('cursor_commands', ['python3', 'lbai_system/tools/check_cursor_commands.py']),
    ]
    ok = True
    for name, cmd in checks:
        print(f'## {name}')
        result = capture(cmd, cwd=root)
        if result.stdout:
            print(result.stdout, end='')
        if result.stderr:
            print(result.stderr, end='', file=sys.stderr)
        if result.returncode != 0:
            if not (getattr(args, 'allow_missing_upstream', False) and 'MISSING_GIT_UPSTREAM' in result.stdout):
                ok = False
    print(f'doctor_status: {"READY" if ok else "BLOCKED"}')
    return 0 if ok else 2


def remove_managed_paths(workspace: Path) -> list[str]:
    removed = []
    for rel in MANAGED_PATHS:
        target = workspace / rel
        if not target.exists():
            continue
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()
        removed.append(rel)

    metadata_path = workspace / '.lbai' / 'workspace.json'
    if metadata_path.exists():
        metadata_path.unlink()
        removed.append('.lbai/workspace.json')
        lbai_dir = metadata_path.parent
        if lbai_dir.exists() and not any(lbai_dir.iterdir()):
            lbai_dir.rmdir()

    return sorted(removed)


def remove_kit(args: argparse.Namespace) -> int:
    if not args.confirm:
        print('remove_kit_status: BLOCKED', file=sys.stderr)
        print('reason: destructive operation requires --confirm', file=sys.stderr)
        print('keeps: role_workspace/, tasks/, and all other employee-owned files', file=sys.stderr)
        print('removes: company-managed workflow kit paths only', file=sys.stderr)
        print('next_step: lbai remove-kit --confirm', file=sys.stderr)
        return 2

    root = find_workspace()
    removed = remove_managed_paths(root)

    if not removed:
        print('remove_kit_status: NO_CHANGES')
        print('kept:')
        for item in EMPLOYEE_DEFAULT_PATHS:
            print(f'- {item}')
        return 0

    if args.no_commit:
        print('remove_kit_status: REMOVED')
        print('git_status: COMMIT_SKIPPED')
        print('removed:')
        for item in removed:
            print(f'- {item}')
        print('kept:')
        for item in EMPLOYEE_DEFAULT_PATHS:
            print(f'- {item}')
        return 0

    run(['git', 'add', '-u', '--', *MANAGED_PATHS, '.lbai'], cwd=root)
    status = capture(['git', 'status', '--porcelain'], cwd=root)
    if not status.stdout.strip():
        print('remove_kit_status: REMOVED')
        print('git_status: NO_CHANGES')
        print('removed:')
        for item in removed:
            print(f'- {item}')
        return 0

    message = 'chore(lbai): remove workflow kit'
    commit = run(['git', 'commit', '-m', message], cwd=root)
    if commit.returncode != 0:
        print('remove_kit_status: REMOVED')
        print('git_status: COMMIT_FAILED')
        return commit.returncode or 2
    if args.no_push:
        print('remove_kit_status: REMOVED')
        print('git_status: COMMITTED')
        print('removed:')
        for item in removed:
            print(f'- {item}')
        return 0

    env, tmp = git_env_with_token()
    try:
        push = run(['git', 'push'], cwd=root, env=env)
    finally:
        if tmp:
            tmp.cleanup()
    print('remove_kit_status: REMOVED')
    print(f'git_status: {"PUSHED" if push.returncode == 0 else "PUSH_FAILED"}')
    print('removed:')
    for item in removed:
        print(f'- {item}')
    print('kept:')
    for item in EMPLOYEE_DEFAULT_PATHS:
        print(f'- {item}')
    return 0 if push.returncode == 0 else 2


def update_kit(args: argparse.Namespace) -> int:
    root = find_workspace()
    changed = copy_template_into_workspace(root, overwrite_managed=True)
    doctor_code = doctor(argparse.Namespace(path=str(root)))

    if args.no_commit:
        print('update_status: UPDATED')
        print('git_status: COMMIT_SKIPPED')
        print_changed(changed)
        return doctor_code

    stage_paths = [p for p in [*MANAGED_PATHS, '.lbai/workspace.json'] if (root / p).exists()]
    run(['git', 'add', '--', *stage_paths], cwd=root)
    status = capture(['git', 'status', '--porcelain'], cwd=root)
    if not status.stdout.strip():
        print('update_status: NO_CHANGES')
        print('git_status: NO_CHANGES')
        return doctor_code

    message = f'chore(lbai): update workflow kit to {read_version()}'
    commit = run(['git', 'commit', '-m', message], cwd=root)
    if commit.returncode != 0:
        print('update_status: BLOCKED')
        print('git_status: COMMIT_FAILED')
        return commit.returncode or 2
    if args.no_push:
        print('update_status: UPDATED')
        print('git_status: COMMITTED')
        return doctor_code

    env, tmp = git_env_with_token()
    try:
        push = run(['git', 'push'], cwd=root, env=env)
    finally:
        if tmp:
            tmp.cleanup()
    print('update_status: UPDATED')
    print(f'git_status: {"PUSHED" if push.returncode == 0 else "PUSH_FAILED"}')
    print_changed(changed)
    return 0 if push.returncode == 0 and doctor_code == 0 else 2


def print_changed(changed: list[str]) -> None:
    print('changed:')
    for item in changed or ['None']:
        print(f'- {item}')


def run_workspace_tool(command: str, args: argparse.Namespace, extra: list[str]) -> int:
    root = find_workspace()
    tool = COMMAND_TO_TOOL[command]
    cmd = ['python3', f'lbai_system/tools/{tool}', *extra]
    return run(cmd, cwd=root).returncode


def finish_task(args: argparse.Namespace, extra: list[str]) -> int:
    root = find_workspace()
    if extra:
        return run(['python3', 'lbai_system/tools/finish_task.py', *extra], cwd=root).returncode
    resolved = capture(['python3', 'lbai_system/tools/resolve_current_task.py', 'finish'], cwd=root)
    print(resolved.stdout, end='')
    if resolved.returncode != 0:
        return resolved.returncode
    task = parse_task_folder(resolved.stdout)
    if not task:
        return 2
    return run(['python3', 'lbai_system/tools/finish_task.py', task], cwd=root).returncode


def execute_task(_args: argparse.Namespace, extra: list[str]) -> int:
    root = find_workspace()
    if extra:
        task = extra[0]
        rest = extra[1:]
    else:
        resolved = capture(['python3', 'lbai_system/tools/resolve_current_task.py', 'execute'], cwd=root)
        print(resolved.stdout, end='')
        if resolved.returncode != 0:
            return resolved.returncode
        task = parse_task_folder(resolved.stdout)
        rest = []
    if not task:
        return 2
    print('execute_status: CONTEXT_READY')
    print(f'task_folder: {task}')
    print('next_step: open this workspace in Codex or Cursor and run /lbai-execute-task so the model can generate task_output.md from the task contract and evidence.')
    if rest:
        print(f'ignored_extra_args: {" ".join(rest)}')
    return 0


def parse_task_folder(text: str) -> str:
    for line in text.splitlines():
        if line.startswith('TASK_FOLDER '):
            return line.split(' ', 1)[1].strip()
    return ''


def serve_dashboard(args: argparse.Namespace) -> int:
    root = find_workspace()
    return run(['python3', 'lbai_system/tools/serve_dashboard.py', *args.extra], cwd=root).returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='lbai')
    parser.add_argument('--version', action='version', version=f'lbai {read_version()}')
    sub = parser.add_subparsers(dest='command')

    auth = sub.add_parser('auth')
    auth_sub = auth.add_subparsers(dest='auth_command')
    auth_sub.add_parser('login')
    auth_sub.add_parser('doctor')

    init = sub.add_parser('init-workspace')
    init.add_argument('--repo-url')
    init.add_argument('--path')
    init.add_argument('--no-commit', action='store_true')
    init.add_argument('--no-push', action='store_true')

    doc = sub.add_parser('doctor')
    doc.add_argument('--path')

    update = sub.add_parser('update-kit')
    update.add_argument('--no-commit', action='store_true')
    update.add_argument('--no-push', action='store_true')

    remove = sub.add_parser(
        'remove-kit',
        help='Remove company-managed workflow kit files from the current workspace.',
    )
    remove.add_argument(
        '--confirm',
        action='store_true',
        help='Required. Removes managed kit files but keeps role_workspace/ and tasks/.',
    )
    remove.add_argument('--no-commit', action='store_true')
    remove.add_argument('--no-push', action='store_true')

    uninstall_parser = sub.add_parser('uninstall')
    uninstall_parser.add_argument(
        '--purge-auth',
        action='store_true',
        help='Also delete saved GitHub token under ~/.lbai/auth/.',
    )
    sub.add_parser('init')
    sub.add_parser('new-task')
    sub.add_parser('add-evidence')
    sub.add_parser('search-artifacts')
    sub.add_parser('execute-task')
    sub.add_parser('finish-task')
    serve = sub.add_parser('serve-dashboard')
    serve.add_argument('extra', nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    known, extra = parser.parse_known_args(argv)

    if known.command == 'auth':
        if known.auth_command == 'login':
            return auth_login(known)
        if known.auth_command == 'doctor':
            return auth_doctor(known)
        parser.error('auth requires login or doctor')
    if known.command == 'init-workspace':
        return init_workspace(known)
    if known.command == 'doctor':
        return doctor(known)
    if known.command == 'update-kit':
        return update_kit(known)
    if known.command == 'remove-kit':
        return remove_kit(known)
    if known.command == 'uninstall':
        return uninstall(known)
    if known.command in {'init', 'new-task', 'add-evidence', 'search-artifacts'}:
        return run_workspace_tool(known.command, known, extra)
    if known.command == 'finish-task':
        return finish_task(known, extra)
    if known.command == 'execute-task':
        return execute_task(known, extra)
    if known.command == 'serve-dashboard':
        return serve_dashboard(known)

    parser.print_help()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
