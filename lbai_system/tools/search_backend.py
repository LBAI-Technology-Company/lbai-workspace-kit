#!/usr/bin/env python3
import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True

from enrichment_utils import load_json_file, resolve_enrichment_path, validate_with_schema
from task_utils import (
    KNOWLEDGE_SERVICE_API_KEY_HEADER,
    employee_identity,
    knowledge_service_config,
    knowledge_service_credentials,
    workspace_root,
)


def backend_url(base_url: str, path: str) -> str:
    return base_url.rstrip('/') + path


def build_request(root: Path, query_plan: dict) -> tuple[dict | None, str | None]:
    config = knowledge_service_config(root)
    identity = employee_identity(root)
    if not config.get('enabled'):
        return None, 'knowledge_service.disabled'
    base_url = str(config.get('base_url') or '').strip()
    if not base_url:
        return None, 'knowledge_service.base_url missing'
    employee_user_id = str(identity.get('employee_user_id') or '').strip()
    if not employee_user_id:
        return None, 'employee_identity.employee_user_id missing'
    return {
        'workspace_repo_id': config.get('workspace_repo_id') or root.name,
        'employee_user_id': employee_user_id,
        'task_text': query_plan.get('query', ''),
        'query_plan': query_plan,
        'limit': int(query_plan.get('limit') or 10),
    }, None


def post_json(
    url: str,
    payload: dict,
    timeout: int,
    api_key: str | None = None,
    api_key_header: str = KNOWLEDGE_SERVICE_API_KEY_HEADER,
) -> tuple[dict | None, str | None]:
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    api_key = str(api_key or '').strip()
    api_key_header = str(api_key_header or KNOWLEDGE_SERVICE_API_KEY_HEADER).strip()
    if api_key and api_key_header:
        headers[api_key_header] = api_key
    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            text = response.read().decode('utf-8')
    except urllib.error.HTTPError as exc:
        return None, f'HTTP_{exc.code}: {exc.reason}'
    except urllib.error.URLError as exc:
        return None, f'URL_ERROR: {exc.reason}'
    except TimeoutError:
        return None, 'TIMEOUT'
    try:
        return json.loads(text), None
    except json.JSONDecodeError as exc:
        return None, f'INVALID_JSON: {exc}'


def render_response(data: dict, source: str = 'backend') -> str:
    status = data.get('query_status', 'ERROR')
    lines = [
        f'backend 查询结果：{status}',
        f'source: {source}',
    ]
    if data.get('backend_status'):
        lines.append(f'backend_status: {data.get("backend_status")}')
    if data.get('backend_error'):
        lines.append(f'backend_error: {data.get("backend_error")}')
    lines.append('evidence_pack:')
    pack = data.get('evidence_pack') or []
    if not pack:
        lines.append('- None')
    for idx, item in enumerate(pack, 1):
        source_data = item.get('source') or {}
        source_path = source_data.get('path') or source_data.get('id') or 'unknown'
        lines.extend([
            f'{idx}. {item.get("subject") or item.get("event_id") or "unknown"}',
            f'   entity_type: {item.get("entity_type", "unknown")}',
            f'   status: {item.get("status", "unknown")}',
            f'   source: {source_path}',
            f'   value: {item.get("value", "")}',
            f'   evidence_text: {item.get("evidence_text", "")}',
            f'   reason: {item.get("reason", "")}',
        ])
    if data.get('open_questions'):
        lines.append('open_questions:')
        lines.extend(f'- {item}' for item in data.get('open_questions') or [])
    if data.get('conflicts'):
        lines.append('conflicts:')
        lines.extend(f'- {item}' for item in data.get('conflicts') or [])
    lines.append(f'下一步：{data.get("next_step", "None")}')
    return '\n'.join(lines) + '\n'


def search_backend(root: Path, query_plan: dict) -> tuple[dict | None, str | None]:
    request_data, config_error = build_request(root, query_plan)
    if config_error:
        return None, config_error
    config = knowledge_service_config(root)
    credentials = knowledge_service_credentials(root)
    if not credentials.get('api_key'):
        return None, 'knowledge_service.api_key missing; run lbai auth backend-login'
    timeout = int(config.get('search_timeout_seconds') or 20)
    url = backend_url(str(config.get('base_url')), '/v1/search/evidence')
    data, error = post_json(
        url,
        request_data,
        timeout,
        credentials.get('api_key'),
        str(credentials.get('api_key_header') or KNOWLEDGE_SERVICE_API_KEY_HEADER),
    )
    if error:
        return None, error
    validation_error = validate_with_schema(root, data, 'backend_evidence_search_response_schema_v1.json')
    if validation_error:
        return None, validation_error
    return data, None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--query-plan', required=True)
    args = parser.parse_args()
    root = workspace_root()
    path = resolve_enrichment_path(root, args.query_plan)
    data, error = load_json_file(path)
    if data is None:
        print('backend 查询结果：ERROR')
        print(f'reason: {error}')
        return 1
    validation_error = validate_with_schema(root, data, 'backend_search_query_plan_schema_v1.json')
    if validation_error:
        print('backend 查询结果：ERROR')
        print(f'reason: {validation_error}')
        return 1
    result, backend_error = search_backend(root, data)
    if result is None:
        print('backend 查询结果：ERROR')
        print(f'reason: {backend_error}')
        return 1
    print(render_response(result), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
