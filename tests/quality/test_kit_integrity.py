"""Quality checks: shipped prompts, schemas, and workspace bootstrap."""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

from tests.helpers.tool_runner import parse_task_folder, run_tool
from tests.helpers.workspace import kit_root, template_root

pytestmark = pytest.mark.quality

PROMPTS = template_root() / 'lbai_system' / 'prompts'
SCHEMAS = template_root() / 'lbai_system' / 'schemas'
CONTRACT = template_root() / 'lbai_system' / 'runner_contracts' / 'lbai_command_contract_v1.md'

EXPECTED_PROMPTS = {
    'evidence_enrichment_prompt_v1.md': 'evidence_enrichment_v1',
    'backend_search_query_plan_prompt_v1.md': 'backend_search_query_plan_v1',
    'task_intake_enrichment_prompt_v1.md': 'task_intake_enrichment_v1',
    'finish_review_enrichment_prompt_v1.md': 'finish_review_enrichment_v1',
    'init_enrichment_prompt_v1.md': 'init_enrichment_v1',
    'execute_task_plan_prompt_v1.md': None,
}

EXPECTED_SCHEMAS = [
    'evidence_enrichment_schema_v1.json',
    'knowledge_search_response_schema_v1.json',
    'backend_search_query_plan_schema_v1.json',
    'task_intake_enrichment_schema_v1.json',
    'finish_review_enrichment_schema_v1.json',
    'init_enrichment_schema_v1.json',
]


