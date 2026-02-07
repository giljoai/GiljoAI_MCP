#!/usr/bin/env python3
"""Fix WebSocket BLE001 violations across the codebase."""
import re
from pathlib import Path

def fix_websocket_exceptions(file_path):
    """Add noqa to WebSocket exception handlers."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # Pattern: except Exception as ws_error: (without noqa)
    pattern = r'([ \t]+)except Exception as ws_error:(?!\s*#\s*noqa)'
    replacement = r'\1except Exception as ws_error:  # noqa: BLE001 - WebSocket failures should not break core operations'

    content = re.sub(pattern, replacement, content)

    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

# Files to fix
files = [
    'src/giljo_mcp/services/message_service.py',
    'src/giljo_mcp/slash_commands/handover.py',
    'src/giljo_mcp/tools/agent_status.py',
    'src/giljo_mcp/tools/orchestration.py',
    'api/endpoints/agent_jobs/simple_handover.py',
    'api/endpoints/git.py',
]

base_dir = Path('/f/GiljoAI_MCP')
for file in files:
    file_path = base_dir / file
    if file_path.exists():
        if fix_websocket_exceptions(file_path):
            print(f"Fixed: {file}")
        else:
            print(f"No changes: {file}")
    else:
        print(f"Not found: {file}")
