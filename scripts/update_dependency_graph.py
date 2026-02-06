#!/usr/bin/env python3
"""Update dependency_graph.html with new JSON data."""

import json
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
JSON_FILE = PROJECT_ROOT / "docs" / "cleanup" / "dependency_graph.json"
HTML_FILE = PROJECT_ROOT / "docs" / "cleanup" / "dependency_graph.html"

def main():
    # Read the new JSON data
    print(f"Reading JSON from {JSON_FILE}...")
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        graph_data = json.load(f)

    print(f"Loaded {len(graph_data['nodes'])} nodes and {len(graph_data['links'])} links")

    # Read the HTML file
    print(f"Reading HTML from {HTML_FILE}...")
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Find the graphData section
    # The graphData is all on one line, followed by "const lc="
    start_marker = "const graphData="
    end_marker = "const lc="

    start_idx = html_content.find(start_marker)
    end_idx = html_content.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        print(f"ERROR: Could not find graphData section in HTML")
        print(f"  start_marker found: {start_idx != -1}")
        print(f"  end_marker found: {end_idx != -1}")
        return 1

    # Build the new graphData section (minified JSON on one line)
    graph_data_json = json.dumps(graph_data, separators=(',', ':'))
    new_graph_data = f"const graphData={graph_data_json};\n"

    # Replace the section
    new_html = (
        html_content[:start_idx] +
        new_graph_data +
        html_content[end_idx:]
    )

    # Write back
    print(f"Writing updated HTML to {HTML_FILE}...")
    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(new_html)

    print("[SUCCESS] Updated dependency_graph.html")
    print(f"   Nodes: {len(graph_data['nodes'])}")
    print(f"   Links: {len(graph_data['links'])}")

    return 0

if __name__ == "__main__":
    exit(main())
