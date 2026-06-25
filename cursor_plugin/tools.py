"""LBAI MCP tool definitions for Cursor.

Each tool is a thin declarative wrapper over an existing ``lbai`` CLI
subcommand. The CLI remains the single source of truth for workflow logic,
workspace resolution, and routing to ``~/.lbai/config.json``; this module only
maps MCP tool calls to CLI arguments.

Tools that require AI enrichment accept ``enrichment_json`` (a JSON object).
The MCP server writes it to a temporary file and passes it to the CLI via
``--enrichment <tmpfile>``, matching the ``--enrichment`` contract enforced by
``lbai_core/lbai/cli.py`` (commands refuse to run without it).
"""
from __future__ import annotations

from typing import Any


# Shared JSON-Schema fragment for an enrichment payload. The exact shape is
# governed by lbai_system/schemas/<name>_schema_v1.json in the workspace; the
# CLI/tool layer validates it. Here we only require a JSON object.
_ENRICHMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": (
        "Enrichment JSON object. Generate it per the matching "
        "lbai_system/schemas/*_schema_v1.json before calling."
    ),
}


# (cli_args_template) is built per-call: keys {enrichment_file} and
# {task_description} are substituted by mcp_server.py.
TOOLS: list[dict[str, Any]] = [
    {
        "name": "lbai_role_setup",
        "description": (
            "Initialize or update LBAI role memory in role_workspace/. Corresponds "
            "to the /lbai-role-setup Cursor command and Codex 'LBAI Role Setup'. "
            "Generate enrichment_json per lbai_system/schemas/init_enrichment_schema_v1.json."
        ),
        "cli": ["init"],
        "requires_enrichment": True,
        "inputSchema": {
            "type": "object",
            "properties": {
                "enrichment_json": _ENRICHMENT_SCHEMA,
            },
            "required": ["enrichment_json"],
        },
    },
    {
        "name": "lbai_new_task",
        "description": (
            "Create a formal evidence-aware LBAI task under tasks/. Corresponds to "
            "/lbai-new-task and Codex 'LBAI New Task'. Generate enrichment_json per "
            "lbai_system/schemas/task_intake_enrichment_schema_v1.json."
        ),
        "cli": ["new-task"],
        "requires_enrichment": True,
        "inputSchema": {
            "type": "object",
            "properties": {
                "enrichment_json": _ENRICHMENT_SCHEMA,
                "task_description": {
                    "type": "string",
                    "description": "One concise task description to register.",
                },
            },
            "required": ["enrichment_json"],
        },
    },
    {
        "name": "lbai_add_evidence",
        "description": (
            "Save source material or reference knowledge into role_workspace/knowledge/evidence/. "
            "Corresponds to /lbai-add-evidence and Codex 'LBAI Add Evidence'. Generate enrichment_json "
            "per lbai_system/schemas/evidence_enrichment_schema_v1.json."
        ),
        "cli": ["add-evidence"],
        "requires_enrichment": True,
        "inputSchema": {
            "type": "object",
            "properties": {
                "enrichment_json": _ENRICHMENT_SCHEMA,
            },
            "required": ["enrichment_json"],
        },
    },
    {
        "name": "lbai_search_artifacts",
        "description": (
            "Search the LBAI backend knowledge service. Corresponds to /lbai-search-artifacts and "
            "Codex 'LBAI Search Artifacts'. Generate enrichment_json (a backend search query plan) per "
            "lbai_system/schemas/backend_search_query_plan_schema_v1.json. Read-only."
        ),
        "cli": ["search-artifacts"],
        "requires_enrichment": True,
        "inputSchema": {
            "type": "object",
            "properties": {
                "enrichment_json": _ENRICHMENT_SCHEMA,
            },
            "required": ["enrichment_json"],
        },
    },
    {
        "name": "lbai_execute_task",
        "description": (
            "Execute the current LBAI task contract; writes execution_plan.md and task_output.md. "
            "Corresponds to /lbai-execute-task and Codex 'LBAI Execute Task'. If task_slug is omitted, "
            "the current OPEN task is auto-resolved from the workspace task ledger."
        ),
        "cli": ["execute-task"],
        "requires_enrichment": False,
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_slug": {
                    "type": "string",
                    "description": "Optional task folder name under tasks/. Omit to auto-resolve the current OPEN task.",
                },
            },
        },
    },
    {
        "name": "lbai_finish_task",
        "description": (
            "Finish an LBAI task, run the hygiene check, and sync safe artifacts to the private GitHub "
            "repo. Corresponds to /lbai-finish-task and Codex 'LBAI Finish Task'. Generate enrichment_json "
            "per lbai_system/schemas/finish_review_enrichment_schema_v1.json. Requires employee_conversation_turns. "
            "If task_slug is omitted, the current completed task is auto-resolved from the workspace task ledger."
        ),
        "cli": ["finish-task"],
        "requires_enrichment": True,
        "inputSchema": {
            "type": "object",
            "properties": {
                "enrichment_json": _ENRICHMENT_SCHEMA,
                "task_slug": {
                    "type": "string",
                    "description": "Optional task folder name under tasks/. Omit to auto-resolve the current completed task.",
                },
            },
            "required": ["enrichment_json"],
        },
    },
    {
        "name": "lbai_update_kit",
        "description": (
            "Update company-maintained LBAI workflow kit files only (.cursor/, .agents/, lbai_system/, "
            "AGENTS.md, README.md, workspace_dashboard.html). Does not touch employee role_workspace/ or tasks/. "
            "Corresponds to /lbai-update-kit and Codex 'LBAI Update Kit'."
        ),
        "cli": ["update-kit"],
        "requires_enrichment": False,
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "lbai_self_iterate",
        "description": (
            "Start or continue the LBAI Prompt Lab self-iteration loop under prompt_lab/. Corresponds to "
            "/lbai-self-iterate and Codex 'LBAI Self Iterate'. Must not modify formal prompts under "
            "lbai_system/prompts/ or employee task artifacts."
        ),
        "cli": ["self-iterate"],
        "requires_enrichment": False,
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "lbai_doctor",
        "description": (
            "Run the LBAI workspace health check (machine-readable). Returns readiness, workspace/version "
            "compatibility, authentication, git, and adapter checks. Does not expose tokens or API keys."
        ),
        "cli": ["doctor", "--json"],
        "requires_enrichment": False,
        "inputSchema": {
            "type": "object",
            "properties": {
                "require_backend": {
                    "type": "boolean",
                    "description": "If true, require backend knowledge-service auth to be READY.",
                    "default": False,
                },
            },
        },
    },
]


