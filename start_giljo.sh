#!/bin/bash

echo "Starting GiljoAI MCP Orchestrator..."
echo "====================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.9 or later"
    exit 1
fi

# Check if virtual environment exists
if [ ! -f "venv/bin/activate" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Start the MCP server in the background
echo "Starting MCP server on port 6001..."
python -m giljo_mcp.server &
MCP_PID=$!

# Wait a moment for server to start
sleep 2

# Start the API server
echo "Starting API server on port 6002..."
python -m giljo_mcp.api_server &
API_PID=$!

# Wait for API to be ready
sleep 2

# Start the frontend development server
if [ -f "frontend/package.json" ]; then
    echo "Starting frontend on port 6000..."
    cd frontend
    npm run dev &
    FRONTEND_PID=$!
    cd ..
fi

# Open browser to dashboard (platform-specific)
sleep 3
echo "Opening dashboard in browser..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open http://localhost:6000
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    xdg-open http://localhost:6000 2>/dev/null || echo "Please open http://localhost:6000 in your browser"
fi

echo ""
echo "GiljoAI MCP Orchestrator is running!"
echo "====================================="
echo "Dashboard: http://localhost:6000"
echo "API: http://localhost:6002"
echo "MCP Server: localhost:6001"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Save PIDs to file for stop script
echo "$MCP_PID" > .giljo_pids
echo "$API_PID" >> .giljo_pids
echo "$FRONTEND_PID" >> .giljo_pids

# Wait and handle Ctrl+C
trap 'echo "Stopping services..."; kill $MCP_PID $API_PID $FRONTEND_PID 2>/dev/null; rm -f .giljo_pids; exit' INT

# Keep the script running
while true; do
    sleep 60
done