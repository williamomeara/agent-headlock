"""Data models for the Headlock MCP server."""

from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field
import uuid


class SessionState(str, Enum):
    """State of a headlock session."""
    WAITING = "waiting"  # AI is waiting for user input
    PROCESSING = "processing"  # AI is processing user instruction
    COMPLETED = "completed"  # Session ended normally
    TERMINATED = "terminated"  # Session was terminated by tap-out


class HeadlockSession(BaseModel):
    """Represents an active headlock session."""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    state: SessionState = SessionState.WAITING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    agent_context: Optional[str] = None  # Context from the AI agent
    pending_instruction: Optional[str] = None  # Instruction from user
    last_response: Optional[str] = None  # Last response from AI
    metadata: dict[str, Any] = Field(default_factory=dict)


class EnterHeadlockRequest(BaseModel):
    """Request from AI to enter headlock mode."""
    session_id: Optional[str] = None  # Optional - will be generated if not provided
    context: Optional[str] = None  # Initial context from the agent


class EnterHeadlockResponse(BaseModel):
    """Response when AI enters headlock mode."""
    session_id: str
    instruction: Optional[str] = None  # Instruction from user (if available)
    should_terminate: bool = False  # True if user sent tap-out


class ContinueHeadlockRequest(BaseModel):
    """Request from AI to continue in headlock mode after completing a task."""
    session_id: str
    context: Optional[str] = None  # Summary/result of completed task


class SendInstructionRequest(BaseModel):
    """Request from terminal to send instruction to AI."""
    instruction: str


class SendInstructionResponse(BaseModel):
    """Response after sending instruction."""
    success: bool
    message: str


class SessionInfoResponse(BaseModel):
    """Information about a session for the terminal."""
    session_id: str
    state: SessionState
    created_at: datetime
    updated_at: datetime
    agent_context: Optional[str] = None
    last_response: Optional[str] = None


class TerminalMessage(BaseModel):
    """WebSocket message for terminal communication."""
    type: str  # "session_update", "instruction", "response", "tap_out"
    session_id: Optional[str] = None
    data: Optional[dict[str, Any]] = None