def tool_names() -> list[str]:
    """Return the ordered list of MCP tool names."""
    return [t["name"] for t in TOOLS]


def build_cli_args(tool: dict[str, Any], arguments: dict[str, Any] | None,
                   enrichment_file: str | None) -> list[str]:
    """Build the ``lbai`` CLI argv for a tool call.

    ``enrichment_file`` is the path where the server already wrote the
    enrichment JSON; it is appended as ``--enrichment <path>`` when the tool
    requires enrichment.
    """
    args = list(tool["cli"])
    if tool["requires_enrichment"]:
        if not enrichment_file:
            raise ValueError(
                f"tool {tool['name']} requires enrichment_json but no enrichment file was provided"
            )
        args.extend(["--enrichment", enrichment_file])
    if tool["name"] == "lbai_new_task":
        desc = (arguments or {}).get("task_description")
        if desc:
            args.append(str(desc))
    if tool["name"] == "lbai_finish_task":
        slug = (arguments or {}).get("task_slug")
        if slug:
            args.append(str(slug))
    if tool["name"] == "lbai_execute_task":
        slug = (arguments or {}).get("task_slug")
        if slug:
            args.append(str(slug))
    if tool["name"] == "lbai_doctor":
        if (arguments or {}).get("require_backend"):
            args.append("--require-backend")
    return args
