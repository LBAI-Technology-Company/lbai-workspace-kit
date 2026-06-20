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
    status = data.get('status', 'ERROR')
    lines = [
        f'artifact 查询结果：{status}',
        f'query: {query or None}',
        'source: backend',
        'matches:',
    ]
    results = data.get('results') or []
    if not results:
        lines.append('- None')
    for idx, item in enumerate(results, 1):
        facts = item.get('facts') or []
        lines.extend([
            f'{idx}. {item.get("title") or item.get("concept_uid") or "unknown"}',
            f'   concept_uid: {item.get("concept_uid", "")}',
            f'   type: {item.get("type", "unknown")}',
            f'   source: {source_label(item)}',
            f'   description: {item.get("description", "")}',
            f'   facts: {"；".join(str(fact.get("statement") or "") for fact in facts)}',
            f'   reason: {item.get("reason", "")}',
        ])
    if data.get('error'):
        lines.append(f'backend_error: {data.get("error")}')
    lines.append('下一步：使用命中的 OKF 概念和原子事实继续当前任务。' if results else '下一步：未找到匹配知识，可补充或调整 OKF 概念。')
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
