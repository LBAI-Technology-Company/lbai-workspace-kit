#!/usr/bin/env python3
import argparse
import getpass
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from lbai.git_sync import push_with_remote_sync
from lbai.workspace_bootstrap import (
    clone_raw_repo,
    inspect_remote_repo,
    pull_personal_repo,
    restore_from_personal_repo,
)
from lbai.workspace_config import (
    clear_active_workspace,
    configured_active_workspace_path,
    default_shared_workspace_path,
    get_active_workspace,
    invocation_cwd,
    is_workspace,
    resolve_workspace_root,
    set_active_workspace,
    source_project_path,
    workspace_resolution_context,
)


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
GITHUB_AUTH_TOKEN_CMD = 'lbai github auth token'
BIND_GITHUB_CMD = 'lbai bind-github'
PLUGIN_MIN_WORKSPACE_VERSION = '1.4.1'

DOCTOR_REQUIRED_FILES = [
    'AGENTS.md',
    'lbai_system/runner_contracts/lbai_command_contract_v1.md',
    'lbai_system/prompts/init_enrichment_prompt_v1.md',
    'lbai_system/prompts/evidence_enrichment_prompt_v1.md',
    'lbai_system/prompts/backend_search_query_plan_prompt_v1.md',
    'lbai_system/prompts/task_intake_enrichment_prompt_v1.md',
    'lbai_system/prompts/execute_task_plan_prompt_v1.md',
    'lbai_system/prompts/finish_review_enrichment_prompt_v1.md',
    'lbai_system/schemas/init_enrichment_schema_v1.json',
    'lbai_system/schemas/evidence_enrichment_schema_v1.json',
    'lbai_system/schemas/backend_search_query_plan_schema_v1.json',
    'lbai_system/schemas/task_intake_enrichment_schema_v1.json',
    'lbai_system/schemas/finish_review_enrichment_schema_v1.json',
    'lbai_system/tools/init_lbai.py',
    'lbai_system/tools/add_evidence.py',
    'lbai_system/tools/search_artifacts.py',
    'lbai_system/tools/new_task.py',
    'lbai_system/tools/prepare_execute_task.py',
    'lbai_system/tools/finish_task.py',
    'lbai_system/prompt_lab/prompt_lab.py',
]

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


def github_cli_enabled() -> bool:
    return os.environ.get('LBAI_GITHUB_AUTH_USE_GH', '1').strip().lower() not in {
        '0',
        'false',
        'no',
    }


def gh_authenticated() -> bool:
    if not github_cli_enabled() or not shutil.which('gh'):
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

    gh = shutil.which('gh') if github_cli_enabled() else None
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
    if not github_cli_enabled():
        return False, 'GitHub CLI credential backend disabled'
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
            return 'stale', 'Git 凭据与已保存 Token 不一致；请运行 lbai github auth token 粘贴新 Token，或直接回车重新同步'
        return 'missing', 'Token 已保存但未同步到 Git；请运行 lbai github auth token 并直接回车重新同步'
    if gh_authenticated():
        if cred:
            return 'ok', '使用 GitHub CLI 凭据'
        ok, msg = setup_gh_for_git()
        if ok:
            return 'ok', msg
        return 'needs_setup', 'gh 已登录但 Git 未配置；请运行 lbai github auth token 并直接回车'
    if cred:
        return 'ok', 'Git 凭据管理器已配置'
    return 'missing', '尚未配置 GitHub 认证；请运行 lbai github auth token'


def print_git_credential_sync(ok: bool, message: str) -> None:
    print(f'git_credential_sync: {"OK" if ok else "NEEDS_ATTENTION"}')
    print(f'git_credential_note: {message}')
    if not ok:
        if 'read:org' in message.lower():
            print(
                f'manual_fix: 重新运行 {GITHUB_AUTH_TOKEN_CMD}，粘贴包含 read:org '
                '且可访问目标 private repo 的新 Token；若无法创建，请联系管理员'
            )
        else:
            print(
                f'manual_fix: 重新运行 {GITHUB_AUTH_TOKEN_CMD}；若仍失败，'
                '联系管理员确认 Token 是否有效且可访问目标 private repo'
            )


def auth_workspace_path() -> Path | None:
    active = get_active_workspace()
    if active:
        return active.resolve()
    context = workspace_resolution_context()
    if context['workspace_valid']:
        return Path(context['workspace_root']).resolve()
    return None


def workspace_origin_url(root: Path) -> str:
    result = capture(['git', 'remote', 'get-url', 'origin'], cwd=root)
    if result.returncode != 0:
        return ''
    return result.stdout.strip()


def set_workspace_origin_url(root: Path, repo_url: str) -> subprocess.CompletedProcess:
    if workspace_origin_url(root):
        return run(['git', 'remote', 'set-url', 'origin', repo_url], cwd=root)
    return run(['git', 'remote', 'add', 'origin', repo_url], cwd=root)


def mask_secret(value: str) -> str:
    if not value:
        return ''
    masked = '*' * min(len(value), 12)
    if len(value) > 12:
        masked += '...'
    return masked


def prompt_secret(label: str, hint: str | None = None) -> str:
    if hint:
        print(hint)
    value = getpass.getpass(f'{label}: ').strip()
    if value:
        print(f'已输入：{mask_secret(value)}')
    return value


