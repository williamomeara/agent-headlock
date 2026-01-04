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
    if getattr(result, "structuredContent", None) is not None:
        return result.structuredContent
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            try:
                return json.loads(text)
            except Exception:
                pass
    raise RuntimeError("Unexpected MCP tool result")


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
        # Preferred: MCP Streamable HTTP
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
            # Fallback: legacy HTTP endpoint
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.server_url}/headlock/enter-headlock",
                    json={"session_id": session_id, "context": context},
                )
                response.raise_for_status()
                data = response.json()
                return HeadlockResponse(
                    session_id=data["session_id"],
                    instruction=data.get("instruction"),
                    should_terminate=data.get("should_terminate", False),
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
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.server_url}/headlock/continue-headlock",
                    json={"session_id": session_id, "context": context},
                )
                response.raise_for_status()
                data = response.json()
                return HeadlockResponse(
                    session_id=data["session_id"],
                    instruction=data.get("instruction"),
                    should_terminate=data.get("should_terminate", False),
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
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.server_url}/headlock/enter-headlock",
                    json={"session_id": session_id, "context": context},
                )
                response.raise_for_status()
                data = response.json()
                return HeadlockResponse(
                    session_id=data["session_id"],
                    instruction=data.get("instruction"),
                    should_terminate=data.get("should_terminate", False),
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
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.server_url}/headlock/continue-headlock",
                    json={"session_id": session_id, "context": context},
                )
                response.raise_for_status()
                data = response.json()
                return HeadlockResponse(
                    session_id=data["session_id"],
                    instruction=data.get("instruction"),
                    should_terminate=data.get("should_terminate", False),
                )
