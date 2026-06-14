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

from new_task import normalize_intake, validate_intake  # noqa: E402

pytestmark = pytest.mark.unit


def test_open_status_with_missing_inputs_is_normalized_to_blocked(tmp_path):
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
    assert err is None
    normalized = normalize_intake(fixture)
    assert normalized['status'] == 'BLOCKED'


def test_blocked_status_without_missing_inputs_is_normalized_to_open(tmp_path):
    root = tmp_path / 'ws'
    (root / 'lbai_system' / 'schemas').mkdir(parents=True)
    schema_src = SCHEMAS / 'task_intake_enrichment_schema_v1.json'
    (root / 'lbai_system' / 'schemas' / schema_src.name).write_text(
        schema_src.read_text(encoding='utf-8'),
        encoding='utf-8',
    )
    fixture = json.loads((FIXTURES / 'task_intake_blocked.json').read_text(encoding='utf-8'))
    fixture['missing_inputs'] = []
    schema = json.loads(schema_src.read_text(encoding='utf-8'))
    jsonschema.validate(instance=fixture, schema=schema)

    err = validate_intake(root, fixture)
    assert err is None
    normalized = normalize_intake(fixture)
    assert normalized['status'] == 'OPEN'
