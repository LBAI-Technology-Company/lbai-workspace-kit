#!/usr/bin/env python3
import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.dont_write_bytecode = True

from enrichment_utils import load_json_file, require_version, resolve_enrichment_path
from task_utils import read_text, workspace_root


MAX_SNIPPET_CHARS = 220
CATALOG_EXCERPT_CHARS = 480
ENRICHMENT_VERSION = 'search_enrichment_v1'
BLOCKED_MESSAGE = (
    'AI enrichment required. Use Cursor or Codex desktop app; '
    'see lbai_system/prompts/search_enrichment_prompt_v1.md'
)


@dataclass
class Artifact:
    kind: str
    artifact_id: str
    path: str
    title: str
    status: str
    usage: str
    linked_task: str
    risk: str
    search_text: str
    reason: str = ''
    score: int = 0


def parse_markdown_table(markdown: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in markdown.splitlines() if line.strip().startswith('|')]
    if len(lines) < 2:
        return []
    header = split_table_line(lines[0])
    rows = []
    for line in lines[2:]:
        cells = split_table_line(line)
        if not cells or all(re.fullmatch(r'-+', cell) for cell in cells):
            continue
        rows.append({name: cells[idx] if idx < len(cells) else '' for idx, name in enumerate(header)})
    return rows


def split_table_line(line: str) -> list[str]:
    return [cell.strip().strip('`') for cell in line.strip().strip('|').split('|')]


def markdown_field(markdown: str, field: str) -> str:
    escaped = re.escape(field)
    match = re.search(rf'(?:^|\n)## {escaped}\s*\n(.*?)(?=\n## |\Z)', markdown, flags=re.S | re.I)
    return match.group(1).strip() if match else ''


def first_heading(markdown: str) -> str:
    match = re.search(r'^#\s+(.+)$', markdown, flags=re.M)
    return match.group(1).strip() if match else ''


def clean(value: str) -> str:
    text = str(value or '').replace('\n', ' ').strip()
    return '' if text.lower() == 'none' else text


def truthy_review_value(value: str) -> bool:
    return str(value or '').strip().lower() in {'true', 'yes', 'review', 'needs_review'}


def has_review_reminder(*values: str) -> bool:
    return any(clean(value).lower() not in {'', 'none', 'false', 'no'} for value in values)


def strip_code_fences(text: str) -> str:
    return re.sub(r'```.*?```', ' ', text, flags=re.S)


def excerpt(text: str, limit: int = CATALOG_EXCERPT_CHARS) -> str:
    compact = re.sub(r'\s+', ' ', strip_code_fences(text)).strip()
    if not compact:
        return ''
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + '...'


def relative_artifact_path(root: Path, path: Path, fallback: str) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return fallback


def evidence_path_for(root: Path, evidence_id: str) -> Path:
    direct = root / evidence_id
    if direct.exists():
        return direct
    return root / 'role_workspace' / 'knowledge' / 'evidence' / evidence_id


def evidence_artifact(root: Path, evidence_id: str, evidence_path: Path, row: dict[str, str]) -> Artifact:
    evidence_rel = relative_artifact_path(root, evidence_path, evidence_id)
    metadata = read_text(evidence_path / 'evidence_metadata.md')
    brief = read_text(evidence_path / 'evidence_brief.md')
    body = read_text(evidence_path / 'input.md')
    kind = clean(row.get('Source Kind', '')) or clean(markdown_field(metadata, 'source_kind'))
    usage = clean(row.get('Usage Intent', '')) or clean(markdown_field(metadata, 'usage_intent'))
    status = clean(row.get('Status', '')) or clean(markdown_field(metadata, 'admissibility_status'))
    linked_task = clean(row.get('Linked Task', '')) or clean(markdown_field(metadata, 'linked_task'))
    sensitive_capture_status = clean(markdown_field(metadata, 'sensitive_capture_status'))
    redacted = clean(markdown_field(metadata, 'redacted')).lower() == 'true'
    if status.upper() == 'NEEDS_REVIEW':
        risk = 'needs_review'
    elif sensitive_capture_status.upper() == 'REDACTED' or redacted:
        risk = 'sensitive_redacted'
    else:
        risk = 'normal'
    title = excerpt(brief.splitlines()[0] if brief else '', 120) or evidence_path.name
    return Artifact(
        kind='evidence',
        artifact_id=evidence_id,
        path=evidence_rel,
        title=title,
        status=status or '-',
        usage=usage or '-',
        linked_task=linked_task or '-',
        risk=risk,
        search_text=' '.join([evidence_id, evidence_rel, kind, usage, status, linked_task, metadata, brief, body]),
    )


