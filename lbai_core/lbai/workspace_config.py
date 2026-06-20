"""Global LBAI workspace registration and cross-project resolution."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

CONFIG_SCHEMA_VERSION = 'lbai_global_config_v1'
ACTIVE_WORKSPACE_KEY = 'active_workspace'


def lbai_home() -> Path:
    return Path(os.environ.get('LBAI_HOME', '~/.lbai')).expanduser()


def config_path() -> Path:
    return lbai_home() / 'config.json'


def is_workspace(path: Path) -> bool:
    return (
        (path / 'AGENTS.md').exists()
        and (path / 'lbai_system' / 'runner_contracts' / 'lbai_command_contract_v1.md').exists()
        and (path / 'role_workspace').exists()
        and (path / 'tasks').exists()
    )


def read_global_config() -> dict:
    path = config_path()
    if not path.exists():
        return {'schema_version': CONFIG_SCHEMA_VERSION}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {'schema_version': CONFIG_SCHEMA_VERSION}
    return data if isinstance(data, dict) else {'schema_version': CONFIG_SCHEMA_VERSION}


def write_global_config(data: dict) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(data)
    payload['schema_version'] = CONFIG_SCHEMA_VERSION
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def configured_active_workspace_path() -> Path | None:
    raw = read_global_config().get(ACTIVE_WORKSPACE_KEY)
    if not raw:
        return None
    text = str(raw).strip()
    if not text:
        return None
    return Path(text).expanduser().resolve()


def get_active_workspace() -> Path | None:
    path = configured_active_workspace_path()
    if path and is_workspace(path):
        return path
    return None


def set_active_workspace(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if not is_workspace(resolved):
        raise ValueError(f'not an LBAI workspace: {resolved}')
    config = read_global_config()
    config[ACTIVE_WORKSPACE_KEY] = str(resolved)
    config['active_workspace_set_at'] = datetime.now(timezone.utc).isoformat()
    write_global_config(config)
    return resolved


def clear_active_workspace() -> bool:
    config = read_global_config()
    if ACTIVE_WORKSPACE_KEY not in config:
        return False
    config.pop(ACTIVE_WORKSPACE_KEY, None)
    config.pop('active_workspace_set_at', None)
    write_global_config(config)
    return True


def resolve_workspace_root(
    *,
    explicit_path: str | Path | None = None,
    start: Path | None = None,
) -> tuple[Path, str]:
    """Return (candidate_root, resolution_source)."""
    if explicit_path:
        return Path(explicit_path).expanduser().resolve(), 'explicit_path'

    env_path = os.environ.get('LBAI_WORKSPACE', '').strip()
    if env_path:
        return Path(env_path).expanduser().resolve(), 'env'

    current = (start or Path.cwd()).resolve()
    for path in [current, *current.parents]:
        if is_workspace(path):
            return path, 'walk_up'

    active = get_active_workspace()
    if active:
        return active, 'active_workspace'

    configured = configured_active_workspace_path()
    if configured:
        return configured, 'active_workspace_invalid'

    return current, 'unresolved'


def invocation_cwd() -> Path:
    return Path.cwd().resolve()


def source_project_path(workspace: Path) -> str | None:
    cwd = invocation_cwd()
    try:
        cwd.relative_to(workspace.resolve())
        return None
    except ValueError:
        return str(cwd)


def workspace_resolution_context(
    *,
    explicit_path: str | Path | None = None,
    start: Path | None = None,
) -> dict:
    root, source = resolve_workspace_root(explicit_path=explicit_path, start=start)
    active = configured_active_workspace_path()
    return {
        'workspace_root': str(root),
        'workspace_valid': is_workspace(root),
        'resolution_source': source,
        'active_workspace': str(active) if active else None,
        'invocation_cwd': str(invocation_cwd()),
        'source_project_path': source_project_path(root) if is_workspace(root) else source_project_path(get_active_workspace() or root),
    }
