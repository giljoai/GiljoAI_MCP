
import os
import re
import json
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path("F:/GiljoAI_MCP")
BS = chr(92)

files_by_layer = {
    "model": [],
    "service": [],
    "api": [],
    "frontend": [],
    "test": [],
    "config": [],
    "docs": []
}

path_to_id = {}
id_to_path = {}
dependencies = defaultdict(set)
dependents = defaultdict(set)
file_metadata = {}
id_counter = 0

def get_layer(file_path):
    fp = file_path.replace(BS, "/")
    fp_lower = fp.lower()
    
    if "/tests/" in fp_lower or "__tests__" in fp_lower:
        return "test"
    if fp.endswith(".spec.js") or fp.endswith(".spec.ts") or fp.endswith(".test.js") or fp.endswith(".test.ts"):
        return "test"
    filename = fp.split("/")[-1]
    if filename.startswith("test_"):
        return "test"
    
    if "/docs/" in fp_lower or "/handovers/" in fp_lower:
        return "docs"
    if fp.endswith(".md") and "/src/" not in fp_lower and "/api/" not in fp_lower:
        return "docs"
    
    if "/frontend/src/" in fp_lower:
        return "frontend"
    
    if "src/giljo_mcp/models/" in fp:
        return "model"
    
    if "src/giljo_mcp/services/" in fp:
        return "service"
    
    if "src/giljo_mcp/repositories/" in fp:
        return "model"
    
    if "src/giljo_mcp/config/" in fp:
        return "config"
    
    if "/api/" in fp_lower:
        return "api"
    
    if "src/giljo_mcp/" in fp:
        return "api"
    
    return "api"

print("Script loaded successfully")
