from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[2] / 'workspace_template' / 'lbai_system' / 'tools'
sys.path.insert(0, str(TOOLS))

from add_evidence import infer_meeting_occurred_at, normalize_meeting_enrichment  # noqa: E402
from new_task import apply_intake_guardrails, has_specific_source_gaps  # noqa: E402


def test_infer_meeting_occurred_at_from_chinese_header():
    content = '【Mock 会议记录】\n时间：2026-06-15 10:00-11:00\n参会：产品部'
    assert infer_meeting_occurred_at(content) == '2026-06-15'


def test_normalize_meeting_enrichment_fills_unknown_date():
    enrichment = {
        'source_type': 'meeting_note',
        'source_occurred_at': 'unknown',
        'title': '产品周会',
    }
    content = '时间：2026-06-15 10:00\n决议：输出技术方案'
    normalized = normalize_meeting_enrichment(enrichment, content)
    assert normalized['source_occurred_at'] == '2026-06-15'


def test_normalize_meeting_enrichment_keeps_existing_date():
    enrichment = {
        'source_type': 'meeting_note',
        'source_occurred_at': '2026-05-01',
        'title': '产品周会',
    }
    normalized = normalize_meeting_enrichment(enrichment, '时间：2026-06-15')
    assert normalized['source_occurred_at'] == '2026-05-01'


def test_has_specific_source_gaps_detects_customer_case_gaps():
    missing = [
        '客户授权或可引用的脱敏案例材料',
        'ROI 或成效数据的来源与计算口径',
    ]
    assert has_specific_source_gaps(missing) is True


def test_apply_intake_guardrails_skips_generic_when_specific_gaps_exist():
    data = {
        'task_description': '写一份客户成功案例突出 ROI，供销售培训使用',
        'goal': '基于可验证客户数据撰写内部销售培训用成功案例摘要',
        'expected_output': 'task_output.md',
        'known_information': [
            {
                'summary': '输出用于销售团队内部培训',
                'source_kind': 'conversation_context',
            }
        ],
        'missing_inputs': [
            '客户授权或可引用的脱敏案例材料',
            'ROI 或成效数据的来源与计算口径',
        ],
        'status': 'BLOCKED',
    }
    guarded = apply_intake_guardrails(data)
    assert '请补充公司工作方法/流程的来源材料或关键要点。' not in guarded['missing_inputs']


def test_apply_intake_guardrails_keeps_generic_for_company_process_without_gaps():
    data = {
        'task_description': '写一篇短文介绍我公司的工作方法流程',
        'goal': '写一篇介绍公司工作方法流程的短文',
        'expected_output': 'task_output.md 包含一篇短文',
        'known_information': [
            {
                'summary': '员工想写一篇短文介绍公司的工作方法流程',
                'source_kind': 'conversation_context',
            }
        ],
        'missing_inputs': [],
        'status': 'OPEN',
    }
    guarded = apply_intake_guardrails(data)
    assert '请补充公司工作方法/流程的来源材料或关键要点。' in guarded['missing_inputs']
