#!/usr/bin/env python3
"""Fix broken test_mcp_tools.py file"""

with open("test_mcp_tools.py", encoding="utf-8") as f:
    lines = f.readlines()

# Fix lines 287-288 (index 286-287)
if lines[286].strip().startswith('print("'):
    lines[286] = '        print("\\n[MESSAGE] Testing MESSAGE TOOLS (6 tools)")\n'
    if lines[287].strip().endswith('")'):
        lines[287] = ""  # Remove the broken continuation

# Fix lines 668-669 (index 667-668)
for i in range(len(lines)):
    if i < len(lines) - 1 and lines[i].strip().startswith('print("') and lines[i + 1].strip().startswith("[STATUS]"):
        lines[i] = '        print("\\n[STATUS] Tool Status:")\n'
        lines[i + 1] = ""

# Remove empty lines that were created
lines = [line for line in lines if line.strip() != ""]

with open("test_mcp_tools.py", "w", encoding="utf-8") as f:
    f.writelines(lines)