def collect_evidence(root: Path) -> list[Artifact]:
    ledger = root / 'role_workspace' / 'ledgers' / 'EVIDENCE_LEDGER_v1.md'
    artifacts = []
    seen = set()
    for row in parse_markdown_table(read_text(ledger)):
        evidence_id = clean(row.get('Evidence ID', ''))
        if not evidence_id:
            continue
        seen.add(evidence_id)
        evidence_path = evidence_path_for(root, evidence_id)
        artifacts.append(evidence_artifact(root, evidence_id, evidence_path, row))

    evidence_root = root / 'role_workspace' / 'knowledge' / 'evidence'
    if evidence_root.exists():
        for evidence_path in sorted(evidence_root.iterdir()):
            if not evidence_path.is_dir() or evidence_path.name.startswith('.'):
                continue
            evidence_rel = relative_artifact_path(root, evidence_path, evidence_path.name)
            if evidence_rel in seen or evidence_path.name in seen:
                continue
            if not (evidence_path / 'input.md').exists() and not (evidence_path / 'evidence_metadata.md').exists():
                continue
            artifacts.append(evidence_artifact(root, evidence_rel, evidence_path, {}))
    return artifacts


def task_artifact(root: Path, task_id: str, row: dict[str, str]) -> Artifact:
    rel = task_id if task_id.startswith('tasks/') else f'tasks/{task_id}'
    task_dir = root / rel
    scope = read_text(task_dir / 'task_scope.md')
    ledger = read_text(task_dir / 'task_ledger.md')
    output = read_text(task_dir / 'task_output.md')
    slot = read_text(task_dir / 'task_slot.md')
    task_markdown = []
    if task_dir.exists():
        for path in sorted(task_dir.rglob('*.md')):
            if path.name in {'task_scope.md', 'task_ledger.md', 'task_output.md', 'task_slot.md'}:
                continue
            task_markdown.append(read_text(path))
    goal = clean(row.get('Task Goal', '')) or clean(markdown_field(scope, 'goal')) or clean(markdown_field(scope, 'task_name')) or task_dir.name
    status = clean(row.get('Status', '')) or clean(markdown_field(ledger, 'status')) or clean(markdown_field(scope, 'status'))
    usage = clean(row.get('Source Artifacts', '')) or clean(markdown_field(ledger, 'source_artifacts'))
    needs_review = (
        status.upper() == 'WAITING_REVIEW'
        or truthy_review_value(row.get('Review Needed', ''))
        or truthy_review_value(markdown_field(scope, 'review_needed'))
        or truthy_review_value(markdown_field(ledger, 'review_needed'))
        or has_review_reminder(markdown_field(scope, 'leader_review_reminder'), markdown_field(ledger, 'leader_review_reminder'))
    )
    risk = 'needs_review' if needs_review else 'normal'
    return Artifact(
        kind='task',
        artifact_id=rel,
        path=rel,
        title=goal,
        status=status or '-',
        usage=usage or '-',
        linked_task='-',
        risk=risk,
        search_text=' '.join([rel, goal, status, usage, scope, ledger, slot, output, ' '.join(task_markdown)]),
    )


def collect_tasks(root: Path) -> list[Artifact]:
    ledger = root / 'role_workspace' / 'ledgers' / 'TASK_LEDGER_v1.md'
    artifacts = []
    seen = set()
    for row in parse_markdown_table(read_text(ledger)):
        task_id = clean(row.get('Task ID', ''))
        if not task_id:
            continue
        seen.add(task_id)
        artifacts.append(task_artifact(root, task_id, row))

    tasks_root = root / 'tasks'
    if tasks_root.exists():
        for task_dir in sorted(tasks_root.iterdir()):
            if not task_dir.is_dir() or task_dir.name.startswith('.'):
                continue
            rel = f'tasks/{task_dir.name}'
            if rel in seen or task_dir.name in seen:
                continue
            artifacts.append(task_artifact(root, rel, {}))
    return [artifact for artifact in artifacts if artifact]


def collect_references(root: Path) -> list[Artifact]:
    ref_root = root / 'role_workspace' / 'knowledge' / 'references'
    if not ref_root.exists():
        return []
    artifacts = []
    for path in sorted(ref_root.rglob('*.md')):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        body = read_text(path)
        artifacts.append(Artifact(
            kind='reference',
            artifact_id=rel,
            path=rel,
            title=first_heading(body) or path.stem,
            status='REFERENCE_ONLY',
            usage='reference',
            linked_task='-',
            risk='normal',
            search_text=f'{rel} {body}',
        ))
    return artifacts


def collect_all(root: Path) -> list[Artifact]:
    return collect_evidence(root) + collect_tasks(root) + collect_references(root)


