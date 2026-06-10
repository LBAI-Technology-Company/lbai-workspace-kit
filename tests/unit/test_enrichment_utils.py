"""Unit tests for shared helper modules."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2] / 'workspace_template' / 'lbai_system' / 'tools'
sys.path.insert(0, str(TOOLS))

from enrichment_utils import load_json_file, require_version, resolve_enrichment_path  # noqa: E402
from task_utils import redact_sensitive, review_required, slugify  # noqa: E402


pytestmark = pytest.mark.unit


class TestEnrichmentUtils:
    def test_load_json_file_missing(self, tmp_path):
        data, err = load_json_file(tmp_path / 'missing.json')
        assert data is None
        assert 'not found' in err

    def test_load_json_file_invalid_json(self, tmp_path):
        path = tmp_path / 'bad.json'
        path.write_text('{not json', encoding='utf-8')
        data, err = load_json_file(path)
        assert data is None
        assert 'parse error' in err

    def test_load_json_file_not_object(self, tmp_path):
        path = tmp_path / 'array.json'
        path.write_text('[]', encoding='utf-8')
        data, err = load_json_file(path)
        assert data is None
        assert 'JSON object' in err

    def test_require_version_match(self):
        assert require_version({'schema_version': 'evidence_enrichment_v1'}, 'evidence_enrichment_v1') is None

    def test_require_version_mismatch(self):
        err = require_version({'schema_version': 'v0'}, 'evidence_enrichment_v1')
        assert err and 'schema_version' in err

    def test_resolve_enrichment_path_relative(self, tmp_path):
        root = tmp_path / 'ws'
        root.mkdir()
        rel = root / 'data.json'
        rel.write_text('{}', encoding='utf-8')
        resolved = resolve_enrichment_path(root, 'data.json')
        assert resolved == rel.resolve()

    def test_validate_with_schema_valid_fixture(self, tmp_path):
        from enrichment_utils import validate_with_schema

        root = tmp_path / 'ws'
        schemas = Path(__file__).resolve().parents[2] / 'workspace_template' / 'lbai_system' / 'schemas'
        (root / 'lbai_system' / 'schemas').mkdir(parents=True)
        schema_name = 'init_enrichment_schema_v1.json'
        (root / 'lbai_system' / 'schemas' / schema_name).write_text(
            (schemas / schema_name).read_text(encoding='utf-8'),
            encoding='utf-8',
        )
        fixture = Path(__file__).resolve().parents[1] / 'fixtures' / 'enrichments' / 'init_valid.json'
        data = json.loads(fixture.read_text(encoding='utf-8'))
        assert validate_with_schema(root, data, schema_name) is None

    def test_validate_with_schema_rejects_bad_version(self, tmp_path):
        from enrichment_utils import validate_with_schema

        root = tmp_path / 'ws'
        schemas = Path(__file__).resolve().parents[2] / 'workspace_template' / 'lbai_system' / 'schemas'
        (root / 'lbai_system' / 'schemas').mkdir(parents=True)
        schema_name = 'init_enrichment_schema_v1.json'
        (root / 'lbai_system' / 'schemas' / schema_name).write_text(
            (schemas / schema_name).read_text(encoding='utf-8'),
            encoding='utf-8',
        )
        err = validate_with_schema(root, {'schema_version': 'wrong'}, schema_name)
        assert err and 'schema validation failed' in err

    def test_slugify_ascii(self):
        assert slugify('Hello World!') == 'hello_world'

    def test_slugify_cjk(self):
        assert '整理' in slugify('整理用户反馈')

class TestReviewRequired:
    def _task_dir(self, tmp_path, scope: str, ledger: str = '# Task Ledger\n'):
        root = tmp_path / 'ws'
        task = root / 'tasks' / '2026_06_10_sample'
        task.mkdir(parents=True)
        (task / 'task_scope.md').write_text(scope, encoding='utf-8')
        (task / 'task_ledger.md').write_text(ledger, encoding='utf-8')
        return task

    def test_true_when_review_needed_in_scope(self, tmp_path):
        task = self._task_dir(tmp_path, '## review_needed\ntrue\n')
        assert review_required(task) is True

    def test_false_when_review_needed_false(self, tmp_path):
        task = self._task_dir(tmp_path, '## review_needed\nfalse\n')
        assert review_required(task) is False

    def test_true_when_risk_level_high(self, tmp_path):
        task = self._task_dir(tmp_path, '## risk_level\nhigh\n')
        assert review_required(task) is True

    def test_redact_sensitive_api_key(self):
        text = 'config api_key=sk-proj-abcdefghijklmnopqrstuvwxyz123456'
        redacted, findings = redact_sensitive(text)
        assert findings
        assert 'REDACTED' in redacted
        assert 'sk-proj' not in redacted

    def test_redact_sensitive_email(self):
        text = '联系人：alice@example.com'
        redacted, findings = redact_sensitive(text)
        assert findings
        assert 'alice@example.com' not in redacted
