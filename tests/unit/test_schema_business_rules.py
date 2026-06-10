"""Business rules beyond JSON Schema validation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema
import pytest

TOOLS = Path(__file__).resolve().parents[2] / 'workspace_template' / 'lbai_system' / 'tools'
SCHEMAS = Path(__file__).resolve().parents[2] / 'workspace_template' / 'lbai_system' / 'schemas'
FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures' / 'enrichments'

sys.path.insert(0, str(TOOLS))

from add_evidence import load_enrichment  # noqa: E402
from new_task import validate_intake  # noqa: E402

pytestmark = pytest.mark.unit


def test_linked_evidence_wrong_usage_passes_schema_fails_business_rule(tmp_path):
    root = tmp_path / 'ws'
    (root / 'lbai_system' / 'schemas').mkdir(parents=True)
    schema_src = SCHEMAS / 'evidence_enrichment_schema_v1.json'
    (root / 'lbai_system' / 'schemas' / schema_src.name).write_text(
        schema_src.read_text(encoding='utf-8'),
        encoding='utf-8',
    )
    fixture = json.loads((FIXTURES / 'evidence_linked_wrong_usage.json').read_text(encoding='utf-8'))
    schema = json.loads(schema_src.read_text(encoding='utf-8'))
    jsonschema.validate(instance=fixture, schema=schema)

    path = tmp_path / 'enrichment.json'
    path.write_text(json.dumps(fixture, ensure_ascii=False), encoding='utf-8')
    data, err = load_enrichment(root, path, 'tasks/2026_06_10_sample')
    assert data is None
    assert err and 'usage_intent must be task_input' in err


def test_open_status_with_missing_inputs_passes_schema_fails_business_rule(tmp_path):
    root = tmp_path / 'ws'
    (root / 'lbai_system' / 'schemas').mkdir(parents=True)
    schema_src = SCHEMAS / 'task_intake_enrichment_schema_v1.json'
    (root / 'lbai_system' / 'schemas' / schema_src.name).write_text(
        schema_src.read_text(encoding='utf-8'),
        encoding='utf-8',
    )
    fixture = json.loads((FIXTURES / 'task_intake_open.json').read_text(encoding='utf-8'))
    fixture['missing_inputs'] = ['still missing budget approval']
    schema = json.loads(schema_src.read_text(encoding='utf-8'))
    jsonschema.validate(instance=fixture, schema=schema)

    err = validate_intake(root, fixture)
    assert err and 'status OPEN requires empty missing_inputs' in err
