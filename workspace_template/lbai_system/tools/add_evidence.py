#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import select
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True

from enrichment_utils import load_json_file, validate_with_schema
from task_utils import (
    employee_identity,
    load_workspace_config,
    prompt_lab_isolated_mode,
    read_text,
    redact_sensitive,
    slugify,
    workspace_root,
)


ENRICHMENT_BLOCKED_MESSAGE = (
    'AI enrichment required (--enrichment). Use Cursor or Codex desktop app; '
    'see lbai_system/prompts/evidence_enrichment_prompt_v1.md. No rule-based fallback.'
)

LEDGER_COLUMNS = [
    'Date',
    'Evidence ID',
    'Employee User ID',
    'Employee User Name',
    'Employee Position',
    'Source Type',
    'Source Visibility',
    'Backend Ingestion Status',
    'Sync Status',
    'Next Step',
]

def run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(['git', *args], cwd=root, capture_output=True, text=True)


def git_remote_available(root: Path) -> bool:
    result = run_git(root, ['remote'])
    return result.returncode == 0 and bool(result.stdout.strip())


def git_upstream_available(root: Path) -> bool:
    result = run_git(root, ['rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'])
    return result.returncode == 0 and bool(result.stdout.strip())


def git_has_staged_changes(root: Path) -> bool:
    result = run_git(root, ['diff', '--cached', '--quiet'])
    return result.returncode == 1


def read_available_stdin() -> str:
    if sys.stdin.isatty():
        return ''
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    if not ready:
        return ''
    return sys.stdin.read().strip()


def parse_input(args: argparse.Namespace) -> str:
    target = args.target_or_content or ''
    rest = ' '.join(args.content).strip()
    content = args.content_text.strip() if args.content_text else ''
    stdin_text = read_available_stdin()
    content = content or ' '.join([part for part in [target, rest] if part]).strip() or stdin_text
    return content


def profile_value(value: object) -> str:
    text = str(value or '').strip()
    if text.startswith('<fill ') and text.endswith('>'):
        return ''
    return text


def load_role_profile(root: Path) -> dict[str, str]:
    path = root / 'role_workspace' / 'world_model' / 'ROLE_PROFILE_v1.json'
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}
    return {
        'employee_user_name': profile_value(data.get('employee_user_name')),
        'employee_position': profile_value(data.get('employee_position')),
        'conversation_preference': profile_value(data.get('conversation_preference')),
    }


def next_available(path: Path) -> Path:
    if not path.exists():
        return path
    for idx in range(2, 100):
        candidate = path.with_name(f'{path.name}_{idx}')
        if not candidate.exists():
            return candidate
    raise RuntimeError(f'No available evidence folder for {path}')


def load_enrichment(root: Path, path: Path) -> tuple[dict | None, str]:
    data, error = load_json_file(path)
    if data is None:
        return None, error or 'enrichment load failed'
    schema_error = validate_with_schema(root, data, 'evidence_enrichment_schema_v1.json')
    if schema_error:
        return None, schema_error
    return data, ''


MEETING_DATE_PATTERNS = (
    re.compile(r'时间[：:]\s*(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})'),
    re.compile(r'(\d{4})-(\d{2})-(\d{2})'),
)


def infer_meeting_occurred_at(content: str) -> str:
    for pattern in MEETING_DATE_PATTERNS:
        match = pattern.search(content)
        if not match:
            continue
        year, month, day = match.group(1), int(match.group(2)), int(match.group(3))
        return f'{year}-{month:02d}-{day:02d}'
    return ''


def normalize_meeting_enrichment(enrichment: dict, content: str) -> dict:
    if str(enrichment.get('source_type') or '').strip() != 'meeting_note':
        return enrichment
    occurred = str(enrichment.get('source_occurred_at') or '').strip()
    if occurred and occurred.lower() != 'unknown':
        return enrichment
    inferred = infer_meeting_occurred_at(content)
    if not inferred:
        return enrichment
    normalized = dict(enrichment)
    normalized['source_occurred_at'] = inferred
    return normalized


def split_table_line(line: str) -> list[str]:
    return [cell.strip().strip('`') for cell in line.strip().strip('|').split('|')]


