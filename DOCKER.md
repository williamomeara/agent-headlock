# Docker Setup for Agent Headlock

This directory includes Docker configuration to run the Headlock MCP server in a container.

## Quick Start

### Build and run in the background:
```bash
docker-compose up -d
```

### View logs:
```bash
docker-compose logs -f headlock-server
```

### Stop the server:
```bash
docker-compose down
```

### Rebuild the image:
```bash
docker-compose up -d --build
```

## Accessing the Server

Once running, the server is available at:
- **HTTP/REST**: `http://localhost:8765`
- **WebSocket**: `ws://localhost:8765/ws`
- **Health Check**: `http://localhost:8765/health`

## Running the Terminal Client

Once the Docker server is running, you can connect to it with:

```bash
# Using the installed command (if you have the package installed locally)
headlock-terminal --server http://localhost:8765

# Or run directly with Python
python -m src.terminal --server http://localhost:8765
```

## Manual Docker Commands

If you prefer to use Docker commands directly instead of docker-compose:

### Build the image:
```bash
docker build -t agent-headlock .
```

### Run the container:
```bash
docker run -d \
  --name agent-headlock-server \
  -p 8765:8765 \
  --restart unless-stopped \
  agent-headlock
```

### View logs:
```bash
docker logs -f agent-headlock-server
```

### Stop the container:
```bash
docker stop agent-headlock-server
```

### Remove the container:
```bash
docker rm agent-headlock-server
```

## Environment Variables

You can customize the server by setting environment variables:

```bash
docker-compose.yml example:
environment:
  - HOST=0.0.0.0
  - PORT=8765
  - HEADLOCK_SERVER_URL=http://localhost:8765
```

Or with docker run:
```bash
docker run -d \
  -p 8765:8765 \
  -e HOST=0.0.0.0 \
  -e PORT=8765 \
  agent-headlock
```

## Troubleshooting

### Container won't start
```bash
docker-compose logs headlock-server
```

### Connection refused
Make sure the port 8765 is not in use:
```bash
netstat -an | grep 8765
```

### Rebuild everything from scratch
```bash
docker-compose down -v
docker-compose up -d --build
```
