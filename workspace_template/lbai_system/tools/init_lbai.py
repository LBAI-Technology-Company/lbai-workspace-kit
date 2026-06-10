#!/usr/bin/env python3
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True

from task_utils import redact_sensitive, workspace_root


QUESTIONS = """# /lbai-init 岗位设定问题

请直接复制下面问题并填写。可以简单写，不需要正式措辞。

说明：
- 标注“必答”的问题请尽量填写，工作区助手会根据这些内容更新岗位设定。
- 标注“选答”的问题可以空着，后续岗位变化时也可以再次运行 `/lbai-init` 补充。

## 岗位名称
必答。例：办公室文职 / 内容助理 / 市场运营

## 主要职责
必答。例：整理会议纪要、汇总用户反馈、编写内部周报

## 常见任务
必答。例：会议纪要、周报、用户反馈总结、资料归档

## 常用资料来源
必答。例：会议记录、Teams、官网草稿、表格、客户反馈

## 常见输出
必答。例：会议纪要、task_output.md、周报、问题清单

## 不能自行决定的事项
必答。例：对外发布内容、价格、法律相关表述、客户承诺

## 需要负责人 review 的情况
必答。例：官网文案、媒体材料、客户承诺、投资人材料

## 当前 1-2 周优先级
必答。例：完成会议纪要流程测试、整理用户反馈分类

## 常协作的人或团队
选答。例：市场团队、产品团队、负责人姓名

## 其他补充
选答。例：希望输出语言简单清楚，避免太技术化
"""


SECTION_NAMES = [
    '岗位名称',
    '主要职责',
    '常见任务',
    '常用资料来源',
    '常见输出',
    '不能自行决定的事项',
    '需要负责人 review 的情况',
    '当前 1-2 周优先级',
    '常协作的人或团队',
    '其他补充',
]

REQUIRED_SECTION_NAMES = SECTION_NAMES[:8]
OPTIONAL_SECTION_NAMES = SECTION_NAMES[8:]


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
    priorities = root / 'role_workspace' / 'world_model' / 'ROLE_CURRENT_PRIORITIES_v1.md'
    archive_dir = root / 'role_workspace' / 'archive'
    archive_dir.mkdir(parents=True, exist_ok=True)
    for path in [world_model, boundary, priorities]:
        path.parent.mkdir(parents=True, exist_ok=True)

    role_name = paragraph_or_placeholder(sections.get('岗位名称', ''), '<fill role name>')
    responsibilities = list_or_placeholder(sections.get('主要职责', ''), '<fill responsibilities>')
    common_tasks = list_or_placeholder(sections.get('常见任务', ''), '<fill common tasks>')
    sources = list_or_placeholder(sections.get('常用资料来源', ''), '<fill common sources>')
    outputs = list_or_placeholder(sections.get('常见输出', ''), '<fill common outputs>')
    not_allowed = list_or_placeholder(sections.get('不能自行决定的事项', ''), 'Public-facing claims, pricing, legal/compliance, investor material, media statements, customer-facing promises, and official product capability claims')
    review_needed = list_or_placeholder(sections.get('需要负责人 review 的情况', ''), 'Public-facing, pricing, legal/compliance, investor, media, customer promise, finance-sensitive, security-sensitive, or hiring-sensitive content')
    current_priorities = list_or_placeholder(sections.get('当前 1-2 周优先级', ''), 'Use LBAI three-command task lifecycle.')
    collaborators = list_or_placeholder(sections.get('常协作的人或团队', ''), '<fill collaborators>')
    notes = paragraph_or_placeholder(sections.get('其他补充', ''), 'None.')

    world_model.write_text(f"""# ROLE_WORLD_MODEL_v1

## Role Name
{role_name}

## Current Understanding of LBAI
LBAI uses Cursor or Codex as project-local workspace runtimes, GitHub as durable artifact memory, and task folders to preserve traceable work.

## Role Goal
Support the role responsibilities below while keeping work traceable, reviewable, and safe to hand over.

## Main Responsibilities
{responsibilities}

## Common Tasks
{common_tasks}

## Common Sources
{sources}

## Common Outputs
{outputs}

## Collaborators
{collaborators}

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

## Current Priorities
See ROLE_CURRENT_PRIORITIES_v1.md.

## Blocked / Unclear Items
See BLOCKED_ITEMS_v1.md.

## Notes
{notes}
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

    priorities.write_text(f"""# ROLE_CURRENT_PRIORITIES_v1

## Current Priorities

{current_priorities}

## Operating Habits

1. Use `/lbai-new-task`, `/lbai-execute-task`, and `/lbai-finish-task` for formal work.
2. Keep important work in `tasks/` artifacts.
3. Update task ledger through `/lbai-finish-task`.
4. Use `/lbai-init` again when the role, responsibilities, review boundary, sources, or priorities change.
""", encoding='utf-8')

    stamp = datetime.now().strftime('%Y_%m_%d_%H%M%S')
    archive = archive_dir / f'init_lbai_answers_{stamp}.md'
    archive_text = '# /lbai-init Answers Archive\n\n' + '\n\n'.join(
        f'## {name}\n{sections.get(name, "").strip() or "<empty>"}' for name in SECTION_NAMES
    ) + '\n'
    archive_redacted, _ = redact_sensitive(archive_text)
    archive.write_text(archive_redacted, encoding='utf-8')
    return [world_model, boundary, priorities, archive]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--print-questions', action='store_true')
    args = parser.parse_args()
    if args.print_questions:
        print(QUESTIONS)
        return 0

    text = __import__('sys').stdin.read().strip()
    if not text:
        print(QUESTIONS)
        return 2

    root = workspace_root()
    sections = parse_sections(text)
    missing = [name for name in REQUIRED_SECTION_NAMES if not sections.get(name, '').strip()]
    if missing:
        print('STATUS BLOCKED')
        print('MISSING_REQUIRED_FIELDS')
        for item in missing:
            print(f'- {item}')
        print('OPTIONAL_FIELDS')
        for item in OPTIONAL_SECTION_NAMES:
            print(f'- {item}')
        print('NEXT_STEP 请补充以上必答问题后再次运行 /lbai-init。选答问题可以空着。')
        return 1

    written = write_role_files(root, sections)
    print('STATUS UPDATED')
    print('UPDATED_FILES')
    for path in written:
        print(f'- {path.relative_to(root)}')
    print('NEXT_STEP 可以开始使用 /lbai-new-task 建立正式任务。岗位变化时再次运行 /lbai-init。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
