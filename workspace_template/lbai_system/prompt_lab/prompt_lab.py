#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROMPT_FILES = [
    'backend_search_query_plan_prompt_v1.md',
    'evidence_enrichment_prompt_v1.md',
    'execute_task_plan_prompt_v1.md',
    'finish_review_enrichment_prompt_v1.md',
    'init_enrichment_prompt_v1.md',
    'task_intake_enrichment_prompt_v1.md',
]

MANAGED_PATHS = [
    'AGENTS.md',
    'README.md',
    '.gitignore',
    '.cursor',
    '.agents',
    'lbai_system',
    'workspace_dashboard.html',
]

SCORE_FIELDS = [
    'schema_compliance',
    'boundary_handling',
    'source_grounding',
    'missing_input_handling',
    'task_quality',
    'finish_review_accuracy',
]

PROMPT_LAB_ISOLATED_ENV = 'LBAI_PROMPT_LAB_ISOLATED'
CHAIN_MODES = frozenset({'intake_evidence', 'full_lifecycle'})
CONTEXT_MODES = frozenset({'auto', 'real_task', 'mock'})
ALLOWED_RUN_TOOLS = frozenset({
    'add_evidence.py',
    'archive_input.py',
    'finish_task.py',
    'init_lbai.py',
    'new_task.py',
    'prepare_execute_task.py',
})
ALLOWED_TASK_ARTIFACTS = frozenset({'execution_plan.md', 'task_output.md'})
SYNC_CAPABLE_TOOLS = frozenset({'add_evidence.py', 'finish_task.py'})
REAL_CONTEXT_TASK_FILES = [
    'task_scope.md',
    'task_slot.md',
    'task_ledger.md',
    'execution_plan.md',
    'task_output.md',
]
REAL_CONTEXT_ROLE_FILES = [
    'role_workspace/world_model/ROLE_PROFILE_v1.json',
    'role_workspace/world_model/ROLE_WORLD_MODEL_v1.md',
    'role_workspace/world_model/ROLE_BOUNDARY_v1.md',
    'role_workspace/ledgers/TASK_LEDGER_v1.md',
    'role_workspace/knowledge/index.md',
    'role_workspace/ledgers/DECISION_LEDGER_v1.md',
    'role_workspace/ledgers/BLOCKED_ITEMS_v1.md',
]
HANDOFF_STATUS_READY = 'READY'
HANDOFF_STATUS_REDACTION_REQUIRED = 'BLOCKED_REDACTION_REQUIRED'


