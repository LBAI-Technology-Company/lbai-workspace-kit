"""Integration tests for new_task.py."""
from __future__ import annotations

import json

import pytest

from tests.helpers.tool_runner import enrichment_path, parse_task_folder, run_tool

pytestmark = pytest.mark.integration


class TestNewTask:
    def test_open_task_created(self, isolated_workspace, fixtures):
        enrich = enrichment_path(fixtures, 'task_intake_open.json')
        result = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
        assert result.returncode == 0, result.output
        assert 'TASK_FOLDER tasks/' in result.stdout
        assert 'STATUS OPEN' in result.stdout
        assert 'REVIEW_NEEDED false' in result.stdout

        task_rel = parse_task_folder(result.stdout)
        task_dir = isolated_workspace / task_rel
        assert (task_dir / 'task_scope.md').exists()
        assert (task_dir / 'task_slot.md').exists()
        assert (task_dir / 'task_ledger.md').exists()
        assert (task_dir / 'task_intake_enrichment.json').exists()
        scope = (task_dir / 'task_scope.md').read_text(encoding='utf-8')
        assert '整理用户反馈周报' in scope
        assert '## status\nOPEN' in scope
        assert '## known_information' in scope
        assert 'conversation_context' in scope
        assert '## recommended_inputs' in scope
        assert (task_dir / 'recommended_inputs.md').exists()
        assert not (task_dir / 'retrieved_context.md').exists()

    def test_blocked_task_with_missing_inputs(self, isolated_workspace, fixtures):
        enrich = enrichment_path(fixtures, 'task_intake_blocked.json')
        result = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
        assert result.returncode == 0, result.output
        assert 'STATUS BLOCKED' in result.stdout
        assert 'MISSING' in result.stdout
        assert '对话框补充' in result.stdout
        task_rel = parse_task_folder(result.stdout)
        assert (isolated_workspace / task_rel / 'missing_inputs.md').exists()
        assert (isolated_workspace / task_rel / 'recommended_inputs.md').exists()
        assert not (isolated_workspace / task_rel / 'retrieved_context.md').exists()

    def test_duplicate_task_name_gets_new_folder(self, isolated_workspace, fixtures):
        enrich = enrichment_path(fixtures, 'task_intake_open.json')
        first = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
        second = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
        assert first.returncode == 0, first.output
        assert second.returncode == 0, second.output
        assert parse_task_folder(first.stdout) != parse_task_folder(second.stdout)

    def test_review_task_creates_review_files(self, isolated_workspace, fixtures):
        enrich = enrichment_path(fixtures, 'task_intake_review.json')
        result = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
        assert result.returncode == 0, result.output
        assert 'REVIEW_NEEDED true' in result.stdout
        task_rel = parse_task_folder(result.stdout)
        task_dir = isolated_workspace / task_rel
        for name in ('overclaim_check.md', 'release_boundary_check.md', 'founder_review_needed.md'):
            assert (task_dir / name).exists(), name

    def test_sensitive_known_information_is_redacted_before_write(self, isolated_workspace, fixtures):
        data = json.loads(enrichment_path(fixtures, 'task_intake_open.json').read_text(encoding='utf-8'))
        data['known_information'] = [
            {
                'summary': '客户邮箱 test@example.com，电话 13800138000',
                'source_kind': 'conversation_context',
                'source_ref': 'employee said test@example.com',
            }
        ]
        enrich = isolated_workspace / 'sensitive_task_intake.json'
        enrich.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

        result = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
        assert result.returncode == 0, result.output
        assert 'SENSITIVE_CAPTURE_STATUS REDACTED' in result.stdout
        task_rel = parse_task_folder(result.stdout)
        task_dir = isolated_workspace / task_rel
        combined = '\n'.join(
            (task_dir / name).read_text(encoding='utf-8')
            for name in ('task_scope.md', 'task_ledger.md', 'task_intake_enrichment.json')
        )
        assert 'test@example.com' not in combined
        assert '13800138000' not in combined
        assert '[SENSITIVE INFORMATION REDACTED - USE APPROVED SECURE CHANNEL]' in combined

    def test_review_reasons_auto_enable_review_needed(self, isolated_workspace, fixtures):
        data = json.loads(enrichment_path(fixtures, 'task_intake_review.json').read_text(encoding='utf-8'))
        data['review_needed'] = False
        enrich = isolated_workspace / 'review_conflict.json'
        enrich.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

        result = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
        assert result.returncode == 0, result.output
        assert 'REVIEW_NEEDED true' in result.stdout

    def test_placeholder_review_reason_does_not_block_internal_task(self, isolated_workspace, fixtures):
        data = json.loads(enrichment_path(fixtures, 'task_intake_open.json').read_text(encoding='utf-8'))
        data['review_reasons'] = ['无']
        enrich = isolated_workspace / 'placeholder_review_reason.json'
        enrich.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

        result = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
        assert result.returncode == 0, result.output
        assert 'REVIEW_NEEDED false' in result.stdout

    def test_required_task_fields_must_not_be_blank(self, isolated_workspace, fixtures):
        data = json.loads(enrichment_path(fixtures, 'task_intake_open.json').read_text(encoding='utf-8'))
        data['goal'] = '   '
        data['expected_output'] = '   '
        data['completion_conditions'] = []
        enrich = isolated_workspace / 'blank_required_fields.json'
        enrich.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

        result = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
        assert result.returncode == 2
        assert 'validation failed' in result.stdout or 'must be non-empty' in result.stdout
        assert not list((isolated_workspace / 'tasks').glob('*/task_scope.md'))

    def test_positional_description_must_match_enrichment(self, isolated_workspace, fixtures):
        enrich = enrichment_path(fixtures, 'task_intake_open.json')
        result = run_tool(isolated_workspace, 'new_task.py', '另一个任务', '--enrichment', str(enrich))
        assert result.returncode == 2
        assert 'does not match enrichment task_description' in result.stdout
        assert not list((isolated_workspace / 'tasks').glob('*/task_scope.md'))

    def test_company_process_writing_requires_source_and_audience(self, isolated_workspace, fixtures):
        data = json.loads(enrichment_path(fixtures, 'task_intake_open.json').read_text(encoding='utf-8'))
        data.update({
            'task_description': '写一篇短文介绍我公司的工作方法流程',
            'goal': '写一篇介绍公司工作方法流程的短文',
            'expected_output': 'task_output.md 包含一篇短文',
            'known_information': [
                {
                    'summary': '员工想写一篇短文介绍公司的工作方法流程',
                    'source_kind': 'conversation_context',
                    'source_ref': 'employee task request',
                }
            ],
            'missing_inputs': [],
            'recommended_inputs': ['受众是内部同事，还是可能对外发布'],
            'status': 'OPEN',
        })
        enrich = isolated_workspace / 'company_process_writing.json'
        enrich.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

        result = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
        assert result.returncode == 0, result.output
        assert 'STATUS BLOCKED' in result.stdout
        assert 'backend_knowledge_search_used:' not in result.stdout
        assert 'backend 查询结果' not in result.stdout
        assert '请补充公司工作方法/流程的来源材料或关键要点' in result.stdout
        assert '请说明这篇短文的受众和用途' in result.stdout
        task_rel = parse_task_folder(result.stdout)
        task_dir = isolated_workspace / task_rel
        missing = (task_dir / 'missing_inputs.md').read_text(encoding='utf-8')
        assert '请补充公司工作方法/流程的来源材料或关键要点' in missing
        assert '请说明这篇短文的受众和用途' in missing

    def test_specific_missing_inputs_skip_generic_company_source(self, isolated_workspace, fixtures):
        data = json.loads(enrichment_path(fixtures, 'task_intake_open.json').read_text(encoding='utf-8'))
        data.update({
            'task_description': '写一份客户成功案例，突出 ROI，给销售团队下周培训用',
            'goal': '基于可验证客户数据撰写内部培训用成功案例摘要',
            'expected_output': 'task_output.md：客户背景、问题、方案、可引用 ROI 数据与培训要点',
            'known_information': [
                {
                    'summary': '输出用于销售团队内部培训',
                    'source_kind': 'conversation_context',
                    'source_ref': 'manager request',
                }
            ],
            'missing_inputs': [
                '客户授权或可引用的脱敏案例材料',
                'ROI 或成效数据的来源与计算口径',
                '需突出的产品/方案名称与交付范围',
            ],
            'recommended_inputs': ['销售负责人确认的培训侧重点'],
            'status': 'BLOCKED',
            'review_needed': True,
            'review_reasons': ['涉及客户成效与 ROI 表述，需来源支撑'],
            'completion_conditions': [
                'task_output.md 已创建',
                'ROI 数据可追溯到来源',
            ],
        })
        enrich = isolated_workspace / 'customer_case_blocked.json'
        enrich.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

        result = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
        assert result.returncode == 0, result.output
        assert 'STATUS BLOCKED' in result.stdout
        assert '请补充公司工作方法/流程的来源材料或关键要点' not in result.stdout
        assert '客户授权或可引用的脱敏案例材料' in result.stdout
        assert 'ROI 或成效数据的来源与计算口径' in result.stdout

    def test_press_release_blocked_without_generic_company_source(self, isolated_workspace, fixtures):
        data = json.loads(enrichment_path(fixtures, 'task_intake_open.json').read_text(encoding='utf-8'))
        data.update({
            'task_description': '起草对外新闻稿，宣布新产品合作，下周可能发媒体',
            'goal': '在获得审批与可发布事实前，整理新闻稿任务边界与待确认事项',
            'expected_output': 'task_output.md：新闻稿大纲、待确认事实清单、审批提醒',
            'known_information': [
                {
                    'summary': '公关同步会：合作方名称与范围尚未经法务确认',
                    'source_kind': 'conversation_context',
                    'source_ref': '公关同步会会议记录',
                }
            ],
            'missing_inputs': [
                '经法务确认的合作事实与可对外表述范围',
                '公关/法务审批状态或发布窗口',
                '可引用的官方产品与合作信息来源',
            ],
            'status': 'BLOCKED',
            'review_needed': True,
            'review_reasons': ['对外媒体发布'],
            'completion_conditions': ['task_output.md 已创建'],
        })
        enrich = isolated_workspace / 'press_release_blocked.json'
        enrich.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

        result = run_tool(isolated_workspace, 'new_task.py', '--enrichment', str(enrich))
        assert result.returncode == 0, result.output
        assert 'STATUS BLOCKED' in result.stdout
        assert 'REVIEW_NEEDED true' in result.stdout
        assert '请补充公司工作方法/流程的来源材料或关键要点' not in result.stdout
        assert '经法务确认的合作事实与可对外表述范围' in result.stdout