def shell_reload_hints() -> list[str]:
    shell_name = os.path.basename(os.environ.get('SHELL', ''))
    hints: list[str] = []
    if shell_name == 'zsh':
        hints.append('source ~/.zshrc')
        if platform.system() == 'Darwin':
            hints.append('source ~/.zprofile   # macOS 上 Codex 需要')
    elif shell_name == 'bash':
        if platform.system() == 'Darwin' and (Path.home() / '.bash_profile').exists():
            hints.append('source ~/.bash_profile')
        else:
            hints.append('source ~/.bashrc')
    else:
        hints.append('关闭并重新打开终端（Windows 请重新打开 PowerShell）')
    return hints


def post_install_setup_lines(workspace_path: Path | str) -> list[str]:
    root = str(workspace_path)
    load_cmds = shell_reload_hints()
    load_block = '\n  '.join(load_cmds)

    return [
        '========== 安装后续配置（请按顺序逐步完成） ==========',
        '',
        '软件已装到本机，还需完成下面各步才能正常工作和同步。',
        '',
        '开始前，向管理员索取（勿发到公开聊天）：',
        '  · GitHub 私有仓库 URL（你的专属 private repo）',
        '  · GitHub Token（Personal Access Token，需 repo 权限）',
        '  · 知识服务 API Key（步骤 5 使用）',
        '',
        '【步骤 1】让 lbai 命令生效',
        f'  {load_block}',
        '  验证：lbai --version  应显示版本号',
        '',
        '【步骤 2】保存 GitHub Token',
        f'  命令：{GITHUB_AUTH_TOKEN_CMD}',
        '  · 粘贴 Token 时终端会显示 ***，表示正在输入',
        '  · 已保存过可直接回车，会重新同步 Git 凭据',
        '',
        '【步骤 3】绑定私有仓库到本机工作区',
        f'  命令：{BIND_GITHUB_CMD}',
        '  · 按提示粘贴管理员给的仓库 URL（无需输入路径，自动使用本机工作区）',
        '  · 个人仓库已有数据时：直接 clone/pull 个人仓库，不会覆盖为安装器模板',
        '  · 个人仓库为空时：才用企业 template 初始化；升级请用 /lbai-update-kit',
        '  · 换电脑请 clone 私有仓库后运行 lbai workspace set --path <克隆目录>',
        '  · 示例：https://github.com/组织名/你的仓库名',
        '',
        '【步骤 4】检查 GitHub 配置是否成功',
        '  命令：lbai auth doctor',
        '  · 成功时应看到 github_repo_status: BOUND',
        '  · 有报错请把完整输出发给管理员',
        '',
        '【步骤 5】登录知识服务',
        '  命令：lbai auth backend-login',
        '  · 粘贴 API Key 时终端会显示 ***，表示正在输入',
        '  · 已配置过直接回车保留原 Key',
        '',
        '【步骤 6】设置岗位角色（首次必做）',
        '  · Codex：任意项目 → 命令面板 → LBAI Role Setup',
        '  · Cursor：聊天输入 /lbai-role-setup',
        '',
        '随时重看本指引：lbai setup-guide',
        '====================================================',
    ]


def github_sync_setup_lines(workspace_path: Path | str) -> list[str]:
    root = str(workspace_path)
    return [
        'GitHub 私有仓库尚未绑定，请继续完成安装后续步骤：',
        f'  步骤 2：{GITHUB_AUTH_TOKEN_CMD}',
        f'  步骤 3：{BIND_GITHUB_CMD}',
        '  步骤 4：lbai auth doctor',
        '  完整分步指引：lbai setup-guide',
    ]


def print_github_sync_setup_guide(workspace_path: Path | str) -> None:
    for line in github_sync_setup_lines(workspace_path):
        print(line)


def setup_guide(args: argparse.Namespace) -> int:
    if args.path:
        workspace_path = Path(args.path).expanduser().resolve()
    else:
        workspace_path = auth_workspace_path() or default_shared_workspace_path().expanduser().resolve()
    for line in post_install_setup_lines(workspace_path):
        print(line)
    return 0


def print_github_repo_binding_guidance(*, auth_ready: bool) -> None:
    root = auth_workspace_path()
    if not root:
        print('workspace_status: NOT_CONFIGURED')
        print(
            '下一步：已有工作区运行 lbai workspace set --path <工作区路径>；'
            '首次创建运行 lbai init-workspace'
        )
        return

    print('workspace_status: READY')
    print(f'workspace_path: {root}')
    origin = workspace_origin_url(root)
    if origin:
        print('github_repo_status: BOUND')
        print(f'github_repo_url: {origin}')
        return

    print('github_repo_status: NOT_BOUND')
    print_github_sync_setup_guide(root)
    if not auth_ready:
        print('（请先完成步骤 2，再执行步骤 3）')


def print_auth_verification_next_step(sync_ok: bool) -> None:
    if not sync_ok:
        print('先修复上方 Token 权限或 Git 凭据问题，然后运行 lbai auth doctor')
        print_github_repo_binding_guidance(auth_ready=False)
        return

    root = auth_workspace_path()
    if root and workspace_origin_url(root):
        print('github_repo_status: BOUND')
        print(f'github_repo_url: {workspace_origin_url(root)}')
        print('运行 lbai auth doctor 可复查全部鉴权状态')
        return
    print_github_repo_binding_guidance(auth_ready=True)


