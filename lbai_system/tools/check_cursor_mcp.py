#!/usr/bin/env python3
"""Check that the LBAI MCP server is registered in Cursor's global config.

Unlike the project-local codex/cursor adapter checks, this inspects the global
``~/.cursor/mcp.json`` because MCP servers are registered globally and made
available to every Cursor project. The check is non-fatal for workspace
validity: a missing MCP registration only means the tools are not surfaced in
Cursor; the CLI workflows still work via ``/lbai-*`` commands.

Exit code: 0 when registered and the server script exists, 1 otherwise.
"""
from __future__ import annotations

import json
import os
from pathlib import Path


SERVER_KEY = "lbai-workspace"


def cursor_config_dir() -> Path:
    """Return Cursor's global config directory across platforms."""
    if os.name == "nt":  # Windows
        return Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".cursor"
    return Path.home() / ".cursor"


def load_mcp_config() -> dict:
    config_path = cursor_config_dir() / "mcp.json"
    if not config_path.exists():
        return {}
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def server_script_exists(entry: dict) -> bool:
    """Best-effort check that the registered command target exists."""
    args = entry.get("args") or []
    if not args:
        return False
    # The first arg is the MCP server script path (mcp_server.py).
    script = Path(os.path.expanduser(str(args[0])))
    return script.is_file()


def main() -> int:
    config = load_mcp_config()
    servers = config.get("mcpServers") if isinstance(config.get("mcpServers"), dict) else {}
    entry = servers.get(SERVER_KEY) if isinstance(servers, dict) else None

    print("# LBAI Cursor MCP 注册检查")
    print(f"- 配置文件: {cursor_config_dir() / 'mcp.json'}")
    if not config:
        print("- 未找到 ~/.cursor/mcp.json（Cursor 未安装或尚未配置 MCP）")
        print("STATUS BLOCKED")
        print("NEXT_STEP 安装 Cursor 后重跑 install.sh / install.ps1，或手动在 ~/.cursor/mcp.json 注册 lbai-workspace MCP server。")
        return 1
    if not entry:
        print(f"- mcpServers 中未注册 {SERVER_KEY}")
        print("STATUS BLOCKED")
        print("NEXT_STEP 重跑 install.sh / install.ps1，或在 ~/.cursor/mcp.json 的 mcpServers 下添加 lbai-workspace 条目。")
        return 1
    if not server_script_exists(entry):
        args = entry.get("args") or []
        print(f"- 已注册 {SERVER_KEY}，但脚本不存在: {args[0] if args else '?'}")
        print("STATUS BLOCKED")
        print("NEXT_STEP 重跑 install.sh / install.ps1（lbai-workspace-kit 升级后路径可能变化），或修正 mcp.json 中的 args 路径。")
        return 1
    print(f"- 已注册 {SERVER_KEY} 且脚本存在")
    print("STATUS OK")
    print("NEXT_STEP 重启 Cursor 后，在任意项目的 agent 工具列表中可看到 lbai_* 工具。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