def parse_markdown_table(markdown: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in markdown.splitlines() if line.strip().startswith('|')]
    if len(lines) < 2:
        return []
    header = split_table_line(lines[0])
    rows = []
    for line in lines[2:]:
        cells = split_table_line(line)
        if not cells or all(set(cell) <= {'-'} for cell in cells):
            continue
        rows.append({name: cells[idx] if idx < len(cells) else '' for idx, name in enumerate(header)})
    return rows


def ledger_cell(value: object) -> str:
    text = str(value or '').replace('\n', ' ').strip()
    if not text or text.lower() == 'none':
        return 'None'
    return text.replace('|', '/')


def migrate_ledger_rows(rows: list[dict[str, str]]) -> list[str]:
    migrated = []
    for row in rows:
        evidence_id = ledger_cell(row.get('Evidence ID'))
        if evidence_id == 'None':
            continue
        values = {
            'Date': ledger_cell(row.get('Date')),
            'Evidence ID': evidence_id,
            'Employee User ID': ledger_cell(row.get('Employee User ID')),
            'Employee User Name': ledger_cell(row.get('Employee User Name')),
            'Employee Position': ledger_cell(row.get('Employee Position')),
            'Source Type': ledger_cell(row.get('Source Type') or row.get('Source Kind')),
            'Source Visibility': ledger_cell(row.get('Source Visibility')),
            'Backend Ingestion Status': ledger_cell(row.get('Backend Ingestion Status') or 'LEGACY_IMPORTED'),
            'Sync Status': ledger_cell(row.get('Sync Status')),
            'Next Step': ledger_cell(row.get('Next Step')),
        }
        migrated.append('| ' + ' | '.join(values[column] for column in LEDGER_COLUMNS) + ' |')
    return migrated


def ensure_ledger(root: Path) -> Path:
    path = root / 'role_workspace' / 'ledgers' / 'EVIDENCE_LEDGER_v1.md'
    path.parent.mkdir(parents=True, exist_ok=True)
    text = read_text(path)
    header = f'| {" | ".join(LEDGER_COLUMNS)} |'
    separator = f'| {" | ".join("---" for _ in LEDGER_COLUMNS)} |'
    if not text.strip():
        path.write_text(f'# EVIDENCE_LEDGER_v1\n\n{header}\n{separator}\n', encoding='utf-8')
    elif header not in text:
        rows = migrate_ledger_rows(parse_markdown_table(text))
        path.write_text(
            '# EVIDENCE_LEDGER_v1\n\n'
            + header
            + '\n'
            + separator
            + ('\n' + '\n'.join(rows) if rows else '')
            + '\n',
            encoding='utf-8',
        )
    return path


def update_ledger(
    root: Path,
    *,
    evidence_id: str,
    employee_user_id: str,
    employee_user_name: str,
    employee_position: str,
    source_type: str,
    source_visibility: str,
    backend_ingestion_status: str,
    sync_status: str,
    next_step: str,
):
    path = ensure_ledger(root)
    line = (
        f'| {datetime.now(timezone.utc).date().isoformat()} | {evidence_id} | {employee_user_id or "None"} | '
        f'{employee_user_name or "None"} | {employee_position or "None"} | {source_type} | {source_visibility} | '
        f'{backend_ingestion_status} | {sync_status} | {next_step} |'
    )
    lines = [existing for existing in read_text(path).splitlines() if f'| {evidence_id} |' not in existing]
    lines.append(line)
    path.write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')


def run_hygiene(root: Path, evidence_rel: str) -> tuple[str, str]:
    script = Path(__file__).resolve().with_name('evidence_hygiene_check.py')
    result = subprocess.run([sys.executable, str(script), evidence_rel], cwd=root, capture_output=True, text=True)
    output = result.stdout + result.stderr
    readiness = 'BLOCKED'
    for line in output.splitlines():
        if line.startswith('commit_readiness:'):
            readiness = line.split(':', 1)[1].strip()
            break
    return readiness, output