class TestPromptSchemaInventory:
    @pytest.mark.parametrize('filename,version', list(EXPECTED_PROMPTS.items()))
    def test_prompts_exist(self, filename, version):
        path = PROMPTS / filename
        assert path.exists(), f'missing prompt: {path}'
        text = path.read_text(encoding='utf-8')
        assert len(text) > 200, f'prompt too short: {filename}'
        if version:
            assert version in text, f'{filename} should mention {version}'

    @pytest.mark.parametrize('filename', EXPECTED_SCHEMAS)
    def test_schemas_exist_and_valid_json(self, filename):
        path = SCHEMAS / filename
        assert path.exists()
        data = json.loads(path.read_text(encoding='utf-8'))
        assert 'schema_version' in str(data) or 'properties' in data

    def test_runner_contract_mentions_enrichment(self):
        text = CONTRACT.read_text(encoding='utf-8')
        for token in (
            'evidence_enrichment',
            'backend_search_query_plan',
            'task_intake_enrichment',
            'finish_review_enrichment',
            'init_enrichment',
            '--enrichment',
        ):
            assert token in text, f'contract missing {token}'

    def test_template_has_no_runtime_cache_files(self):
        offenders = [
            path.relative_to(template_root()).as_posix()
            for path in template_root().rglob('*')
            if path.name == '__pycache__' or path.suffix == '.pyc' or path.name == '.DS_Store'
        ]
        assert not offenders, f'template contains runtime/cache files: {offenders}'

    def test_employee_search_docs_are_backend_only(self):
        paths = [
            template_root() / 'README.md',
            template_root() / 'lbai_system/cursor/commands/lbai-search-artifacts.md',
            template_root() / '.cursor/commands/lbai-search-artifacts.md',
            template_root() / 'lbai_system/cursor/skills/lbai-search-artifacts/SKILL.md',
            template_root() / '.agents/skills/lbai-search-artifacts/SKILL.md',
        ]
        forbidden = ('--print-catalog', 'search_enrichment', 'local_fallback')
        for path in paths:
            text = path.read_text(encoding='utf-8')
            assert not any(token in text for token in forbidden), f'{path} mentions old local search path'

    def test_cursor_commands_present(self):
        cursor_cmds = template_root() / '.cursor' / 'commands'
        expected = {
            'lbai-add-evidence.md',
            'lbai-search-artifacts.md',
            'lbai-role-setup.md',
            'lbai-new-task.md',
            'lbai-execute-task.md',
            'lbai-finish-task.md',
            'lbai-update-kit.md',
            'lbai-self-iterate.md',
        }
        existing = {p.name for p in cursor_cmds.glob('*.md')}
        missing = expected - existing
        assert not missing, f'missing cursor commands: {missing}'

    def test_execute_task_adapter_mentions_prepare_tool(self):
        for rel in (
            '.cursor/commands/lbai-execute-task.md',
            'lbai_system/cursor/commands/lbai-execute-task.md',
            '.agents/skills/lbai-execute-task/SKILL.md',
            'lbai_system/cursor/skills/lbai-execute-task/SKILL.md',
        ):
            text = (template_root() / rel).read_text(encoding='utf-8')
            assert 'prepare_execute_task.py' in text, f'{rel} should call prepare_execute_task.py'

    def test_pipe_install_does_not_misdetect_current_directory(self):
        text = (kit_root() / 'install.sh').read_text(encoding='utf-8')
        assert 'detect_script_dir()' in text
        assert 'SCRIPT_DIR="$(detect_script_dir || true)"' in text
        assert 'SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"' not in text

    def test_install_launchers_pin_lbai_home_and_runtime_dependencies(self):
        install_sh = (kit_root() / 'install.sh').read_text(encoding='utf-8')
        install_ps1 = (kit_root() / 'install.ps1').read_text(encoding='utf-8')

        assert 'VENV_DIR="$LBAI_HOME/venv"' in install_sh
        assert 'export LBAI_HOME="$LBAI_HOME"' in install_sh
        assert 'exec "$RUNTIME_PYTHON" -m lbai.cli "\\$@"' in install_sh
        assert 'Warning: could not install jsonschema' not in install_sh
        assert 'fail "could not install Python dependencies' in install_sh
        assert 'RUNTIME_PYTHON="$(create_python_runtime)"' not in install_sh
        assert 'RUNTIME_PYTHON="$VENV_DIR/bin/python"' in install_sh
        assert 'pip install --disable-pip-version-check -r "$INSTALL_DIR/lbai_core/requirements.txt" >/dev/null' in install_sh

        assert 'ensure_codex_cli' in install_sh
        assert 'ensure_codex_plugin' in install_sh
        assert '[步骤' in install_sh
        assert 'ensure_shared_workspace' in install_sh
        assert 'Write-Step' in install_ps1
        assert 'workspace ensure' in install_sh
        assert 'print_install_summary' in install_sh
        assert '安装结果汇总' in install_sh
        assert 'bootstrap_latest_installer' in install_sh
        assert 'INSTALLER_VERSION' in install_sh
        assert 'install_codex_via_github_binary' in install_sh
        assert 'install_codex_via_npm' in install_sh
        assert 'releases/latest/download/install.sh' in install_sh
        assert 'https://chatgpt.com/codex/install.sh' in install_sh
        assert 'plugin marketplace add' in install_sh
        assert 'lbai-workspace@$CODEX_PLUGIN_MARKETPLACE' in install_sh
        assert 'LBAI_SKIP_CODEX_CLI' in install_sh
        assert 'LBAI_SKIP_CODEX_PLUGIN' in install_sh

        assert '$VenvDir = Join-Path $LbaiHome "venv"' in install_ps1
        assert 'set "LBAI_HOME=$LbaiHome"' in install_ps1
        assert '"$RuntimePython" -m lbai.cli %*' in install_ps1
        assert 'Warning: could not install jsonschema' not in install_ps1
        assert 'Fail "could not install Python dependencies' in install_ps1

        assert 'Ensure-CodexCli' in install_ps1
        assert 'Ensure-CodexPlugin' in install_ps1
        assert 'Ensure-SharedWorkspace' in install_ps1
        assert 'Write-InstallSummary' in install_ps1
        assert '安装结果汇总' in install_ps1
        assert 'Bootstrap-LatestInstaller' in install_ps1
        assert 'InstallerVersion' in install_ps1
        assert 'Install-CodexViaGithubBinary' in install_ps1
        assert 'Install-CodexViaNpm' in install_ps1
        assert 'https://chatgpt.com/codex/install.ps1' in install_ps1
        assert 'plugin marketplace add' in install_ps1
        assert 'lbai-workspace@$CodexPluginMarketplace' in install_ps1
        assert 'LBAI_SKIP_CODEX_CLI' in install_ps1
        assert 'LBAI_SKIP_CODEX_PLUGIN' in install_ps1

    def test_update_kit_prefers_nested_workspace_template(self, tmp_path):
        tools_dir = template_root() / 'lbai_system' / 'tools'
        sys.path.insert(0, str(tools_dir))
        try:
            spec = importlib.util.spec_from_file_location('update_kit_for_test', tools_dir / 'update_kit.py')
            assert spec and spec.loader
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        finally:
            sys.path.remove(str(tools_dir))

        source_root = tmp_path / 'checkout'
        (source_root / '.cursor').mkdir(parents=True)
        (source_root / 'lbai_system').mkdir()
        (source_root / 'lbai_core' / 'lbai').mkdir(parents=True)
        (source_root / 'lbai_core' / 'lbai' / 'cli.py').write_text('# test cli\n', encoding='utf-8')
        (source_root / 'VERSION').write_text('0.0.0-test\n', encoding='utf-8')
        (source_root / 'workspace_template' / '.cursor').mkdir(parents=True)
        (source_root / 'workspace_template' / 'lbai_system').mkdir()

        assert module.kit_template_root(source_root) == source_root / 'workspace_template'
        assert module.package_root_from_source(source_root / 'workspace_template') == source_root

    def test_managed_git_stage_forces_ignored_paths(self):
        text = (template_root() / 'lbai_system' / 'tools' / 'update_kit.py').read_text(encoding='utf-8')
        cli_text = (kit_root() / 'lbai_core' / 'lbai' / 'cli.py').read_text(encoding='utf-8')
        assert "['add', '-A', '-f', '--', *paths]" in text
        assert "['git', 'add', '-f', '--', *stage_paths]" in cli_text


