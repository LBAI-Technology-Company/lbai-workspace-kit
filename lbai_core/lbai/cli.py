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
import urllib.error
import urllib.request
from datetime import datetime, timezone
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
    'prompt_lab',
]
KNOWLEDGE_SERVICE_BASE_URL = 'https://workflow-kit.lbai.ai'
KNOWLEDGE_SERVICE_API_KEY_ENV = 'LBAI_KNOWLEDGE_SERVICE_API_KEY'
KNOWLEDGE_SERVICE_API_KEY_HEADER = 'X-LBAI-API-Key'

COMMAND_TO_TOOL = {
    'init': 'init_lbai.py',
    'new-task': 'new_task.py',
    'add-evidence': 'add_evidence.py',
    'search-artifacts': 'search_artifacts.py',
    'finish-task': 'finish_task.py',
}

AI_COMMAND_SLUG = {
    'init': '/lbai-init',
    'new-task': '/lbai-new-task',
    'add-evidence': '/lbai-add-evidence',
    'search-artifacts': '/lbai-search-artifacts',
    'finish-task': '/lbai-finish-task',
}


def python_cmd() -> list[str]:
    return [sys.executable]


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


def knowledge_service_auth_path() -> Path:
    return lbai_home() / 'auth' / 'knowledge_service.json'


def saved_token() -> str:
    path = auth_token_path()
    if path.exists():
        return path.read_text(encoding='utf-8').strip()
    return ''


