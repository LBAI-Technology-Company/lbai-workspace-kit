#!/usr/bin/env python3
import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.dont_write_bytecode = True

from task_utils import read_text, workspace_root


MAX_SNIPPET_CHARS = 220


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


def tokenize(query: str) -> list[str]:
    raw = [part.strip().lower() for part in re.split(r'[\s,，;；]+', query) if part.strip()]
    terms = []
    for part in raw:
        if part not in terms:
            terms.append(part)
    compact = re.sub(r'[\s,，;；]+', '', query).lower()
    if compact and compact not in terms:
        terms.insert(0, compact)
    if re.search(r'[\u4e00-\u9fff]', compact) and len(compact) > 2:
        for idx in range(0, len(compact) - 1):
            chunk = compact[idx:idx + 2]
            if chunk not in terms:
                terms.append(chunk)
    return terms


def score_artifact(artifact: Artifact, terms: list[str]) -> tuple[int, list[str]]:
    haystack = artifact.search_text.lower()
    title = artifact.title.lower()
    path = artifact.path.lower()
    usage = artifact.usage.lower()
    reasons = []
    score = 0

    for term in terms:
        if not term:
            continue
        if term in title:
            score += 8
            reasons.append(f'title matches "{term}"')
        if term in path:
            score += 5
            reasons.append(f'path matches "{term}"')
        if term in usage:
            score += 3
            reasons.append(f'usage matches "{term}"')
        count = haystack.count(term)
        if count:
            score += min(count, 6) * 2
            reasons.append(f'content matches "{term}"')

    if artifact.kind == 'evidence':
        score += 1
    if artifact.status.upper() in {'NEEDS_REVIEW', 'WAITING_REVIEW'} or artifact.risk in {'needs_review', 'sensitive_redacted'}:
        score -= 1
    return score, reasons[:4]


def snippet(text: str, terms: list[str]) -> str:
    compact = re.sub(r'\s+', ' ', strip_code_fences(text)).strip()
    if not compact:
        return '无可预览内容'
    low = compact.lower()
    positions = [low.find(term) for term in terms if term and low.find(term) >= 0]
    start = max(min(positions) - 70, 0) if positions else 0
    excerpt = compact[start:start + MAX_SNIPPET_CHARS]
    if start:
        excerpt = '...' + excerpt
    if start + MAX_SNIPPET_CHARS < len(compact):
        excerpt += '...'
    return excerpt


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
    return Artifact(
        kind='evidence',
        artifact_id=evidence_id,
        path=evidence_rel,
        title=evidence_path.name or evidence_id.rsplit('/', 1)[-1],
        status=status or '-',
        usage=usage or '-',
        linked_task=linked_task or '-',
        risk=risk,
        search_text=' '.join([
            evidence_id,
            evidence_rel,
            kind,
            usage,
            status,
            linked_task,
            clean(row.get('Covers Gaps', '')),
            clean(row.get('Next Step', '')),
            metadata,
            brief,
            body,
        ]),
    )


def evidence_path_for(root: Path, evidence_id: str) -> Path:
    direct = root / evidence_id
    if direct.exists():
        return direct
    return root / 'role_workspace' / 'knowledge' / 'evidence' / evidence_id


def relative_artifact_path(root: Path, path: Path, fallback: str) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return fallback


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
        search_text=' '.join([
            rel,
            goal,
            status,
            clean(row.get('Outputs Created', '')),
            clean(row.get('Next Dependency', '')),
            usage,
            scope,
            ledger,
            slot,
            output,
            ' '.join(task_markdown),
        ]),
    )


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


def suggested_use(artifact: Artifact) -> str:
    if artifact.kind == 'evidence':
        if artifact.status.upper() == 'NEEDS_REVIEW':
            return '对外发布前请负责人 review；本流程不阻断执行。'
        if artifact.risk == 'sensitive_redacted':
            return '只能使用仓库内脱敏版本；原始内容需走批准的安全渠道。'
        if artifact.usage == 'possible_task_input':
            return '可作为新任务候选输入；用户确认后再用 /lbai-new-task。'
        if artifact.linked_task and artifact.linked_task != '-':
            return '已关联历史任务；复用前请确认是否适用于当前任务。'
        return '可作为参考资料；如要驱动任务，需显式关联到当前 task。'
    if artifact.kind == 'task':
        if artifact.risk == 'needs_review' or artifact.status.upper() == 'WAITING_REVIEW':
            return '可参考历史产出；对外发布前请负责人 review。'
        return '可参考历史任务产出；需要复用时显式写入当前 task 的 source artifacts。'
    return '可作为长期参考资料；不得自动变成当前任务依据。'


def render_results(query: str, matches: list[Artifact], limit: int, terms: list[str]) -> str:
    if not query.strip():
        return (
            'artifact 查询结果：BLOCKED\n'
            'query: None\n'
            'matches: None\n'
            '下一步：请提供查询关键词，例如 /lbai-search-artifacts 用户反馈 官网文案\n'
        )

    if not matches:
        return (
            'artifact 查询结果：NO_MATCH\n'
            f'query: {query}\n'
            'matches: None\n'
            '下一步：如果这是新资料，请用 /lbai-add-evidence 保存；如果是新任务，请用 /lbai-new-task 创建。\n'
        )

    lines = [
        'artifact 查询结果：FOUND',
        f'query: {query}',
        'matches:',
    ]
    for idx, artifact in enumerate(matches[:limit], 1):
        lines.extend([
            f'{idx}. {artifact.path}',
            f'   type: {artifact.kind}',
            f'   title: {artifact.title}',
            f'   status: {artifact.status}',
            f'   usage: {artifact.usage}',
            f'   linked_task: {artifact.linked_task}',
            f'   risk: {artifact.risk}',
            f'   match_reason: {artifact.reason or "keyword match"}',
            f'   preview: {snippet(artifact.search_text, terms)}',
            f'   suggested_use: {suggested_use(artifact)}',
        ])
    lines.append('下一步：选择候选后，在 /lbai-new-task 或当前 task artifacts 中显式引用；本查询不会自动创建任务、关联资料或更新状态。')
    return '\n'.join(lines) + '\n'


def main() -> int:
    parser = argparse.ArgumentParser(description='Search prior LBAI evidence, task outputs, and references without mutating artifacts.')
    parser.add_argument('query', nargs='*', help='Search keywords')
    parser.add_argument('--limit', type=int, default=8)
    args = parser.parse_args()

    query = ' '.join(args.query).strip()
    terms = tokenize(query)
    root = workspace_root()
    artifacts = collect_evidence(root) + collect_tasks(root) + collect_references(root)
    matches = []
    for artifact in artifacts:
        score, reasons = score_artifact(artifact, terms)
        if score > 0:
            artifact.score = score
            artifact.reason = '; '.join(reasons)
            matches.append(artifact)
    matches.sort(key=lambda item: (-item.score, item.kind, item.path))
    print(render_results(query, matches, max(args.limit, 1), terms), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
