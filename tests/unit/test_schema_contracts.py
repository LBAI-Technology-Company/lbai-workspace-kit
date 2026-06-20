"""Validate fixture enrichments against JSON schemas shipped with the kit."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures' / 'enrichments'
SCHEMAS = Path(__file__).resolve().parents[2] / 'workspace_template' / 'lbai_system' / 'schemas'

FIXTURE_SCHEMA_MAP = {
    'evidence_valid.json': 'evidence_enrichment_schema_v1.json',
    'evidence_needs_review.json': 'evidence_enrichment_schema_v1.json',
    'evidence_task_independent.json': 'evidence_enrichment_schema_v1.json',
    'evidence_internal_finance_workstream.json': 'evidence_enrichment_schema_v1.json',
    'task_intake_open.json': 'task_intake_enrichment_schema_v1.json',
    'task_intake_review.json': 'task_intake_enrichment_schema_v1.json',
    'task_intake_blocked.json': 'task_intake_enrichment_schema_v1.json',
    'init_valid.json': 'init_enrichment_schema_v1.json',
    'finish_approve.json': 'finish_review_enrichment_schema_v1.json',
    'finish_block.json': 'finish_review_enrichment_schema_v1.json',
}

INVALID_FIXTURES = {
    'evidence_invalid_schema.json',
    'evidence_missing_practical_next_step.json',
    'init_missing_key.json',
}

pytestmark = pytest.mark.unit


@pytest.mark.parametrize('fixture_name,schema_name', list(FIXTURE_SCHEMA_MAP.items()))
def test_valid_fixtures_match_schema(fixture_name, schema_name):
    fixture = json.loads((FIXTURES / fixture_name).read_text(encoding='utf-8'))
    schema = json.loads((SCHEMAS / schema_name).read_text(encoding='utf-8'))
    jsonschema.validate(instance=fixture, schema=schema)


@pytest.mark.parametrize('fixture_name', sorted(INVALID_FIXTURES))
def test_invalid_fixtures_fail_schema(fixture_name):
    fixture = json.loads((FIXTURES / fixture_name).read_text(encoding='utf-8'))
    schema_file = {
        'evidence_invalid_schema.json': 'evidence_enrichment_schema_v1.json',
        'evidence_missing_practical_next_step.json': 'evidence_enrichment_schema_v1.json',
        'init_missing_key.json': 'init_enrichment_schema_v1.json',
    }[fixture_name]
    schema = json.loads((SCHEMAS / schema_file).read_text(encoding='utf-8'))
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=fixture, schema=schema)
