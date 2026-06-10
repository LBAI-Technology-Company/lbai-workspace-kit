#!/usr/bin/env python3
import argparse
import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True

from task_utils import LEADER_REVIEW_REMINDER, classify_risk, today_slugged_task_dir, workspace_root, write_if_missing


ROOT = workspace_root()


def likely_missing_inputs(description: str) -> list[str]:
    low = description.lower()
    missing = []
    if any(k in low for k in ['会议', 'meeting', '纪要', 'action items']):
        missing.append('会议全文或会议笔记')
    if any(k in low for k in ['官网', '文案', 'homepage', 'website', '产品说明']):
        missing.append('产品说明、原始草稿或 approved source')
    if any(k in low for k in ['用户反馈', '客户反馈', 'feedback']):
        missing.append('用户反馈原文，敏感信息会自动脱敏')
    if any(k in low for k in ['周报', 'weekly']):
        missing.append('本周工作材料或要点')
    return missing

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('task_description', nargs='*')
    parser.add_argument('--owner', default='<owner>')
    args = parser.parse_args()
    task_description = ' '.join(args.task_description).strip()
    if not task_description:
        print('TASK_FOLDER unresolved')
        print('STATUS BLOCKED')
        print('MISSING task_description')
        print('NEXT_STEP 请补充任务描述，例如：/lbai-new-task 整理今天市场会议纪要和 action items')
        return 2

    task_dir = today_slugged_task_dir(ROOT, task_description)
    task_id = task_dir.name
    risk_level, review_needed, review_reason = classify_risk(task_description)
    missing_inputs = likely_missing_inputs(task_description)
    status = 'BLOCKED' if missing_inputs else 'OPEN'

    write_if_missing(task_dir / 'task_scope.md', f"""# Task Scope

## task_id
{task_id}

## task_name
{task_description}

## goal
{task_description}

## owner
{args.owner}

## inputs_available
- Task description from user chat

## inputs_missing
{chr(10).join(f'- {item}' for item in missing_inputs) if missing_inputs else '- None'}

## expected_output
<define expected output>

## risk_level
{risk_level}

## review_needed
{str(review_needed).lower()}

## review_reason
{review_reason}

## leader_review_reminder
{LEADER_REVIEW_REMINDER if review_needed else 'None'}

## sensitive_info_expected
false

## status
{status}
""", ROOT)

    write_if_missing(task_dir / 'task_slot.md', f"""# Task Slot

## task_id
{task_id}

## allowed_sources
- This task folder
- Linked evidence saved under role_workspace/knowledge/evidence/
- Legacy task-local input_*.md when present
- Role world model files under role_workspace/world_model/
- Company guardrails under lbai_system/company_guardrails/

## forbidden_actions
- Do not invent missing source facts
- Do not fabricate data, metrics, benchmarks, customer evidence, case results, product capabilities, pricing, legal positions, approvals, or company commitments
- Do not write sensitive information
- Do not generate unauthorized public claims
- Do not mark review-required work as approved

## execution_standard
- Treat the output as internal company work, not casual chat
- Separate facts, assumptions, uncertainty, recommendations, and next steps
- Cite or name the source for success data, market claims, performance claims, and customer claims
- If feasibility is not verified, label the recommendation as an assumption and provide the validation step
- If required information is missing, state the exact missing material or decision

## output_path
{task_dir.relative_to(ROOT)}/task_output.md

## required_outputs
- task_output.md
- task_ledger.md

## completion_conditions
- Required input exists
- task_output.md generated
- /lbai-finish-task updates ledgers and commit readiness
""", ROOT)

    write_if_missing(task_dir / 'task_ledger.md', f"""# Task Ledger

## task_id
{task_id}

## date
{date.today().isoformat()}

## task_name
{task_description}

## task_goal
{task_description}

## source_artifacts
- Task description from user chat

## agents_or_tools_used
- /lbai-new-task
- lbai_system/tools/new_task.py

## outputs_created
- task_scope.md
- task_slot.md
- task_ledger.md

## status
{status}

## blocked_reason
{'; '.join(missing_inputs) if missing_inputs else 'None'}

## owner
{args.owner}

## review_needed
{str(review_needed).lower()}

## leader_review_reminder
{LEADER_REVIEW_REMINDER if review_needed else 'None'}

## commit_readiness
UNKNOWN

## git_status
NOT_SYNCED

## next_dependency
{'Missing input from employee via /lbai-add-evidence' if missing_inputs else 'Run /lbai-execute-task'}

## next_step
{f'请直接粘贴缺失输入，工作区助手应使用 /lbai-add-evidence {task_dir.relative_to(ROOT)} 保存为 evidence 并更新缺口状态。' if missing_inputs else f'Run /lbai-execute-task {task_dir.relative_to(ROOT)}.'}
""", ROOT)

    if missing_inputs:
        write_if_missing(task_dir / 'missing_inputs.md', "# Missing Inputs\n\n" + "\n".join(f"- {item}" for item in missing_inputs) + "\n", ROOT)

    if review_needed:
        write_if_missing(task_dir / 'overclaim_check.md', "# Overclaim Check\n\nReview required. Do not add unapproved public, pricing, legal, investor, media, product capability, or customer promise claims.\n", ROOT)
        write_if_missing(task_dir / 'release_boundary_check.md', "# Release Boundary Check\n\nThis task is not approved for public release until founder or role owner review is complete.\n", ROOT)
        write_if_missing(task_dir / 'founder_review_needed.md', "# Founder Review Reminder\n\nRemind the employee: leader review is required before external release. This workflow does not block execution or finish.\n", ROOT)

    print(f"TASK_FOLDER {task_dir.relative_to(ROOT)}")
    print(f"STATUS {status}")
    print(f"REVIEW_NEEDED {str(review_needed).lower()}")
    if review_needed:
        print(f"leader_review_reminder: {LEADER_REVIEW_REMINDER}")
    if missing_inputs:
        print("MISSING " + "; ".join(missing_inputs))
        print(f"NEXT_STEP 请直接粘贴缺失输入，工作区助手应使用 /lbai-add-evidence {task_dir.relative_to(ROOT)} 保存为 evidence 并更新缺口状态。")
    else:
        print(f"NEXT_STEP /lbai-execute-task {task_dir.relative_to(ROOT)}")

if __name__ == '__main__':
    raise SystemExit(main() or 0)
