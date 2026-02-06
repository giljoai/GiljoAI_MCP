#!/usr/bin/env python3
"""Analyze remaining docs files in graph."""

import json
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent
JSON_FILE = PROJECT_ROOT / "docs" / "cleanup" / "dependency_graph.json"

with open(JSON_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Group docs files by directory
docs_by_dir = defaultdict(list)
for node in data['nodes']:
    if node['layer'] == 'docs':
        path = node['path']
        # Get first directory component
        parts = path.replace('\\', '/').split('/')
        dir_name = parts[0] if len(parts) > 1 else 'root'
        docs_by_dir[dir_name].append(path)

print('Remaining .md files by directory:')
print('=' * 60)
for dir_name in sorted(docs_by_dir.keys()):
    files = docs_by_dir[dir_name]
    print(f'\n{dir_name}/ ({len(files)} files)')
    for f in files[:3]:
        print(f'  - {f}')
    if len(files) > 3:
        print(f'  ... and {len(files) - 3} more')

print(f'\n\nTotal: {sum(len(files) for files in docs_by_dir.values())} .md files')
print('\nThese are scattered documentation files, not in docs/ folder.')
print('Should we exclude ALL .md files from the graph?')
