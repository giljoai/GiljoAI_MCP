#!/bin/bash

echo "Stopping GiljoAI MCP Orchestrator..."

# Try to read PIDs from file first (if started with start_giljo.sh)
if [ -f .giljo_pids ]; then
    echo "Reading PIDs from .giljo_pids file..."
    while read pid; do
        if [ ! -z "$pid" ]; then
            kill $pid 2>/dev/null && echo "Stopped process $pid"
        fi
    done < .giljo_pids
    rm -f .giljo_pids
fi

# Also try to find and kill processes by port (fallback method)
echo "Checking for processes on service ports..."

# Function to kill process on port
kill_port() {
    local port=$1
    local pid=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$pid" ]; then
        kill $pid 2>/dev/null && echo "Stopped process on port $port (PID: $pid)"
    fi
}

# Kill processes on known ports
kill_port 6000  # Frontend
kill_port 6001  # MCP Server
kill_port 6002  # API Server
kill_port 6003  # WebSocket

# Also try to kill Python processes running our services
pkill -f "giljo_mcp.server" 2>/dev/null && echo "Stopped MCP server"
pkill -f "giljo_mcp.api_server" 2>/dev/null && echo "Stopped API server"

# Kill node processes running frontend
pkill -f "npm run dev" 2>/dev/null && echo "Stopped frontend dev server"

echo "All services stopped."