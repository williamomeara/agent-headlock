"""
Headlock MCP Client - For use by AI agents to connect to the Headlock server.

This module provides a simple interface for AI agents to enter headlock mode
and communicate with the Headlock MCP server.
"""

import asyncio
import json
from dataclasses import dataclass
from typing import Optional

import httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


@dataclass
class HeadlockResponse:
    """Response from headlock operations."""
    session_id: str
    instruction: Optional[str] = None
    should_terminate: bool = False


def _parse_mcp_result(result) -> dict:
    # First try structured content
    if getattr(result, "structuredContent", None) is not None:
        content = result.structuredContent
        if isinstance(content, dict):
            return content
        # If it's a Pydantic model, convert to dict
        if hasattr(content, "model_dump"):
            return content.model_dump()
        elif hasattr(content, "__dict__"):
            return content.__dict__
    
    # Fall back to parsing text content
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            try:
                return json.loads(text)
            except Exception:
                pass
    
    raise RuntimeError("Could not parse MCP result")


class HeadlockClient:
    """
    Client for AI agents to interact with the Headlock MCP server.
    
    Usage:
        client = HeadlockClient("http://localhost:8765")
        
        # Enter headlock mode - blocks until user sends instruction
        response = client.enter_headlock()
        
        while not response.should_terminate:
            # Execute the instruction
            result = execute_task(response.instruction)
            
            # Report back and wait for next instruction
            response = client.continue_headlock(
                session_id=response.session_id,
                context=result
            )
        
        print("Session ended by user tap-out")
    """
    
    def __init__(self, server_url: str = "http://localhost:8765", timeout: float = None):
        """
        Initialize the headlock client.
        
        Args:
            server_url: URL of the Headlock MCP server
            timeout: Request timeout in seconds (None for infinite wait)
        """
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
    
    def enter_headlock(
        self,
        session_id: Optional[str] = None,
        context: Optional[str] = None,
    ) -> HeadlockResponse:
        return asyncio.run(self._enter_headlock_async(session_id=session_id, context=context))

    async def _enter_headlock_async(
        self,
        session_id: Optional[str] = None,
        context: Optional[str] = None,
    ) -> HeadlockResponse:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as http_client:
                async with streamable_http_client(
                    f"{self.server_url}/mcp/",
                    http_client=http_client,
                ) as (read, write, _get_session_id):
                    session = ClientSession(read, write)
                    await session.initialize()
                    result = await session.call_tool(
                        "headlock-enter_headlock",
                        {"session_id": session_id, "context": context},
                    )

            data = _parse_mcp_result(result)
            return HeadlockResponse(
                session_id=data["session_id"],
                instruction=data.get("instruction"),
                should_terminate=data.get("should_terminate", False),
            )
        except Exception:
            # On error, return a response that terminates the session
            return HeadlockResponse(
                session_id=session_id or "error",
                instruction=None,
                should_terminate=True,
            )
    
    def continue_headlock(
        self,
        session_id: str,
        context: Optional[str] = None,
    ) -> HeadlockResponse:
        return asyncio.run(self._continue_headlock_async(session_id=session_id, context=context))

    async def _continue_headlock_async(
        self,
        session_id: str,
        context: Optional[str] = None,
    ) -> HeadlockResponse:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as http_client:
                async with streamable_http_client(
                    f"{self.server_url}/mcp/",
                    http_client=http_client,
                ) as (read, write, _get_session_id):
                    session = ClientSession(read, write)
                    await session.initialize()
                    result = await session.call_tool(
                        "headlock-continue_headlock",
                        {"session_id": session_id, "context": context},
                    )

            data = _parse_mcp_result(result)
            return HeadlockResponse(
                session_id=data["session_id"],
                instruction=data.get("instruction"),
                should_terminate=data.get("should_terminate", False),
            )
        except Exception:
            # On error, return a response that terminates the session
            return HeadlockResponse(
                session_id=session_id,
                instruction=None,
                should_terminate=True,
            )


# Async version for use with async AI agents
class AsyncHeadlockClient:
    """Async version of HeadlockClient for async AI agents."""
    
    def __init__(self, server_url: str = "http://localhost:8765", timeout: float = None):
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
    
    async def enter_headlock(
        self,
        session_id: Optional[str] = None,
        context: Optional[str] = None,
    ) -> HeadlockResponse:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as http_client:
                async with streamable_http_client(
                    f"{self.server_url}/mcp/",
                    http_client=http_client,
                ) as (read, write, _get_session_id):
                    session = ClientSession(read, write)
                    await session.initialize()
                    result = await session.call_tool(
                        "headlock-enter_headlock",
                        {"session_id": session_id, "context": context},
                    )

            data = _parse_mcp_result(result)
            return HeadlockResponse(
                session_id=data["session_id"],
                instruction=data.get("instruction"),
                should_terminate=data.get("should_terminate", False),
            )
        except Exception:
            # On error, return a response that terminates the session
            return HeadlockResponse(
                session_id=session_id or "error",
                instruction=None,
                should_terminate=True,
            )
    
    async def continue_headlock(
        self,
        session_id: str,
        context: Optional[str] = None,
    ) -> HeadlockResponse:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as http_client:
                async with streamable_http_client(
                    f"{self.server_url}/mcp/",
                    http_client=http_client,
                ) as (read, write, _get_session_id):
                    session = ClientSession(read, write)
                    await session.initialize()
                    result = await session.call_tool(
                        "headlock-continue_headlock",
                        {"session_id": session_id, "context": context},
                    )

            data = _parse_mcp_result(result)
            return HeadlockResponse(
                session_id=data["session_id"],
                instruction=data.get("instruction"),
                should_terminate=data.get("should_terminate", False),
            )
        except Exception:
            # On error, return a response that terminates the session
            return HeadlockResponse(
                session_id=session_id,
                instruction=None,
                should_terminate=True,
            )
