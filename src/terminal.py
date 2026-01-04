#!/usr/bin/env python3
"""Interactive terminal client for Headlock MCP server."""

import asyncio
import json
import sys
from datetime import datetime
from typing import Optional

import click
import httpx
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt
from rich.layout import Layout
from rich.markdown import Markdown

console = Console()

DEFAULT_SERVER_URL = "http://localhost:8765"


class HeadlockTerminal:
    """Interactive terminal for controlling headlock sessions."""
    
    def __init__(self, server_url: str = DEFAULT_SERVER_URL):
        self.server_url = server_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)
        self.current_session: Optional[str] = None
        self.running = True
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def check_health(self) -> bool:
        """Check if the server is running."""
        try:
            response = await self.client.get(f"{self.server_url}/health")
            return response.status_code == 200
        except Exception:
            return False
    
    async def list_sessions(self) -> list[dict]:
        """Get all active sessions."""
        try:
            response = await self.client.get(f"{self.server_url}/sessions")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            console.print(f"[red]Error listing sessions: {e}[/red]")
            return []
    
    async def list_waiting_sessions(self) -> list[dict]:
        """Get sessions waiting for input."""
        try:
            response = await self.client.get(f"{self.server_url}/sessions/waiting")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            console.print(f"[red]Error listing waiting sessions: {e}[/red]")
            return []
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get a specific session."""
        try:
            response = await self.client.get(f"{self.server_url}/sessions/{session_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception as e:
            console.print(f"[red]Error getting session: {e}[/red]")
            return None
    
    async def send_instruction(self, session_id: str, instruction: str) -> bool:
        """Send an instruction to a session."""
        try:
            response = await self.client.post(
                f"{self.server_url}/sessions/{session_id}/instruct",
                json={"instruction": instruction}
            )
            response.raise_for_status()
            result = response.json()
            return result.get("success", False)
        except Exception as e:
            console.print(f"[red]Error sending instruction: {e}[/red]")
            return False
    
    async def tap_out(self, session_id: str) -> bool:
        """Send tap out signal to a session."""
        try:
            response = await self.client.post(
                f"{self.server_url}/sessions/{session_id}/tap-out"
            )
            response.raise_for_status()
            result = response.json()
            return result.get("success", False)
        except Exception as e:
            console.print(f"[red]Error sending tap out: {e}[/red]")
            return False
    
    def display_sessions_table(self, sessions: list[dict]):
        """Display sessions in a table format."""
        if not sessions:
            console.print("[yellow]No active sessions[/yellow]")
            return
        
        table = Table(title="Headlock Sessions", show_header=True, header_style="bold magenta")
        table.add_column("Session ID", style="cyan", no_wrap=True)
        table.add_column("State", style="green")
        table.add_column("Context", style="white", max_width=50)
        table.add_column("Updated", style="dim")
        
        for session in sessions:
            state = session.get("state", "unknown")
            state_style = {
                "waiting": "[bold green]WAITING[/bold green]",
                "processing": "[bold yellow]PROCESSING[/bold yellow]",
                "completed": "[dim]COMPLETED[/dim]",
                "terminated": "[red]TERMINATED[/red]",
            }.get(state, state)
            
            context = session.get("agent_context") or session.get("last_response") or "-"
            if len(context) > 50:
                context = context[:47] + "..."
            
            updated = session.get("updated_at", "")
            if updated:
                try:
                    dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    updated = dt.strftime("%H:%M:%S")
                except Exception:
                    pass
            
            # Shorten session ID for display
            session_id = session.get("session_id", "")
            short_id = session_id[:8] + "..." if len(session_id) > 12 else session_id
            
            table.add_row(short_id, state_style, context, updated)
        
        console.print(table)
    
    def display_session_detail(self, session: dict):
        """Display detailed session information."""
        session_id = session.get("session_id", "unknown")
        state = session.get("state", "unknown")
        context = session.get("agent_context") or "No context available"
        last_response = session.get("last_response") or "No response yet"
        
        state_color = {
            "waiting": "green",
            "processing": "yellow",
            "completed": "blue",
            "terminated": "red",
        }.get(state, "white")
        
        panel_content = f"""[bold]Session ID:[/bold] {session_id}
