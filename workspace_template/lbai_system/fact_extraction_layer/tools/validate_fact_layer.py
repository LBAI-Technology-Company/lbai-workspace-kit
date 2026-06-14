#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
LAYER_ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> tuple[Any | None, list[str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except FileNotFoundError:
        return None, [f"file not found: {path}"]
    except json.JSONDecodeError as exc:
        return None, [f"json parse error in {path}: {exc}"]


def validate_json_schema(data: Any, schema_path: Path) -> list[str]:
    schema, errors = read_json(schema_path)
    if errors:
        return errors

    try:
        import jsonschema
    except ImportError:
        return []

    validator = jsonschema.Draft202012Validator(schema)
    messages = []
    for error in sorted(validator.iter_errors(data), key=lambda item: list(item.absolute_path)):
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        messages.append(f"{schema_path.name}: {location}: {error.message}")
    return messages


def catalog_index(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {field["id"]: field for field in catalog.get("fields", []) if isinstance(field, dict) and "id" in field}


def validate_catalog_semantics(catalog: dict[str, Any]) -> list[str]:
    errors = []
    fields = catalog.get("fields", [])
    ids = []

    for field in fields:
        field_id = field.get("id")
        if field_id in ids:
            errors.append(f"duplicate field id: {field_id}")
        ids.append(field_id)

        lifecycle = field.get("lifecycle")
        consumers = field.get("consumer_rules", [])
        if lifecycle == "formal_decision" and not consumers:
            errors.append(f"{field_id}: formal_decision fields must declare consumer_rules")

        if field.get("type") == "enum":
            values = field.get("enum", [])
            if "unknown" not in values:
                errors.append(f"{field_id}: enum fields should include unknown")

        if lifecycle == "deprecated" and not field.get("replaced_by"):
            errors.append(f"{field_id}: deprecated fields must declare replaced_by")

        if field.get("layer") == "derived_facts" and "derived_rule" not in field.get("source_priority", []):
            errors.append(f"{field_id}: derived_facts should include derived_rule in source_priority")

    return errors


def type_matches(value: Any, expected_type: str) -> bool:
    if value is None or value == "unknown":
        return True
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "enum":
        return True
    if expected_type == "date":
        return isinstance(value, str)
    if expected_type == "money":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return True


def validate_fact_values(output: dict[str, Any], catalog: dict[str, Any]) -> list[str]:
    errors = []
    fields = catalog_index(catalog)

    for layer in ("base_facts", "derived_facts"):
        values = output.get(layer, {})
        for fact_id, fact in values.items():
            field = fields.get(fact_id)
            if not field:
                errors.append(f"{layer}.{fact_id}: field is not registered in fact catalog")
                continue

            expected_layer = field.get("layer")
            if expected_layer != layer:
                errors.append(f"{layer}.{fact_id}: field belongs to {expected_layer}, not {layer}")

            value = fact.get("value")
            expected_type = field.get("type")
            if not type_matches(value, expected_type):
                errors.append(f"{layer}.{fact_id}: value {value!r} does not match type {expected_type}")

            if expected_type == "enum":
                allowed = field.get("enum", [])
                if value not in allowed:
                    errors.append(f"{layer}.{fact_id}: value {value!r} not in enum {allowed}")

            source = fact.get("source")
            source_priority = field.get("source_priority", [])
            if source_priority and source not in source_priority and source != "derived_rule":
                errors.append(f"{layer}.{fact_id}: source {source!r} is not allowed by source_priority")

    return errors


def validate_state(output: dict[str, Any], catalog: dict[str, Any]) -> list[str]:
    errors = []
    fields = catalog_index(catalog)
    state = output.get("decision_state", {})

    for fact_id in state.get("missing_facts", []):
        if fact_id not in fields:
            errors.append(f"decision_state.missing_facts: {fact_id} is not registered in catalog")

    if output.get("unmapped_facts") and state.get("state") == "ready_for_rule_check":
        errors.append("decision_state.state cannot be ready_for_rule_check when unmapped_facts is not empty")

    for item in output.get("unmapped_facts", []):
        if item.get("decision_impact") in {"may_affect_decision", "affects_decision"}:
            if state.get("state") not in {"needs_schema_change", "needs_rule", "blocked"}:
                errors.append("decision-impacting unmapped_facts require needs_schema_change, needs_rule, or blocked")

    return errors


def validate(catalog_path: Path, output_path: Path | None) -> int:
    catalog, errors = read_json(catalog_path)
    if errors:
        print_errors(errors)
        return 1

    errors = []
    errors.extend(validate_json_schema(catalog, LAYER_ROOT / "schemas" / "fact_catalog_schema_v1.json"))
    if isinstance(catalog, dict):
        errors.extend(validate_catalog_semantics(catalog))

    if output_path:
        output, output_errors = read_json(output_path)
        errors.extend(output_errors)
        if isinstance(output, dict):
            errors.extend(validate_json_schema(output, LAYER_ROOT / "schemas" / "fact_extraction_output_schema_v1.json"))
            if isinstance(catalog, dict):
                errors.extend(validate_fact_values(output, catalog))
                errors.extend(validate_state(output, catalog))

    if errors:
        print_errors(errors)
        return 1

    target = f"{catalog_path}"
    if output_path:
        target = f"{target} + {output_path}"
    print(f"OK fact layer validation passed: {target}")
    return 0


def print_errors(errors: list[str]) -> None:
    print("FACT LAYER VALIDATION FAILED")
    for error in errors:
        print(f"- {error}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate fact catalog and fact extraction output.")
    parser.add_argument("--catalog", required=True, help="Path to fact_catalog_v1 JSON.")
    parser.add_argument("--output", help="Path to fact_extraction_output_v1 JSON.")
    args = parser.parse_args()

    return validate(Path(args.catalog).resolve(), Path(args.output).resolve() if args.output else None)


if __name__ == "__main__":
    sys.exit(main())

