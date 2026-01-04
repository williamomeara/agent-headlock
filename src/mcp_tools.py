"""MCP Tools definition for AI agent integration."""

import json
from typing import Any


def get_mcp_tools_schema() -> list[dict[str, Any]]:
    """
    Returns the MCP tools schema for AI agent integration.
    These tools allow AI agents to enter and maintain headlock mode.
    """
    return [
        {
            "name": "headlock-enter_headlock",
            "description": "Enter headlock mode - block indefinitely waiting for instructions from the UI",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID (optional - new session created if not provided)"
                    }
                },
                "required": []
            }
        },
        {
            "name": "headlock-continue_headlock",
            "description": "Continue headlock - send context and wait for next instruction",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID (required)"
                    },
                    "context": {
                        "type": "string",
                        "description": "Context/summary from completed instruction"
                    }
                },
                "required": ["session_id"]
            }
        }
    ]


# MCP Server manifest for tool discovery
MCP_MANIFEST = {
    "name": "headlock",
    "version": "1.0.0",
    "description": "MCP server for AI agent headlock mode - enables user control over AI execution flow",
    "tools": get_mcp_tools_schema()
}


def format_mcp_manifest() -> str:
    """Return formatted MCP manifest as JSON string."""
    return json.dumps(MCP_MANIFEST, indent=2)
