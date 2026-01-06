#!/usr/bin/env python3
"""Interactive terminal client for Headlock MCP server."""

import asyncio
import json
import sys
from datetime import datetime
from typing import Optional

import click
import httpx
import websockets
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.markdown import Markdown
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.widgets import Header, Footer, TextArea, Static, Button, DataTable, Label
from textual import events
from textual.binding import Binding

console = Console()

DEFAULT_SERVER_URL = "http://localhost:8765"


class HeadlockTerminalApp(App):
    """Full-featured Textual terminal app for Headlock MCP server."""

    CSS = """
    Screen {
        background: $surface;
    }

    #sidebar {
        width: 40;
        background: $panel;
        border-right: solid $primary;
    }

    #main-content {
        height: 100%;
    }

    #input-area {
        height: 40%;
        border-top: solid $primary;
    }

    #output-area {
        height: 60%;
    }

    TextArea {
        border: solid $primary;
    }

    DataTable {
        height: 100%;
    }

    #status {
        background: $boost;
        color: $text;
        padding: 1;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding("ctrl+j", "submit_instruction", "Submit"),
        Binding("ctrl+c", "quit", "Quit"),
        Binding("f1", "show_help", "Help"),
        Binding("ctrl+r", "refresh_sessions", "Refresh"),
        Binding("ctrl+t", "tap_out_session", "Tap Out"),
    ]

    def __init__(self, server_url: str = DEFAULT_SERVER_URL):
        super().__init__()
        self.server_url = server_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)
        self.current_session: Optional[str] = None
        self.sessions = []
        self.instruction_text = ""
        self.messages = []  # Store messages for output display
        self.websocket_task: Optional[asyncio.Task] = None

    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield Header()

        with Horizontal():
            # Sidebar with session list
            with Vertical(id="sidebar"):
                yield Static("📋 Sessions", classes="sidebar-title")
                yield DataTable(id="sessions-table")

            # Main content area
            with Vertical(id="main-content"):
                # Output area
                with Vertical(id="output-area"):
                    yield Static("Output", classes="section-title")
                    yield VerticalScroll(Static("", id="output-display"))

                # Input area
                with Vertical(id="input-area"):
                    yield Static("Instruction Input (Ctrl+J to submit)", classes="section-title")
                    yield TextArea(id="instruction-input")

        yield Footer()

    def update_status_bar(self) -> None:
        """Update the status bar with current information."""
        session_info = f"Session: {self.current_session[:8] if self.current_session else 'None'}"
        server_info = f"Server: {self.server_url}"
        refresh_info = "Auto-refresh: ON"
        status_text = f"{session_info} | {server_info} | {refresh_info} | Ctrl+J: Submit | Ctrl+R: Refresh | Ctrl+T: Tap Out | F1: Help"
        
        # Update footer if it exists
        try:
            footer = self.query_one(Footer)
            footer.renderable = status_text
        except Exception:
            pass  # Footer might not be ready yet

    async def on_mount(self) -> None:
        """Initialize the app."""
        # Set up the sessions table
        table = self.query_one("#sessions-table", DataTable)
        table.add_columns("ID", "State", "Context")
        table.cursor_type = "row"

        # Show initial status
        self.show_message("🚀 Headlock Terminal started")
        self.show_message(f"📡 Connecting to {self.server_url}")

        # Check server health
        if not await self.check_health():
            self.show_message("❌ Cannot connect to server. Make sure it's running.")
            self.show_message("💡 Start the server with: python -m src.server")
        else:
            self.show_message("✅ Connected to Headlock server")
            await self.refresh_sessions()
        
        self.update_status_bar()

        # Start auto-refresh timer (every 5 seconds)
        self.set_interval(5.0, self.auto_refresh_sessions)

        # Start WebSocket connection for real-time updates
        self.websocket_task = asyncio.create_task(self.websocket_listener())

    async def check_health(self) -> bool:
        """Check if the server is running."""
        try:
            response = await self.client.get(f"{self.server_url}/health")
            return response.status_code == 200
        except Exception:
            return False

    async def refresh_sessions(self) -> None:
        """Refresh the sessions list."""
        try:
            response = await self.client.get(f"{self.server_url}/sessions")
            response.raise_for_status()
            self.sessions = response.json()
            await self.update_sessions_table()
        except Exception as e:
            self.show_message(f"❌ Error loading sessions: {e}")

    async def auto_refresh_sessions(self) -> None:
        """Auto-refresh sessions silently."""
        try:
            response = await self.client.get(f"{self.server_url}/sessions")
            response.raise_for_status()
            self.sessions = response.json()
            await self.update_sessions_table()
        except Exception:
            # Don't show error messages for auto-refresh to avoid spam
            pass

    async def websocket_listener(self) -> None:
        """Listen for real-time updates via WebSocket."""
        ws_url = self.server_url.replace("http", "ws") + "/ws"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                self.show_message("🔗 Connected to real-time updates")
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        event_type = data.get("type")
                        
                        if event_type in ["session_waiting", "task_completed", "session_terminated", "instruction_sent"]:
                            # Refresh sessions when something changes
                            await self.refresh_sessions()
                            
                            # Show relevant messages
                            if event_type == "session_waiting":
                                session_id = data.get("session_id", "")[:8]
                                self.show_message(f"🎯 New session waiting: {session_id}")
                            elif event_type == "task_completed":
                                session_id = data.get("session_id", "")[:8]
                                self.show_message(f"✅ Task completed in session: {session_id}")
                            elif event_type == "instruction_sent":
                                self.show_message("📤 Instruction sent to AI agent")
                                
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            # WebSocket connection failed, fall back to polling
            self.show_message("⚠️  Real-time updates unavailable, using auto-refresh")

    async def update_sessions_table(self) -> None:
        """Update the sessions table display."""
        table = self.query_one("#sessions-table", DataTable)
        table.clear()

        for session in self.sessions:
            session_id = session.get("session_id", "")
            state = session.get("state", "unknown")
            context = session.get("agent_context") or session.get("last_response") or ""
            if len(context) > 30:
                context = context[:27] + "..."

            # Color coding for states
            state_display = {
                "waiting": "🟢 WAITING",
                "processing": "🟡 PROCESSING",
                "completed": "🔵 COMPLETED",
                "terminated": "🔴 TERMINATED",
            }.get(state, f"⚪ {state.upper()}")

            table.add_row(session_id[:12], state_display, context, key=session_id)

    def show_message(self, message: str) -> None:
        """Show a message in the output area."""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.messages.append(f"[{current_time}] {message}")
        
        # Keep only the last 50 messages to avoid memory issues
        if len(self.messages) > 50:
            self.messages = self.messages[-50:]
        
        # Update the display
        output = self.query_one("#output-display", Static)
        output.update("\n".join(self.messages))

    async def action_submit_instruction(self) -> None:
        """Submit the current instruction."""
        if not self.current_session:
            self.show_message("❌ No session selected. Click on a session in the sidebar first.")
            return

        textarea = self.query_one("#instruction-input", TextArea)
        instruction = textarea.text.strip()

        if not instruction:
            self.show_message("❌ Instruction is empty")
            return

        try:
            response = await self.client.post(
                f"{self.server_url}/sessions/{self.current_session}/instruct",
                json={"instruction": instruction}
            )
            response.raise_for_status()
            result = response.json()

            if result.get("success", False):
                self.show_message(f"✅ Instruction sent to session {self.current_session[:8]}")
                textarea.text = ""  # Clear the input
            else:
                self.show_message("❌ Failed to send instruction")

        except Exception as e:
            self.show_message(f"❌ Error sending instruction: {e}")

    async def action_refresh_sessions(self) -> None:
        """Refresh sessions action."""
        await self.refresh_sessions()
        self.show_message("🔄 Sessions refreshed")
        self.update_status_bar()

    async def action_tap_out_session(self) -> None:
        """Tap out the current session."""
        if not self.current_session:
            self.show_message("❌ No session selected. Click on a session in the sidebar first.")
            return

        try:
            response = await self.client.post(
                f"{self.server_url}/sessions/{self.current_session}/tap-out"
            )
            response.raise_for_status()
            result = response.json()

            if result.get("success", False):
                self.show_message(f"✅ Tapped out of session {self.current_session[:8]}")
                self.current_session = None
                self.update_status_bar()
                await self.refresh_sessions()  # Refresh to update the session list
            else:
                self.show_message("❌ Failed to tap out")

        except Exception as e:
            self.show_message(f"❌ Error tapping out: {e}")

    def action_show_help(self) -> None:
        """Show help information."""
        help_text = """
