"""Session manager for Headlock MCP server."""

import asyncio
from datetime import datetime
from typing import Optional
from .models import HeadlockSession, SessionState


class SessionManager:
    """Manages headlock sessions and synchronization between AI and terminal."""
    
    def __init__(self):
        self._sessions: dict[str, HeadlockSession] = {}
        self._instruction_events: dict[str, asyncio.Event] = {}
        self._terminal_connections: dict[str, set] = {}  # session_id -> set of websocket connections
        self._broadcast_callbacks: list = []
    
    def create_session(self, session_id: Optional[str] = None, context: Optional[str] = None) -> HeadlockSession:
        """Create a new headlock session."""
        session = HeadlockSession(agent_context=context)
        if session_id:
            session.session_id = session_id
        
        self._sessions[session.session_id] = session
        self._instruction_events[session.session_id] = asyncio.Event()
        return session
    
    def get_session(self, session_id: str) -> Optional[HeadlockSession]:
        """Get a session by ID."""
        return self._sessions.get(session_id)
    
    def get_all_sessions(self) -> list[HeadlockSession]:
        """Get all active sessions."""
        return list(self._sessions.values())
    
    def get_waiting_sessions(self) -> list[HeadlockSession]:
        """Get all sessions waiting for user input."""
        return [s for s in self._sessions.values() if s.state == SessionState.WAITING]
    
    async def wait_for_instruction(self, session_id: str, timeout: Optional[float] = None) -> tuple[Optional[str], bool]:
        """
        Wait for an instruction from the terminal.
        Returns (instruction, should_terminate).
        """
        session = self._sessions.get(session_id)
        if not session:
            return None, True
        
        event = self._instruction_events.get(session_id)
        if not event:
            return None, True
        
        try:
            if timeout:
                await asyncio.wait_for(event.wait(), timeout=timeout)
            else:
                await event.wait()
        except asyncio.TimeoutError:
            return None, False
        
        # Get the instruction and reset
        session = self._sessions.get(session_id)
        if not session:
            return None, True
        
        instruction = session.pending_instruction
        should_terminate = session.state == SessionState.TERMINATED
        
        # Clear the event for next wait
        event.clear()
        session.pending_instruction = None
        
        if not should_terminate:
            session.state = SessionState.PROCESSING
            session.updated_at = datetime.utcnow()
        
        return instruction, should_terminate
    
    def send_instruction(self, session_id: str, instruction: str) -> bool:
        """Send an instruction to a waiting AI agent."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        session.pending_instruction = instruction
        session.updated_at = datetime.utcnow()
        
        event = self._instruction_events.get(session_id)
        if event:
            event.set()
        
        return True
    
    def tap_out(self, session_id: str) -> bool:
        """Signal the AI to terminate the session."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        session.state = SessionState.TERMINATED
        session.updated_at = datetime.utcnow()
        
        event = self._instruction_events.get(session_id)
        if event:
            event.set()
        
        return True
    
    def update_context(self, session_id: str, context: str) -> bool:
        """Update the context/response from the AI agent."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        session.agent_context = context
        session.last_response = context
        session.state = SessionState.WAITING
        session.updated_at = datetime.utcnow()
        return True
    
    def complete_session(self, session_id: str) -> bool:
        """Mark a session as completed."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        session.state = SessionState.COMPLETED
        session.updated_at = datetime.utcnow()
        return True
    
    def remove_session(self, session_id: str) -> bool:
        """Remove a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            if session_id in self._instruction_events:
                del self._instruction_events[session_id]
            return True
        return False
    
    def register_broadcast_callback(self, callback):
        """Register a callback for broadcasting updates."""
        self._broadcast_callbacks.append(callback)
    
    async def broadcast_update(self, session_id: str, update_type: str, data: dict):
        """Broadcast an update to all registered callbacks."""
        for callback in self._broadcast_callbacks:
            try:
                await callback(session_id, update_type, data)
            except Exception:
                pass


# Global session manager instance
session_manager = SessionManager()
