#!/usr/bin/env python3
import json
from pathlib import Path

from task_utils import read_text


def load_json_file(path: Path) -> tuple[dict | None, str]:
    if not path.exists():
        return None, f'enrichment file not found: {path}'
    try:
        data = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        return None, f'enrichment JSON parse error: {exc}'
    if not isinstance(data, dict):
        return None, 'enrichment must be a JSON object'
    return data, ''


def require_version(data: dict, version: str) -> str | None:
    if data.get('schema_version') != version:
        return f'schema_version must be {version}'
    return None


def resolve_enrichment_path(root: Path, raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = (root / path).resolve()
    return path
