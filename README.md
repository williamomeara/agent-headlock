# Agent Headlock MCP

**Control AI agents mid-execution with interactive terminal commands.**

Agent Headlock is an MCP (Model Context Protocol) server that enables real-time user control over AI agent execution. It creates a "headlock" mode where AI agents pause between tasks and wait for user instructions, allowing for step-by-step interactive control of AI workflows.

## 🎯 Concept

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│    AI Agent     │◄───────►│  Headlock MCP   │◄───────►│    Terminal     │
│                 │         │     Server      │         │     (User)      │
│  Enters         │         │                 │         │                 │
│  Headlock Mode  │  HTTP/  │  Holds agent    │  HTTP/  │  Sends          │
│  ───────────►   │  WS     │  state, routes  │  WS     │  instructions   │
│                 │         │  instructions   │         │  ───────────►   │
│  Waits...       │         │                 │         │                 │
│       ◄─────────│         │                 │         │  Taps out       │
│  Executes       │         │                 │         │  ───────────►   │
│  instruction    │         │                 │         │                 │
└─────────────────┘         └─────────────────┘         └─────────────────┘
```

### Flow

1. **AI Agent enters Headlock Mode** - Agent calls the MCP server and blocks
2. **User sees waiting session** - Terminal shows agent is ready for instructions
3. **User sends instruction** - Terminal sends command to MCP server
4. **Agent receives and executes** - Instruction flows to waiting agent
5. **Agent reports result** - Agent sends context back, re-enters headlock
6. **Cycle repeats** - User can send more instructions
7. **User taps out** - Sends termination signal, agent exits gracefully

## ✨ Features

- **Real-time Control**: Pause AI agents mid-execution and provide step-by-step instructions
- **MCP Integration**: Full Model Context Protocol support with streamable HTTP
- **Interactive Terminal**: Rich CLI interface for managing sessions
- **WebSocket Updates**: Live updates for session status and activity
- **Async Support**: Both synchronous and asynchronous agent clients
- **Session Management**: Track multiple concurrent AI agent sessions
- **Health Monitoring**: Built-in health checks and session statistics

## 🚀 Quick Start

### Installation

```bash
cd agent-headlock

# Install with pip
pip install -e .

# Or install dependencies directly
pip install fastapi uvicorn websockets pydantic rich click httpx python-dotenv mcp
```

### Running the Server

```bash
# Option 1: Using the installed command
headlock-server

# Option 2: Direct Python
python -m src.server

# Option 3: With uvicorn directly
uvicorn src.server:app --host 0.0.0.0 --port 8765 --reload
```

Server runs at `http://localhost:8765`

### VSCode Configuration

This project includes VSCode workspace settings that automatically activate the virtual environment in new terminals.

**Automatic Setup:**
- VSCode will automatically activate the virtual environment when opening new terminals
- The Textual terminal UI is configured as the default interface
- Shell integration is enabled for better Python support

**Manual Activation (if needed):**
```bash
# Activate the virtual environment manually
source .venv/bin/activate

# Or use the convenience script
./activate.sh

# Check if everything is set up correctly
python check_env.py
```

### Running the Terminal Client

```bash
# In a new terminal window

# Option 1: Using the installed command (Textual UI - recommended)
headlock-terminal

# Option 2: Direct Python (Textual UI)
python -m src.terminal

# Option 3: Connect to different server
headlock-terminal --server http://localhost:8765

# Option 4: Force simple mode (if needed)
headlock-terminal --simple
```

The terminal now features a modern **Textual-based UI** that provides:

- **Split-pane interface** with session sidebar and main content area
- **Code editor-like input** with proper multi-line support
- **Real-time session updates** with color-coded status
- **Mouse support** for clicking to select sessions
- **SSH-friendly** operation with reliable key bindings
- **Rich formatting** and visual feedback

## 📖 Terminal Interface

### Textual UI (Default)

The modern Textual interface provides a floating app experience:

**Layout:**
- **Left Sidebar**: Session list with status indicators
- **Main Area**: Split between output display and instruction input
- **Bottom**: Status bar with keyboard shortcuts

**Controls:**
- **Click sessions** in the sidebar to select them
- **Type instructions** in the text area (Enter creates new lines)
- **Ctrl+J** to submit instructions
- **Ctrl+R** to refresh sessions
- **Ctrl+T** to tap out current session
- **F1** for help
- **Ctrl+C** to quit