🎯 Headlock Terminal Help

📋 Sessions Sidebar:
  • Click on any session to select it
  • Green = Waiting, Yellow = Processing, Blue = Completed, Red = Terminated

⌨️  Keyboard Shortcuts:
  • Ctrl+J: Submit instruction
  • Ctrl+R: Refresh sessions
  • Ctrl+T: Tap out current session
  • F1: Show this help
  • Ctrl+C: Quit

📝 Instruction Input:
  • Type your instruction in the text area
  • Enter creates new lines (like a code editor)
  • Ctrl+J sends the instruction
  • Works great over SSH!

💡 Tips:
  • Multi-line instructions work perfectly
  • Rich formatting in output area
  • Real-time session updates
        """
        # Clear messages and show help
        self.messages = []
        output = self.query_one("#output-display", Static)
        output.update(help_text)

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle session selection."""
        if event.data_table.id == "sessions-table" and event.row_key is not None:
            try:
                # The row_key.value is now the session_id (string)
                selected_session_id = event.row_key.value
                if selected_session_id:
                    self.current_session = selected_session_id
                    self.show_message(f"🎯 Selected session: {selected_session_id[:12]}")
                    self.update_status_bar()
            except Exception as e:
                self.show_message(f"❌ Error selecting session: {e}")

    async def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle row highlighting."""
        pass  # Could add preview functionality here


class HeadlockTerminal:
    """Simple wrapper for the Textual app."""
    
    def __init__(self, server_url: str = DEFAULT_SERVER_URL):
        self.server_url = server_url
    
    async def run_interactive(self):
        """Run the interactive terminal."""
        app = HeadlockTerminalApp(self.server_url)
        await app.run_async()
    
    async def run_interactive(self):
        """Run the interactive terminal."""
        app = HeadlockTerminalApp(self.server_url)
        await app.run_async()


@click.command()
@click.option(
    "--server", "-s",
    default=DEFAULT_SERVER_URL,
    help="Headlock server URL",
    envvar="HEADLOCK_SERVER_URL",
)
@click.option(
    "--textual/--simple",
    default=True,
    help="Use Textual terminal app (default) or simple mode",
)
def main(server: str, textual: bool):
    """Interactive terminal for Headlock MCP server."""
    if textual:
        terminal = HeadlockTerminal(server_url=server)
        asyncio.run(terminal.run_interactive())
    else:
        # Fallback to simple console mode if needed
        console.print("[yellow]Simple mode not implemented yet. Use --textual flag.[/yellow]")


if __name__ == "__main__":
    main()