def sync_paths(root: Path, evidence_rel: str, message: str) -> tuple[str, str]:
    if not git_remote_available(root):
        return 'BLOCKED', 'MISSING_GITHUB_REMOTE: no Git remote configured'
    if not git_upstream_available(root):
        return 'BLOCKED', 'MISSING_GIT_UPSTREAM: current branch has no upstream'
    paths = [evidence_rel, 'role_workspace/ledgers/EVIDENCE_LEDGER_v1.md']
    add_result = run_git(root, ['add', '-A', '--', *paths])
    if add_result.returncode != 0:
        return 'BLOCKED', f'git add failed: {(add_result.stdout + add_result.stderr).strip()}'
    if not git_has_staged_changes(root):
        return 'NO_CHANGES', 'No local changes to commit'
    commit_result = run_git(root, ['commit', '-m', message])
    if commit_result.returncode != 0:
        return 'BLOCKED', f'git commit failed: {(commit_result.stdout + commit_result.stderr).strip()}'
    push_result = run_git(root, ['push'])
    if push_result.returncode != 0:
        return 'PUSH_FAILED', f'git push failed: {(push_result.stdout + push_result.stderr).strip()}'
    return 'PUSHED', 'git push completed'


def block(reason: str, next_step: str) -> int:
    print('evidence_status: BLOCKED')
    print('sync_status: BLOCKED')
    print(f'reason: {reason}')
    print(f'next_step: {next_step}')
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('target_or_content', nargs='?')
    parser.add_argument('content', nargs='*')
    parser.add_argument('--content', dest='content_text', default='')
    parser.add_argument('--enrichment', required=True, help='Path to AI-generated evidence metadata JSON.')
    parser.add_argument('--no-sync', action='store_true', help='Create evidence artifacts without committing or pushing.')
    args = parser.parse_args()
    if prompt_lab_isolated_mode():
        args.no_sync = True

    root = workspace_root()
    content = parse_input(args)
    enrichment_path = Path(args.enrichment).expanduser()
    if not enrichment_path.is_absolute():
        enrichment_path = (root / enrichment_path).resolve()

    enrichment, enrichment_error = load_enrichment(root, enrichment_path)
    if enrichment is None:
        return block(enrichment_error or ENRICHMENT_BLOCKED_MESSAGE, ENRICHMENT_BLOCKED_MESSAGE)
    if not content.strip():
        return block('no evidence content provided', 'Paste source material and rerun with AI enrichment via Cursor or Codex desktop app.')

    enrichment = normalize_meeting_enrichment(enrichment, content)

    workspace_config = load_workspace_config(root)
    identity = employee_identity(root)
    role_profile = load_role_profile(root)
    employee_user_id = str(identity.get('employee_user_id') or '').strip()
    employee_user_name = role_profile.get('employee_user_name') or str(identity.get('display_name') or '').strip()
    employee_position = role_profile.get('employee_position') or str(identity.get('department') or '').strip()

    redacted_content, findings = redact_sensitive(content)
    source_type = str(enrichment['source_type']).strip()
    source_visibility = str(enrichment.get('source_visibility') or 'private').strip()
    backend_ingestion_status = 'PENDING_GITHUB_SYNC'
    sensitive_scan_status = 'redacted' if findings else 'passed'
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    content_hash_full = hashlib.sha256(redacted_content.encode('utf-8')).hexdigest()
    content_hash = f'sha256:{content_hash_full}'
    evidence_id_seed = f'{source_type}_{content_hash_full[:10]}'
    evidence_dir = next_available(
        root / 'role_workspace' / 'knowledge' / 'evidence' / f'{datetime.now(timezone.utc).strftime("%Y_%m_%d")}_{slugify(evidence_id_seed)[:64]}'
    )
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (root / 'role_workspace' / 'knowledge' / 'references').mkdir(parents=True, exist_ok=True)
    evidence_rel = str(evidence_dir.relative_to(root))
    evidence_id = evidence_dir.name

    raw_path = evidence_dir / 'raw.md'
    raw_path.write_text(
        '# Evidence Raw Input\n\n'
        f'## content\n{redacted_content.strip()}\n',
        encoding='utf-8',
    )
    metadata = {
        'schema_version': 'employee_evidence_metadata_v1',
        'evidence_id': evidence_id,
        'title': enrichment['title'],
        'source_type': source_type,
        'source_origin': enrichment.get('source_origin') or 'unknown',
        'source_occurred_at': enrichment.get('source_occurred_at') or 'unknown',
        'submitted_at': now,
        'submitted_by': employee_user_id,
        'submitted_by_display_name': identity.get('display_name') or employee_user_name,
        'submitted_by_email': identity.get('email') or '',
        'department': identity.get('department') or '',
        'employee_user_name': employee_user_name,
        'employee_position': employee_position,
        'source_visibility': source_visibility,
        'related_objects': enrichment.get('related_objects') or [],
        'language': enrichment.get('language') or 'zh-CN',
        'content_files': ['raw.md'],
        'attachment_files': [],
        'content_hash': content_hash,
        'sensitive_scan_status': sensitive_scan_status,
        'redacted': bool(findings),
        'redaction_note': 'sensitive values replaced locally before commit' if findings else 'none',
        'backend_ingestion_status': backend_ingestion_status,
        'backend_ingestion_hint': enrichment.get('backend_ingestion_hint') or 'source_for_company_knowledge',
        'admissibility_status': enrichment.get('admissibility_status') or 'CAPTURED',
        'review_reasons': enrichment.get('review_reasons') or [],
        'workspace_repo_id': (workspace_config.get('knowledge_service') or {}).get('workspace_repo_id') or root.name,
    }
    (evidence_dir / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (evidence_dir / 'evidence_enrichment.json').write_text(json.dumps(enrichment, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    if args.no_sync:
        if prompt_lab_isolated_mode():
            next_step = 'Prompt Lab 本地 mock 证据已写入隔离 workspace，未同步 GitHub 或后端知识服务。'
        else:
            next_step = '证据已本地写入 workspace，未同步 GitHub 或后端知识服务。'
    else:
        next_step = '资料已保存到 GitHub workspace；后端将异步入库。可稍后使用 /lbai-search-artifacts 搜索。'
    evidence_status = metadata['admissibility_status']
    sync_status = 'NOT_SYNCED'
    update_ledger(
        root,
        evidence_id=evidence_id,
        employee_user_id=employee_user_id,
        employee_user_name=employee_user_name,
        employee_position=employee_position,
        source_type=source_type,
        source_visibility=source_visibility,
        backend_ingestion_status=backend_ingestion_status,
        sync_status=sync_status,
        next_step=next_step,
    )

    sync_detail = 'Sync skipped by --no-sync.' if args.no_sync else ''
    hygiene_output = ''
    if not args.no_sync:
        readiness, hygiene_output = run_hygiene(root, evidence_rel)
        if readiness != 'READY':
            sync_status = 'BLOCKED'
            sync_detail = 'Evidence sync blocked by hygiene check.'
        else:
            sync_status, sync_detail = sync_paths(root, evidence_rel, f'docs(lbai): add evidence {evidence_id}')
        metadata['sync_status'] = sync_status
        (evidence_dir / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        update_ledger(
            root,
            evidence_id=evidence_id,
            employee_user_id=employee_user_id,
            employee_user_name=employee_user_name,
            employee_position=employee_position,
            source_type=source_type,
            source_visibility=source_visibility,
            backend_ingestion_status=backend_ingestion_status,
            sync_status=sync_status,
            next_step=next_step,
        )

    print(f'EVIDENCE_FOLDER {evidence_rel}')
    print(f'raw: {evidence_rel}/raw.md')
    print(f'metadata: {evidence_rel}/metadata.json')
    print(f'evidence_status: {evidence_status}')
    print(f'employee_user_id: {employee_user_id or "None"}')
    print(f'employee_user_name: {employee_user_name or "None"}')
    print(f'employee_position: {employee_position or "None"}')
    print(f'source_type: {source_type}')
    print(f'source_visibility: {source_visibility}')
    print(f'backend_ingestion_status: {backend_ingestion_status}')
    print(f'sensitive_capture_status: {"REDACTED" if findings else "NONE"}')
    print(f'sync_status: {sync_status}')
    print(f'sync_detail: {sync_detail}')
    if hygiene_output.strip():
        print('hygiene_check:')
        print(hygiene_output.strip())
    print(f'next_step: {next_step}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