def print_ready_workspace_next_step() -> None:
    print_github_repo_binding_guidance(auth_ready=True)


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
    identity_token: str = "",
    identity_header: str = "X-LBAI-Identity-Token",
) -> Path:
    path = knowledge_service_auth_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        'schema_version': 'knowledge_service_auth_v1',
        'api_key': api_key.strip(),
        'api_key_header': (api_key_header or KNOWLEDGE_SERVICE_API_KEY_HEADER).strip(),
        'base_url': (base_url or KNOWLEDGE_SERVICE_BASE_URL).strip(),
        'identity_token': identity_token.strip(),
        'identity_header': identity_header.strip(),
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
    identity_token: str = "",
    identity_header: str = "X-LBAI-Identity-Token",
) -> tuple[bool, str]:
    url = base_url.rstrip('/') + '/v1/knowledge/search'
    payload = {
        'workspace_repo_id': 'auth-check',
        'query': 'auth check',
        'statuses': ['active'],
        'limit': 1,
    }
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        (api_key_header or KNOWLEDGE_SERVICE_API_KEY_HEADER).strip(): api_key.strip(),
    }
    if identity_token.strip():
        headers[identity_header.strip() or "X-LBAI-Identity-Token"] = identity_token.strip()
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


def find_workspace(start: Path | None = None) -> Path:
    root, source = resolve_workspace_root(start=start)
    if is_workspace(root):
        return root
    if source == 'active_workspace_invalid':
        print(f'ERROR: configured active workspace is missing or invalid: {root}', file=sys.stderr)
    else:
        print('ERROR: no LBAI workspace is available for this directory.', file=sys.stderr)
    print('NEXT_STEP: run lbai init-workspace, or lbai workspace set --path <lbai-workspace>', file=sys.stderr)
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
        knowledge.pop('api_key', None)
        knowledge['enabled'] = True
        knowledge['base_url'] = KNOWLEDGE_SERVICE_BASE_URL
        knowledge['api_key_header'] = KNOWLEDGE_SERVICE_API_KEY_HEADER
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


