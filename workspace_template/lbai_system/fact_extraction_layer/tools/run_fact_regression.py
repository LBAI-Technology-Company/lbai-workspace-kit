#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
LAYER_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from validate_fact_layer import (  # noqa: E402
    read_json,
    validate_catalog_semantics,
    validate_fact_values,
    validate_json_schema,
    validate_state,
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    cases = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{index}: JSON parse error: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{index}: case must be a JSON object")
        cases.append(value)
    return cases


def fact_value(output: dict[str, Any], field_id: str) -> Any:
    if field_id in output.get("base_facts", {}):
        return output["base_facts"][field_id].get("value")
    if field_id in output.get("derived_facts", {}):
        return output["derived_facts"][field_id].get("value")
    return None


def validate_output(output: dict[str, Any], catalog: dict[str, Any]) -> list[str]:
    errors = []
    errors.extend(validate_json_schema(output, LAYER_ROOT / "schemas" / "fact_extraction_output_schema_v1.json"))
    errors.extend(validate_fact_values(output, catalog))
    errors.extend(validate_state(output, catalog))
    return errors


def run_case(case: dict[str, Any], catalog: dict[str, Any], case_root: Path) -> list[str]:
    errors = []
    case_id = case.get("id", "<missing id>")
    output_file = case.get("actual_output_file")
    if not output_file:
        return [f"{case_id}: missing actual_output_file"]

    output_path = (case_root / output_file).resolve()
    output, load_errors = read_json(output_path)
    if load_errors:
        return [f"{case_id}: {error}" for error in load_errors]
    if not isinstance(output, dict):
        return [f"{case_id}: output must be a JSON object"]

    for error in validate_output(output, catalog):
        errors.append(f"{case_id}: {error}")

    expected_state = case.get("expected_state")
    actual_state = output.get("decision_state", {}).get("state")
    if expected_state and actual_state != expected_state:
        errors.append(f"{case_id}: expected state {expected_state!r}, got {actual_state!r}")

    for field_id, expected in case.get("expected_facts", {}).items():
        actual = fact_value(output, field_id)
        if actual != expected:
            errors.append(f"{case_id}: expected {field_id}={expected!r}, got {actual!r}")

    expected_unmapped_min = case.get("expected_unmapped_count_min")
    if expected_unmapped_min is not None and len(output.get("unmapped_facts", [])) < expected_unmapped_min:
        errors.append(f"{case_id}: expected at least {expected_unmapped_min} unmapped_facts")

    expected_change_min = case.get("expected_field_change_count_min")
    if expected_change_min is not None and len(output.get("field_change_requests", [])) < expected_change_min:
        errors.append(f"{case_id}: expected at least {expected_change_min} field_change_requests")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Run fact extraction regression cases.")
    parser.add_argument("--catalog", required=True, help="Path to fact catalog JSON.")
    parser.add_argument("--cases", required=True, help="Path to JSONL regression cases.")
    args = parser.parse_args()

    catalog_path = Path(args.catalog).resolve()
    cases_path = Path(args.cases).resolve()
    catalog, errors = read_json(catalog_path)
    if isinstance(catalog, dict):
        errors.extend(validate_json_schema(catalog, LAYER_ROOT / "schemas" / "fact_catalog_schema_v1.json"))
        errors.extend(validate_catalog_semantics(catalog))

    try:
        cases = load_jsonl(cases_path)
    except ValueError as exc:
        errors.append(str(exc))
        cases = []

    if isinstance(catalog, dict):
        for case in cases:
            errors.extend(run_case(case, catalog, cases_path.parent))

    if errors:
        print("FACT REGRESSION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"OK fact regression passed: {len(cases)} cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
