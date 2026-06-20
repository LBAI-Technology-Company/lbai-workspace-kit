#!/usr/bin/env python3
import json
import os
import re
import subprocess
from datetime import date
from pathlib import Path
from typing import Optional


STATUS_VALUES = ['OPEN', 'BLOCKED', 'COMPLETED']
KNOWLEDGE_SERVICE_BASE_URL = 'https://workflow-kit.lbai.ai'
KNOWLEDGE_SERVICE_API_KEY_ENV = 'LBAI_KNOWLEDGE_SERVICE_API_KEY'
KNOWLEDGE_SERVICE_API_KEY_HEADER = 'X-LBAI-API-Key'
KNOWLEDGE_SERVICE_IDENTITY_HEADER = 'X-LBAI-Identity-Token'
LEADER_REVIEW_REMINDER = '对外发布或涉及官网/定价/合规/投资人/媒体/客户承诺等内容前，请负责人 review；本流程不阻断执行。'
REVIEW_TASK_FILES = ['overclaim_check.md', 'release_boundary_check.md', 'founder_review_needed.md']
OPTIONAL_REVIEW_TASK_FILES = ['leader_review_request.md']
REVIEW_ALLOWED_TASK_FILES = REVIEW_TASK_FILES + OPTIONAL_REVIEW_TASK_FILES
REQUIRED_TASK_FILES = ['task_scope.md', 'task_slot.md', 'task_output.md', 'task_ledger.md']
RECOMMENDED_TASK_FILES = ['execution_plan.md']

SENSITIVE_PATTERNS = [
    r'\b(password|api[_-]?key|access[_-]?token|secret[_-]?token|secret)\b\s*[:=]\s*(?!["\']?(?:[\$<{]|粘贴|YOUR_|your_|xxx|XXX|example|EXAMPLE|os\.|None|none|str\b|api[_-]?key\b|env_|config\.get))[^\s,，。;；]+',
    r'bearer\s+[a-zA-Z0-9\._\-]+',
    r'sk-[a-zA-Z0-9]{20,}',
    r'sk-proj-[a-zA-Z0-9_\-]{20,}',
    r'AIza[0-9A-Za-z\-_]{20,}',
    r'ghp_[0-9A-Za-z]{20,}',
    r'github_pat_[0-9A-Za-z_]{20,}',
    r'AKIA[0-9A-Z]{16}',
    r'xox[baprs]-[0-9A-Za-z\-]{20,}',
    r'(?i)stripe[_-]?(secret|live)?[_-]?key\s*[:=]\s*\S+',
    r'eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}',
    r'-----BEGIN (RSA |EC |OPENSSH |PRIVATE )?PRIVATE KEY-----',
    r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b',
    r'(?<!\d)(?:\+?86[-\s]?)?1[3-9]\d{9}(?!\d)',
    r'(?<!\d)(?:\+?1[-\s.]?)?\(?\d{3}\)?[-\s.]?\d{3}[-\s.]?\d{4}(?!\d)',
]

REDACTION = '[SENSITIVE INFORMATION REDACTED - USE APPROVED SECURE CHANNEL]'


