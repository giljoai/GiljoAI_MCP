# Connecting Your Project to GiljoAI MCP

## Quick Start

After installing the GiljoAI MCP server, connect your development projects:

```bash
# In your project directory
python C:\GiljoAI_MCP\connect_project.py

# Or on Windows
C:\GiljoAI_MCP\connect_project.bat
```

## What This Does

The connection script creates a `.mcp.json` file in your project that:
- Points to the MCP server location
- Configures authentication (if needed)
- Enables orchestration for your coding agent

## Manual Configuration

If you prefer manual setup, create `.mcp.json` in your project:

### For Local MCP Server

```json
{
  "mcpServers": {
    "giljo-orchestrator": {
      "command": "C:\\GiljoAI_MCP\\venv\\Scripts\\python.exe",
      "args": ["-m", "giljo_mcp"],
      "env": {
        "GILJO_MCP_HOME": "C:\\GiljoAI_MCP"
      }
    }
  }
}
```

### For Network MCP Server

```json
{
  "mcpServers": {
    "giljo-orchestrator": {
      "type": "http",
      "url": "http://server-ip:8000",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}
```

## Verification

After connecting:
1. Restart your coding agent (Claude, Cursor, etc.)
2. Type: "List available MCP tools"
3. You should see GiljoAI orchestration tools

## Troubleshooting

- **Server not found**: Check GILJO_MCP_HOME environment variable
- **Connection failed**: Ensure MCP server is running (`start_giljo.bat`)
- **No tools available**: Verify .mcp.json exists in your project