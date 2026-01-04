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

## 🚀 Quick Start

### Installation

```bash
cd agent-headlock-v4

# Install with pip
pip install -e .

# Or install dependencies directly
pip install fastapi uvicorn websockets pydantic rich click httpx mcp
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

### Running the Terminal Client

```bash
# In a new terminal window

# Option 1: Using the installed command
headlock-terminal

# Option 2: Direct Python
python -m src.terminal

# Option 3: Connect to different server
headlock-terminal --server http://localhost:8765
```

### Running an Example Agent

```bash
# In another terminal window
python examples/example_agent.py
```

## 📖 Terminal Commands

| Command | Description |
|---------|-------------|
| `list`, `ls` | List all active sessions |
| `waiting`, `w` | List sessions waiting for input |
| `select <id>` | Select a session to interact with |
| `info` | Show current session details |
| `send <instruction>` | Send instruction to selected session |
| `tap`, `tapout` | End the session (tap out) |
| `refresh`, `r` | Refresh session status |
| `watch` | Live watch for session updates |
| `help`, `?` | Show help |
| `exit`, `quit` | Exit terminal |

**Tip:** When a session is selected, you can just type your instruction directly!

## 🔌 API Endpoints

### MCP Endpoint (for AI Agents)

This server exposes an **MCP Streamable HTTP** endpoint at:

- `POST /mcp` (and related MCP traffic at the same base path)

Tools exposed:
- `headlock-enter_headlock` (optional `session_id`, optional `context`)
- `headlock-continue_headlock` (required `session_id`, optional `context`)

### Legacy HTTP Endpoints (for non-MCP Agents)

#### `POST /headlock/enter-headlock`
Enter headlock mode and wait for instruction.

```json
// Request
{
  "session_id": "optional-custom-id",
  "context": "Initial context for the user"
}

// Response (blocks until user responds)
{
  "session_id": "uuid",
  "instruction": "User's instruction",
  "should_terminate": false
}
```

#### `POST /headlock/continue-headlock`
Continue in headlock after completing a task.

```json
// Request
{
  "session_id": "uuid",
  "context": "Result of last task"
}

// Response (blocks until user responds)
{
  "session_id": "uuid",
  "instruction": "Next instruction",
  "should_terminate": false
}
```

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

### Direct HTTP (any language)

```bash
# Enter headlock (will block)
curl -X POST http://localhost:8765/headlock/enter-headlock \
  -H "Content-Type: application/json" \
  -d '{"context": "Agent ready"}'
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
agent-headlock-v4/
├── src/
│   ├── __init__.py
│   ├── server.py          # FastAPI server
│   ├── session_manager.py # Session state management
│   ├── models.py          # Pydantic models
│   ├── terminal.py        # Interactive CLI client
│   ├── client.py          # Python client for agents
│   └── mcp_tools.py       # MCP tool definitions
├── examples/
│   ├── example_agent.py   # Sync agent example
│   └── async_agent.py     # Async agent example
├── tests/
├── pyproject.toml
└── README.md
```

## 🧪 Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## 📝 License

MIT