def workspace_root() -> Path:
    import sys

    module = None
    for base in [
        Path(os.environ.get('LBAI_HOME', '~/.lbai')).expanduser() / 'kit' / 'lbai_core',
        Path(__file__).resolve().parents[2] / 'lbai_core',
    ]:
        if (base / 'lbai' / 'workspace_config.py').exists():
            base_str = str(base)
            if base_str not in sys.path:
                sys.path.insert(0, base_str)
            from lbai import workspace_config as module  # type: ignore[no-redef]
            break

    if module:
        root, _source = module.resolve_workspace_root()
        if module.is_workspace(root):
            return root
        if _source in {'active_workspace', 'active_workspace_invalid'}:
            return root

    try:
        out = subprocess.check_output(
            ['git', 'rev-parse', '--show-toplevel'],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if out:
            candidate = Path(out)
            if (
                (candidate / 'AGENTS.md').exists()
                and (candidate / 'lbai_system').exists()
                and (candidate / 'role_workspace').exists()
                and (candidate / 'tasks').exists()
            ):
                return candidate
    except Exception:
        pass

    current = Path.cwd().resolve()
    for path in [current, *current.parents]:
        if (
            (path / 'AGENTS.md').exists()
            and (path / 'lbai_system').exists()
            and (path / 'role_workspace').exists()
            and (path / 'tasks').exists()
        ):
            return path
    return current


def system_root(root: Path) -> Path:
    return root / 'lbai_system'


def prompt_lab_root(root: Path) -> Path:
    return root / 'prompt_lab'


def current_prompt_dir(root: Path) -> Path:
    return prompt_lab_root(root) / 'prompt_versions' / 'current'


def formal_prompt_dir(root: Path) -> Path:
    return system_root(root) / 'prompts'


def now_id() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        raise SystemExit(f'ERROR: file not found: {path}')
    except json.JSONDecodeError as exc:
        raise SystemExit(f'ERROR: JSON parse failed for {path}: {exc}')
    if not isinstance(data, dict):
        raise SystemExit(f'ERROR: JSON root must be an object: {path}')
    return data


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def copy_prompts(src: Path, dst: Path, *, overwrite: bool) -> list[str]:
    copied = []
    dst.mkdir(parents=True, exist_ok=True)
    for name in PROMPT_FILES:
        source = src / name
        target = dst / name
        if not source.exists():
            continue
        if target.exists() and not overwrite:
            continue
        shutil.copy2(source, target)
        copied.append(name)
    return copied


def ensure_current_prompts(root: Path, reset: bool = False) -> list[str]:
    current = current_prompt_dir(root)
    if reset and current.exists():
        shutil.rmtree(current)
    return copy_prompts(formal_prompt_dir(root), current, overwrite=reset)


def round_dir(run_dir: Path, round_number: int) -> Path:
    return run_dir / f'round_{round_number:03d}'


def seed_round_dirs(path: Path) -> None:
    for rel in [
        'scenario_inputs',
        'tool_outputs',
        'chain_outputs',
        'evaluations',
        'optimizer',
        'prompt_before_patch_snapshot',
        'accepted_prompt_snapshot',
    ]:
        (path / rel).mkdir(parents=True, exist_ok=True)


def read_text_excerpt(path: Path, limit: int = 4000) -> str:
    try:
        text = path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return ''
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + '\n\n[TRUNCATED]'


def task_dirs(root: Path) -> list[Path]:
    tasks_root = root / 'tasks'
    if not tasks_root.exists():
        return []
    return sorted(
        [path for path in tasks_root.iterdir() if path.is_dir() and (path / 'task_scope.md').exists()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def copy_file_if_exists(src: Path, dst: Path) -> bool:
    if not src.exists() or not src.is_file():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def copy_real_context_into_workspace(root: Path, workspace: Path, selected_tasks: list[Path]) -> list[str]:
    copied: list[str] = []
    for rel in REAL_CONTEXT_ROLE_FILES:
        if copy_file_if_exists(root / rel, workspace / rel):
            copied.append(rel)
    for task in selected_tasks:
        task_rel = task.relative_to(root)
        for name in REAL_CONTEXT_TASK_FILES:
            if copy_file_if_exists(task / name, workspace / task_rel / name):
                copied.append((task_rel / name).as_posix())
    return copied


def exclude_real_context_from_isolated_git(workspace: Path) -> None:
    exclude = workspace / '.git' / 'info' / 'exclude'
    if not exclude.exists():
        return
    existing = exclude.read_text(encoding='utf-8')
    additions = [
        '# LBAI Prompt Lab real task context copies',
        '/tasks/*',
        '/role_workspace/*',
    ]
    missing = [line for line in additions if line not in existing]
    if missing:
        exclude.write_text(existing.rstrip() + '\n' + '\n'.join(missing) + '\n', encoding='utf-8')


def build_real_task_context(root: Path, task_limit: int) -> tuple[dict, str]:
    selected_tasks = task_dirs(root)[:max(1, task_limit)]
    role_files = [rel for rel in REAL_CONTEXT_ROLE_FILES if (root / rel).exists()]
    available = bool(selected_tasks)
    context = {
        'schema_version': 'prompt_lab_real_task_context_v1',
        'source': 'real_task' if available else 'mock',
        'available': available,
        'created_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'task_limit': max(1, task_limit),
        'tasks': [],
        'role_files': role_files,
    }
    lines = [
        '# Prompt Lab Real Task Context',
        '',
        'Use this as grounding for scenario generation. Do not mutate the employee root workspace.',
        'If the context is too thin to create meaningful scenarios, fall back to mock office data.',
        '',
    ]
    for task in selected_tasks:
        task_rel = task.relative_to(root).as_posix()
        item = {'task_folder': task_rel, 'files': []}
        lines.extend([f'## Task: {task_rel}', ''])
        for name in REAL_CONTEXT_TASK_FILES:
            path = task / name
            if not path.exists():
                continue
            rel = (task.relative_to(root) / name).as_posix()
            item['files'].append(rel)
            lines.extend([f'### {name}', '', read_text_excerpt(path), ''])
        context['tasks'].append(item)
    if role_files:
        lines.extend(['## Role Context', ''])
        for rel in role_files:
            lines.extend([f'### {rel}', '', read_text_excerpt(root / rel, limit=2500), ''])
    if not available:
        lines.append('No real task or role context was found.')
    return context, '\n'.join(lines)


def write_real_task_context(run_dir: Path, context: dict, context_text: str) -> None:
    context_dir = run_dir / 'real_task_context'
    context_dir.mkdir(parents=True, exist_ok=True)
    write_json(context_dir / 'context_manifest.json', context)
    (context_dir / 'context.md').write_text(context_text, encoding='utf-8')


def load_manifest(run_dir: Path) -> dict:
    return read_json(run_dir / 'run_manifest.json')


def save_manifest(run_dir: Path, data: dict) -> None:
    write_json(run_dir / 'run_manifest.json', data)


def context_from_manifest(root: Path, run_dir: Path, manifest: dict) -> dict | None:
    if manifest.get('effective_context_mode') != 'real_task':
        return None
    context_path = run_dir / 'real_task_context' / 'context_manifest.json'
    if not context_path.exists():
        return None
    data = read_json(context_path)
    return data if data.get('source') == 'real_task' else None


def init_git_repo(workspace: Path) -> None:
    subprocess.run(['git', 'init'], cwd=workspace, check=True, capture_output=True, text=True)
    subprocess.run(['git', 'config', 'user.email', 'prompt-lab-local'], cwd=workspace, check=True)
    subprocess.run(['git', 'config', 'user.name', 'LBAI Prompt Lab'], cwd=workspace, check=True)
    subprocess.run(['git', 'add', '-A'], cwd=workspace, check=True, capture_output=True, text=True)
    subprocess.run(['git', 'commit', '-m', 'test: prompt lab seed'], cwd=workspace, check=True, capture_output=True, text=True)
    subprocess.run(['git', 'branch', '-M', 'main'], cwd=workspace, check=True, capture_output=True, text=True)


def ignore_for_isolated(_dir: str, names: list[str]) -> set[str]:
    ignored = {'__pycache__', '.DS_Store', '.git', 'prompt_lab', 'tasks', 'role_workspace'}
    ignored.update(name for name in names if name.endswith('.pyc'))
    return ignored & set(names)


def sync_isolated_prompts(root: Path, workspace: Path) -> None:
    current = current_prompt_dir(root)
    if not current.exists():
        return
    prompt_dst = workspace / 'lbai_system' / 'prompts'
    prompt_dst.mkdir(parents=True, exist_ok=True)
    copy_prompts(current, prompt_dst, overwrite=True)


def create_isolated_workspace(
    root: Path,
    run_dir: Path,
    round_number: int,
    context: dict | None = None,
) -> Path:
    workspaces = run_dir / 'workspaces'
    workspace = workspaces / f'round_{round_number:03d}_workspace'
    workspace.parent.mkdir(parents=True, exist_ok=True)
    if workspace.exists():
        sync_isolated_prompts(root, workspace)
        if context and context.get('source') == 'real_task':
            exclude_real_context_from_isolated_git(workspace)
            selected = [root / str(item.get('task_folder')) for item in context.get('tasks') or []]
            copy_real_context_into_workspace(root, workspace, selected)
        return workspace

    template = root / 'workspace_template'
    if template.exists():
        shutil.copytree(template, workspace, ignore=ignore_for_isolated)
    else:
        workspace.mkdir()
        for rel in MANAGED_PATHS:
            src = root / rel
            dst = workspace / rel
            if not src.exists():
                continue
            if src.is_dir():
                shutil.copytree(src, dst, ignore=ignore_for_isolated)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        role_template = workspace / 'lbai_system' / 'templates' / 'role_workspace'
        if role_template.exists():
            shutil.copytree(role_template, workspace / 'role_workspace')
        else:
            (workspace / 'role_workspace').mkdir(parents=True, exist_ok=True)
        (workspace / 'tasks').mkdir(parents=True, exist_ok=True)

    if not (workspace / 'role_workspace').exists():
        role_template = workspace / 'lbai_system' / 'templates' / 'role_workspace'
        if role_template.exists():
            shutil.copytree(role_template, workspace / 'role_workspace')
        else:
            (workspace / 'role_workspace').mkdir(parents=True, exist_ok=True)
    (workspace / 'tasks').mkdir(parents=True, exist_ok=True)

    current = current_prompt_dir(root)
    if current.exists():
        prompt_dst = workspace / 'lbai_system' / 'prompts'
        prompt_dst.mkdir(parents=True, exist_ok=True)
        copy_prompts(current, prompt_dst, overwrite=True)

    init_git_repo(workspace)
    if context and context.get('source') == 'real_task':
        exclude_real_context_from_isolated_git(workspace)
        selected = [root / str(item.get('task_folder')) for item in context.get('tasks') or []]
        copy_real_context_into_workspace(root, workspace, selected)
    return workspace


def validate_json(schema_name: str, data_path: Path, root: Path) -> str | None:
    schema_path = system_root(root) / 'prompt_lab' / 'schemas' / schema_name
    try:
        import jsonschema
    except ImportError:
        return 'jsonschema package is required'
    schema = read_json(schema_path)
    data = read_json(data_path)
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as exc:
        location = '.'.join(str(part) for part in exc.absolute_path)
        return f'{location + ": " if location else ""}{exc.message}'
    return None


def command_start(args: argparse.Namespace) -> int:
    root = workspace_root()
    ensure_current_prompts(root, reset=args.reset_current)
    lab = prompt_lab_root(root)
    run_id = args.run_id or f'run_{now_id()}'
    run_dir = lab / 'runs' / run_id
    if run_dir.exists():
        print(f'prompt_lab_status: BLOCKED')
        print(f'reason: run already exists: {run_dir}')
        return 2

    requested_context_mode = args.context_mode
    real_context, real_context_text = build_real_task_context(root, args.real_task_limit)
    effective_context_mode = 'mock'
    if requested_context_mode == 'real_task' and not real_context.get('available'):
        print('prompt_lab_status: BLOCKED')
        print('reason: --context-mode real_task was requested but no task or role context was found')
        return 2
    if requested_context_mode == 'real_task' or (requested_context_mode == 'auto' and real_context.get('available')):
        effective_context_mode = 'real_task'

    run_dir.mkdir(parents=True)
    copied = copy_prompts(current_prompt_dir(root), run_dir / 'baseline_prompt_snapshot', overwrite=True)
    rounds = max(1, args.rounds)
    for idx in range(1, rounds + 1):
        seed_round_dirs(round_dir(run_dir, idx))
    write_real_task_context(run_dir, real_context, real_context_text)
    context_for_workspace = real_context if effective_context_mode == 'real_task' else None
    workspace = create_isolated_workspace(root, run_dir, 1, context_for_workspace)

    manifest = {
        'schema_version': 'prompt_lab_run_manifest_v1',
        'run_id': run_id,
        'created_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'rounds': rounds,
        'scenarios_per_round': max(1, args.scenarios_per_round),
        'focus': args.focus or 'general_office_writing',
        'chain_mode': args.chain_mode,
        'review_mode': args.review_mode,
        'auto_continue': args.auto_continue,
        'apply_threshold': args.apply_threshold,
        'context_mode': requested_context_mode,
        'effective_context_mode': effective_context_mode,
        'real_task_context': str((run_dir / 'real_task_context').relative_to(root)),
        'status': 'OPEN',
        'current_round': 1,
        'baseline_prompt_files': copied,
        'isolated_workspace': str(workspace.relative_to(root)),
    }
    save_manifest(run_dir, manifest)

    print('prompt_lab_status: STARTED')
    print(f'run_id: {run_id}')
    print(f'run_dir: {run_dir.relative_to(root)}')
    print(f'isolated_workspace: {workspace.relative_to(root)}')
    print(f'chain_mode: {args.chain_mode}')
    print(f'context_mode: {effective_context_mode}')
    if effective_context_mode == 'real_task':
        print(f'real_task_context: {(run_dir / "real_task_context" / "context.md").relative_to(root)}')
    print('next_step:')
    print(f'- python3 lbai_system/prompt_lab/prompt_lab.py next-step --run {run_dir.relative_to(root)}')
    return 0


def resolve_run_dir(root: Path, run: str) -> tuple[Path | None, str]:
    path = Path(run)
    if not path.is_absolute():
        path = root / path
    run_dir = path.resolve()
    runs_root = (prompt_lab_root(root) / 'runs').resolve()
    try:
        run_dir.relative_to(runs_root)
    except ValueError:
        return None, '--run must be under prompt_lab/runs/'
    return run_dir, ''


def resolve_isolated_workspace(root: Path, workspace: str) -> tuple[Path | None, str]:
    path = Path(workspace)
    if not path.is_absolute():
        path = (root / path).resolve()
    else:
        path = path.resolve()
    runs_root = (prompt_lab_root(root) / 'runs').resolve()
    try:
        rel = path.relative_to(runs_root)
    except ValueError:
        return None, '--workspace must be a Prompt Lab isolated workspace under prompt_lab/runs/*/workspaces/'
    parts = rel.parts
    if len(parts) < 3 or parts[1] != 'workspaces':
        return None, '--workspace must live under prompt_lab/runs/<run_id>/workspaces/'
    return path, ''


def run_dir_from_workspace(workspace: Path) -> Path:
    return workspace.parent.parent


def resolve_chain_output_source(root: Path, workspace: Path, source: str) -> tuple[Path | None, str]:
    source_path = Path(source)
    if not source_path.is_absolute():
        source_path = (root / source_path).resolve()
    else:
        source_path = source_path.resolve()
    if not source_path.exists():
        return None, f'source not found: {source_path}'
    if not source_path.is_file():
        return None, f'source must be a file under the current run chain_outputs/: {source_path}'

    run_dir = run_dir_from_workspace(workspace).resolve()
    try:
        rel = source_path.relative_to(run_dir)
    except ValueError:
        return None, '--source must be under the same Prompt Lab run as the isolated workspace'
    parts = rel.parts
    if len(parts) < 3 or not parts[0].startswith('round_') or parts[1] != 'chain_outputs':
        return None, '--source must be under prompt_lab/runs/<run_id>/round_*/chain_outputs/'
    return source_path, ''


def round_is_complete(rdir: Path) -> tuple[bool, str]:
    path = rdir / 'optimizer' / 'apply_result.json'
    if not path.exists():
        return False, 'apply_result.json missing'
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        return False, f'invalid apply_result.json: {exc}'
    if not isinstance(data, dict):
        return False, 'apply_result.json root must be an object'
    if data.get('schema_version') != 'prompt_lab_apply_result_v1':
        return False, 'apply_result.json schema_version must be prompt_lab_apply_result_v1'
    if data.get('apply_status') not in {'APPLIED', 'NO_CHANGES', 'SKIPPED'}:
        return False, 'apply_result.json apply_status must be APPLIED, NO_CHANGES, or SKIPPED'
    return True, ''


def command_advance_round(args: argparse.Namespace) -> int:
    root = workspace_root()
    run_dir, err = resolve_run_dir(root, args.run)
    if run_dir is None:
        print('advance_round_status: BLOCKED')
        print(f'reason: {err}')
        return 2
    manifest = load_manifest(run_dir)
    current_round = int(manifest.get('current_round') or 1)
    total_rounds = int(manifest.get('rounds') or 1)
    rdir = round_dir(run_dir, current_round)

    complete, reason = round_is_complete(rdir)
    if not complete:
        print('advance_round_status: BLOCKED')
        print(f'reason: current round is not complete; {reason}')
        print(f'round: {current_round}/{total_rounds}')
        return 2
    if current_round >= total_rounds:
        print('advance_round_status: BLOCKED')
        print(f'reason: already at final round {current_round}/{total_rounds}')
        print(f'finalize_command: python3 lbai_system/prompt_lab/prompt_lab.py finalize --run {run_dir.relative_to(root)}')
        return 2

    next_round = current_round + 1
    seed_round_dirs(round_dir(run_dir, next_round))
    workspace = create_isolated_workspace(root, run_dir, next_round, context_from_manifest(root, run_dir, manifest))
    manifest['current_round'] = next_round
    manifest['isolated_workspace'] = str(workspace.relative_to(root))
    save_manifest(run_dir, manifest)

    print('advance_round_status: OK')
    print(f'run_dir: {run_dir.relative_to(root)}')
    print(f'current_round: {next_round}/{total_rounds}')
    print(f'isolated_workspace: {workspace.relative_to(root)}')
    print('next_step:')
    print(f'- python3 lbai_system/prompt_lab/prompt_lab.py next-step --run {run_dir.relative_to(root)}')
    return 0


def resolve_task_in_workspace(workspace: Path, task: str) -> tuple[Path | None, str]:
    task_path = Path(task)
    if task_path.is_absolute():
        candidate = task_path.resolve()
    else:
        candidate = (workspace / task_path).resolve()
    tasks_root = (workspace / 'tasks').resolve()
    try:
        candidate.relative_to(tasks_root)
    except ValueError:
        return None, '--task must be under tasks/ in the isolated workspace'
    if not (candidate / 'task_scope.md').exists():
        return None, 'task folder missing task_scope.md'
    if not (candidate / 'task_ledger.md').exists():
        return None, 'task folder missing task_ledger.md'
    return candidate, ''


def print_full_chain_instructions(root: Path, run_dir: Path, manifest: dict, current_round: int) -> None:
    rel_run = run_dir.relative_to(root)
    workspace = manifest.get('isolated_workspace')
    round_label = f'round_{current_round:03d}'
    print('- lifecycle_flow: meeting_mock -> add_evidence -> new_task -> prepare_execute -> task_output -> finish_task')
    print('- per_scenario_steps:')
    print('  1. Write meeting mock in scenario source_material; archive with add_evidence.py')
    print('  2. Create OPEN task from a meeting action item with new_task.py')
    print('  3. Run prepare_execute_task.py <task_folder> to create execution_plan.md')
    print('  4. AI writes task_output.md under chain_outputs/<scenario_id>/ using execute_task_plan_prompt_v1.md')
    print(
        f'  5. write-task-artifact --workspace {workspace} --task <task_folder> --artifact task_output.md '
        f'--source {rel_run}/{round_label}/chain_outputs/<scenario_id>/task_output.md --output <tool_outputs/...>'
    )
    print('  6. Run finish_task.py <task_folder> --enrichment <finish_review.json>')
    print('- evaluate: score finish_review_accuracy when finish step ran; boundary/source on execute output')
    print('- prompts_under_test: evidence_enrichment, task_intake, execute_task_plan, finish_review')
    print('- do_not: call search_artifacts.py or write into employee root workspace')


def print_context_instructions(root: Path, run_dir: Path, manifest: dict) -> None:
    effective = str(manifest.get('effective_context_mode') or 'mock')
    print(f'- context_mode: {effective}')
    if effective == 'real_task':
        context_md = run_dir / 'real_task_context' / 'context.md'
        context_manifest = run_dir / 'real_task_context' / 'context_manifest.json'
        print(f'- real_task_context: {context_md.relative_to(root)}')
        print(f'- real_task_context_manifest: {context_manifest.relative_to(root)}')
        print('- scenario_source: build scenarios from the copied real task context first; use mock details only to fill harmless gaps.')
        print('- privacy_note: do not paste unnecessary raw sensitive content into admin reports; keep raw context inside prompt_lab/runs/.')
    else:
        print('- scenario_source: no real task context is available; generate mock office scenarios.')


def command_next_step(args: argparse.Namespace) -> int:
    root = workspace_root()
    run_dir, err = resolve_run_dir(root, args.run)
    if run_dir is None:
        print('prompt_lab_next_step:')
        print(f'- run: {args.run}')
        print(f'- action: BLOCKED')
        print(f'- reason: {err}')
        return 2
    manifest = load_manifest(run_dir)
    current_round = int(manifest.get('current_round') or 1)
    rdir = round_dir(run_dir, current_round)
    scenarios = rdir / 'scenario_inputs' / 'scenarios.json'
    score = rdir / 'round_score.json'
    patch = rdir / 'optimizer' / 'prompt_patch.json'
    apply_result = rdir / 'optimizer' / 'apply_result.json'

    print('prompt_lab_next_step:')
    print(f'- run: {run_dir.relative_to(root)}')
    print(f'- round: {current_round}/{manifest.get("rounds")}')
    chain_mode = str(manifest.get('chain_mode') or 'intake_evidence')
    print(f'- chain_mode: {chain_mode}')
    print_context_instructions(root, run_dir, manifest)
    if not scenarios.exists():
        print('- action: generate_scenarios')
        print(f'- write: {scenarios.relative_to(root)}')
        print('- schema: prompt_lab_scenarios_v1')
        print(f'- count: {manifest.get("scenarios_per_round")}')
        print(f'- focus: {manifest.get("focus")}')
        print('- scenario_quality: each scenario must name the observed problem, expected behavior, and the prompt being tested.')
        if chain_mode == 'full_lifecycle':
            print('- scenario_requirements: include lifecycle=full_chain scenarios with meeting mock + one actionable meeting item')
            print_full_chain_instructions(root, run_dir, manifest, current_round)
        else:
            print('- categories: internal_report, meeting_minutes, manager_request, customer_feedback, policy_summary, hr_copy, sales_material, product_explanation, review_sensitive_external')
        return 0
    if not score.exists():
        print('- action: run_flow_and_evaluate')
        print(f'- isolated_workspace: {manifest.get("isolated_workspace")}')
        if chain_mode == 'full_lifecycle':
            print_full_chain_instructions(root, run_dir, manifest, current_round)
        else:
            print('- run existing tools with AI-produced enrichment JSON, save outputs under tool_outputs/, then write prompt_lab_evaluation_v1 JSON files under evaluations/.')
        print('- evaluation_quality: list clear issues, a concrete optimization plan, and expected effect for each scenario.')
        print('- admin_handoff_safety: set admin_handoff_safe=true only when issues and suggestions are redacted and safe for administrator handoff; set sensitive_content_present=true if raw names, conversations, secrets, or customer/project details appear.')
        print(f'- score_command: python3 lbai_system/prompt_lab/prompt_lab.py score --run {run_dir.relative_to(root)} --round {current_round}')
        return 0
    if not patch.exists():
        print('- action: propose_prompt_patch')
        print(f'- write: {patch.relative_to(root)}')
        print('- schema: prompt_lab_prompt_patch_v1')
        print('- only target experimental prompt copies; do not edit lbai_system/prompts/.')
        print('- patch_quality: rationale must explain problem -> change -> expected effect in plain language.')
        return 0
    if not apply_result.exists():
        print('- action: apply_prompt_patch_if_qualified')
        print(f'- command: python3 lbai_system/prompt_lab/prompt_lab.py apply-prompt-patch --run {run_dir.relative_to(root)} --round {current_round} --patch {patch.relative_to(root)}')
        return 0
    print('- action: review_or_continue')
    print(f'- human_review: {(rdir / "human_review.md").relative_to(root)}')
    print(f'- round_report: {(rdir / "round_report.md").relative_to(root)}')
    print(f'- admin_report: {(rdir / "admin_report.md").relative_to(root)}')
    print(f'- admin_outbox: {(prompt_lab_root(root) / "admin_feedback" / "outbox" / run_dir.name / f"round_{current_round:03d}").relative_to(root)}')
    print(f'- finalize_after_approval: python3 lbai_system/prompt_lab/prompt_lab.py finalize --run {run_dir.relative_to(root)}')
    if manifest.get('auto_continue') and current_round < int(manifest.get('rounds') or 1):
        rel_run = run_dir.relative_to(root)
        print(f'- auto_continue: true; next command after review: python3 lbai_system/prompt_lab/prompt_lab.py advance-round --run {rel_run}')
    else:
        print('- auto_continue: false; wait for human direction before another round.')
        if current_round < int(manifest.get('rounds') or 1):
            rel_run = run_dir.relative_to(root)
            print(f'- continue_next_round: python3 lbai_system/prompt_lab/prompt_lab.py advance-round --run {rel_run}')
    return 0


def command_validate(args: argparse.Namespace) -> int:
    root = workspace_root()
    schema_by_kind = {
        'scenarios': 'scenarios_schema_v1.json',
        'evaluation': 'evaluation_schema_v1.json',
        'prompt_patch': 'prompt_patch_schema_v1.json',
    }
    schema = schema_by_kind[args.kind]
    err = validate_json(schema, Path(args.path), root)
    if err:
        print('validation_status: BLOCKED')
        print(f'reason: {err}')
        return 1
    print('validation_status: OK')
    print(f'path: {args.path}')
    return 0


def command_run_tool(args: argparse.Namespace) -> int:
    root = workspace_root()
    if args.tool not in ALLOWED_RUN_TOOLS:
        print('tool_status: BLOCKED')
        print(f'reason: unsupported tool for Prompt Lab: {args.tool}')
        print(f'allowed_tools: {", ".join(sorted(ALLOWED_RUN_TOOLS))}')
        return 2
    workspace, err = resolve_isolated_workspace(root, args.workspace)
    if workspace is None:
        print('tool_status: BLOCKED')
        print(f'reason: {err}')
        return 2
    script = workspace / 'lbai_system' / 'tools' / args.tool
    if not script.exists():
        print('tool_status: BLOCKED')
        print(f'reason: tool not found: {script}')
        return 2
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['LBAI_HOME'] = str(workspace / '.lbai_home')
    env[PROMPT_LAB_ISOLATED_ENV] = '1'
    extra = list(args.extra)
    if extra and extra[0] == '--':
        extra = extra[1:]
    if args.tool in SYNC_CAPABLE_TOOLS and '--no-sync' not in extra:
        extra.append('--no-sync')
    proc = subprocess.run(
        [sys.executable, str(script), *extra],
        cwd=workspace,
        capture_output=True,
        text=True,
        env=env,
    )
    output = {
        'schema_version': 'prompt_lab_tool_output_v1',
        'tool': args.tool,
        'extra_args': extra,
        'returncode': proc.returncode,
        'stdout': proc.stdout,
        'stderr': proc.stderr,
        'workspace': str(workspace),
    }
    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = root / out_path
    write_json(out_path, output)
    print(f'tool_status: {"OK" if proc.returncode == 0 else "FAILED"}')
    print(f'output: {out_path.relative_to(root)}')
    return proc.returncode


def command_write_task_artifact(args: argparse.Namespace) -> int:
    root = workspace_root()
    workspace, err = resolve_isolated_workspace(root, args.workspace)
    if workspace is None:
        print('artifact_status: BLOCKED')
        print(f'reason: {err}')
        return 2
    task_dir, err = resolve_task_in_workspace(workspace, args.task)
    if task_dir is None:
        print('artifact_status: BLOCKED')
        print(f'reason: {err}')
        return 2
    artifact_name = str(args.artifact or '').strip()
    if artifact_name not in ALLOWED_TASK_ARTIFACTS:
        print('artifact_status: BLOCKED')
        print(f'reason: unsupported artifact {artifact_name!r}; allowed: {", ".join(sorted(ALLOWED_TASK_ARTIFACTS))}')
        return 2
    source_path, err = resolve_chain_output_source(root, workspace, args.source)
    if source_path is None:
        print('artifact_status: BLOCKED')
        print(f'reason: {err}')
        return 2
    target_path = task_dir / artifact_name
    shutil.copy2(source_path, target_path)
    rel_task = task_dir.relative_to(workspace)
    result = {
        'schema_version': 'prompt_lab_task_artifact_v1',
        'task_folder': str(rel_task),
        'artifact': artifact_name,
        'source': str(source_path),
        'target': str(target_path),
    }
    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = root / out_path
    write_json(out_path, result)
    print('artifact_status: OK')
    print(f'task_folder: {rel_task}')
    print(f'artifact: {artifact_name}')
    print(f'output: {out_path.relative_to(root)}')
    return 0


def evaluation_files(rdir: Path) -> list[Path]:
    return sorted((rdir / 'evaluations').glob('*.json'))


def previous_score(run_dir: Path, current_round: int) -> float | None:
    if current_round <= 1:
        return None
    path = round_dir(run_dir, current_round - 1) / 'round_score.json'
    if not path.exists():
        return None
    return float(read_json(path).get('overall_score') or 0)


def relative_existing_paths(base: Path, folder: Path, pattern: str = '*') -> list[str]:
    if not folder.exists():
        return []
    return sorted(path.relative_to(base).as_posix() for path in folder.glob(pattern) if path.is_file())


def effect_text(summary: dict) -> str:
    previous = summary.get('previous_score')
    current = summary.get('overall_score')
    if previous is None:
        return '首轮已形成问题和优化方案；修改后的真实效果需要下一轮复跑后与本轮评分对比。'
    if current is not None and float(current) > float(previous):
        return f'本轮评分从 {previous} 提升到 {current}，上一轮 prompt 修改后的整体效果变好。'
    if current is not None:
        return f'本轮评分为 {current}，未高于上一轮 {previous}，优化方案需要继续收敛。'
    return '尚未形成可比较评分。'


def summarize_admin_payload(
    summary: dict,
    patch_data: dict | None = None,
    apply_data: dict | None = None,
    *,
    redacted: bool = False,
) -> dict:
    problems = (summary.get('red_flags') or []) + (summary.get('issues') or [])
    optimization_plan = summary.get('prompt_improvement_candidates') or []
    rationale = (patch_data or {}).get('rationale') or ''
    return {
        'schema_version': 'prompt_lab_admin_summary_v1',
        'overall_score': summary.get('overall_score'),
        'previous_score': summary.get('previous_score'),
        'red_flag_count': summary.get('red_flag_count', 0),
        'problems': [] if redacted else problems,
        'optimization_plan': [] if redacted else optimization_plan,
        'optimizer_rationale': '' if redacted else rationale,
        'apply_status': (apply_data or {}).get('apply_status') or 'PENDING',
        'changed_files': (apply_data or {}).get('changed_files') or [],
        'effect': effect_text(summary),
        'handoff_status': summary.get('admin_handoff_status') or HANDOFF_STATUS_READY,
        'redaction_notes': summary.get('redaction_notes') or [],
    }


def admin_report_lines(
    root: Path,
    context_mode: str,
    source_context: Path,
    files_for_admin: dict[str, Path],
    payload: dict,
) -> list[str]:
    lines = [
        '# LBAI Prompt Iteration Report',
        '',
        '## 结论',
        f'- 上下文来源：{"真实任务" if context_mode == "real_task" else "模拟数据"}',
        f'- 管理员交接状态：{payload["handoff_status"]}',
        f'- 本轮评分：{payload["overall_score"]}',
        f'- 上轮评分：{payload["previous_score"] if payload["previous_score"] is not None else "无"}',
        f'- 应用状态：{payload["apply_status"]}',
        f'- 优化后效果：{payload["effect"]}',
        '',
        '## 清晰的问题',
    ]
    if payload['handoff_status'] == HANDOFF_STATUS_REDACTION_REQUIRED:
        lines.append('- 真实任务上下文尚未确认脱敏，管理员交接包已隐藏问题原文。请先检查本地 run 报告和 evaluation JSON，脱敏后再发送。')
        notes = payload.get('redaction_notes') or []
        lines.extend(f'- 脱敏说明：{item}' for item in notes[:10])
        lines.extend([
            '',
            '## 优化方案',
            '- 真实任务上下文尚未确认脱敏，管理员交接包已隐藏优化方案原文。',
            '',
            '## 优化后的效果',
            f'- {payload["effect"]}',
        ])
    else:
        problems = payload['problems']
        if problems:
            lines.extend(f'- {item}' for item in problems[:30])
        else:
            lines.append('- 本轮未记录明确问题。')

        lines.extend(['', '## 优化方案'])
        if payload['optimizer_rationale']:
            lines.append(f'- 修改理由：{payload["optimizer_rationale"]}')
        plans = payload['optimization_plan']
        if plans:
            lines.extend(f'- {item}' for item in plans[:30])
        if payload['changed_files']:
            lines.extend(f'- 已修改实验 prompt：{item}' for item in payload['changed_files'])
        if not payload['optimizer_rationale'] and not plans and not payload['changed_files']:
            lines.append('- 尚未生成可应用的 prompt 修改方案。')

        lines.extend([
            '',
            '## 优化后的效果',
            f'- {payload["effect"]}',
        ])

    lines.extend(['', '## 管理员复核索引'])
    for label, path in files_for_admin.items():
        if path.exists():
            lines.append(f'- {label}: {path.relative_to(root).as_posix()}')
    if context_mode == 'real_task' and source_context.exists():
        lines.append(f'- real_task_context_manifest: {source_context.relative_to(root).as_posix()}')
        lines.append('- raw_context_policy: 原始真实任务上下文保留在 prompt_lab/runs/ 本地记录中，管理员默认先看本报告和索引。')
    lines.append('')
    return lines


def write_admin_report_bundle(
    root: Path,
    run_dir: Path,
    rdir: Path,
    summary: dict,
    patch_data: dict | None = None,
    apply_data: dict | None = None,
) -> None:
    manifest = load_manifest(run_dir)
    round_label = rdir.name
    outbox = prompt_lab_root(root) / 'admin_feedback' / 'outbox' / run_dir.name / round_label
    outbox.mkdir(parents=True, exist_ok=True)
    context_mode = manifest.get('effective_context_mode') or 'mock'
    source_context = run_dir / 'real_task_context' / 'context_manifest.json'
    files_for_admin = {
        'round_score': rdir / 'round_score.json',
        'human_review': rdir / 'human_review.md',
        'round_report': rdir / 'round_report.md',
        'prompt_patch': rdir / 'optimizer' / 'prompt_patch.json',
        'prompt_diff': rdir / 'optimizer' / 'prompt_patch.diff',
        'apply_result': rdir / 'optimizer' / 'apply_result.json',
    }

    local_payload = summarize_admin_payload(summary, patch_data, apply_data)
    outbox_redacted = local_payload['handoff_status'] == HANDOFF_STATUS_REDACTION_REQUIRED
    outbox_payload = summarize_admin_payload(summary, patch_data, apply_data, redacted=outbox_redacted)
    local_report = '\n'.join(admin_report_lines(root, context_mode, source_context, files_for_admin, local_payload))
    outbox_report = '\n'.join(admin_report_lines(root, context_mode, source_context, files_for_admin, outbox_payload))
    (rdir / 'admin_report.md').write_text(local_report, encoding='utf-8')
    (outbox / 'admin_report.md').write_text(outbox_report, encoding='utf-8')
    write_json(outbox / 'admin_summary.json', {
        **outbox_payload,
        'run_id': run_dir.name,
        'round': round_label,
        'context_mode': context_mode,
        'source_run': run_dir.relative_to(root).as_posix(),
        'source_round': rdir.relative_to(root).as_posix(),
        'artifact_refs': {
            label: path.relative_to(root).as_posix()
            for label, path in files_for_admin.items()
            if path.exists()
        },
    })


def print_admin_summary(summary: dict, patch_data: dict | None = None, apply_data: dict | None = None) -> None:
    payload = summarize_admin_payload(summary, patch_data, apply_data)
    print('admin_summary:')
    print(f'- score: {payload["overall_score"]}')
    print(f'- apply_status: {payload["apply_status"]}')
    print(f'- handoff_status: {payload["handoff_status"]}')
    problems = payload['problems'][:5]
    if problems:
        print('- clear_problems:')
        for item in problems:
            print(f'  - {item}')
    else:
        print('- clear_problems: None')
    plans = payload['optimization_plan'][:5]
    if payload['optimizer_rationale'] or plans or payload['changed_files']:
        print('- optimization_plan:')
        if payload['optimizer_rationale']:
            print(f'  - {payload["optimizer_rationale"]}')
        for item in plans:
            print(f'  - {item}')
        for item in payload['changed_files']:
            print(f'  - changed: {item}')
    else:
        print('- optimization_plan: Not ready')
    print(f'- optimized_effect: {payload["effect"]}')


def write_round_report(
    root: Path,
    run_dir: Path,
    rdir: Path,
    summary: dict,
    patch_data: dict | None = None,
    apply_data: dict | None = None,
) -> None:
    previous = summary.get('previous_score')
    current = summary.get('overall_score')
    effect = effect_text(summary)

    red_flags = summary.get('red_flags') or []
    issues = summary.get('issues') or []
    candidates = summary.get('prompt_improvement_candidates') or []
    changed = (apply_data or {}).get('changed_files') or []
    apply_status = (apply_data or {}).get('apply_status') or 'PENDING'
    rationale = (patch_data or {}).get('rationale') or '尚未生成 prompt 修改方案。'

    lines = [
        '# Prompt Lab Round Report',
        '',
        '## 简单结果',
        f'- 本轮评分：{current}',
        f'- 上轮评分：{previous if previous is not None else "无"}',
        f'- 红线问题数：{summary.get("red_flag_count", 0)}',
        f'- 修改应用状态：{apply_status}',
        f'- 修改后效果：{effect}',
        '',
        '## Prompt 欠缺或 AI 犯错',
    ]
    if red_flags:
        lines.extend(f'- 红线：{item}' for item in red_flags)
    if issues:
        lines.extend(f'- {item}' for item in issues)
    if not red_flags and not issues:
        lines.append('- 本轮评估未记录明确问题。')

    lines.extend(['', '## 怎么修改'])
    lines.append(f'- 修改理由：{rationale}')
    if candidates:
        lines.extend(f'- 建议：{item}' for item in candidates[:20])
    if changed:
        lines.extend(f'- 已修改实验 prompt：{item}' for item in changed)
    else:
        lines.append('- 尚未应用 prompt 修改，或本轮不满足自动应用条件。')

    lines.extend([
        '',
        '## 原始数据索引',
        f'- 原始正式 prompt 快照：{(run_dir / "baseline_prompt_snapshot").relative_to(root).as_posix()}',
        f'- 本轮改前实验 prompt 快照：{(rdir / "prompt_before_patch_snapshot").relative_to(root).as_posix()}',
        f'- 本轮改后实验 prompt 快照：{(rdir / "accepted_prompt_snapshot").relative_to(root).as_posix()}',
        f'- prompt diff：{(rdir / "optimizer" / "prompt_patch.diff").relative_to(root).as_posix()}',
        f'- prompt patch JSON：{(rdir / "optimizer" / "prompt_patch.json").relative_to(root).as_posix()}',
        f'- 评分 JSON：{(rdir / "round_score.json").relative_to(root).as_posix()}',
        '',
        '## AI 产出记录',
        '### 修改前/本轮流程产出',
    ])
    tool_outputs = relative_existing_paths(root, rdir / 'tool_outputs', '*.json')
    evaluations = relative_existing_paths(root, rdir / 'evaluations', '*.json')
    if tool_outputs:
        lines.extend(f'- {item}' for item in tool_outputs)
    else:
        lines.append('- 尚未保存 tool output JSON。')
    lines.extend(['', '### 本轮评估原文'])
    if evaluations:
        lines.extend(f'- {item}' for item in evaluations)
    else:
        lines.append('- 尚未保存 evaluation JSON。')
    lines.extend([
        '',
        '### 修改后产出',
        '- Prompt 修改后的 AI 产出需在下一轮复跑后查看下一轮 `tool_outputs/`；该轮评分会与本轮分数对比。',
        '',
    ])
    (rdir / 'round_report.md').write_text('\n'.join(lines), encoding='utf-8')
    write_admin_report_bundle(root, run_dir, rdir, summary, patch_data, apply_data)


def write_human_review(root: Path, run_dir: Path, rdir: Path, summary: dict) -> None:
    lines = [
        '# Prompt Lab Human Review',
        '',
        f'overall_score: {summary["overall_score"]}',
        f'red_flag_count: {summary["red_flag_count"]}',
        f'evaluation_count: {summary["evaluation_count"]}',
        '',
        '## Top Issues',
    ]
    issues = summary.get('issues') or []
    lines.extend(f'- {item}' for item in issues[:20])
    if not issues:
        lines.append('- None')
    lines.extend(['', '## Prompt Improvement Candidates'])
    candidates = summary.get('prompt_improvement_candidates') or []
    lines.extend(f'- {item}' for item in candidates[:20])
    if not candidates:
        lines.append('- None')
    lines.append('')
    (rdir / 'human_review.md').write_text('\n'.join(lines), encoding='utf-8')
    write_round_report(root, run_dir, rdir, summary)


def command_score(args: argparse.Namespace) -> int:
    root = workspace_root()
    run_dir, err = resolve_run_dir(root, args.run)
    if run_dir is None:
        print('score_status: BLOCKED')
        print(f'reason: {err}')
        return 2
    rdir = round_dir(run_dir, args.round)
    files = evaluation_files(rdir)
    if not files:
        print('score_status: BLOCKED')
        print(f'reason: no evaluation JSON files found under {(rdir / "evaluations").relative_to(root)}')
        return 2

    manifest = load_manifest(run_dir)
    requires_safe_handoff = manifest.get('effective_context_mode') == 'real_task'
    total = 0.0
    count = 0
    red_flags: list[str] = []
    issues: list[str] = []
    candidates: list[str] = []
    redaction_notes: list[str] = []
    sensitive_content_present = False
    admin_handoff_safe = True
    for path in files:
        err = validate_json('evaluation_schema_v1.json', path, root)
        if err:
            print('score_status: BLOCKED')
            print(f'reason: invalid evaluation {path.relative_to(root)}: {err}')
            return 1
        data = read_json(path)
        scores = data.get('scores') or {}
        total += sum(float(scores.get(field) or 0) for field in SCORE_FIELDS)
        count += len(SCORE_FIELDS)
        red_flags.extend(str(item) for item in data.get('red_flags') or [])
        issues.extend(str(item) for item in data.get('issues') or [])
        candidates.extend(str(item) for item in data.get('prompt_improvement_candidates') or [])
        if data.get('sensitive_content_present'):
            sensitive_content_present = True
        if requires_safe_handoff and data.get('admin_handoff_safe') is not True:
            admin_handoff_safe = False
        if data.get('admin_handoff_safe') is False:
            admin_handoff_safe = False
        redaction_notes.extend(str(item) for item in data.get('redaction_notes') or [])

    if sensitive_content_present:
        admin_handoff_safe = False
    handoff_status = HANDOFF_STATUS_READY
    if requires_safe_handoff and not admin_handoff_safe:
        handoff_status = HANDOFF_STATUS_REDACTION_REQUIRED
        if not redaction_notes:
            redaction_notes.append('real task evaluation did not explicitly confirm admin_handoff_safe=true')

    overall = round((total / (count * 5)) * 100, 2) if count else 0.0
    summary = {
        'schema_version': 'prompt_lab_round_score_v1',
        'round': args.round,
        'evaluation_count': len(files),
        'overall_score': overall,
        'previous_score': previous_score(run_dir, args.round),
        'red_flag_count': len(red_flags),
        'red_flags': red_flags,
        'issues': issues,
        'prompt_improvement_candidates': candidates,
        'admin_handoff_safe': admin_handoff_safe,
        'admin_handoff_status': handoff_status,
        'sensitive_content_present': sensitive_content_present,
        'redaction_notes': redaction_notes,
    }
    write_json(rdir / 'round_score.json', summary)
    write_human_review(root, run_dir, rdir, summary)
    print('score_status: OK')
    print(f'overall_score: {overall}')
    print(f'red_flag_count: {len(red_flags)}')
    print(f'human_review: {(rdir / "human_review.md").relative_to(root)}')
    print(f'round_report: {(rdir / "round_report.md").relative_to(root)}')
    print(f'admin_report: {(rdir / "admin_report.md").relative_to(root)}')
    print_admin_summary(summary)
    return 0


def apply_patch_to_text(text: str, change: dict) -> str:
    operation = change.get('operation')
    if operation == 'append_rule':
        content = str(change.get('content') or '').strip()
        if not content:
            raise ValueError('append_rule requires content')
        section = '\n\n## Prompt Lab Learned Rule\n\n' + content + '\n'
        return text.rstrip() + section
    if operation == 'replace_text':
        find = str(change.get('find') or '')
        replace = str(change.get('replace') or '')
        if not find:
            raise ValueError('replace_text requires find')
        if find not in text:
            raise ValueError('replace_text find value not found')
        return text.replace(find, replace, 1)
    raise ValueError(f'unsupported operation: {operation}')


def qualified_for_apply(score_data: dict, threshold: float) -> tuple[bool, str]:
    score = float(score_data.get('overall_score') or 0)
    previous = score_data.get('previous_score')
    red_flags = int(score_data.get('red_flag_count') or 0)
    if red_flags:
        return False, 'red flags present'
    if score < threshold:
        return False, f'overall_score {score} below threshold {threshold}'
    if previous is not None and score <= float(previous):
        return False, f'overall_score {score} did not improve over previous {previous}'
    if int(score_data.get('evaluation_count') or 0) < 1:
        return False, 'no evaluated scenarios'
    return True, 'qualified'


def restore_prompt_dir(dst: Path, src: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def apply_patch_to_prompt_dir(current: Path, patch_data: dict) -> tuple[list[str], list[str]]:
    staging = current.parent / '.patch_staging'
    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(current, staging)
    diff_lines: list[str] = []
    changed_files: list[str] = []
    try:
        for change in patch_data.get('files') or []:
            name = Path(str(change.get('prompt_file') or '')).name
            if name not in PROMPT_FILES:
                raise ValueError(f'unsupported prompt_file: {name}')
            path = staging / name
            before = path.read_text(encoding='utf-8')
            after = apply_patch_to_text(before, change)
            if before != after:
                path.write_text(after, encoding='utf-8')
                changed_files.append(name)
                diff_lines.extend(difflib.unified_diff(
                    before.splitlines(),
                    after.splitlines(),
                    fromfile=f'before/{name}',
                    tofile=f'after/{name}',
                    lineterm='',
                ))
        if changed_files:
            restore_prompt_dir(current, staging)
        return changed_files, diff_lines
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def command_apply_prompt_patch(args: argparse.Namespace) -> int:
    root = workspace_root()
    run_dir, err = resolve_run_dir(root, args.run)
    if run_dir is None:
        print('apply_status: BLOCKED')
        print(f'reason: {err}')
        return 2
    rdir = round_dir(run_dir, args.round)
    score_path = rdir / 'round_score.json'
    if not score_path.exists():
        print('apply_status: BLOCKED')
        print('reason: round_score.json missing')
        return 2
    score_data = read_json(score_path)
    ok, reason = qualified_for_apply(score_data, args.threshold)
    result_path = rdir / 'optimizer' / 'apply_result.json'
    if not ok:
        apply_data = {
            'schema_version': 'prompt_lab_apply_result_v1',
            'apply_status': 'SKIPPED',
            'reason': reason,
        }
        write_json(result_path, apply_data)
        write_round_report(root, run_dir, rdir, score_data, apply_data=apply_data)
        print('apply_status: SKIPPED')
        print(f'reason: {reason}')
        print(f'round_report: {(rdir / "round_report.md").relative_to(root)}')
        print(f'admin_report: {(rdir / "admin_report.md").relative_to(root)}')
        print_admin_summary(score_data, apply_data=apply_data)
        return 0

    patch_path = Path(args.patch)
    if not patch_path.is_absolute():
        patch_path = root / patch_path
    err = validate_json('prompt_patch_schema_v1.json', patch_path, root)
    if err:
        print('apply_status: BLOCKED')
        print(f'reason: {err}')
        return 1
    patch_data = read_json(patch_path)
    current = current_prompt_dir(root)
    if not current.exists():
        ensure_current_prompts(root)
    snapshot = rdir / 'accepted_prompt_snapshot'
    if snapshot.exists():
        shutil.rmtree(snapshot)
    before_snapshot = rdir / 'prompt_before_patch_snapshot'
    if before_snapshot.exists():
        shutil.rmtree(before_snapshot)
    shutil.copytree(current, before_snapshot)
    (rdir / 'optimizer' / 'optimizer_rationale.md').write_text(
        '# Optimizer Rationale\n\n' + str(patch_data.get('rationale') or '').strip() + '\n',
        encoding='utf-8',
    )

    try:
        changed_files, diff_lines = apply_patch_to_prompt_dir(current, patch_data)
    except Exception as exc:
        restore_prompt_dir(current, before_snapshot)
        write_json(result_path, {
            'schema_version': 'prompt_lab_apply_result_v1',
            'apply_status': 'BLOCKED',
            'reason': str(exc),
        })
        print('apply_status: BLOCKED')
        print(f'reason: {exc}')
        return 1

    shutil.copytree(current, snapshot)
    diff_path = rdir / 'optimizer' / 'prompt_patch.diff'
    diff_path.write_text('\n'.join(diff_lines) + ('\n' if diff_lines else ''), encoding='utf-8')
    write_json(rdir / 'optimizer' / 'before_after_score.json', {
        'schema_version': 'prompt_lab_before_after_score_v1',
        'previous_score': score_data.get('previous_score'),
        'overall_score': score_data.get('overall_score'),
        'threshold': args.threshold,
    })
    write_json(result_path, {
        'schema_version': 'prompt_lab_apply_result_v1',
        'apply_status': 'APPLIED' if changed_files else 'NO_CHANGES',
        'reason': reason,
        'changed_files': changed_files,
    })
    write_round_report(root, run_dir, rdir, score_data, patch_data, read_json(result_path))
    print(f'apply_status: {"APPLIED" if changed_files else "NO_CHANGES"}')
    print(f'changed_files: {", ".join(changed_files) if changed_files else "None"}')
    print(f'diff: {diff_path.relative_to(root)}')
    print(f'round_report: {(rdir / "round_report.md").relative_to(root)}')
    print(f'admin_report: {(rdir / "admin_report.md").relative_to(root)}')
    print_admin_summary(score_data, patch_data, read_json(result_path))
    return 0


def command_finalize(args: argparse.Namespace) -> int:
    root = workspace_root()
    run_dir, err = resolve_run_dir(root, args.run)
    if run_dir is None:
        print('finalize_status: BLOCKED')
        print(f'reason: {err}')
        return 2
    if not run_dir.exists():
        print('finalize_status: BLOCKED')
        print(f'reason: run not found: {run_dir}')
        return 2

    run_id = run_dir.name
    if args.keep_report:
        report_root = prompt_lab_root(root) / 'finalized_reports' / run_id
        if report_root.exists():
            shutil.rmtree(report_root)
        report_root.mkdir(parents=True, exist_ok=True)
        for report in run_dir.glob('round_*/round_report.md'):
            target = report_root / report.parent.name / report.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(report, target)
        for report in run_dir.glob('round_*/human_review.md'):
            target = report_root / report.parent.name / report.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(report, target)

    shutil.rmtree(run_dir)
    print('finalize_status: CLEANED')
    print(f'run_id: {run_id}')
    print(f'kept_prompt_dir: {current_prompt_dir(root).relative_to(root)}')
    if args.keep_report:
        print(f'kept_reports: {(prompt_lab_root(root) / "finalized_reports" / run_id).relative_to(root)}')
    else:
        print('kept_reports: None')
    print('deleted: mock scenarios, tool outputs, evaluations, isolated workspaces, and run-local raw data')
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='prompt_lab.py')
    sub = parser.add_subparsers(dest='command', required=True)

    start = sub.add_parser('start')
    start.add_argument('--rounds', type=int, default=1)
    start.add_argument('--scenarios-per-round', type=int, default=6)
    start.add_argument('--focus', default='general_office_writing')
    start.add_argument(
        '--chain-mode',
        choices=sorted(CHAIN_MODES),
        default='intake_evidence',
        help='intake_evidence: archive/intake only; full_lifecycle: meeting -> task -> execute -> finish',
    )
    start.add_argument('--review-mode', choices=['human_each_round', 'auto'], default='human_each_round')
    start.add_argument('--auto-continue', action='store_true')
    start.add_argument('--apply-threshold', type=float, default=80.0)
    start.add_argument(
        '--context-mode',
        choices=sorted(CONTEXT_MODES),
        default='auto',
        help='auto: use real task context when present; real_task: require it; mock: always synthesize mock scenarios',
    )
    start.add_argument('--real-task-limit', type=int, default=3)
    start.add_argument('--run-id')
    start.add_argument('--reset-current', action='store_true')
    start.set_defaults(func=command_start)

    advance_round = sub.add_parser('advance-round')
    advance_round.add_argument('--run', required=True)
    advance_round.set_defaults(func=command_advance_round)

    next_step = sub.add_parser('next-step')
    next_step.add_argument('--run', required=True)
    next_step.set_defaults(func=command_next_step)

    validate = sub.add_parser('validate')
    validate.add_argument('--kind', choices=['scenarios', 'evaluation', 'prompt_patch'], required=True)
    validate.add_argument('--path', required=True)
    validate.set_defaults(func=command_validate)

    run_tool = sub.add_parser('run-tool')
    run_tool.add_argument('--workspace', required=True)
    run_tool.add_argument('--tool', required=True)
    run_tool.add_argument('--output', required=True)
    run_tool.add_argument('extra', nargs=argparse.REMAINDER)
    run_tool.set_defaults(func=command_run_tool)

    write_task_artifact = sub.add_parser('write-task-artifact')
    write_task_artifact.add_argument('--workspace', required=True)
    write_task_artifact.add_argument('--task', required=True, help='Task folder under tasks/ in isolated workspace')
    write_task_artifact.add_argument('--artifact', required=True, choices=sorted(ALLOWED_TASK_ARTIFACTS))
    write_task_artifact.add_argument('--source', required=True, help='Mock artifact file under prompt_lab/runs/')
    write_task_artifact.add_argument('--output', required=True)
    write_task_artifact.set_defaults(func=command_write_task_artifact)

    score = sub.add_parser('score')
    score.add_argument('--run', required=True)
    score.add_argument('--round', type=int, default=1)
    score.set_defaults(func=command_score)

    apply_prompt_patch = sub.add_parser('apply-prompt-patch')
    apply_prompt_patch.add_argument('--run', required=True)
    apply_prompt_patch.add_argument('--round', type=int, default=1)
    apply_prompt_patch.add_argument('--patch', required=True)
    apply_prompt_patch.add_argument('--threshold', type=float, default=80.0)
    apply_prompt_patch.set_defaults(func=command_apply_prompt_patch)

    finalize = sub.add_parser('finalize')
    finalize.add_argument('--run', required=True)
    finalize.add_argument('--keep-report', action='store_true')
    finalize.set_defaults(func=command_finalize)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