**Session States:**
- 🟢 **WAITING** - Agent ready for instructions
- 🟡 **PROCESSING** - Agent executing instruction
- 🔵 **COMPLETED** - Session finished
- 🔴 **TERMINATED** - Session ended

### Multi-line Input

The TextArea widget behaves like a code editor:
- **Enter** = New line (always)
- **Ctrl+J** = Submit instruction
- **Works perfectly over SSH**
- **Syntax highlighting ready** (can be added later)

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+J` | Submit instruction |
| `F1` | Show help |
| `F2` | Refresh sessions |
| `Ctrl+C` | Quit |

**Pro Tip:** The interface is designed to work seamlessly over SSH connections with proper key binding support.

## 🔌 API Endpoints

### MCP Endpoint (for AI Agents)

This server exposes an **MCP Streamable HTTP** endpoint at:

- `POST /mcp` (and related MCP traffic at the same base path)

Tools exposed:
- `headlock-enter_headlock` (optional `session_id`, optional `context`)
  - Enters headlock mode and blocks waiting for the user's first instruction
  - Returns `{session_id, instruction, should_terminate}`
- `headlock-continue_headlock` (required `session_id`, optional `context`)
  - Continues headlock after executing a task, sends context and waits for next instruction
  - Returns `{session_id, instruction, should_terminate}`

### Terminal Endpoints (for Users)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sessions` | GET | List all sessions |
| `/sessions/waiting` | GET | List waiting sessions |
| `/sessions/{id}` | GET | Get session details |
| `/sessions/{id}/instruct` | POST | Send instruction |
| `/sessions/{id}/tap-out` | POST | Terminate session |
| `/health` | GET | Health check |

### WebSocket Endpoints

- `ws://localhost:8765/ws` - Global updates for all sessions
- `ws://localhost:8765/ws/{session_id}` - Updates for specific session

## 🤖 Using with AI Agents

### Python Client

```python
from src.client import HeadlockClient

client = HeadlockClient("http://localhost:8765")

# Enter headlock - blocks until user sends instruction
response = client.enter_headlock(
    context="Agent ready for instructions"
)

while not response.should_terminate:
    # Execute the instruction
    result = do_something(response.instruction)
    
    # Continue in headlock with result
    response = client.continue_headlock(
        session_id=response.session_id,
        context=f"Completed: {result}"
    )

print("Session ended by user")
```

### Async Python Client

```python
from src.client import AsyncHeadlockClient

client = AsyncHeadlockClient()

response = await client.enter_headlock(context="Ready")

while not response.should_terminate:
    result = await do_task(response.instruction)
    response = await client.continue_headlock(
        session_id=response.session_id,
        context=result
    )
```

## 🔧 Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `HEADLOCK_SERVER_URL` | `http://localhost:8765` | Server URL for terminal |
| `HOST` | `0.0.0.0` | Server bind host |
| `PORT` | `8765` | Server port |

## 📁 Project Structure

```
agent-headlock/
├── src/
│   ├── __init__.py
│   ├── server.py          # FastAPI server with MCP integration
│   ├── session_manager.py # Session state management
│   ├── models.py          # Pydantic models and data structures
│   ├── terminal.py        # Interactive CLI client
│   ├── client.py          # Python client for agents
│   └── mcp_tools.py       # MCP tool definitions
├── examples/
│   ├── example_agent.py   # Synchronous agent example
│   └── async_agent.py     # Asynchronous agent example
├── tests/
│   └── __init__.py
├── pyproject.toml         # Project configuration
├── requirements.txt       # Dependencies
└── README.md
```

## 🧪 Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## 🛠️ Development

### Setting up Development Environment

```bash
# Clone and enter directory
cd agent-headlock

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Run server in development mode
uvicorn src.server:app --reload --host 0.0.0.0 --port 8765
```

### Code Quality

The project uses:
- **pytest** for testing
- **Black** for code formatting (if configured)
- **isort** for import sorting (if configured)
- **mypy** for type checking (if configured)

### Architecture

- **Server**: FastAPI-based MCP server with WebSocket support
- **Session Management**: Async event-driven session handling
- **Terminal Client**: Rich CLI with real-time updates
- **Client Libraries**: Both sync and async Python clients for agents

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📧 Contact

For questions or support, please open an issue on GitHub.
