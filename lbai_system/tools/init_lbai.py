#!/usr/bin/env python3
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True

from enrichment_utils import load_json_file, resolve_enrichment_path, validate_with_schema
from task_utils import redact_sensitive, workspace_root


ENRICHMENT_VERSION = 'init_enrichment_v1'
BLOCKED_MESSAGE = (
    'AI enrichment required (--enrichment). Use Cursor or Codex desktop app; '
    'see lbai_system/prompts/init_enrichment_prompt_v1.md'
)


QUESTIONS = """# /lbai-init 岗位设定问题

请直接复制下面内容并填写，简单写即可。

说明：
- 这些信息会用于后续任务上下文、资料归档身份和岗位记忆检索。
- 其他边界类规则会使用公司默认规则，不需要初始化时逐项填写。

## 用户姓名
必答。例：张三 / Alice

## 岗位名称
必答。例：办公室文职 / 内容助理 / 市场运营

## 主要职责
必答。例：整理会议纪要、汇总用户反馈、编写内部周报。简单列 1-3 项即可。

## 对话习惯
必答。例：简洁 / 详细 / 先给结论再给依据 / 中文为主
"""


SECTION_NAMES = [
    '用户姓名',
    '岗位名称',
    '主要职责',
    '对话习惯',
]

REQUIRED_SECTION_NAMES = SECTION_NAMES


def parse_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    matches = list(re.finditer(r'^##\s+(.+?)\s*$', text, flags=re.M))
    for idx, match in enumerate(matches):
        name = match.group(1).strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        raw = text[start:end].strip()
        cleaned_lines = []
        for line in raw.splitlines():
            stripped = line.strip()
            if re.match(r'^(必答|选答)。例[：:]', stripped):
                continue
            if stripped in {'必答', '选答'}:
                continue
            cleaned_lines.append(line)
        sections[name] = '\n'.join(cleaned_lines).strip()
    return sections


def list_or_placeholder(value: str, placeholder: str) -> str:
    value = value.strip()
    if not value:
        return f'- {placeholder}'
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    if not lines:
        return f'- {placeholder}'
    if len(lines) == 1 and not lines[0].startswith(('-', '*', '1.')):
        return f'- {lines[0]}'
    return '\n'.join(lines)


def paragraph_or_placeholder(value: str, placeholder: str) -> str:
    return value.strip() or placeholder


