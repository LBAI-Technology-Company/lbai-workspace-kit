#!/usr/bin/env python3
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from search_backend import backend_url, post_json
from task_utils import (
    KNOWLEDGE_SERVICE_API_KEY_HEADER,
    employee_identity,
    knowledge_service_config,
    knowledge_service_credentials,
    workspace_root,
)


def role_profile(root: Path) -> dict:
    path = root / 'role_workspace' / 'world_model' / 'ROLE_PROFILE_v1.json'
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def role_id_from_profile(profile: dict) -> str:
    value = str(profile.get('employee_position') or '').strip().lower()
    return '_'.join(part for part in value.replace('/', ' ').replace('-', ' ').split() if part) or 'unknown_role'


def fetch_role_memory_context(root: Path, task_text: str, limit: int = 10) -> tuple[dict | None, str | None]:
    config = knowledge_service_config(root)
    if not config.get('enabled'):
        return None, 'knowledge_service.disabled'
    base_url = str(config.get('base_url') or '').strip()
    if not base_url:
        return None, 'knowledge_service.base_url missing'
    identity = employee_identity(root)
    employee_user_id = str(identity.get('employee_user_id') or '').strip()
    if not employee_user_id:
        return None, 'employee_identity.employee_user_id missing'
    credentials = knowledge_service_credentials(root)
    if not credentials.get('api_key'):
        return None, 'knowledge_service.api_key missing; run lbai auth backend-login'

    profile = role_profile(root)
    payload = {
        'employee_user_id': employee_user_id,
        'workspace_repo_id': config.get('workspace_repo_id') or root.name,
        'role_id': role_id_from_profile(profile),
        'employee_position': profile.get('employee_position') or '',
        'task_text': task_text,
        'limit': limit,
    }
    timeout = int(config.get('search_timeout_seconds') or 20)
    data, error = post_json(
        backend_url(base_url, '/v1/role-memory/context'),
        payload,
        timeout,
        credentials.get('api_key'),
        str(credentials.get('api_key_header') or KNOWLEDGE_SERVICE_API_KEY_HEADER),
    )
    if error:
        return None, error
    if not isinstance(data, dict):
        return None, 'INVALID_RESPONSE: expected object'
    return data, None


def render_role_memory_context(data: dict, source: str = 'backend') -> str:
    status = data.get('context_status', 'UNKNOWN')
    lines = [
        f'role_memory_context: {status}',
        f'source: {source}',
        'memory_items:',
    ]
    items = data.get('memory_items') or []
    if not items:
        lines.append('- None')
    for idx, item in enumerate(items, 1):
        lines.extend([
            f'{idx}. {item.get("title") or item.get("memory_id") or "untitled"}',
            f'   type: {item.get("type", "unknown")}',
            f'   confidence: {item.get("confidence", "unknown")}',
            f'   rule: {item.get("rule") or item.get("content") or ""}',
        ])
    return '\n'.join(lines) + '\n'


def write_role_memory_context(root: Path, task_dir: Path, data: dict, source: str = 'backend') -> list[str]:
    if str(data.get('context_status') or '').upper() != 'FOUND':
        return []
    task_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        'schema_version': 'task_role_memory_context_v1',
        'source': source,
        'role_memory_context': data,
    }
    json_path = task_dir / 'role_memory_context.json'
    md_path = task_dir / 'role_memory_context.md'
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    md_path.write_text('# Role Memory Context\n\n' + render_role_memory_context(data, source), encoding='utf-8')
    return [str(json_path.relative_to(root)), str(md_path.relative_to(root))]


def retrieve_role_memory_context(root: Path, task_dir: Path, task_text: str) -> str:
    data, error = fetch_role_memory_context(root, task_text)
    if data is None:
        return f'role_memory_context skipped: {error}'
    written = write_role_memory_context(root, task_dir, data, 'backend')
    detail = render_role_memory_context(data, 'backend').strip()
    if written:
        detail += '\nwritten:\n' + '\n'.join(f'- {item}' for item in written)
    return detail


def main() -> int:
    root = workspace_root()
    task_text = ' '.join(sys.argv[1:]).strip()
    if not task_text:
        print('role_memory_context: ERROR')
        print('reason: task_text missing')
        return 2
    data, error = fetch_role_memory_context(root, task_text)
    if data is None:
        print('role_memory_context: ERROR')
        print(f'reason: {error}')
        return 1
    print(render_role_memory_context(data), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