def workspace_kit_version(root: Path) -> str:
    metadata_path = root / '.lbai' / 'workspace.json'
    if metadata_path.exists():
        try:
            data = json.loads(metadata_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            data = {}
        value = str(data.get('workspaceKitVersion') or '').strip() if isinstance(data, dict) else ''
        if value:
            return value.lstrip('v')
    return 'unknown'


def semver_tuple(value: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?', value.strip())
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def version_at_least(current: str, minimum: str) -> bool:
    current_parts = semver_tuple(current)
    minimum_parts = semver_tuple(minimum)
    return bool(current_parts and minimum_parts and current_parts >= minimum_parts)


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


def github_auth_token(_args: argparse.Namespace) -> int:
    path = auth_token_path()
    source = auth_source_label()

    if source:
        print('auth_check: already configured')
        print(f'auth_source: {source}')
        print('如需更换 Token 请粘贴新 Token；直接回车会重新同步 Git 凭据（推荐换 Token 后执行一次）。')
        token = prompt_secret('GitHub Token', '粘贴 Token 时终端会显示 ***，表示正在输入')
        if not token:
            print('auth_status: UNCHANGED')
            ok, message = ensure_git_credentials_synced()
            print_git_credential_sync(ok, message)
            print_auth_verification_next_step(ok)
            return 0 if ok else 2
    else:
        print('GitHub Token 将保存在本机 ~/.lbai/auth/，不会写入工作区文件。')
        print('粘贴后 lbai 会自动同步到 Git，终端 git push 也能直接使用。')
        print('Do not paste this token into README, .env, role_workspace, tasks, or chat artifacts.')
        token = prompt_secret('GitHub Token', '粘贴 Token 时终端会显示 ***，表示正在输入')
        if not token:
            if gh_authenticated():
                print('auth_status: USING_GH')
                ok, message = setup_gh_for_git()
                print_git_credential_sync(ok, message)
                print_auth_verification_next_step(ok)
                return 0 if ok else 2
            print('auth_status: BLOCKED')
            print('reason: empty token')
            print(f'next_step: 向管理员索取 GitHub Token（需 repo 权限），或先运行 gh auth login 后再执行 {GITHUB_AUTH_TOKEN_CMD} 并回车')
            return 2

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(token + '\n', encoding='utf-8')
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    print('auth_status: SAVED')
    print(f'token_store: {path}')
    ok, message = sync_git_credentials(token)
    print_git_credential_sync(ok, message)
    print_auth_verification_next_step(ok)
    return 0 if ok else 2


def auth_backend_login(args: argparse.Namespace) -> int:
    existing = read_knowledge_service_auth()
    if existing.get('api_key'):
        print('backend_auth_check: already configured')
        print('直接回车保持不变；如需更换请输入新 API Key。')
        api_key_hint = '粘贴 API Key 时终端会显示 ***，表示正在输入'
        prompt = 'LBAI backend API key: '
    else:
        print('LBAI backend API key will be saved outside the workspace.')
        print('It will not be written to workspace files, Git commits, role_workspace, or tasks.')
        api_key_hint = '粘贴 API Key 时终端会显示 ***，表示正在输入'
        prompt = 'Paste LBAI backend API key: '

    api_key = (args.api_key or '').strip()
    identity_token = (args.identity_token or '').strip()
    if not api_key:
        api_key = prompt_secret(prompt.rstrip(': '), api_key_hint)
    if not api_key:
        if args.optional:
            print('backend_auth_status: SKIPPED')
            print('next_step: lbai auth backend-login')
            return 0
        if existing.get('api_key'):
            print('backend_auth_status: UNCHANGED')
            print('知识服务已配置。')
            print_ready_workspace_next_step()
            print('完整安装后续步骤：lbai setup-guide')
            return 0
        print('backend_auth_status: BLOCKED')
        print('reason: empty API key')
        return 2
    if not identity_token:
        identity_token = str(existing.get('identity_token') or '').strip()
    if not identity_token:
        print('backend_auth_status: BLOCKED')
        print('reason: empty identity token')
        print('next_step: 向管理员索取绑定员工身份的知识服务 identity token。')
        return 2

    if not args.no_verify:
        ok, message = verify_knowledge_service_key(
            api_key,
            args.api_key_header,
            args.base_url,
            args.verify_timeout,
            identity_token,
            args.identity_header,
        )
        print(message)
        if not ok:
            print('backend_auth_status: BLOCKED')
            print('next_step: 检查 API Key 是否正确；如果只是暂时无法联网，可使用 lbai auth backend-login --no-verify 离线保存。')
            return 2
    else:
        print('backend_key_check: SKIPPED (--no-verify)')

    path = write_knowledge_service_auth(
        api_key, args.api_key_header, args.base_url, identity_token, args.identity_header
    )
    print('backend_auth_status: SAVED')
    print(f'backend_auth_store: {path}')
    print_ready_workspace_next_step()
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
    print(
        f'- backend_identity_token_available: '
        f'{"yes" if backend_auth.get("identity_token") else "no"}'
    )
    if source:
        print(f'- auth_source: {source}')
    if backend_auth.get('api_key'):
        print(f'- backend_auth_source: {knowledge_service_auth_path()}')
    if sync_status == 'ok':
        print('auth_status: READY')
        print_ready_workspace_next_step()
        return 0
    if sync_status in {'stale', 'missing', 'needs_setup'}:
        print('auth_status: NEEDS_SYNC')
        print(
            f'next_step: {GITHUB_AUTH_TOKEN_CMD}  # 若曾报告权限缺失请粘贴新 Token；'
            '否则可直接回车重新同步'
        )
        print_github_repo_binding_guidance(auth_ready=False)
        return 2
    print('auth_status: BLOCKED')
    print(f'next_step: {GITHUB_AUTH_TOKEN_CMD}  # 粘贴管理员提供的 GitHub Token')
    print_github_repo_binding_guidance(auth_ready=False)
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


def commit_and_push_workspace(
    local_path: Path,
    repo_url: str | None,
    env: dict[str, str],
    args: argparse.Namespace,
    *,
    commit_message: str,
) -> None:
    if args.no_commit:
        print('git_status: COMMIT_SKIPPED')
        return
    if not repo_url or not (local_path / '.git').exists():
        return

    remote = set_workspace_origin_url(local_path, repo_url)
    if remote.returncode != 0:
        print('git_status: BLOCKED')
        print('reason: failed to configure Git remote origin')
        return

    stage_paths = [
        p for p in [*MANAGED_PATHS, *EMPLOYEE_DEFAULT_PATHS, '.lbai/workspace.json']
        if (local_path / p).exists()
    ]
    run(['git', 'add', '-f', '--', *stage_paths], cwd=local_path)
    status = capture(['git', 'status', '--porcelain'], cwd=local_path)
    if not status.stdout.strip():
        print('git_status: NO_CHANGES')
        return

    commit = run(['git', 'commit', '-m', commit_message], cwd=local_path)
    if commit.returncode != 0:
        print('git_status: COMMIT_FAILED')
        return
    if args.no_push:
        print('git_status: COMMITTED')
        return

    ok, pull_status, detail = push_workspace_with_remote_sync(
        local_path,
        env=env,
        set_upstream=True,
    )
    print_git_push_result(ok, pull_status, detail)


def register_workspace_if_ready(local_path: Path) -> Path | None:
    if not is_workspace(local_path):
        return None
    return set_active_workspace(local_path)


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
        remote_state = inspect_remote_repo(repo_url, env=env)
        if remote_state == 'unreachable':
            print('init_status: BLOCKED')
            print('reason: cannot reach remote repo')
            print('next_step: check repo URL, token permissions, or run gh auth login')
            return 2

        if local_path.exists() and any(local_path.iterdir()):
            if not (local_path / '.git').exists():
                print('init_status: BLOCKED')
                print(f'reason: local path exists and is not a git repo: {local_path}')
                return 2
            print(f'using_existing_repo: {local_path}')
        elif remote_state == 'lbai_workspace':
            ok, detail = restore_from_personal_repo(local_path, repo_url, env=env)
            if not ok:
                print('init_status: BLOCKED')
                print(f'reason: {detail}')
                return 2
        elif remote_state == 'seedable':
            ok, detail = clone_raw_repo(local_path, repo_url, env=env)
            if not ok:
                print('init_status: BLOCKED')
                print(f'reason: {detail}')
                return 2
        else:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            if local_path.exists():
                shutil.rmtree(local_path)
            local_path.mkdir(parents=True, exist_ok=True)

        if (local_path / '.git').exists():
            remote = set_workspace_origin_url(local_path, repo_url)
            if remote.returncode != 0:
                print('init_status: BLOCKED')
                print('reason: failed to configure Git remote origin')
                return remote.returncode or 2

        if is_workspace(local_path):
            print('workspace_source: personal_repo')
            ok, detail = pull_personal_repo(local_path, repo_url, env=env) if (local_path / '.git').exists() else (True, 'restored from personal repo')
            if not ok:
                print('init_status: BLOCKED')
                print(f'reason: {detail}')
                return 2
            print(f'workspace_sync: {detail}')
            changed = []
        else:
            print('workspace_source: enterprise_template')
            changed = copy_template_into_workspace(local_path, overwrite_managed=True)
            if not (local_path / '.git').exists():
                run(['git', 'init', '-b', 'main'], cwd=local_path)
            if not args.no_commit:
                commit_and_push_workspace(
                    local_path,
                    repo_url,
                    env,
                    args,
                    commit_message='chore(lbai): initialize workspace kit',
                )
            else:
                print('git_status: COMMIT_SKIPPED')

        registered = set_active_workspace(local_path)
        print(f'active_workspace: {registered}')

        doctor_code = doctor(argparse.Namespace(path=str(local_path), allow_missing_upstream=args.no_commit or args.no_push))
        print('init_status: READY' if doctor_code == 0 else 'init_status: NEEDS_REVIEW')
        print(f'workspace_path: {local_path}')
        print(f'cursor_open: {local_path}')
        parent = local_path.parent.resolve()
        if parent != local_path and not is_workspace(parent):
            print(f'cursor_note: 请在 Cursor 或 Codex 中打开 cursor_open 路径；/lbai-* 命令只在该目录下的 .cursor/commands/ 生效，不要打开外层父目录 {parent}')
        else:
            print('cursor_note: 请在 Cursor 或 Codex 中打开 cursor_open 路径；/lbai-* 命令只在该目录下的 .cursor/commands/ 生效')
        print(f'next_step: 用 Cursor 或 Codex 打开 cursor_open 目录，运行 /lbai-role-setup')
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


def push_workspace_with_remote_sync(
    workspace: Path,
    env: dict[str, str] | None = None,
    *,
    set_upstream: bool = False,
) -> tuple[bool, str, str]:
    branch = current_branch(workspace)
    return push_with_remote_sync(workspace, branch=branch, env=env, set_upstream=set_upstream)


def print_git_push_result(ok: bool, pull_status: str, detail: str) -> None:
    if pull_status == 'PULL_FAILED':
        print('git_pull_status: PULL_FAILED')
        print('git_status: PUSH_FAILED')
        print(f'reason: {detail}')
        return
    if ok:
        if pull_status not in {
            'SKIPPED',
            'no origin configured; skipping pull',
            'already up to date with remote',
        } and not pull_status.endswith('does not exist yet; nothing to pull'):
            print(f'git_pull_status: OK ({pull_status})')
        print('git_status: PUSHED')
        return
    print('git_status: PUSH_FAILED')
    print(f'reason: {detail}')


def workspace_metadata(root: Path) -> dict:
    path = root / '.lbai' / 'workspace.json'
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def git_preflight(root: Path) -> dict:
    remote = capture(['git', 'remote', 'get-url', 'origin'], cwd=root)
    upstream = capture(
        ['git', 'rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{upstream}'],
        cwd=root,
    )
    status = capture(['git', 'status', '--porcelain'], cwd=root)
    return {
        'repository': (root / '.git').exists(),
        'origin_configured': remote.returncode == 0 and bool(remote.stdout.strip()),
        'upstream_configured': upstream.returncode == 0 and bool(upstream.stdout.strip()),
        'working_tree_dirty': bool(status.stdout.strip()),
    }


def doctor_report(args: argparse.Namespace) -> dict:
    requested_path = getattr(args, 'path', None)
    root, resolution_source = resolve_workspace_root(explicit_path=requested_path)
    resolution = workspace_resolution_context(explicit_path=requested_path)

    valid_workspace = is_workspace(root)
    minimum = getattr(args, 'min_workspace_version', None) or PLUGIN_MIN_WORKSPACE_VERSION
    plugin_version = getattr(args, 'plugin_version', None)
    backend_auth = read_knowledge_service_auth()
    report = {
        'schema_version': 'lbai_doctor_v1',
        'cli_version': read_version(),
        'workspace_root': str(root),
        'workspace_valid': valid_workspace,
        'resolution_source': resolution_source,
        'active_workspace': resolution.get('active_workspace'),
        'invocation_cwd': resolution.get('invocation_cwd'),
        'source_project_path': resolution.get('source_project_path'),
        'workspace_kit_version': workspace_kit_version(root) if valid_workspace else 'unknown',
        'required_workspace_version': minimum,
        'plugin_version': plugin_version or None,
        'required_files': {'status': 'BLOCKED', 'missing': DOCTOR_REQUIRED_FILES},
        'git': {
            'repository': False,
            'origin_configured': False,
            'upstream_configured': False,
            'working_tree_dirty': False,
        },
        'authentication': {
            'github_available': bool(read_token() or gh_authenticated()),
            'knowledge_service_available': bool(
                backend_auth.get('api_key') and backend_auth.get('identity_token')
            ),
        },
        'knowledge_service': {
            'enabled': False,
            'status': 'DISABLED',
        },
        'compatibility': {
            'status': 'BLOCKED',
            'reason': 'workspace_not_initialized',
        },
        'checks': {},
        'doctor_status': 'BLOCKED',
        'next_steps': [],
    }
    if not valid_workspace:
        if resolution_source == 'active_workspace_invalid':
            report['compatibility'] = {
                'status': 'BLOCKED',
                'reason': 'active_workspace_invalid',
            }
            report['next_steps'].append(
                f'Run lbai init-workspace or lbai workspace set --path <lbai-workspace>; invalid path: {root}',
            )
        else:
            report['next_steps'].append('Run lbai init-workspace, then open the initialized workspace in Codex.')
        return report

    missing = [rel for rel in DOCTOR_REQUIRED_FILES if not (root / rel).is_file()]
    report['required_files'] = {
        'status': 'READY' if not missing else 'BLOCKED',
        'missing': missing,
    }
    report['git'] = git_preflight(root)

    metadata = workspace_metadata(root)
    knowledge = metadata.get('knowledge_service') if isinstance(metadata.get('knowledge_service'), dict) else {}
    enabled = bool(knowledge.get('enabled'))
    backend_authenticated = report['authentication']['knowledge_service_available']
    report['knowledge_service'] = {
        'enabled': enabled,
        'status': 'READY' if enabled and backend_authenticated else ('NEEDS_AUTH' if enabled else 'DISABLED'),
    }

    current_version = report['workspace_kit_version']
    compatible = version_at_least(current_version, minimum)
    report['compatibility'] = {
        'status': 'READY' if compatible else 'BLOCKED',
        'reason': 'compatible' if compatible else 'workspace_update_required',
    }
    if not compatible:
        report['next_steps'].append(f'Run lbai update-kit; workspace {current_version} must be at least {minimum}.')

    checks = [
        ('bootstrap', [*python_cmd(), 'lbai_system/tools/bootstrap_check.py']),
        ('codex_adapter', [*python_cmd(), 'lbai_system/tools/check_codex_adapter.py']),
        ('cursor_commands', [*python_cmd(), 'lbai_system/tools/check_cursor_commands.py']),
    ]
    checks_ok = True
    for name, cmd in checks:
        result = capture(cmd, cwd=root)
        passed = result.returncode == 0
        if getattr(args, 'allow_missing_upstream', False) and 'MISSING_GIT_UPSTREAM' in result.stdout:
            passed = True
        report['checks'][name] = {
            'status': 'READY' if passed else 'BLOCKED',
            'returncode': result.returncode,
        }
        checks_ok = checks_ok and passed

    require_backend = bool(getattr(args, 'require_backend', False))
    backend_ok = not require_backend or report['knowledge_service']['status'] == 'READY'
    git_ok = report['git']['repository'] and report['git']['origin_configured']
    upstream_ok = report['git']['upstream_configured'] or bool(getattr(args, 'allow_missing_upstream', False))
    ready = not missing and compatible and checks_ok and backend_ok and git_ok and upstream_ok

    if not report['authentication']['github_available']:
        report['next_steps'].append(f'Run {GITHUB_AUTH_TOKEN_CMD} before a workflow that pushes to GitHub.')
    if require_backend and not backend_ok:
        report['next_steps'].append('Run lbai auth backend-login before using knowledge search.')
    if not report['git']['origin_configured']:
        report['next_steps'].append('Configure the workspace Git origin.')
    if not report['git']['upstream_configured'] and not getattr(args, 'allow_missing_upstream', False):
        report['next_steps'].append('Configure an upstream branch before sync workflows.')

    report['doctor_status'] = 'READY' if ready else 'BLOCKED'
    return report


def doctor(args: argparse.Namespace) -> int:
    report = doctor_report(args)
    if getattr(args, 'json', False):
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report['doctor_status'] == 'READY' else 2

    root = Path(report['workspace_root'])
    print('# LBAI doctor')
    print(f'workspace_root: {root}')
    if not report['workspace_valid']:
        print('workspace_status: BLOCKED')
        print('reason: missing AGENTS.md, lbai_system, role_workspace, or tasks')
        return 2

    for name, item in report['checks'].items():
        print(f'## {name}')
        print(f'STATUS {item["status"]}')
    print(f'workspace_kit_version: {report["workspace_kit_version"]}')
    print(f'compatibility_status: {report["compatibility"]["status"]}')
    print(f'doctor_status: {report["doctor_status"]}')
    for step in report['next_steps']:
        print(f'next_step: {step}')
    return 0 if report['doctor_status'] == 'READY' else 2


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


def workspace_show(args: argparse.Namespace) -> int:
    active = get_active_workspace()
    configured = configured_active_workspace_path()
    context = workspace_resolution_context()
    payload = {
        'schema_version': 'lbai_workspace_config_v1',
        'active_workspace': str(active) if active else None,
        'configured_active_workspace': str(configured) if configured else None,
        'configured_active_workspace_valid': bool(active),
        'resolved_workspace': context['workspace_root'],
        'resolution_source': context['resolution_source'],
        'invocation_cwd': context['invocation_cwd'],
        'source_project_path': context['source_project_path'],
    }
    if getattr(args, 'json', False):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    print('# LBAI workspace')
    print(f"active_workspace: {payload['active_workspace'] or 'unset'}")
    if configured and not active:
        print(f"configured_active_workspace_invalid: {configured}")
    print(f"resolved_workspace: {payload['resolved_workspace']}")
    print(f"resolution_source: {payload['resolution_source']}")
    print(f"invocation_cwd: {payload['invocation_cwd']}")
    if payload['source_project_path']:
        print(f"source_project_path: {payload['source_project_path']}")
    return 0


def workspace_set(args: argparse.Namespace) -> int:
    target = Path(args.path).expanduser().resolve()
    try:
        registered = set_active_workspace(target)
    except ValueError:
        print('workspace_set_status: BLOCKED', file=sys.stderr)
        print(f'reason: not an LBAI workspace: {target}', file=sys.stderr)
        print('next_step: run lbai init-workspace or point --path at an initialized LBAI workspace', file=sys.stderr)
        return 2
    print('workspace_set_status: READY')
    print(f'active_workspace: {registered}')
    return 0


def workspace_clear(_args: argparse.Namespace) -> int:
    cleared = clear_active_workspace()
    print('workspace_clear_status: READY' if cleared else 'workspace_clear_status: NOOP')
    return 0


def bind_github(args: argparse.Namespace) -> int:
    root = auth_workspace_path()
    if not root:
        root = default_shared_workspace_path().expanduser().resolve()

    print(f'workspace_path: {root}')
    repo_url = (args.repo_url or '').strip()
    if not repo_url:
        print('粘贴管理员提供的 GitHub 私有仓库 URL：')
        repo_url = input().strip()
    if not repo_url:
        print('bind_github_status: BLOCKED')
        print('reason: empty repo URL')
        return 2

    ensure_args = argparse.Namespace(
        path=str(root),
        repo_url=repo_url,
        no_git=False,
        no_commit=args.no_commit,
        no_push=args.no_push,
        quiet=False,
    )
    code = workspace_ensure(ensure_args)
    if code == 0:
        print('bind_github_status: READY')
        print(f'github_repo_url: {repo_url}')
        print('next_step: lbai auth doctor')
    return code


def workspace_ensure(args: argparse.Namespace) -> int:
    if args.path:
        local_path = Path(args.path).expanduser().resolve()
    else:
        active = get_active_workspace()
        local_path = active if active else default_shared_workspace_path().expanduser().resolve()

    repo_url = (args.repo_url or os.environ.get('LBAI_WORKSPACE_REPO_URL', '')).strip() or None
    quiet = getattr(args, 'quiet', False)
    if not quiet:
        print(f'shared_workspace_path: {local_path}')

    if local_path.exists() and any(local_path.iterdir()) and not is_workspace(local_path) and not repo_url:
        print('workspace_ensure_status: BLOCKED')
        print(f'reason: path exists but is not an LBAI workspace: {local_path}')
        return 2

    env, tmp = git_env_with_token()
    try:
        changed: list[str] = []

        if not repo_url:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            if is_workspace(local_path):
                registered = set_active_workspace(local_path)
                print('workspace_ensure_status: READY')
                print(f'active_workspace: {registered}')
                if quiet:
                    return 0
                print(f'workspace_path: {local_path}')
                return 0

            if local_path.exists() and any(local_path.iterdir()):
                print('workspace_ensure_status: BLOCKED')
                print(f'reason: path exists but is not an LBAI workspace: {local_path}')
                return 2

            local_path.mkdir(parents=True, exist_ok=True)
            print('workspace_ensure_status: PENDING_BIND')
            print(f'workspace_path: {local_path}')
            print(f'next_step: {BIND_GITHUB_CMD}')
            if quiet:
                return 0
            print_github_sync_setup_guide(local_path)
            return 0

        remote_state = inspect_remote_repo(repo_url, env=env)
        if remote_state == 'unreachable':
            print('workspace_ensure_status: BLOCKED')
            print('reason: cannot reach remote repo')
            print(f'next_step: check repo URL, token permissions, or run {GITHUB_AUTH_TOKEN_CMD}')
            return 2

        if remote_state == 'lbai_workspace':
            print('workspace_source: personal_repo')
            ok, detail = restore_from_personal_repo(local_path, repo_url, env=env)
            if not ok:
                print('workspace_ensure_status: BLOCKED')
                print(f'reason: {detail}')
                return 2
            print(f'workspace_sync: {detail}')
        else:
            print('workspace_source: enterprise_template')
            if remote_state == 'seedable':
                ok, detail = clone_raw_repo(local_path, repo_url, env=env)
                if not ok:
                    print('workspace_ensure_status: BLOCKED')
                    print(f'reason: {detail}')
                    return 2
            else:
                local_path.parent.mkdir(parents=True, exist_ok=True)
                if local_path.exists() and any(local_path.iterdir()) and not is_workspace(local_path):
                    shutil.rmtree(local_path)
                local_path.mkdir(parents=True, exist_ok=True)

            changed = copy_template_into_workspace(local_path, overwrite_managed=True)
            if not args.no_git and not (local_path / '.git').exists():
                run(['git', 'init', '-b', 'main'], cwd=local_path)
            commit_and_push_workspace(
                local_path,
                repo_url,
                env,
                args,
                commit_message='chore(lbai): initialize shared workspace',
            )

        registered = register_workspace_if_ready(local_path)
        if not registered:
            print('workspace_ensure_status: BLOCKED')
            print('reason: workspace is missing required LBAI files')
            return 2

        print('workspace_ensure_status: READY')
        print(f'active_workspace: {registered}')
        if quiet:
            return 0
        print(f'workspace_path: {local_path}')
        if changed:
            print('changed:')
            for item in changed:
                print(f'- {item}')
        return 0
    finally:
        if tmp:
            tmp.cleanup()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='lbai')
    parser.add_argument('--version', action='version', version=f'lbai {read_version()}')
    sub = parser.add_subparsers(dest='command')

    auth = sub.add_parser('auth', help='Backend auth and credential checks.')
    auth_sub = auth.add_subparsers(dest='auth_command')
    backend_login = auth_sub.add_parser('backend-login')
    backend_login.add_argument('--api-key')
    backend_login.add_argument('--api-key-header', default=KNOWLEDGE_SERVICE_API_KEY_HEADER)
    backend_login.add_argument('--base-url', default=KNOWLEDGE_SERVICE_BASE_URL)
    backend_login.add_argument('--identity-token')
    backend_login.add_argument('--identity-header', default='X-LBAI-Identity-Token')
    backend_login.add_argument('--verify-timeout', type=int, default=10)
    backend_login.add_argument('--no-verify', action='store_true')
    backend_login.add_argument('--optional', action='store_true')
    auth_sub.add_parser('doctor', help='Check GitHub token sync and backend auth status.')

    github = sub.add_parser('github', help='GitHub integration for LBAI CLI.')
    github_sub = github.add_subparsers(dest='github_command')
    github_auth = github_sub.add_parser('auth', help='Configure GitHub authentication.')
    github_auth_sub = github_auth.add_subparsers(dest='github_auth_command')
    github_auth_sub.add_parser(
        'token',
        help='Save GitHub personal access token and sync Git credentials.',
    )

    init = sub.add_parser('init-workspace')
    init.add_argument('--repo-url')
    init.add_argument('--path')
    init.add_argument('--no-commit', action='store_true')
    init.add_argument('--no-push', action='store_true')

    bind_github_parser = sub.add_parser(
        'bind-github',
        help='Bind a private GitHub repo URL to the active workspace (paste URL only).',
    )
    bind_github_parser.add_argument('--repo-url')
    bind_github_parser.add_argument('--no-commit', action='store_true')
    bind_github_parser.add_argument('--no-push', action='store_true')

    doc = sub.add_parser('doctor')
    doc.add_argument('--path')
    doc.add_argument('--json', action='store_true')
    doc.add_argument('--plugin-version')
    doc.add_argument('--min-workspace-version', default=PLUGIN_MIN_WORKSPACE_VERSION)
    doc.add_argument('--require-backend', action='store_true')
    doc.add_argument('--allow-missing-upstream', action='store_true')

    workspace = sub.add_parser('workspace', help='Show or update the registered global LBAI workspace.')
    workspace_sub = workspace.add_subparsers(dest='workspace_command')
    workspace_show_parser = workspace_sub.add_parser('show', help='Show the active workspace and current resolution.')
    workspace_show_parser.add_argument('--json', action='store_true')
    workspace_set_parser = workspace_sub.add_parser('set', help='Register the global active LBAI workspace path.')
    workspace_set_parser.add_argument('--path', required=True)
    workspace_sub.add_parser('clear', help='Clear the registered global active workspace path.')
    workspace_ensure_parser = workspace_sub.add_parser(
        'ensure',
        help='Create or refresh the default shared LBAI workspace and register it globally.',
    )
    workspace_ensure_parser.add_argument('--path')
    workspace_ensure_parser.add_argument('--repo-url')
    workspace_ensure_parser.add_argument('--no-git', action='store_true')
    workspace_ensure_parser.add_argument('--no-commit', action='store_true')
    workspace_ensure_parser.add_argument('--no-push', action='store_true')
    workspace_ensure_parser.add_argument(
        '--quiet',
        action='store_true',
        help='Only print readiness status (for install scripts).',
    )

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
    setup_guide_parser = sub.add_parser(
        'setup-guide',
        help='Show beginner-friendly post-install setup steps.',
    )
    setup_guide_parser.add_argument(
        '--path',
        help='Workspace path for step 3 (defaults to active or shared workspace).',
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
        if known.auth_command == 'backend-login':
            return auth_backend_login(known)
        if known.auth_command == 'doctor':
            return auth_doctor(known)
        parser.error(f'auth requires backend-login or doctor; use {GITHUB_AUTH_TOKEN_CMD} for GitHub token setup')
    if known.command == 'github':
        if known.github_command == 'auth':
            if known.github_auth_command == 'token':
                return github_auth_token(known)
            parser.error('github auth requires token')
        parser.error('github requires auth')
    if known.command == 'init-workspace':
        return init_workspace(known)
    if known.command == 'bind-github':
        return bind_github(known)
    if known.command == 'doctor':
        return doctor(known)
    if known.command == 'workspace':
        if known.workspace_command == 'show':
            return workspace_show(known)
        if known.workspace_command == 'set':
            return workspace_set(known)
        if known.workspace_command == 'clear':
            return workspace_clear(known)
        if known.workspace_command == 'ensure':
            return workspace_ensure(known)
        parser.error('workspace requires show, set, ensure, or clear')
    if known.command == 'update-kit':
        return update_kit(known)
    if known.command == 'remove-kit':
        return remove_kit(known)
    if known.command == 'uninstall':
        return uninstall(known)
    if known.command == 'setup-guide':
        return setup_guide(known)
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
