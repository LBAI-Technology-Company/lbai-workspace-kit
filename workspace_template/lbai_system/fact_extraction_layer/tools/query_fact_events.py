#!/usr/bin/env python3
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
LAYER_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from validate_fact_layer import validate_json_schema  # noqa: E402


INACTIVE_STATUSES = {"rejected", "superseded"}
CONFIRMED_STATUSES = {"confirmed", "closed"}


def parse_time(value: str | None) -> tuple[int, str]:
    if not value:
        return (0, "")
    normalized = value.replace("Z", "+00:00")
    try:
        return (1, datetime.fromisoformat(normalized).isoformat())
    except ValueError:
        return (1, value)


def load_events(path: Path, validate_schema: bool) -> tuple[list[dict[str, Any]], list[str]]:
    events = []
    errors = []
    schema_path = LAYER_ROOT / "schemas" / "fact_event_schema_v1.json"

    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            event = json.loads(stripped)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{index}: JSON parse error: {exc}")
            continue
        if not isinstance(event, dict):
            errors.append(f"{path}:{index}: event must be an object")
            continue
        if validate_schema:
            for error in validate_json_schema(event, schema_path):
                errors.append(f"{path}:{index}: {error}")
        events.append(event)
    return events, errors


def matches(event: dict[str, Any], args: argparse.Namespace) -> bool:
    subject = event.get("subject", {})
    entity = event.get("entity", {})
    source = event.get("source", {})
    validity = event.get("validity", {})

    filters = [
        (args.subject_id, subject.get("id")),
        (args.subject_type, subject.get("type")),
        (args.entity_id, entity.get("id")),
        (args.entity_type, entity.get("type")),
        (args.field_id, event.get("field_id")),
        (args.status, event.get("status")),
        (args.source_type, source.get("type")),
    ]
    for expected, actual in filters:
        if expected and expected != actual:
            return False

    if args.as_of:
        occurred = validity.get("source_occurred_at")
        if occurred and occurred > args.as_of:
            return False

    if args.contains:
        needle = args.contains.lower()
        haystack = json.dumps(event.get("value"), ensure_ascii=False).lower()
        haystack += " " + event.get("evidence_text", "").lower()
        if needle not in haystack:
            return False

    return True


def event_sort_key(event: dict[str, Any]) -> tuple[Any, ...]:
    status = event.get("status")
    confirmed_rank = 1 if status in CONFIRMED_STATUSES else 0
    validity = event.get("validity", {})
    source = event.get("source", {})
    occurred = parse_time(validity.get("source_occurred_at"))
    recorded = parse_time(validity.get("recorded_at"))
    extracted = parse_time(validity.get("extracted_at"))
    priority = source.get("priority", 0)
    confidence = event.get("confidence", 0)
    return (confirmed_rank, occurred, recorded, extracted, priority, confidence)


def detect_conflict(events: list[dict[str, Any]]) -> bool:
    if len(events) < 2:
        return False
    top_key = event_sort_key(events[0])
    top_group = [event for event in events if event_sort_key(event) == top_key]
    values = {json.dumps(event.get("value"), ensure_ascii=False, sort_keys=True) for event in top_group}
    return len(values) > 1


def current_result(events: list[dict[str, Any]], include_inactive: bool) -> dict[str, Any]:
    candidates = events if include_inactive else [event for event in events if event.get("status") not in INACTIVE_STATUSES]
    candidates = sorted(candidates, key=event_sort_key, reverse=True)

    if not candidates:
        return {
            "query_status": "not_found",
            "mode": "current",
            "result": None,
            "history_count": len(events)
        }

    if detect_conflict(candidates):
        return {
            "query_status": "conflict",
            "mode": "current",
            "result": None,
            "conflict_candidates": candidates[:5],
            "history_count": len(events)
        }

    return {
        "query_status": "found",
        "mode": "current",
        "result": candidates[0],
        "history_count": len(events)
    }


def history_result(events: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(events, key=event_sort_key, reverse=False)
    return {
        "query_status": "found" if ordered else "not_found",
        "mode": "history",
        "results": ordered,
        "history_count": len(ordered)
    }


def list_result(events: list[dict[str, Any]], limit: int) -> dict[str, Any]:
    ordered = sorted(events, key=event_sort_key, reverse=True)
    return {
        "query_status": "found" if ordered else "not_found",
        "mode": "list",
        "results": ordered[:limit],
        "result_count": len(ordered)
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Query fact events JSONL.")
    parser.add_argument("--events", required=True, help="Path to fact events JSONL.")
    parser.add_argument("--mode", choices=["current", "history", "list"], default="current")
    parser.add_argument("--subject-id")
    parser.add_argument("--subject-type")
    parser.add_argument("--entity-id")
    parser.add_argument("--entity-type")
    parser.add_argument("--field-id")
    parser.add_argument("--status")
    parser.add_argument("--source-type")
    parser.add_argument("--contains")
    parser.add_argument("--as-of", help="Only include events whose source_occurred_at is <= this value.")
    parser.add_argument("--include-inactive", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--skip-schema-validation", action="store_true")
    args = parser.parse_args()

    events, errors = load_events(Path(args.events).resolve(), not args.skip_schema_validation)
    if errors:
        print(json.dumps({"query_status": "validation_failed", "errors": errors}, ensure_ascii=False, indent=2))
        return 1

    filtered = [event for event in events if matches(event, args)]

    if args.mode == "current":
        result = current_result(filtered, args.include_inactive)
    elif args.mode == "history":
        result = history_result(filtered)
    else:
        result = list_result(filtered, args.limit)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