def env_token() -> str:
    return (os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN') or '').strip()


def gh_authenticated() -> bool:
    if not shutil.which('gh'):
        return False
    return capture(['gh', 'auth', 'status']).returncode == 0


def read_token() -> str:
    token = env_token()
    if token:
        return token
    return saved_token()


def auth_source_label() -> str:
    if saved_token():
        return f'token_store:{auth_token_path()}'
    if env_token():
        return 'environment:GITHUB_TOKEN or GH_TOKEN'
    if gh_authenticated():
        return 'github_cli:gh auth login'
    return ''


def run_with_input(cmd: list[str], input_text: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(cmd, input=input_text, text=True, capture_output=True, env=merged_env)


def erase_git_github_credentials() -> None:
    payload = 'protocol=https\nhost=github.com\n\n'
    run_with_input(['git', 'credential', 'reject'], payload)
    if sys.platform == 'darwin':
        run_with_input(['git', 'credential-osxkeychain', 'erase'], payload)


def sync_git_credentials(token: str) -> tuple[bool, str]:
    token = token.strip()
    if not token:
        return False, 'empty token'

    erase_git_github_credentials()

    gh = shutil.which('gh')
    if gh:
        login = run_with_input([gh, 'auth', 'login', '--with-token'], token + '\n')
        if login.returncode != 0:
            detail = (login.stderr or login.stdout or '').strip()
            return False, detail or 'GitHub CLI 拒绝了 Token；请向管理员确认 Token 是否有效且有 repo 权限'
        setup = capture([gh, 'auth', 'setup-git'])
        if setup.returncode != 0:
            detail = (setup.stderr or setup.stdout or '').strip()
            return False, detail or 'gh auth setup-git failed'
        return True, '已同步到 GitHub CLI；终端 git push 可直接使用'

    approve_payload = (
        'protocol=https\n'
        'host=github.com\n'
        'username=x-access-token\n'
        f'password={token}\n\n'
    )
    approve = run_with_input(['git', 'credential', 'approve'], approve_payload)
    if approve.returncode == 0:
        return True, '已同步到 Git 凭据管理器；终端 git push 可直接使用'
    detail = (approve.stderr or approve.stdout or '').strip()
    return False, detail or 'git credential approve failed'


def setup_gh_for_git() -> tuple[bool, str]:
    gh = shutil.which('gh')
    if not gh:
        return False, '未安装 GitHub CLI (gh)'
    if not gh_authenticated():
        return False, 'gh 未登录'
    result = capture([gh, 'auth', 'setup-git'])
    if result.returncode == 0:
        return True, '已配置 Git 使用 gh 凭据；终端 git push 可直接使用'
    detail = (result.stderr or result.stdout or '').strip()
    return False, detail or 'gh auth setup-git failed'


def git_credential_password() -> str:
    result = run_with_input(['git', 'credential', 'fill'], 'protocol=https\nhost=github.com\n\n')
    if result.returncode != 0:
        return ''
    for line in result.stdout.splitlines():
        if line.startswith('password='):
            return line.split('=', 1)[1].strip()
    return ''


def git_credential_sync_status() -> tuple[str, str]:
    token = read_token()
    cred = git_credential_password()
    if token:
        if cred and token == cred:
            return 'ok', '已保存 Token 与 Git 凭据一致'
        if cred:
            return 'stale', 'Git 凭据与已保存 Token 不一致；请运行 lbai auth login 粘贴新 Token，或直接回车重新同步'
        return 'missing', 'Token 已保存但未同步到 Git；请运行 lbai auth login 并直接回车重新同步'
    if gh_authenticated():
        if cred:
            return 'ok', '使用 GitHub CLI 凭据'
        ok, msg = setup_gh_for_git()
        if ok:
            return 'ok', msg
        return 'needs_setup', 'gh 已登录但 Git 未配置；请运行 lbai auth login 并直接回车'
    if cred:
        return 'ok', 'Git 凭据管理器已配置'
    return 'missing', '尚未配置 GitHub 认证；请运行 lbai auth login'


def print_git_credential_sync(ok: bool, message: str) -> None:
    print(f'git_credential_sync: {"OK" if ok else "NEEDS_ATTENTION"}')
    print(f'git_credential_note: {message}')
    if not ok:
        print('manual_fix: 重新运行 lbai auth login；若仍失败，联系管理员确认 Token 是否有 repo 权限')


def ensure_git_credentials_synced() -> tuple[bool, str]:
    token = read_token()
    if token:
        return sync_git_credentials(token)
    if gh_authenticated():
        return setup_gh_for_git()
    return False, 'no token or gh session to sync'


def read_knowledge_service_auth() -> dict:
    path = knowledge_service_auth_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def write_knowledge_service_auth(
    api_key: str,
    api_key_header: str = KNOWLEDGE_SERVICE_API_KEY_HEADER,
    base_url: str = KNOWLEDGE_SERVICE_BASE_URL,
) -> Path:
    path = knowledge_service_auth_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        'schema_version': 'knowledge_service_auth_v1',
        'api_key': api_key.strip(),
        'api_key_header': (api_key_header or KNOWLEDGE_SERVICE_API_KEY_HEADER).strip(),
        'base_url': (base_url or KNOWLEDGE_SERVICE_BASE_URL).strip(),
        'created_at': datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return path


def verify_knowledge_service_key(
    api_key: str,
    api_key_header: str = KNOWLEDGE_SERVICE_API_KEY_HEADER,
    base_url: str = KNOWLEDGE_SERVICE_BASE_URL,
    timeout: int = 10,
) -> tuple[bool, str]:
    url = base_url.rstrip('/') + '/v1/search/evidence'
    payload = {
        'workspace_repo_id': 'auth-check',
        'employee_user_id': 'auth-check',
        'task_text': 'auth check',
        'query_plan': {
            'schema_version': 'backend_search_query_plan_v1',
            'query': 'auth check',
            'keywords': [],
            'concepts': [],
            'entity_types': [],
            'prefer_status': [],
            'limit': 1,
        },
        'limit': 1,
    }
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        (api_key_header or KNOWLEDGE_SERVICE_API_KEY_HEADER).strip(): api_key.strip(),
    }
    request = urllib.request.Request(url, data=body, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
            return True, f'backend_key_check: OK ({response.status})'
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            return False, f'backend_key_check: FAILED HTTP_{exc.code} ({exc.reason}); API key was not saved.'
        if 400 <= exc.code < 500:
            return True, f'backend_key_check: REACHED_BACKEND HTTP_{exc.code} ({exc.reason}); key was accepted but auth-check payload was rejected.'
        return False, f'backend_key_check: FAILED HTTP_{exc.code} ({exc.reason}); API key was not saved.'
    except urllib.error.URLError as exc:
        return False, f'backend_key_check: FAILED URL_ERROR ({exc.reason}); API key was not saved.'
    except TimeoutError:
        return False, 'backend_key_check: FAILED TIMEOUT; API key was not saved.'
    except Exception as exc:
        return False, f'backend_key_check: FAILED {exc}; API key was not saved.'


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
    metadata = merged_workspace_metadata(workspace, {
        'workspaceKitVersion': read_version(),
        'coreVersionRequired': '>=0.1.0',
        'templateSource': 'LBAI-Technology-Company/lbai-workspace-kit',
        'managedPaths': MANAGED_PATHS,
    })
    old = metadata_path.read_text(encoding='utf-8') if metadata_path.exists() else ''
    new = json.dumps(metadata, ensure_ascii=False, indent=2) + '\n'
    if old != new:
        metadata_path.write_text(new, encoding='utf-8')
        changed.append('.lbai/workspace.json')

    return sorted(set(changed))


def default_employee_user_id(workspace: Path) -> str:
    raw = workspace.name.lower()
    cleaned = ''.join(ch if ch.isalnum() else '-' for ch in raw).strip('-')
    return cleaned or 'employee'


def default_workspace_metadata(workspace: Path) -> dict:
    repo_id = workspace.name
    return {
        'employee_identity': {
            'employee_user_id': default_employee_user_id(workspace),
            'display_name': '',
            'email': '',
            'department': '',
        },
        'knowledge_service': {
            'enabled': True,
            'base_url': KNOWLEDGE_SERVICE_BASE_URL,
            'api_key_header': KNOWLEDGE_SERVICE_API_KEY_HEADER,
            'auth_mode': 'local_api_key',
            'workspace_repo_id': repo_id,
            'search_timeout_seconds': 20,
        },
    }


def deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def merged_workspace_metadata(workspace: Path, base_metadata: dict) -> dict:
    metadata_path = workspace / '.lbai' / 'workspace.json'
    existing = {}
    if metadata_path.exists():
        try:
            loaded = json.loads(metadata_path.read_text(encoding='utf-8'))
            if isinstance(loaded, dict):
                existing = loaded
        except (OSError, json.JSONDecodeError):
            existing = {}
    metadata = deep_merge(deep_merge(base_metadata, default_workspace_metadata(workspace)), existing)
    knowledge = metadata.setdefault('knowledge_service', {})
    if isinstance(knowledge, dict):
        legacy_key = str(knowledge.pop('api_key', '') or '').strip()
        if legacy_key and not read_knowledge_service_auth().get('api_key'):
            write_knowledge_service_auth(legacy_key, str(knowledge.get('api_key_header') or KNOWLEDGE_SERVICE_API_KEY_HEADER))
        knowledge['enabled'] = True
        knowledge['base_url'] = KNOWLEDGE_SERVICE_BASE_URL
        knowledge['api_key_header'] = KNOWLEDGE_SERVICE_API_KEY_HEADER
        knowledge['auth_mode'] = 'local_api_key'
        env_key = os.environ.get(KNOWLEDGE_SERVICE_API_KEY_ENV, '').strip()
        if env_key and not read_knowledge_service_auth().get('api_key'):
            write_knowledge_service_auth(env_key, KNOWLEDGE_SERVICE_API_KEY_HEADER)
        knowledge.setdefault('workspace_repo_id', workspace.name)
        knowledge.setdefault('search_timeout_seconds', 20)
    return metadata


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
    backend_auth_path = knowledge_service_auth_path()

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
    if args.purge_auth and backend_auth_path.exists():
        backend_auth_path.unlink()
        removed.append(str(backend_auth_path))
    if args.purge_auth:
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
    kept_auth = [path for path in (token_path, backend_auth_path) if path.exists()]
    if not args.purge_auth and kept_auth:
        print('kept:')
        for path in kept_auth:
            print(f'- {path}')
        print('note: auth files kept for reinstall. Use --purge-auth to delete them.')
    print('not_removed:')
    print('- employee workspace folders')
    print('- employee private GitHub repos')
    print('next_step: remove ~/.lbai/bin from PATH if install.sh added it to your shell rc')
    return 0


def auth_login(_args: argparse.Namespace) -> int:
    path = auth_token_path()
    source = auth_source_label()

    if source:
        print('auth_check: already configured')
        print(f'auth_source: {source}')
        print('如需更换 Token 请粘贴新 Token；直接回车会重新同步 Git 凭据（推荐换 Token 后执行一次）。')
        token = getpass.getpass('GitHub Token: ').strip()
        if not token:
            print('auth_status: UNCHANGED')
            ok, message = ensure_git_credentials_synced()
            print_git_credential_sync(ok, message)
            print('next_step: lbai auth doctor  # 确认 READY 后再 lbai init-workspace')
            return 0 if ok else 2
    else:
        print('GitHub Token 将保存在本机 ~/.lbai/auth/，不会写入工作区文件。')
        print('粘贴 Token 后，lbai 会自动同步到 Git，终端 git push 也能直接使用。')
        print('Do not paste this token into README, .env, role_workspace, tasks, or chat artifacts.')
        token = getpass.getpass('Paste GitHub token: ').strip()
        if not token:
            if gh_authenticated():
                print('auth_status: USING_GH')
                ok, message = setup_gh_for_git()
                print_git_credential_sync(ok, message)
                print('next_step: lbai auth doctor  # 确认 READY 后再 lbai init-workspace')
                return 0 if ok else 2
            print('auth_status: BLOCKED')
            print('reason: empty token')
            print('next_step: 向管理员索取 GitHub Token（需 repo 权限），或先运行 gh auth login 后再执行 lbai auth login 并回车')
            return 2

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(token + '\n', encoding='utf-8')
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    print('auth_status: SAVED')
    print(f'token_store: {path}')
    ok, message = sync_git_credentials(token)
    print_git_credential_sync(ok, message)
    print('next_step: lbai auth doctor  # 确认 READY 后再 lbai init-workspace')
    return 0 if ok else 2


def auth_backend_login(args: argparse.Namespace) -> int:
    existing = read_knowledge_service_auth()
    if existing.get('api_key'):
        print('backend_auth_check: already configured')
        print(f'backend_auth_store: {knowledge_service_auth_path()}')
        print('如需重新配置请输入新 API Key；直接回车保持不变。')
        prompt = 'LBAI backend API key: '
    else:
        print('LBAI backend API key will be saved outside the workspace.')
        print('It will not be written to workspace files, Git commits, role_workspace, or tasks.')
        prompt = 'Paste LBAI backend API key: '

    api_key = (args.api_key or '').strip()
    if not api_key:
        api_key = getpass.getpass(prompt).strip()
    if not api_key:
        if args.optional:
            print('backend_auth_status: SKIPPED')
            print('next_step: lbai auth backend-login')
            return 0
        if existing.get('api_key'):
            print('backend_auth_status: UNCHANGED')
            print('next_step: lbai init-workspace')
            return 0
        print('backend_auth_status: BLOCKED')
        print('reason: empty API key')
        return 2

    if not args.no_verify:
        ok, message = verify_knowledge_service_key(
            api_key,
            args.api_key_header,
            args.base_url,
            args.verify_timeout,
        )
        print(message)
        if not ok:
            print('backend_auth_status: BLOCKED')
            print('next_step: 检查 API Key 是否正确；如果只是暂时无法联网，可使用 lbai auth backend-login --no-verify 离线保存。')
            return 2
    else:
        print('backend_key_check: SKIPPED (--no-verify)')

    path = write_knowledge_service_auth(api_key, args.api_key_header, args.base_url)
    print('backend_auth_status: SAVED')
    print(f'backend_auth_store: {path}')
    print('next_step: lbai init-workspace')
    return 0


def auth_doctor(_args: argparse.Namespace) -> int:
    token = read_token()
    gh = shutil.which('gh')
    gh_ok = gh_authenticated() if gh else False
    source = auth_source_label()
    backend_auth = read_knowledge_service_auth()
    sync_status, sync_detail = git_credential_sync_status()
    print('auth_check:')
    print(f'- token_available: {"yes" if token else "no"}')
    print(f'- gh_available: {"yes" if gh else "no"}')
    print(f'- gh_auth_status: {"ok" if gh_ok else "not_authenticated"}')
    print(f'- git_credential_sync: {sync_status}')
    print(f'- git_credential_note: {sync_detail}')
    print(f'- backend_api_key_available: {"yes" if backend_auth.get("api_key") else "no"}')
    if source:
        print(f'- auth_source: {source}')
    if backend_auth.get('api_key'):
        print(f'- backend_auth_source: {knowledge_service_auth_path()}')
    if sync_status == 'ok':
        print('auth_status: READY')
        print('next_step: lbai init-workspace')
        return 0
    if sync_status in {'stale', 'missing', 'needs_setup'}:
        print('auth_status: NEEDS_SYNC')
        print('next_step: lbai auth login  # 粘贴新 Token，或直接回车重新同步')
        return 2
    print('auth_status: BLOCKED')
    print('next_step: lbai auth login  # 粘贴管理员提供的 GitHub Token')
    return 2


def repo_basename(repo_url: str) -> str:
    name = repo_url.rstrip('/').split('/')[-1]
    if name.endswith('.git'):
        name = name[:-4]
    return name or 'lbai-workspace'


def default_workspace_path(repo_url: str) -> Path:
    return Path.cwd() / repo_basename(repo_url)


def workspace_path_from_pick(picked: str, repo_url: str) -> Path:
    picked_path = Path(picked).expanduser()
    if picked_path.name == repo_basename(repo_url):
        return picked_path
    return picked_path / repo_basename(repo_url)


def pick_folder_macos(prompt: str) -> str:
    escaped = prompt.replace('\\', '\\\\').replace('"', '\\"')
    script = f'POSIX path of (choose folder with prompt "{escaped}")'
    result = capture(['osascript', '-e', script])
    if result.returncode != 0:
        return ''
    return result.stdout.strip()


def pick_folder_windows(prompt: str) -> str:
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        try:
            root.attributes('-topmost', True)
        except tk.TclError:
            pass
        root.update()
        picked = filedialog.askdirectory(title=prompt, mustexist=True)
        root.destroy()
        if picked:
            return picked
    except Exception:
        pass

    escaped = prompt.replace("'", "''")
    ps = (
        'Add-Type -AssemblyName System.Windows.Forms; '
        '$d = New-Object System.Windows.Forms.FolderBrowserDialog; '
        f"$d.Description = '{escaped}'; "
        'if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { '
        '$d.SelectedPath }'
    )
    result = capture(['powershell', '-NoProfile', '-Command', ps])
    if result.returncode == 0:
        return result.stdout.strip()
    return ''


def pick_folder_interactive(prompt: str) -> str:
    if sys.platform == 'darwin':
        return pick_folder_macos(prompt)
    if sys.platform == 'win32':
        return pick_folder_windows(prompt)
    return ''


def resolve_local_path(repo_url: str, path_arg: str | None) -> Path:
    if path_arg and path_arg.strip():
        return Path(path_arg.strip()).expanduser()

    default = default_workspace_path(repo_url)
    default_text = str(default)
    picker_prompt = '请选择 LBAI 工作区保存位置'

    if sys.stdin.isatty() and sys.platform in {'darwin', 'win32'}:
        print(f'默认工作区路径: {default_text}')
        print('正在打开文件夹选择窗口；取消则使用默认路径。')
        print('提示: 工作区会创建在「所选目录/<仓库名>」；请在 Cursor 中打开内层工作区目录，不要只打开外层父目录。')
        picked = pick_folder_interactive(picker_prompt)
        if picked:
            return workspace_path_from_pick(picked, repo_url)
        return default

    entered = input(f'本地文件夹路径 [{default_text}]: ').strip()
    return Path(entered or default_text).expanduser()


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
    repo_url = args.repo_url or input('GitHub 仓库地址: ').strip()
    if not repo_url:
        print('init_status: BLOCKED')
        print('reason: repo URL is required')
        return 2

    local_path = resolve_local_path(repo_url, args.path).resolve()
    print(f'workspace_path: {local_path}')
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
            run(['git', 'add', '-f', '--', *stage_paths], cwd=local_path)
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
        print(f'cursor_open: {local_path}')
        parent = local_path.parent.resolve()
        if parent != local_path and not is_workspace(parent):
            print(f'cursor_note: 请在 Cursor 或 Codex 中打开 cursor_open 路径；/lbai-* 命令只在该目录下的 .cursor/commands/ 生效，不要打开外层父目录 {parent}')
        else:
            print('cursor_note: 请在 Cursor 或 Codex 中打开 cursor_open 路径；/lbai-* 命令只在该目录下的 .cursor/commands/ 生效')
        print(f'next_step: 用 Cursor 或 Codex 打开 cursor_open 目录，运行 /lbai-init')
        print(f'cursor_cli: cursor "{local_path}"')
        print('day1_reminder: 业务命令必须在 Cursor/Codex 桌面 App 里输入 /lbai-*；不要在终端裸跑 lbai new-task 等命令。')
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
        ('bootstrap', [*python_cmd(), 'lbai_system/tools/bootstrap_check.py']),
        ('codex_adapter', [*python_cmd(), 'lbai_system/tools/check_codex_adapter.py']),
        ('cursor_commands', [*python_cmd(), 'lbai_system/tools/check_cursor_commands.py']),
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
    cmd = [*python_cmd(), 'lbai_system/tools/update_kit.py']
    if args.no_commit:
        cmd.append('--no-commit')
    if args.no_push:
        cmd.append('--no-push')
    return run(cmd, cwd=root).returncode


def print_changed(changed: list[str]) -> None:
    print('changed:')
    for item in changed or ['None']:
        print(f'- {item}')


def has_enrichment_flag(extra: list[str]) -> bool:
    return any(item == '--enrichment' or item.startswith('--enrichment=') for item in extra)


def print_terminal_misuse_hint(command: str) -> None:
    slug = AI_COMMAND_SLUG.get(command, f'/lbai-{command}')
    print('STATUS BLOCKED', file=sys.stderr)
    print('reason: 此命令需要 AI 先生成结构化 JSON，不能直接在终端裸跑。', file=sys.stderr)
    print(f'next_step: 请在 Cursor 或 Codex 桌面 App 中打开本工作区，输入 `{slug}` 并按提示完成。', file=sys.stderr)
    print('hint: 高级用户可在终端透传 --enrichment <json_path>。', file=sys.stderr)


def run_workspace_tool(command: str, args: argparse.Namespace, extra: list[str]) -> int:
    if command == 'init' and '--print-questions' not in extra and not has_enrichment_flag(extra):
        print_terminal_misuse_hint(command)
        return 2
    if command != 'init' and not has_enrichment_flag(extra):
        print_terminal_misuse_hint(command)
        return 2
    root = find_workspace()
    tool = COMMAND_TO_TOOL[command]
    cmd = [*python_cmd(), f'lbai_system/tools/{tool}', *extra]
    return run(cmd, cwd=root).returncode


def finish_task(args: argparse.Namespace, extra: list[str]) -> int:
    if not has_enrichment_flag(extra):
        print_terminal_misuse_hint('finish-task')
        return 2
    root = find_workspace()
    if extra and not extra[0].startswith('-'):
        return run([*python_cmd(), 'lbai_system/tools/finish_task.py', *extra], cwd=root).returncode
    resolved = capture([*python_cmd(), 'lbai_system/tools/resolve_current_task.py', 'finish'], cwd=root)
    print(resolved.stdout, end='')
    if resolved.returncode != 0:
        return resolved.returncode
    task = parse_task_folder(resolved.stdout)
    if not task:
        return 2
    return run([*python_cmd(), 'lbai_system/tools/finish_task.py', task, *extra], cwd=root).returncode


def execute_task(_args: argparse.Namespace, extra: list[str]) -> int:
    root = find_workspace()
    if extra:
        task = extra[0]
        rest = extra[1:]
    else:
        resolved = capture([*python_cmd(), 'lbai_system/tools/resolve_current_task.py', 'execute'], cwd=root)
        print(resolved.stdout, end='')
        if resolved.returncode != 0:
            return resolved.returncode
        task = parse_task_folder(resolved.stdout)
        rest = []
    if not task:
        return 2
    result = run([*python_cmd(), 'lbai_system/tools/prepare_execute_task.py', task], cwd=root)
    if result.returncode != 0:
        return result.returncode
    print('model_handoff: open this workspace in Codex or Cursor and run /lbai-execute-task so the model can write task_output.md from execution_plan.md.')
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
    return run([*python_cmd(), 'lbai_system/tools/serve_dashboard.py', *args.extra], cwd=root).returncode


def self_iterate(args: argparse.Namespace) -> int:
    root = find_workspace()
    cmd = [*python_cmd(), 'lbai_system/prompt_lab/prompt_lab.py', 'start']
    if args.rounds is not None:
        cmd.extend(['--rounds', str(args.rounds)])
    if args.scenarios_per_round is not None:
        cmd.extend(['--scenarios-per-round', str(args.scenarios_per_round)])
    if args.focus:
        cmd.extend(['--focus', args.focus])
    if args.chain_mode:
        cmd.extend(['--chain-mode', args.chain_mode])
    if args.review_mode:
        cmd.extend(['--review-mode', args.review_mode])
    if args.auto_continue:
        cmd.append('--auto-continue')
    if args.apply_threshold is not None:
        cmd.extend(['--apply-threshold', str(args.apply_threshold)])
    if args.context_mode:
        cmd.extend(['--context-mode', args.context_mode])
    if args.real_task_limit is not None:
        cmd.extend(['--real-task-limit', str(args.real_task_limit)])
    run_id = ''
    captured = capture(cmd, cwd=root)
    print(captured.stdout, end='')
    print(captured.stderr, end='', file=sys.stderr)
    if captured.returncode != 0:
        return captured.returncode
    for line in captured.stdout.splitlines():
        if line.startswith('run_dir:'):
            run_id = line.split(':', 1)[1].strip()
            break
    if not run_id:
        print('ERROR: prompt lab start succeeded but run_dir was missing from output', file=sys.stderr)
        return 1
    return run([*python_cmd(), 'lbai_system/prompt_lab/prompt_lab.py', 'next-step', '--run', run_id], cwd=root).returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='lbai')
    parser.add_argument('--version', action='version', version=f'lbai {read_version()}')
    sub = parser.add_subparsers(dest='command')

    auth = sub.add_parser('auth')
    auth_sub = auth.add_subparsers(dest='auth_command')
    auth_sub.add_parser('login')
    backend_login = auth_sub.add_parser('backend-login')
    backend_login.add_argument('--api-key')
    backend_login.add_argument('--api-key-header', default=KNOWLEDGE_SERVICE_API_KEY_HEADER)
    backend_login.add_argument('--base-url', default=KNOWLEDGE_SERVICE_BASE_URL)
    backend_login.add_argument('--verify-timeout', type=int, default=10)
    backend_login.add_argument('--no-verify', action='store_true')
    backend_login.add_argument('--optional', action='store_true')
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
    iterate = sub.add_parser('self-iterate')
    iterate.add_argument('--rounds', type=int)
    iterate.add_argument('--scenarios-per-round', type=int)
    iterate.add_argument('--focus')
    iterate.add_argument('--chain-mode', choices=['intake_evidence', 'full_lifecycle'])
    iterate.add_argument('--review-mode', choices=['human_each_round', 'auto'])
    iterate.add_argument('--auto-continue', action='store_true')
    iterate.add_argument('--apply-threshold', type=float)
    iterate.add_argument('--context-mode', choices=['auto', 'real_task', 'mock'])
    iterate.add_argument('--real-task-limit', type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    known, extra = parser.parse_known_args(argv)

    if known.command == 'auth':
        if known.auth_command == 'login':
            return auth_login(known)
        if known.auth_command == 'backend-login':
            return auth_backend_login(known)
        if known.auth_command == 'doctor':
            return auth_doctor(known)
        parser.error('auth requires login, backend-login, or doctor')
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
    if known.command == 'self-iterate':
        return self_iterate(known)

    parser.print_help()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
