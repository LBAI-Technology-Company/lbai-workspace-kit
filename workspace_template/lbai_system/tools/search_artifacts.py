#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from enrichment_utils import load_json_file, resolve_enrichment_path, validate_with_schema
from search_backend import search_backend
from task_utils import workspace_root


BLOCKED_MESSAGE = (
    'AI backend query plan required. Use Cursor or Codex desktop app; '
    'see lbai_system/prompts/backend_search_query_plan_prompt_v1.md'
)


def source_label(item: dict) -> str:
    source = item.get('source') or {}
    if isinstance(source, dict):
        return str(source.get('path') or source.get('id') or 'unknown')
    return str(source or 'unknown')


def render_backend_result(data: dict, query: str) -> str:
    status = data.get('query_status', 'ERROR')
    lines = [
        f'artifact 查询结果：{status}',
        f'query: {query or None}',
        'source: backend',
        'matches:',
    ]
    pack = data.get('evidence_pack') or []
    if not pack:
        lines.append('- None')
    for idx, item in enumerate(pack, 1):
        lines.extend([
            f'{idx}. {item.get("subject") or item.get("event_id") or "unknown"}',
            f'   event_id: {item.get("event_id", "")}',
            f'   entity_type: {item.get("entity_type", "unknown")}',
            f'   status: {item.get("status", "unknown")}',
            f'   source: {source_label(item)}',
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
    if data.get('error'):
        lines.append(f'backend_error: {data.get("error")}')
    lines.append(f'下一步：{data.get("next_step", "None")}')
    return '\n'.join(lines) + '\n'


def render_backend_error(message: str, query: str | None = None) -> str:
    lines = [
        'artifact 查询结果：ERROR',
        f'query: {query or "None"}',
        'source: backend',
        'matches:',
        '- None',
        f'backend_error: {message}',
        '下一步：搜索结果仅供参考；不要回退搜索本地 workspace artifacts，也不要自动阻断、修改或推进其他任务流程。',
    ]
    return '\n'.join(lines) + '\n'


def block(message: str, query: str | None = None) -> int:
    print('artifact 查询结果：BLOCKED')
    print(f'query: {query or "None"}')
    print('source: backend')
    print('matches: None')
    print(f'backend_error: {message}')
    print('下一步：检查后端知识服务配置或稍后重试；不要降级搜索本地 workspace artifacts。')
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description='Search LBAI backend knowledge service with an AI query plan.')
    parser.add_argument('--enrichment', help='Path to AI-generated backend search query plan JSON.')
    args = parser.parse_args()

    root = workspace_root()
    if not args.enrichment:
        return block(BLOCKED_MESSAGE)

    enrichment_path = resolve_enrichment_path(root, args.enrichment)
    data, error = load_json_file(enrichment_path)
    if data is None:
        return block(error or BLOCKED_MESSAGE)

    validation_error = validate_with_schema(root, data, 'backend_search_query_plan_schema_v1.json')
    if validation_error:
        return block(validation_error, str(data.get('query') or ''))

    result, backend_error = search_backend(root, data)
    if result is None:
        print(render_backend_error(backend_error or 'backend search failed', str(data.get('query') or '')), end='')
        return 0

    print(render_backend_result(result, str(data.get('query') or '')), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
