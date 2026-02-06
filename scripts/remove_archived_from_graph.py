#!/usr/bin/env python3
"""Remove archived files from dependency graph."""

import json
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
JSON_FILE = PROJECT_ROOT / "docs" / "cleanup" / "dependency_graph.json"

def main():
    print(f"Reading JSON from {JSON_FILE}...")
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        graph_data = json.load(f)

    original_node_count = len(graph_data['nodes'])
    original_link_count = len(graph_data['links'])
    print(f"Original: {original_node_count} nodes, {original_link_count} links")

    # Filter out archived nodes
    archived_ids = set()
    filtered_nodes = []

    for node in graph_data['nodes']:
        path = node['path']
        # Check if path contains Archive or archive folder
        if 'Archive' in path or 'archive' in path or '\\Archive\\' in path or '/Archive/' in path:
            archived_ids.add(node['id'])
            print(f"  Removing archived: {path}")
        else:
            filtered_nodes.append(node)

    # Re-index nodes (IDs need to be sequential 0, 1, 2...)
    old_id_to_new_id = {}
    for new_id, node in enumerate(filtered_nodes):
        old_id = node['id']
        old_id_to_new_id[old_id] = new_id
        node['id'] = new_id

    # Update dependents and dependencies in nodes
    for node in filtered_nodes:
        # Filter out archived IDs and remap
        node['dependents'] = [
            old_id_to_new_id[dep_id]
            for dep_id in node['dependents']
            if dep_id not in archived_ids and dep_id in old_id_to_new_id
        ]
        node['dependencies'] = [
            old_id_to_new_id[dep_id]
            for dep_id in node['dependencies']
            if dep_id not in archived_ids and dep_id in old_id_to_new_id
        ]

    # Filter and remap links
    filtered_links = []
    for link in graph_data['links']:
        source = link['source']
        target = link['target']

        # Skip if either end is archived
        if source in archived_ids or target in archived_ids:
            continue

        # Remap IDs
        if source in old_id_to_new_id and target in old_id_to_new_id:
            filtered_links.append({
                'source': old_id_to_new_id[source],
                'target': old_id_to_new_id[target]
            })

    # Update graph data
    graph_data['nodes'] = filtered_nodes
    graph_data['links'] = filtered_links

    # Save filtered data
    print(f"Writing filtered JSON...")
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(graph_data, f, indent=2)

    new_node_count = len(graph_data['nodes'])
    new_link_count = len(graph_data['links'])

    print(f"\n[SUCCESS] Filtered dependency graph")
    print(f"  Nodes: {original_node_count} -> {new_node_count} (removed {original_node_count - new_node_count})")
    print(f"  Links: {original_link_count} -> {new_link_count} (removed {original_link_count - new_link_count})")

    return 0

if __name__ == "__main__":
    exit(main())
