#!/usr/bin/env python3
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
LAYER_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from validate_fact_layer import (  # noqa: E402
    catalog_index,
    read_json,
    validate_catalog_semantics,
    validate_fact_values,
    validate_json_schema,
    validate_state,
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_ai_request(input_text: str, catalog: dict[str, Any], task_type: str) -> str:
    prompt_path = LAYER_ROOT / "FACT_EXTRACTION_PROMPT_v1.md"
    prompt = read_text(prompt_path)
    catalog_text = json.dumps(catalog, ensure_ascii=False, indent=2)
    return (
        f"{prompt}\n\n"
        "## Concrete Request\n\n"
        "```text\n"
        f"业务输入：\n{input_text}\n\n"
        f"事实字典：\n{catalog_text}\n\n"
        f"当前任务类型：\n{task_type}\n\n"
        "请输出 fact_extraction_output_schema_v1 JSON。\n"
        "```\n"
    )


def validate_catalog(catalog: dict[str, Any]) -> list[str]:
    errors = []
    errors.extend(validate_json_schema(catalog, LAYER_ROOT / "schemas" / "fact_catalog_schema_v1.json"))
    errors.extend(validate_catalog_semantics(catalog))
    return errors


def validate_output(output: dict[str, Any], catalog: dict[str, Any]) -> list[str]:
    errors = []
    errors.extend(validate_json_schema(output, LAYER_ROOT / "schemas" / "fact_extraction_output_schema_v1.json"))
    errors.extend(validate_fact_values(output, catalog))
    errors.extend(validate_state(output, catalog))
    return errors


def report_for_output(input_path: Path, catalog_path: Path, output_path: Path, catalog: dict[str, Any], output: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    state = output.get("decision_state", {}).get("state")
    next_action = output.get("decision_state", {}).get("next_action")
    fields = sorted(list(output.get("base_facts", {}).keys()) + list(output.get("derived_facts", {}).keys()))
    registered = catalog_index(catalog)

    unknown_registered_fields = [
        field_id
        for field_id, fact in output.get("base_facts", {}).items()
        if field_id in registered and fact.get("value") in {None, "unknown"}
    ]

    if errors:
        flow_status = "validation_failed"
    elif state == "ready_for_rule_check":
        flow_status = "ready_for_rule_engine"
    elif state in {"needs_schema_change", "needs_rule", "needs_fact", "conflict", "blocked"}:
        flow_status = state
    else:
        flow_status = "unknown_state"

    return {
        "schema_version": "fact_extraction_flow_report_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "flow_status": flow_status,
        "input_file": str(input_path),
        "catalog_file": str(catalog_path),
        "extraction_output_file": str(output_path),
        "validation_errors": errors,
        "decision_state": output.get("decision_state", {}),
        "extracted_fields": fields,
        "unknown_registered_fields": unknown_registered_fields,
        "unmapped_facts_count": len(output.get("unmapped_facts", [])),
        "field_change_requests_count": len(output.get("field_change_requests", [])),
        "next_action": next_action,
    }


def run(args: argparse.Namespace) -> int:
    input_path = Path(args.input).resolve()
    catalog_path = Path(args.catalog).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    catalog, catalog_errors = read_json(catalog_path)
    if catalog_errors:
        report = {
            "schema_version": "fact_extraction_flow_report_v1",
            "flow_status": "catalog_load_failed",
            "validation_errors": catalog_errors,
        }
        write_json(output_dir / "fact_extraction_flow_report.json", report)
        print("FAILED catalog_load_failed")
        return 1

    input_text = read_text(input_path)
    catalog_validation_errors = validate_catalog(catalog)

    if args.extraction is None:
        request = build_ai_request(input_text, catalog, args.task_type)
        request_path = output_dir / "fact_extraction_ai_request.md"
        write_text(request_path, request)
        report = {
            "schema_version": "fact_extraction_flow_report_v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "flow_status": "waiting_for_ai_output",
            "input_file": str(input_path),
            "catalog_file": str(catalog_path),
            "ai_request_file": str(request_path),
            "validation_errors": catalog_validation_errors,
            "next_action": "send_ai_request_and_save_json_output",
        }
        write_json(output_dir / "fact_extraction_flow_report.json", report)
        if catalog_validation_errors:
            print("FAILED catalog_validation_failed")
            return 1
        print(f"OK wrote AI extraction request: {request_path}")
        return 0

    extraction_path = Path(args.extraction).resolve()
    extraction, extraction_errors = read_json(extraction_path)
    errors = catalog_validation_errors + extraction_errors
    if isinstance(extraction, dict):
        errors.extend(validate_output(extraction, catalog))
        report = report_for_output(input_path, catalog_path, extraction_path, catalog, extraction, errors)
    else:
        report = {
            "schema_version": "fact_extraction_flow_report_v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "flow_status": "extraction_load_failed",
            "input_file": str(input_path),
            "catalog_file": str(catalog_path),
            "extraction_output_file": str(extraction_path),
            "validation_errors": errors,
            "next_action": "fix_extraction_output_json",
        }

    write_json(output_dir / "fact_extraction_flow_report.json", report)
    if errors:
        print("FAILED validation_failed")
        return 1
    print(f"OK fact extraction flow status: {report['flow_status']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the fact extraction layer flow.")
    parser.add_argument("--input", required=True, help="Path to user input document.")
    parser.add_argument("--catalog", required=True, help="Path to fact catalog JSON.")
    parser.add_argument("--task-type", default="receivable_review", help="Task type for the extraction request.")
    parser.add_argument("--output-dir", required=True, help="Directory for request/report artifacts.")
    parser.add_argument("--extraction", help="Optional AI-produced fact_extraction_output_v1 JSON.")
    return run(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())