def default_workspace_config() -> dict:
    return {
        'employee_identity': {
            'employee_user_id': '',
            'display_name': '',
            'email': '',
            'department': '',
        },
        'knowledge_service': {
            'enabled': False,
            'base_url': KNOWLEDGE_SERVICE_BASE_URL,
            'api_key_header': KNOWLEDGE_SERVICE_API_KEY_HEADER,
            'workspace_repo_id': '',
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


def load_workspace_config(root: Path | None = None) -> dict:
    root = root or workspace_root()
    path = root / '.lbai' / 'workspace.json'
    defaults = default_workspace_config()
    if not path.exists():
        return defaults
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return defaults
    if not isinstance(data, dict):
        return defaults
    return deep_merge(defaults, data)


def employee_identity(root: Path | None = None) -> dict:
    return load_workspace_config(root).get('employee_identity', {})


def knowledge_service_config(root: Path | None = None) -> dict:
    return load_workspace_config(root).get('knowledge_service', {})


def lbai_home() -> Path:
    return Path(os.environ.get('LBAI_HOME', '~/.lbai')).expanduser()


def knowledge_service_auth_path() -> Path:
    return lbai_home() / 'auth' / 'knowledge_service.json'


def load_knowledge_service_auth() -> dict:
    path = knowledge_service_auth_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def knowledge_service_credentials(root: Path | None = None) -> dict:
    config = knowledge_service_config(root)
    auth = load_knowledge_service_auth()
    api_key = str(auth.get('api_key') or '').strip()
    api_key_header = str(auth.get('api_key_header') or '').strip()
    if not api_key:
        api_key = os.environ.get(KNOWLEDGE_SERVICE_API_KEY_ENV, '').strip()
        api_key_header = KNOWLEDGE_SERVICE_API_KEY_HEADER
    return {
        'api_key': api_key,
        'api_key_header': api_key_header or KNOWLEDGE_SERVICE_API_KEY_HEADER,
        'identity_token': str(auth.get('identity_token') or '').strip(),
        'identity_header': str(auth.get('identity_header') or KNOWLEDGE_SERVICE_IDENTITY_HEADER).strip(),
    }


def knowledge_service_enabled(root: Path | None = None) -> bool:
    config = knowledge_service_config(root)
    return bool(config.get('enabled')) and bool(str(config.get('base_url') or '').strip())


def git_root() -> Optional[Path]:
    try:
        out = subprocess.check_output(
            ['git', 'rev-parse', '--show-toplevel'],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return Path(out)
    except Exception:
        return None


def _lbai_core_search_paths() -> list[Path]:
    home = lbai_home()
    return [
        home / 'kit' / 'lbai_core',
        Path(__file__).resolve().parents[2] / 'lbai_core',
    ]


def _workspace_config_module():
    import sys

    for base in _lbai_core_search_paths():
        if (base / 'lbai' / 'workspace_config.py').exists():
            base_str = str(base)
            if base_str not in sys.path:
                sys.path.insert(0, base_str)
            from lbai import workspace_config

            return workspace_config
    return None


def is_workspace(path: Path) -> bool:
    module = _workspace_config_module()
    if module:
        return module.is_workspace(path)
    return (
        (path / 'AGENTS.md').exists()
        and (path / 'lbai_system' / 'runner_contracts' / 'lbai_command_contract_v1.md').exists()
        and (path / 'role_workspace').exists()
        and (path / 'tasks').exists()
    )


def workspace_root() -> Path:
    module = _workspace_config_module()
    if module:
        root, source = module.resolve_workspace_root()
        if module.is_workspace(root):
            return root
        if source in {'active_workspace', 'active_workspace_invalid'}:
            return root

    current = Path.cwd().resolve()
    for path in [current, *current.parents]:
        if is_workspace(path):
            return path

    git = git_root()
    if git and is_workspace(git):
        return git
    return git or current


def source_project_path(root: Path | None = None) -> str | None:
    workspace = (root or workspace_root()).resolve()
    module = _workspace_config_module()
    if module:
        return module.source_project_path(workspace)
    try:
        Path.cwd().resolve().relative_to(workspace)
        return None
    except ValueError:
        return str(Path.cwd().resolve())


def prompt_lab_isolated_mode() -> bool:
    return os.environ.get('LBAI_PROMPT_LAB_ISOLATED') == '1'


def slugify(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "untitled_task"


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return ''


def write_if_missing(path: Path, content: str, root: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content, encoding='utf-8')
        print(f"CREATE {path.relative_to(root)}")
    else:
        print(f"SKIP existing {path.relative_to(root)}")


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def task_root(root: Path) -> Path:
    return root / 'tasks'


def is_task_dir(path: Path, root: Path) -> bool:
    resolved = path.resolve()
    return (
        is_relative_to(resolved, task_root(root))
        and (resolved / 'task_scope.md').exists()
        and (resolved / 'task_ledger.md').exists()
    )


def unresolved_missing_inputs(task_dir: Path) -> list[str]:
    missing = task_dir / 'missing_inputs.md'
    if not missing.exists():
        return []
    items = []
    for line in read_text(missing).splitlines():
        stripped = line.strip()
        if not stripped.startswith('-'):
            continue
        value = stripped.lstrip('-').strip()
        low = value.lower()
        if not value or value.lower() == 'none' or 'resolved' in low:
            continue
        items.append(value)
    return items


def set_markdown_field(text: str, field: str, value: str) -> str:
    pattern = rf'(## {re.escape(field)}\n)(.*?)(?=\n## |\Z)'
    if re.search(pattern, text, flags=re.S):
        return re.sub(pattern, lambda match: f'{match.group(1)}{value.strip()}\n', text, flags=re.S)
    suffix = '' if text.endswith('\n') else '\n'
    return f'{text}{suffix}\n## {field}\n{value.strip()}\n'


def markdown_field(text: str, field: str) -> str:
    match = re.search(rf'## {re.escape(field)}\n(.*?)(?=\n## |\Z)', text, flags=re.S)
    return match.group(1).strip() if match else ''


def any_markdown_field_value(text: str, field: str, predicate) -> bool:
    pattern = rf'(?:^|\n)## {re.escape(field)}\s*\n(.*?)(?=\n## |\Z)'
    for match in re.finditer(pattern, text, flags=re.S | re.I):
        if predicate(match.group(1).strip()):
            return True
    return False


def task_status(task_dir: Path) -> str:
    combined = f"{read_text(task_dir / 'task_scope.md')}\n{read_text(task_dir / 'task_ledger.md')}"
    matches = re.findall(r'(?:^|\n)## status\s*\n([A-Z_]+)|status\s*[:=]\s*([A-Z_]+)', combined, flags=re.I)
    values = [m[0] or m[1] for m in matches]
    for value in reversed(values):
        upper = value.upper()
        if upper in STATUS_VALUES:
            return upper
    if (task_dir / 'task_output.md').exists():
        return 'COMPLETED'
    return 'OPEN'


def review_required(task_path: Path) -> bool:
    combined = f"{read_text(task_path / 'task_scope.md')}\n{read_text(task_path / 'task_ledger.md')}".lower()
    if re.search(r'review_needed\s*\ntrue', combined) or re.search(r'review_needed\s*[:=]\s*true', combined):
        return True
    if any_markdown_field_value(combined, 'leader_review_reminder', lambda value: bool(value) and value not in {'none', 'false', 'no'}):
        return True
    if re.search(r'review_needed\s*\nfalse', combined) or re.search(r'review_needed\s*[:=]\s*false', combined):
        return False
    risk = markdown_field(combined, 'risk_level')
    return 'high' in risk


def redact_sensitive(text: str) -> tuple[str, list[str]]:
    findings = []
    redacted = text
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, redacted, re.IGNORECASE | re.MULTILINE):
            findings.append(pattern)
            redacted = re.sub(pattern, REDACTION, redacted, flags=re.IGNORECASE | re.MULTILINE)
    return redacted, findings


def today_slugged_task_dir(root: Path, description: str) -> Path:
    today = date.today().strftime('%Y_%m_%d')
    slug = slugify(description)[:80]
    return root / 'tasks' / f'{today}_{slug}'