[bold]State:[/bold] [{state_color}]{state.upper()}[/{state_color}]
[bold]Created:[/bold] {session.get('created_at', 'N/A')}
[bold]Updated:[/bold] {session.get('updated_at', 'N/A')}

[bold]Agent Context/Last Response:[/bold]
{last_response}
"""
        console.print(Panel(panel_content, title="Session Details", border_style=state_color))
    
    def print_help(self):
        """Print available commands."""
        help_text = """
[bold cyan]Available Commands:[/bold cyan]

  [green]list[/green], [green]ls[/green]              List all active sessions
  [green]waiting[/green], [green]w[/green]           List sessions waiting for input
  [green]select[/green] <id>          Select a session to interact with
  [green]info[/green]                 Show current session details
  [green]send[/green] <instruction>   Send instruction to current session
  [green]tap[/green], [green]tapout[/green]          Send tap out signal to end session
  [green]refresh[/green], [green]r[/green]           Refresh current session status
  [green]watch[/green]                Watch for session updates (Ctrl+C to stop)
  [green]clear[/green]                Clear the screen
  [green]help[/green], [green]?[/green]              Show this help
  [green]exit[/green], [green]quit[/green], [green]q[/green]       Exit the terminal

[dim]Tip: You can also just type your instruction directly when a session is selected![/dim]
"""
        console.print(Panel(help_text, title="Help", border_style="cyan"))
    
    async def watch_sessions(self):
        """Watch for session updates."""
        console.print("[dim]Watching for session updates... (Ctrl+C to stop)[/dim]")
        try:
            while True:
                sessions = await self.list_waiting_sessions()
                console.clear()
                console.print(f"[dim]Watching sessions - {datetime.now().strftime('%H:%M:%S')}[/dim]")
                self.display_sessions_table(sessions)
                await asyncio.sleep(2)
        except KeyboardInterrupt:
            console.print("\n[dim]Stopped watching[/dim]")
    
    async def interactive_loop(self):
        """Main interactive loop."""
        console.print(Panel.fit(
            "[bold cyan]Headlock Terminal[/bold cyan]\n"
            f"[dim]Connected to {self.server_url}[/dim]\n"
            "[dim]Type 'help' for available commands[/dim]",
            border_style="cyan"
        ))
        
        # Check server health
        if not await self.check_health():
            console.print("[red]Warning: Cannot connect to server. Make sure it's running.[/red]")
        
        while self.running:
            try:
                # Build prompt
                if self.current_session:
                    short_id = self.current_session[:8]
                    prompt_text = f"[cyan]headlock[/cyan]:[green]{short_id}[/green]> "
                else:
                    prompt_text = "[cyan]headlock[/cyan]> "
                
                # Get user input
                user_input = Prompt.ask(prompt_text).strip()
                
                if not user_input:
                    continue
                
                # Parse command
                parts = user_input.split(maxsplit=1)
                command = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""
                
                # Handle commands
                if command in ("exit", "quit", "q"):
                    self.running = False
                    console.print("[dim]Goodbye![/dim]")
                
                elif command in ("help", "?"):
                    self.print_help()
                
                elif command in ("list", "ls"):
                    sessions = await self.list_sessions()
                    self.display_sessions_table(sessions)
                
                elif command in ("waiting", "w"):
                    sessions = await self.list_waiting_sessions()
                    self.display_sessions_table(sessions)
                
                elif command == "select":
                    if not args:
                        # Show sessions and let user pick
                        sessions = await self.list_sessions()
                        if not sessions:
                            console.print("[yellow]No sessions available[/yellow]")
                            continue
                        
                        self.display_sessions_table(sessions)
                        session_id = Prompt.ask("Enter session ID (or partial)")
                        
                        # Find matching session
                        matching = [s for s in sessions if s["session_id"].startswith(session_id)]
                        if len(matching) == 1:
                            self.current_session = matching[0]["session_id"]
                            console.print(f"[green]Selected session: {self.current_session}[/green]")
                        elif len(matching) > 1:
                            console.print("[yellow]Multiple matches, be more specific[/yellow]")
                        else:
                            console.print("[red]No matching session found[/red]")
                    else:
                        # Direct selection
                        sessions = await self.list_sessions()
                        matching = [s for s in sessions if s["session_id"].startswith(args)]
                        if len(matching) == 1:
                            self.current_session = matching[0]["session_id"]
                            console.print(f"[green]Selected session: {self.current_session}[/green]")
                        elif len(matching) > 1:
                            console.print("[yellow]Multiple matches, be more specific[/yellow]")
                        else:
                            console.print("[red]No matching session found[/red]")
                
                elif command == "info":
                    if not self.current_session:
                        console.print("[yellow]No session selected. Use 'select' first.[/yellow]")
                        continue
                    
                    session = await self.get_session(self.current_session)
                    if session:
                        self.display_session_detail(session)
                    else:
                        console.print("[red]Session not found[/red]")
                        self.current_session = None
                
                elif command == "send":
                    if not self.current_session:
                        console.print("[yellow]No session selected. Use 'select' first.[/yellow]")
                        continue
                    
                    if not args:
                        args = Prompt.ask("Enter instruction")
                    
                    if args:
                        success = await self.send_instruction(self.current_session, args)
                        if success:
                            console.print("[green]✓ Instruction sent[/green]")
                        else:
                            console.print("[red]Failed to send instruction[/red]")
                
                elif command in ("tap", "tapout", "tap-out"):
                    if not self.current_session:
                        console.print("[yellow]No session selected. Use 'select' first.[/yellow]")
                        continue
                    
                    confirm = Prompt.ask("Are you sure you want to tap out? (y/n)", default="n")
                    if confirm.lower() == "y":
                        success = await self.tap_out(self.current_session)
                        if success:
                            console.print("[green]✓ Tap out signal sent[/green]")
                            self.current_session = None
                        else:
                            console.print("[red]Failed to send tap out[/red]")
                
                elif command in ("refresh", "r"):
                    if self.current_session:
                        session = await self.get_session(self.current_session)
                        if session:
                            self.display_session_detail(session)
                        else:
                            console.print("[red]Session not found[/red]")
                            self.current_session = None
                    else:
                        sessions = await self.list_sessions()
                        self.display_sessions_table(sessions)
                
                elif command == "watch":
                    await self.watch_sessions()
                
                elif command == "clear":
                    console.clear()
                
                else:
                    # If a session is selected, treat unknown input as instruction
                    if self.current_session:
                        success = await self.send_instruction(self.current_session, user_input)
                        if success:
                            console.print("[green]✓ Instruction sent[/green]")
                        else:
                            console.print("[red]Failed to send instruction[/red]")
                    else:
                        console.print(f"[red]Unknown command: {command}[/red]")
                        console.print("[dim]Type 'help' for available commands[/dim]")
            
            except KeyboardInterrupt:
                console.print("\n[dim]Use 'exit' or 'quit' to exit[/dim]")
            except EOFError:
                self.running = False
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")


@click.command()
@click.option(
    "--server", "-s",
    default=DEFAULT_SERVER_URL,
    help="Headlock server URL",
    envvar="HEADLOCK_SERVER_URL",
)
@click.option(
    "--command", "-c",
    default=None,
    help="Execute a single command and exit",
)
def main(server: str, command: Optional[str]):
    """Interactive terminal for Headlock MCP server."""
    terminal = HeadlockTerminal(server_url=server)
    
    async def run():
        try:
            if command:
                # Execute single command
                parts = command.split(maxsplit=1)
                cmd = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""
                
                if cmd in ("list", "ls"):
                    sessions = await terminal.list_sessions()
                    terminal.display_sessions_table(sessions)
                elif cmd in ("waiting", "w"):
                    sessions = await terminal.list_waiting_sessions()
                    terminal.display_sessions_table(sessions)
                else:
                    console.print(f"[red]Unknown command: {cmd}[/red]")
            else:
                await terminal.interactive_loop()
        finally:
            await terminal.close()
    
    asyncio.run(run())


if __name__ == "__main__":
    main()
