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


def existing_concept_path(knowledge_root: Path, uid: str) -> Path | None:
    uid_pattern = re.compile(rf'^uid:\s*["\']?{re.escape(uid)}["\']?\s*$', re.MULTILINE)
    for path in knowledge_root.rglob('*.md'):
        if path.name in {'index.md', 'log.md'}:
            continue
        if uid_pattern.search(read_text(path)):
            return path
    return None


def yaml_value(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def ensure_okf_index(root: Path, concept_rel: str, title: str, description: str) -> tuple[Path, Path]:
    knowledge_root = root / 'role_workspace' / 'knowledge'
    index_path = knowledge_root / 'index.md'
    log_path = knowledge_root / 'log.md'
    index_path.parent.mkdir(parents=True, exist_ok=True)
    entry = f'* [{title}]({concept_rel.removeprefix("role_workspace/knowledge/")}) - {description}'
    existing = read_text(index_path)
    if not existing.strip():
        existing = '# Company Knowledge\n'
    if '# References' not in existing:
        existing = existing.rstrip() + '\n\n# References\n'
    if entry not in existing:
        index_path.write_text(existing.rstrip() + '\n\n' + entry + '\n', encoding='utf-8')
    today = datetime.now(timezone.utc).date().isoformat()
    log_entry = f'* **Creation**: Added [{title}](/' + concept_rel.removeprefix('role_workspace/knowledge/') + ').'
    log_text = read_text(log_path)
    if f'## {today}' not in log_text:
        log_text = f'# Knowledge Update Log\n\n## {today}\n{log_entry}\n\n' + log_text.replace('# Knowledge Update Log', '').lstrip()
    elif log_entry not in log_text:
        log_text = log_text.replace(f'## {today}\n', f'## {today}\n{log_entry}\n', 1)
    log_path.write_text(log_text, encoding='utf-8')
    return index_path, log_path


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


def run_hygiene(root: Path, concept_rel: str) -> tuple[str, str]:
    script = Path(__file__).resolve().with_name('knowledge_hygiene_check.py')
    result = subprocess.run([sys.executable, str(script), concept_rel], cwd=root, capture_output=True, text=True)
    output = result.stdout + result.stderr
    readiness = 'BLOCKED'
    for line in output.splitlines():
        if line.startswith('commit_readiness:'):
            readiness = line.split(':', 1)[1].strip()
            break
    return readiness, output


def sync_paths(root: Path, concept_rel: str, message: str) -> tuple[str, str]:
    if not git_remote_available(root):
        return 'BLOCKED', 'MISSING_GITHUB_REMOTE: no Git remote configured'
    if not git_upstream_available(root):
        return 'BLOCKED', 'MISSING_GIT_UPSTREAM: current branch has no upstream'
    paths = [concept_rel, 'role_workspace/knowledge/index.md', 'role_workspace/knowledge/log.md']
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

    identity = employee_identity(root)
    role_profile = load_role_profile(root)
    employee_user_id = str(identity.get('employee_user_id') or '').strip()
    employee_user_name = role_profile.get('employee_user_name') or str(identity.get('display_name') or '').strip()
    employee_position = role_profile.get('employee_position') or str(identity.get('department') or '').strip()

    redacted_content, findings = redact_sensitive(content)
    source_type = str(enrichment['source_type']).strip()
    source_visibility = str(enrichment.get('source_visibility') or 'private').strip()
    effective_visibility = (
        source_visibility
        if source_visibility in {'private', 'team', 'company'}
        else 'private'
    )
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    content_hash_full = hashlib.sha256(redacted_content.encode('utf-8')).hexdigest()
    content_hash = f'sha256:{content_hash_full}'
    concept_slug_seed = f'{source_type}_{content_hash_full[:10]}'
    concept_uid = f'kn_{content_hash_full[:20]}'
    knowledge_root = root / 'role_workspace' / 'knowledge'
    concept_path = existing_concept_path(knowledge_root, concept_uid) or (
        knowledge_root / 'references'
        / f'{datetime.now(timezone.utc).strftime("%Y_%m_%d")}_{slugify(concept_slug_seed)[:64]}.md'
    )
    concept_path.parent.mkdir(parents=True, exist_ok=True)
    concept_rel = str(concept_path.relative_to(root))
    title = str(enrichment['title']).strip()
    description = f'{source_type} from {enrichment.get("source_origin") or "unknown source"}'
    tags = [source_type, *(enrichment.get('related_objects') or [])][:20]
    evidence_status = enrichment.get('admissibility_status') or 'CAPTURED'
    concept_status = 'draft' if evidence_status == 'NEEDS_REVIEW' else 'active'
    occurred_at = str(enrichment.get('source_occurred_at') or '').strip()
    effective_from = occurred_at if re.fullmatch(r'\d{4}-\d{2}-\d{2}', occurred_at) else ''
    source_origin = str(enrichment.get('source_origin') or 'Employee-provided source').strip()
    citation = (
        f'[Source]({source_origin})'
        if re.match(r'^https?://', source_origin)
        else f'Source: {source_origin}'
    )
    concept_path.write_text(
        '---\n'
        f'type: Reference\nuid: {yaml_value(concept_uid)}\n'
        f'title: {yaml_value(title)}\ndescription: {yaml_value(description)}\n'
        f'tags: {yaml_value(tags)}\nresource: {yaml_value("")}\n'
        f'timestamp: {yaml_value(now)}\nowner: {yaml_value(employee_user_id or "unknown")}\n'
        f'department: {yaml_value(identity.get("department") or "")}\n'
        f'visibility: {yaml_value(effective_visibility)}\n'
        f'status: {concept_status}\n'
        f'effective_from: {yaml_value(effective_from)}\n'
        f'aliases: {yaml_value(enrichment.get("related_objects") or [])}\n'
        f'source_type: {yaml_value(source_type)}\nsource_origin: {yaml_value(source_origin)}\n'
        f'source_occurred_at: {yaml_value(occurred_at)}\n'
        f'language: {yaml_value(enrichment.get("language") or "")}\n'
        f'admissibility_status: {yaml_value(evidence_status)}\n'
        f'review_reasons: {yaml_value(enrichment.get("review_reasons") or [])}\n'
        f'content_hash: {yaml_value(content_hash)}\nredacted: {yaml_value(bool(findings))}\n'
        '---\n\n# Summary\n\n'
        f'{title}\n\n# Details\n\n{redacted_content.strip()}\n\n'
        '# Citations\n\n'
        f'{citation}\n',
        encoding='utf-8',
    )
    index_path, log_path = ensure_okf_index(root, concept_rel, title, description)

    sync_status = 'NOT_SYNCED'

    sync_detail = 'Sync skipped by --no-sync.' if args.no_sync else ''
    hygiene_output = ''
    if not args.no_sync:
        readiness, hygiene_output = run_hygiene(root, concept_rel)
        if readiness != 'READY':
            sync_status = 'BLOCKED'
            sync_detail = 'OKF Concept sync blocked by hygiene check.'
        else:
            sync_status, sync_detail = sync_paths(root, concept_rel, f'docs(lbai): add OKF concept {concept_uid}')
    backend_ingestion_status = (
        'PENDING_BACKEND_SYNC'
        if sync_status == 'PUSHED'
        else ('ALREADY_SYNCED' if sync_status == 'NO_CHANGES' else 'NOT_SYNCED')
    )
    if args.no_sync:
        next_step = (
            'Prompt Lab 本地 mock OKF Concept 已写入隔离 workspace，未同步 GitHub 或后端知识服务。'
            if prompt_lab_isolated_mode()
            else 'OKF Concept 已本地写入 workspace，未同步 GitHub 或后端知识服务。'
        )
    elif sync_status == 'PUSHED':
        next_step = '资料已推送到 GitHub；后端将异步入库。可稍后使用 /lbai-search-artifacts 搜索。'
    elif sync_status == 'NO_CHANGES':
        next_step = 'GitHub 中已有相同 OKF Concept，无需重复提交。'
    else:
        next_step = f'同步未完成：{sync_detail}。处理后重新运行 /lbai-add-evidence。'

    print(f'OKF_CONCEPT {concept_rel}')
    print(f'concept_uid: {concept_uid}')
    print(f'index: {index_path.relative_to(root)}')
    print(f'log: {log_path.relative_to(root)}')
    print(f'evidence_status: {evidence_status}')
    print(f'employee_user_id: {employee_user_id or "None"}')
    print(f'employee_user_name: {employee_user_name or "None"}')
    print(f'employee_position: {employee_position or "None"}')
    print(f'source_type: {source_type}')
    print(f'source_visibility: {effective_visibility}')
    print(f'backend_ingestion_status: {backend_ingestion_status}')
    print(f'sensitive_capture_status: {"REDACTED" if findings else "NONE"}')
    print(f'sync_status: {sync_status}')
    print(f'sync_detail: {sync_detail}')
    if hygiene_output.strip():
        print('hygiene_check:')
        print(hygiene_output.strip())
    print(f'next_step: {next_step}')
    if sync_status == 'PUSH_FAILED':
        return 3
    if sync_status == 'BLOCKED':
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
