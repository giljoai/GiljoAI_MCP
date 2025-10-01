# GiljoAI MCP Coding Orchestrator - Installation Guide

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Installation](#detailed-installation)
- [Configuration](#configuration)
- [Running the System](#running-the-system)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

- **Python 3.11 or higher** - [Download](https://www.python.org/downloads/)
- **Node.js 18+ and npm** - [Download](https://nodejs.org/) (for frontend)
- **Terminal Access**:
  - Windows: PowerShell, Command Prompt, or Git Bash
  - Mac/Linux: Terminal

### Optional Software

- **PostgreSQL 14+** - For production deployments
- **Redis** - For advanced caching (production)
- **Docker** - For containerized deployment

## Quick Start

### The Installation Flow

**CRITICAL**: The installation scripts are the TRUE entry points. They handle Python installation FIRST, then launch the rest of the system.

```
install.bat (Windows) / quickstart.sh (Mac/Linux)
    ↓ Checks for Python, installs if missing
bootstrap.py
    ↓ Checks dependencies, detects GUI
setup.py or setup_gui.py
    ↓ Configures application
System Ready!
```

### Current Installation Process

#### Windows Users

```batch
# Run the installation script
install.bat
```

#### Mac/Linux Users

```bash
# Make the script executable and run
chmod +x quickstart.sh
./quickstart.sh
```

This will set up your environment and install Python dependencies.

## Detailed Installation

### Step 1: Install Python Dependencies

```bash
# Create a virtual environment (recommended)
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

### Step 2: Set Up Configuration

```bash
# Copy the example configuration files
cp config.yaml.example config.yaml
cp .env.example .env
```

Edit `config.yaml` to match your needs. Key settings:

```yaml
database:
  database_type: postgresql
  host: localhost
  port: 5432
  database: giljo_mcp

server:
  mode: local
  host: localhost
  ports:
    mcp: 6001
    api: 6002
    frontend: 6000

tenant:
  enable_multi_tenant: false

app:
  name: "GiljoAI MCP Orchestrator"
  version: "1.0.0"
```

### Step 3: Initialize the Database

```bash
# Create data directory
mkdir -p data

# Run database setup
python -c "from src.giljo_mcp.database import init_db; init_db()"
```

### Step 4: Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

### Step 5: Run the MCP Server

The MCP server can be run in different modes:

#### Option A: Run as MCP Server (for use with Claude Desktop)

```bash
python -m giljo_mcp.mcp_server
```

#### Option B: Run Full Stack (API + Frontend)

```bash
# Terminal 1: Start the API server
python -m api.main

# Terminal 2: Start the frontend
cd frontend
npm run dev
```

### Step 6: Verify Installation

1. MCP Server: Check that it's running on `localhost:6001`
2. API Server: Visit `http://localhost:6002/health`
3. Frontend: Open `http://localhost:6000` in your browser

## Configuration for Claude Desktop

To use with Claude Desktop, add this to your Claude Desktop config:

```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "python",
      "args": ["-m", "giljo_mcp.mcp_server"],
      "cwd": "C:\\Projects\\installed",
      "env": {
        "PYTHONPATH": "C:\\Projects\\installed\\src"
      }
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **Module not found errors**: Make sure you're in the correct directory and have activated your virtual environment.

2. **Port already in use**: Change the port numbers in `config.yaml`

3. **Database errors**: Ensure the data directory exists and has write permissions

4. **Frontend build errors**: Make sure Node.js 18+ is installed

### Getting Help

- Check the README.md for more detailed documentation
- Report issues at: https://github.com/yourusername/giljo-mcp/issues

## Next Steps

- Read the full documentation in README.md
- Explore the examples directory for usage patterns
- Configure multi-tenant mode for enterprise use
- Set up PostgreSQL for production deployments
