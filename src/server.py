"""FastAPI server for Headlock MCP."""

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .models import (
    EnterHeadlockResponse,
    SendInstructionRequest,
    SendInstructionResponse,
    SessionInfoResponse,
    SessionState,
)
from .session_manager import session_manager


# MCP Tools (Streamable HTTP mounted at /mcp)
mcp = FastMCP(
    name="headlock",
    instructions="""EXECUTOR AI MODE: You receive instructions and execute them using ALL TOOLS AVAILABLE TO YOU.

INSTRUCTION EXECUTION PROTOCOL:
1. Call headlock-enter_headlock → receive instruction  
2. **IMMEDIATELY EXECUTE** the instruction using ALL available tools (read files, run commands, analyze code, edit files, etc.)
3. **RESPOND CONVERSATIONALLY** with the complete execution results
4. Call headlock-continue_headlock to get the next instruction
5. Repeat for next instruction

**TOOL USAGE IS MANDATORY FOR EXECUTION** - Use filesystem tools, code analysis tools, terminal commands, file editing tools, etc. to fulfill each instruction completely.

**You are a tool-using executor that responds conversationally with results, then continues the loop.**""",
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


# Track active WebSocket connections
active_websockets: dict[str, set[WebSocket]] = {}


async def broadcast_to_terminals(session_id: str, update_type: str, data: dict):
    """Broadcast updates to all connected terminals for a session."""
    message = json.dumps({
        "type": update_type,
        "session_id": session_id,
        "data": data
    })
    
    # Broadcast to session-specific connections
    if session_id in active_websockets:
        dead_connections = set()
        for ws in active_websockets[session_id]:
            try:
                await ws.send_text(message)
            except Exception:
                dead_connections.add(ws)
        active_websockets[session_id] -= dead_connections
    
    # Broadcast to global listeners (session_id = "global")
    if "global" in active_websockets:
        dead_connections = set()
        for ws in active_websockets["global"]:
            try:
                await ws.send_text(message)
            except Exception:
                dead_connections.add(ws)
        active_websockets["global"] -= dead_connections


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    session_manager.register_broadcast_callback(broadcast_to_terminals)

    # FastMCP's Streamable HTTP transport needs its background task group started.
    mcp.streamable_http_app()
    async with mcp.session_manager.run():
        yield


app = FastAPI(
    title="Headlock MCP Server",
    description="MCP server for AI agent headlock mode - enables user control over AI execution flow",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Headlock Core Logic
# ============================================================================

async def _enter_headlock(session_id: Optional[str], context: Optional[str]) -> EnterHeadlockResponse:
    """Enter headlock mode and block until an instruction or tap-out."""
    session = session_manager.get_session(session_id) if session_id else None

    if not session:
        session = session_manager.create_session(session_id=session_id, context=context)
    else:
        session_manager.update_context(session.session_id, context or "")

    await broadcast_to_terminals(session.session_id, "session_waiting", {
        "session_id": session.session_id,
        "context": context,
        "created_at": session.created_at.isoformat(),
    })

    instruction, should_terminate = await session_manager.wait_for_instruction(session.session_id, timeout=3600)

    return EnterHeadlockResponse(
        session_id=session.session_id,
        instruction=instruction,
        should_terminate=should_terminate,
        next_action="Execute the instruction using all available tools (read files, run commands, analyze code, edit files, etc.), respond conversationally with the results, then call headlock-continue_headlock to get the next instruction." if instruction and not should_terminate else None,
    )


async def _continue_headlock(session_id: str, context: Optional[str]) -> EnterHeadlockResponse:
    """Continue headlock after a task result and block for the next instruction."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session_manager.update_context(session_id, context or "")

    await broadcast_to_terminals(session_id, "task_completed", {
        "session_id": session_id,
        "context": context,
    })

    instruction, should_terminate = await session_manager.wait_for_instruction(session_id, timeout=3600)

    return EnterHeadlockResponse(
        session_id=session_id,
        instruction=instruction,
        should_terminate=should_terminate,
        next_action="Execute the instruction using all available tools (read files, run commands, analyze code, edit files, etc.), respond conversationally with the results, then call headlock-continue_headlock to get the next instruction." if instruction and not should_terminate else None,
    )


# ============================================================================
# MCP Tools (Streamable HTTP at /mcp)
# ============================================================================

@mcp.tool(
    name="headlock-enter_headlock",
    description="GET FIRST INSTRUCTION. Call this to start execution loop. Returns instruction. Then USE ALL AVAILABLE TOOLS to execute it completely (read files, run commands, analyze code, edit files, etc.), respond conversationally with results, then call continue_headlock.",
)
async def mcp_enter_headlock(session_id: Optional[str] = None, context: Optional[str] = None) -> str:
    response = await _enter_headlock(session_id, context)
    return json.dumps({
        "session_id": response.session_id,
        "instruction": response.instruction,
        "should_terminate": response.should_terminate,
    })


@mcp.tool(
    name="headlock-continue_headlock",
    description="GET NEXT INSTRUCTION. Call this AFTER responding conversationally with execution results. Gets the next instruction to execute.",
)
async def mcp_continue_headlock(session_id: str, context: Optional[str] = None) -> str:
    response = await _continue_headlock(session_id, context)
    return json.dumps({
        "session_id": response.session_id,
        "instruction": response.instruction,
        "should_terminate": response.should_terminate,
    })


# Mount the MCP Streamable HTTP server at /mcp
app.mount("/mcp", mcp.streamable_http_app())


# ============================================================================
# Terminal/User Endpoints
# ============================================================================

@app.get("/sessions", response_model=list[SessionInfoResponse])
async def list_sessions():
    """List all active headlock sessions."""
    sessions = session_manager.get_all_sessions()
    return [
        SessionInfoResponse(
            session_id=s.session_id,
            state=s.state,
            created_at=s.created_at,
            updated_at=s.updated_at,
            agent_context=s.agent_context,
            last_response=s.last_response,
        )
        for s in sessions
    ]


@app.get("/sessions/waiting", response_model=list[SessionInfoResponse])
async def list_waiting_sessions():
    """List sessions waiting for user input."""
    sessions = session_manager.get_waiting_sessions()
    return [
        SessionInfoResponse(
            session_id=s.session_id,
            state=s.state,
            created_at=s.created_at,
            updated_at=s.updated_at,
            agent_context=s.agent_context,
            last_response=s.last_response,
        )
        for s in sessions
    ]


@app.get("/sessions/{session_id}", response_model=SessionInfoResponse)
async def get_session(session_id: str):
    """Get information about a specific session."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionInfoResponse(
        session_id=session.session_id,
        state=session.state,
        created_at=session.created_at,
        updated_at=session.updated_at,
        agent_context=session.agent_context,
        last_response=session.last_response,
    )


@app.post("/sessions/{session_id}/instruct", response_model=SendInstructionResponse)
async def send_instruction(session_id: str, request: SendInstructionRequest):
    """Send an instruction to a waiting AI agent."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.state != SessionState.WAITING:
        raise HTTPException(
            status_code=400, 
            detail=f"Session is not waiting for input (state: {session.state})"
        )
    
    success = session_manager.send_instruction(session_id, request.instruction)
    
    if success:
        await broadcast_to_terminals(session_id, "instruction_sent", {
            "instruction": request.instruction,
        })
    
    return SendInstructionResponse(
        success=success,
        message="Instruction sent" if success else "Failed to send instruction",
    )


@app.post("/sessions/{session_id}/tap-out", response_model=SendInstructionResponse)
async def tap_out(session_id: str):
    """Signal the AI to terminate the session (tap out)."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    success = session_manager.tap_out(session_id)
    
    if success:
        await broadcast_to_terminals(session_id, "session_terminated", {
            "reason": "tap_out",
        })
    
    return SendInstructionResponse(
        success=success,
        message="Tap out signal sent" if success else "Failed to send tap out",
    )


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Remove a session."""
    success = session_manager.remove_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "message": "Session removed"}


# ============================================================================
# WebSocket for Real-time Terminal Updates
# ============================================================================

@app.websocket("/ws")
async def websocket_global(websocket: WebSocket):
    """Global WebSocket connection for monitoring all sessions."""
    await websocket.accept()
    
    if "global" not in active_websockets:
        active_websockets["global"] = set()
    active_websockets["global"].add(websocket)
    
    try:
        # Send current sessions on connect
        sessions = session_manager.get_all_sessions()
        await websocket.send_text(json.dumps({
            "type": "initial_state",
            "data": {
                "sessions": [
                    {
                        "session_id": s.session_id,
                        "state": s.state.value,
                        "context": s.agent_context,
                        "created_at": s.created_at.isoformat(),
                    }
                    for s in sessions
                ]
            }
        }))
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle terminal commands via WebSocket
            if message.get("type") == "instruct":
                session_id = message.get("session_id")
                instruction = message.get("instruction")
                if session_id and instruction:
                    session_manager.send_instruction(session_id, instruction)
            
            elif message.get("type") == "tap_out":
                session_id = message.get("session_id")
                if session_id:
                    session_manager.tap_out(session_id)
    
    except WebSocketDisconnect:
        active_websockets["global"].discard(websocket)
    except Exception:
        active_websockets["global"].discard(websocket)


@app.websocket("/ws/{session_id}")
async def websocket_session(websocket: WebSocket, session_id: str):
    """WebSocket connection for a specific session."""
    await websocket.accept()
    
    if session_id not in active_websockets:
        active_websockets[session_id] = set()
    active_websockets[session_id].add(websocket)
    
    try:
        # Send current session state on connect
        session = session_manager.get_session(session_id)
        if session:
            await websocket.send_text(json.dumps({
                "type": "session_state",
                "session_id": session_id,
                "data": {
                    "state": session.state.value,
                    "context": session.agent_context,
                    "created_at": session.created_at.isoformat(),
                }
            }))
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "instruct":
                instruction = message.get("instruction")
                if instruction:
                    session_manager.send_instruction(session_id, instruction)
            
            elif message.get("type") == "tap_out":
                session_manager.tap_out(session_id)
    
    except WebSocketDisconnect:
        active_websockets[session_id].discard(websocket)
    except Exception:
        active_websockets[session_id].discard(websocket)


@app.get("/", include_in_schema=False)
async def root():
    return {"name": "headlock", "mcp": "/mcp", "health": "/health"}

# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_sessions": len(session_manager.get_all_sessions()),
        "waiting_sessions": len(session_manager.get_waiting_sessions()),
    }


def main():
    """Run the server."""
    import uvicorn
    uvicorn.run(
        "src.server:app",
        host="0.0.0.0",
        port=8765,
        reload=True,
    )


if __name__ == "__main__":
    main()