def write_role_files(root: Path, sections: dict[str, str]):
    world_model = root / 'role_workspace' / 'world_model' / 'ROLE_WORLD_MODEL_v1.md'
    boundary = root / 'role_workspace' / 'world_model' / 'ROLE_BOUNDARY_v1.md'
    role_profile = root / 'role_workspace' / 'world_model' / 'ROLE_PROFILE_v1.json'
    archive_dir = root / 'role_workspace' / 'archive'
    archive_dir.mkdir(parents=True, exist_ok=True)
    for path in [world_model, boundary, role_profile]:
        path.parent.mkdir(parents=True, exist_ok=True)

    user_name = paragraph_or_placeholder(sections.get('用户姓名', ''), '<fill user name>')
    role_name = paragraph_or_placeholder(sections.get('岗位名称', ''), '<fill role name>')
    responsibilities = list_or_placeholder(sections.get('主要职责', ''), '<fill responsibilities>')
    conversation_preference = paragraph_or_placeholder(sections.get('对话习惯', ''), 'Concise by default; expand details when needed.')
    not_allowed = (
        '- Public-facing claims\n'
        '- Pricing\n'
        '- Legal / compliance claims\n'
        '- Investor material\n'
        '- Media statements\n'
        '- Customer-facing promises\n'
        '- Official product capability claims'
    )
    review_needed = (
        '- Public-facing, pricing, legal/compliance, investor, media, customer promise, '
        'finance-sensitive, security-sensitive, or hiring-sensitive content'
    )

    role_profile.write_text(json.dumps({
        'schema_version': 'role_profile_v1',
        'employee_user_name': user_name,
        'employee_position': role_name,
        'conversation_preference': conversation_preference,
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    world_model.write_text(f"""# ROLE_WORLD_MODEL_v1

## User Name
{user_name}

## Role Name
{role_name}

## Current Understanding of LBAI
LBAI uses Cursor or Codex as project-local workspace runtimes, GitHub as durable artifact memory, and task folders to preserve traceable work.

## Role Goal
Support the role responsibilities below while keeping work traceable, reviewable, and safe to hand over.

## Main Responsibilities
{responsibilities}

## Conversation Preference
{conversation_preference}

## Task Execution Standard

Treat every `/lbai-execute-task` run as internal company work, not casual chat.

Default posture:
- Be objective, evidence-seeking, concise, and scoped to the role's real business need.
- Do not flatter, appease, or simply confirm the user's first framing.
- Use first-principles reasoning to identify the actual problem, constraints, desired outcome, and tradeoffs.
- Separate facts, assumptions, uncertainty, recommendations, and next steps.
- If the request is vague, inconsistent, or likely aimed at the wrong problem, say so directly and explain the missing decision or source material.
- Any success data, metrics, benchmarks, customer evidence, case results, market claims, performance claims, product capability claims, pricing claims, legal positions, approvals, or company commitments must have a traceable source in task inputs, approved references, or explicitly cited external sources when browsing is allowed.
- Do not fabricate numbers, success stories, rankings, conversion rates, growth rates, financial results, customer logos, adoption claims, or evidence-like details.
- Recommendations must be feasible under stated constraints. If feasibility cannot be verified, label the recommendation as an assumption and provide the validation step.
- When information is missing, name the exact missing materials, background, decisions, or source documents needed to finish responsibly.
- Follow the employee conversation preference unless it conflicts with accuracy, safety, or review requirements.

## Blocked / Unclear Items
See BLOCKED_ITEMS_v1.md.
""", encoding='utf-8')

    boundary.write_text(f"""# ROLE_BOUNDARY_v1

## Allowed

- Internal task planning
- Internal meeting notes
- Role artifacts
- Task ledgers
- Draft outputs for review
- Role-specific work within the responsibilities listed in ROLE_WORLD_MODEL_v1.md

## Role Responsibilities
{responsibilities}

## Not Allowed Without Review

{not_allowed}

## Review Needed

{review_needed}

## Sensitive Information Boundary

Do not write secrets, passwords, API keys, access tokens, legal privileged communication, confidential customer data, financial account information, or unnecessary personal data into repo artifacts.
""", encoding='utf-8')

    stamp = datetime.now().strftime('%Y_%m_%d_%H%M%S')
    archive = archive_dir / f'init_lbai_answers_{stamp}.md'
    archive_text = '# /lbai-init Answers Archive\n\n' + '\n\n'.join(
        f'## {name}\n{sections.get(name, "").strip() or "<empty>"}' for name in SECTION_NAMES
    ) + '\n'
    archive_redacted, _ = redact_sensitive(archive_text)
    archive.write_text(archive_redacted, encoding='utf-8')
    return [role_profile, world_model, boundary, archive]


def validate_init_enrichment(root: Path, data: dict) -> tuple[dict[str, str] | None, str | None]:
    err = validate_with_schema(root, data, 'init_enrichment_schema_v1.json')
    if err:
        return None, err
    sections = data.get('sections')
    if not isinstance(sections, dict):
        return None, 'sections must be an object'
    missing = [name for name in REQUIRED_SECTION_NAMES if not str(sections.get(name, '')).strip()]
    if missing:
        return None, 'missing required sections: ' + ', '.join(missing)
    cleaned = {name: str(sections.get(name, '')).strip() for name in SECTION_NAMES}
    return cleaned, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--print-questions', action='store_true')
    parser.add_argument('--enrichment', help='Path to AI-generated init enrichment JSON.')
    args = parser.parse_args()
    if args.print_questions:
        print(QUESTIONS)
        return 0

    if not args.enrichment:
        print('STATUS BLOCKED')
        print(f'reason: {BLOCKED_MESSAGE}')
        print('NEXT_STEP 在 Cursor 或 Codex 桌面 App 中完成岗位问答并生成 init enrichment JSON。')
        return 2

    root = workspace_root()
    enrichment_path = resolve_enrichment_path(root, args.enrichment)
    data, error = load_json_file(enrichment_path)
    if data is None:
        print('STATUS BLOCKED')
        print(f'reason: {error or BLOCKED_MESSAGE}')
        print('NEXT_STEP 请重新生成 init enrichment JSON 后重试。')
        return 1

    sections, validation_error = validate_init_enrichment(root, data)
    if sections is None:
        print('STATUS BLOCKED')
        print(f'reason: {validation_error}')
        print('NEXT_STEP 请补全必答 section 后重试。')
        return 1

    written = write_role_files(root, sections)
    archive_dir = root / 'role_workspace' / 'archive'
    archive_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y_%m_%d_%H%M%S')
    archive = archive_dir / f'init_enrichment_{stamp}.json'
    archive.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    written.append(archive)
    print('STATUS UPDATED')
    print('UPDATED_FILES')
    for path in written:
        print(f'- {path.relative_to(root)}')
    print('NEXT_STEP 可以开始使用 /lbai-new-task 建立正式任务。岗位变化时再次运行 /lbai-init。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