class TestBootstrapInIsolatedWorkspace:
    def test_codex_adapter_passes(self, isolated_workspace):
        result = run_tool(isolated_workspace, 'check_codex_adapter.py')
        assert result.returncode == 0, result.output
        assert 'STATUS OK' in result.stdout

    def test_cursor_commands_check_passes(self, isolated_workspace):
        result = run_tool(isolated_workspace, 'check_cursor_commands.py')
        assert result.returncode == 0, result.output

    def test_hygiene_check_blocks_incomplete_task(self, isolated_workspace, fixtures):
        enrich = json.loads((Path(__file__).parents[1] / 'fixtures/enrichments/task_intake_open.json').read_text())
        created = run_tool(
            isolated_workspace,
            'new_task.py',
            '--enrichment',
            str(Path(__file__).parents[1] / 'fixtures/enrichments/task_intake_open.json'),
        )
        task_rel = parse_task_folder(created.stdout)
        result = run_tool(isolated_workspace, 'hygiene_check.py', task_rel)
        assert result.returncode != 0
        assert 'commit_readiness: BLOCKED' in result.stdout

    def test_hygiene_check_ready_with_output(self, isolated_workspace, fixtures):
        created = run_tool(
            isolated_workspace,
            'new_task.py',
            '--enrichment',
            str(Path(__file__).parents[1] / 'fixtures/enrichments/task_intake_open.json'),
        )
        task_rel = parse_task_folder(created.stdout)
        (isolated_workspace / task_rel / 'task_output.md').write_text('# out\n', encoding='utf-8')
        result = run_tool(isolated_workspace, 'hygiene_check.py', task_rel)
        assert 'commit_readiness: READY' in result.stdout
        assert '推荐文件（非阻断）' in result.stdout
        assert 'execution_plan.md' in result.stdout
