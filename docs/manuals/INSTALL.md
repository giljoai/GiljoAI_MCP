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

### PostgreSQL 18 Requirement

- **PostgreSQL 18** is the ONLY supported database for GiljoAI MCP
- **Recommended**: Install PostgreSQL 18 before running the installer
- **Auto-Install Option**: The CLI installer can automatically install PostgreSQL 18 if not detected

## Quick Start

### The Installation Flow

**CRITICAL**: The CLI installer is the TRUE entry point. It handles all system configuration.

```
python install.py
    ↓ Checks for dependencies
    ↓ Configures PostgreSQL 18
    ↓ Sets up application
System Ready!
```

### Current Installation Process

```bash
# Clone the repository
git clone https://github.com/patrik-giljoai/GiljoAI-MCP.git
cd GiljoAI_MCP

# Run the CLI installer
python install.py
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
  type: postgresql  # Only option
  host: localhost
  port: 5432
  database: giljo_mcp

server:
  mode: localhost   # localhost or server
  host: localhost
  ports:
    api: 7272
    frontend: 7274

tenant:
  multi_tenant: false  # Future feature

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

The MCP server can be run in two modes:

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

1. API Server: Visit `http://localhost:7272/health`
2. Frontend: Open `http://localhost:7274` in your browser

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

3. **Database errors**: Ensure PostgreSQL 18 is installed and configured correctly

4. **Frontend build errors**: Make sure Node.js 18+ is installed

### Getting Help

- Check the README.md for more detailed documentation
- Report issues at: https://github.com/yourusername/giljo-mcp/issues

## Next Steps

- Read the full documentation in README.md
- Explore the examples directory for usage patterns
- Configure your preferred installation mode (localhost or server)