def catalog_entry(root: Path, artifact: Artifact) -> dict:
    path = root / artifact.path
    excerpt_source = ''
    if artifact.kind == 'evidence' and path.is_dir():
        excerpt_source = read_text(path / 'evidence_brief.md') or read_text(path / 'input.md')
    elif artifact.kind == 'task' and path.is_dir():
        excerpt_source = read_text(path / 'task_output.md') or read_text(path / 'task_scope.md')
    elif path.is_file():
        excerpt_source = read_text(path)
    else:
        excerpt_source = artifact.search_text
    return {
        'path': artifact.path,
        'type': artifact.kind,
        'title': artifact.title,
        'status': artifact.status,
        'usage': artifact.usage,
        'linked_task': artifact.linked_task,
        'risk': artifact.risk,
        'excerpt': excerpt(excerpt_source),
    }


def build_catalog(root: Path) -> list[dict]:
    return [catalog_entry(root, artifact) for artifact in collect_all(root)]


def validate_search_enrichment(data: dict, catalog_by_path: dict[str, dict]) -> str | None:
    err = require_version(data, ENRICHMENT_VERSION)
    if err:
        return err
    for field in ('query', 'result_status', 'matches', 'next_step'):
        if field not in data:
            return f'missing required field: {field}'
    if data['result_status'] not in {'FOUND', 'NO_MATCH'}:
        return 'invalid result_status'
    if not isinstance(data['matches'], list):
        return 'matches must be an array'
    if data['result_status'] == 'NO_MATCH' and data['matches']:
        return 'matches must be empty when result_status is NO_MATCH'
    for item in data['matches']:
        if not isinstance(item, dict):
            return 'each match must be an object'
        for field in ('path', 'match_reason', 'suggested_use', 'preview'):
            if field not in item:
                return f'match missing field: {field}'
        if item['path'] not in catalog_by_path:
            return f"match path not in catalog: {item['path']}"
    return None


def render_enrichment(data: dict, catalog_by_path: dict[str, dict]) -> str:
    query = clean(data.get('query', ''))
    interpretation = clean(data.get('query_interpretation', ''))
    status = data['result_status']
    if status == 'NO_MATCH':
        return (
            'artifact 查询结果：NO_MATCH\n'
            f'query: {query}\n'
            f'query_interpretation: {interpretation or query}\n'
            'matches: None\n'
            f'下一步：{data["next_step"]}\n'
        )

    lines = [
        'artifact 查询结果：FOUND',
        f'query: {query}',
        f'query_interpretation: {interpretation or query}',
        'matches:',
    ]
    for idx, item in enumerate(data['matches'], 1):
        meta = catalog_by_path[item['path']]
        lines.extend([
            f'{idx}. {item["path"]}',
            f'   type: {meta["type"]}',
            f'   title: {meta["title"]}',
            f'   status: {meta["status"]}',
            f'   usage: {meta["usage"]}',
            f'   linked_task: {meta["linked_task"]}',
            f'   risk: {meta["risk"]}',
            f'   match_reason: {item["match_reason"]}',
            f'   preview: {item["preview"]}',
            f'   suggested_use: {item["suggested_use"]}',
        ])
    lines.append(f'下一步：{data["next_step"]}')
    return '\n'.join(lines) + '\n'


def block(message: str) -> int:
    print('artifact 查询结果：BLOCKED')
    print('query: None')
    print('matches: None')
    print(f'下一步：{message}')
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description='Search prior LBAI artifacts with AI enrichment.')
    parser.add_argument('--print-catalog', action='store_true', help='Export artifact catalog JSON for AI ranking.')
    parser.add_argument('--enrichment', help='Path to AI-generated search enrichment JSON.')
    parser.add_argument('--limit', type=int, default=8, help='Reserved for agent-side match limiting.')
    args = parser.parse_args()

    root = workspace_root()

    if args.print_catalog:
        catalog = build_catalog(root)
        print(json.dumps({'schema_version': 'search_catalog_v1', 'artifacts': catalog}, ensure_ascii=False, indent=2))
        return 0

    if not args.enrichment:
        return block(BLOCKED_MESSAGE)

    enrichment_path = resolve_enrichment_path(root, args.enrichment)
    data, error = load_json_file(enrichment_path)
    if data is None:
        return block(error or BLOCKED_MESSAGE)

    catalog = build_catalog(root)
    catalog_by_path = {item['path']: item for item in catalog}
    validation_error = validate_search_enrichment(data, catalog_by_path)
    if validation_error:
        return block(validation_error)

    if args.limit and isinstance(data.get('matches'), list):
        data['matches'] = data['matches'][: max(args.limit, 1)]

    print(render_enrichment(data, catalog_by_path), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
