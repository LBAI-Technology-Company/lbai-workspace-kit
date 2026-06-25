#!/usr/bin/env python3
"""LBAI MCP server for Cursor (stdio JSON-RPC transport, stdlib-only).

Exposes the eight LBAI workflows plus a health-check tool as MCP tools. Each
tool is a thin wrapper that shells out to the ``lbai`` CLI, which remains the
single source of truth for workspace resolution, routing to the registered
active workspace in ``~/.lbai/config.json``, and Git synchronization.

Protocol: a minimal subset of MCP over stdio:
  - initialize       -> server info + capabilities
  - tools/list       -> the 9 tool definitions
  - tools/call       -> run the matching ``lbai`` subcommand, return stdout

No third-party dependencies (no ``mcp`` SDK, no Node). If the official ``mcp``
Python SDK is desired later, the tool table in ``tools.py`` can be reused
unchanged.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

# Allow importing the sibling tools.py whether launched by file path or as a
# module. The installer sets PYTHONPATH to the kit root so lbai_core resolves.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from tools import TOOLS, build_cli_args  # noqa: E402

SERVER_NAME = "lbai-workspace"
SERVER_VERSION_FILE = _HERE / "manifest.json"


def read_server_version() -> str:
    try:
        return json.loads(SERVER_VERSION_FILE.read_text(encoding="utf-8")).get("version", "0.0.0")
    except Exception:
        return "0.0.0"


def resolve_lbai_command() -> list[str] | None:
    """Return the argv prefix to invoke the ``lbai`` CLI, or None if missing.

    Prefers a ``lbai`` on PATH; falls back to the sibling ``lbai_core`` source
    tree when running from a development checkout.
    """
    lbai = shutil.which("lbai")
    if lbai:
        return [lbai]
    source_core = _HERE.parent / "lbai_core"
    if (source_core / "lbai" / "cli.py").exists():
        env_path = os.environ.get("PYTHONPATH", "")
        if str(source_core) not in env_path.split(os.pathsep):
            os.environ["PYTHONPATH"] = (
                f"{source_core}{os.pathsep}{env_path}" if env_path else str(source_core)
            )
        return [sys.executable, "-m", "lbai.cli"]
    return None


def write_enrichment(payload: Any) -> str:
    """Write an enrichment JSON object to a temp file and return its path."""
    fd, path = tempfile.mkstemp(prefix="lbai_enrichment_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
    except Exception:
        os.unlink(path)
        raise
    return path


def resolve_task_folder(command: str) -> str | None:
    """Auto-resolve the current task folder for *command* (execute or finish).

    Calls ``resolve_current_task.py`` which reads the workspace task ledger.
    Returns the relative task folder name (e.g. ``2025-12-01-my-task``) when
    exactly one candidate is found, or ``None`` otherwise.
    """
    resolver = _HERE.parent / "lbai_system" / "tools" / "resolve_current_task.py"
    if not resolver.is_file():
        return None
    result = subprocess.run(
        [sys.executable, str(resolver), command],
        capture_output=True,
        text=True,
    )
    for line in result.stdout.splitlines():
        if line.startswith("TASK_FOLDER "):
            return line.split("TASK_FOLDER ", 1)[-1].strip()
    return None


def send(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message, ensure_ascii=False))
    sys.stdout.write("\n")
    sys.stdout.flush()


def respond(request_id: Any, result: Any) -> None:
    send({"jsonrpc": "2.0", "id": request_id, "result": result})


def respond_error(request_id: Any, code: int, message: str, data: Any = None) -> None:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    send({"jsonrpc": "2.0", "id": request_id, "error": error})


def handle_initialize(request_id: Any) -> None:
    respond(request_id, {
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}},
        "serverInfo": {
            "name": SERVER_NAME,
            "version": read_server_version(),
        },
    })


def handle_tools_list(request_id: Any) -> None:
    items = []
    for tool in TOOLS:
        items.append({
            "name": tool["name"],
            "description": tool["description"],
            "inputSchema": tool["inputSchema"],
        })
    respond(request_id, {"tools": items})


def handle_tools_call(request_id: Any, params: dict[str, Any]) -> None:
    name = params.get("name")
    arguments = params.get("arguments") or {}
    tool = next((t for t in TOOLS if t["name"] == name), None)
    if not tool:
        respond_error(request_id, -32602, f"unknown tool: {name}")
        return

    # Auto-resolve task folder for execute-task and finish-task when the
    # caller does not provide an explicit task_slug.
    if name in {"lbai_execute_task", "lbai_finish_task"} and not arguments.get("task_slug"):
        command = "execute" if name == "lbai_execute_task" else "finish"
        resolved = resolve_task_folder(command)
        if resolved:
            arguments["task_slug"] = resolved

    lbai_cmd = resolve_lbai_command()
    if not lbai_cmd:
        respond_error(
            request_id,
            -32603,
            "lbai_cli_missing",
            "Install the LBAI CLI, run 'lbai github auth token', then 'lbai init-workspace'.",
        )
        return

    enrichment_path: str | None = None
    try:
        if tool["requires_enrichment"]:
            payload = arguments.get("enrichment_json")
            if payload is None:
                respond_error(
                    request_id,
                    -32602,
                    "invalid_params",
                    f"tool {name} requires 'enrichment_json'",
                )
                return
            enrichment_path = write_enrichment(payload)

        argv = lbai_cmd + build_cli_args(tool, arguments, enrichment_path)
        result = subprocess.run(argv, capture_output=True, text=True)
        content = []
        if result.stdout:
            content.append({"type": "text", "text": result.stdout})
        if result.stderr:
            content.append({"type": "text", "text": result.stderr, "isError": True})
        respond(request_id, {"content": content or [{"type": "text", "text": ""}],
                             "isError": result.returncode != 0})
    except ValueError as exc:
        respond_error(request_id, -32602, "invalid_params", str(exc))
    except Exception as exc:  # pragma: no cover - defensive
        respond_error(request_id, -32603, "internal_error", str(exc))
    finally:
        if enrichment_path and os.path.exists(enrichment_path):
            try:
                os.unlink(enrichment_path)
            except OSError:
                pass


def dispatch(line: str) -> None:
    try:
        message = json.loads(line)
    except json.JSONDecodeError:
        return
    request_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}

    if method == "initialize":
        handle_initialize(request_id)
    elif method == "notifications/initialized":
        # Client ack; no response expected for notifications.
        return
    elif method == "tools/list":
        handle_tools_list(request_id)
    elif method == "tools/call":
        handle_tools_call(request_id, params)
    elif method == "ping":
        respond(request_id, {})
    elif method:
        respond_error(request_id, -32601, f"method not found: {method}")
    # Notifications without a method/id are ignored.


def main() -> int:
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        dispatch(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
