#!/usr/bin/env python3
"""Add production vs test dependency breakdown to hub files table."""

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent
JSON_FILE = PROJECT_ROOT / "docs" / "cleanup" / "dependency_graph.json"


def classify_dependents(graph_data, node):
    """Classify dependents into production vs test/other."""
    production = 0
    test = 0

    # Build lookup for node layers
    node_layers = {n["id"]: n["layer"] for n in graph_data["nodes"]}

    for dep_id in node["dependents"]:
        layer = node_layers.get(dep_id, "unknown")
        if layer == "test":
            test += 1
        else:
            production += 1

    return production, test


def main():
    print(f"Reading JSON from {JSON_FILE}...")
    with open(JSON_FILE, encoding="utf-8") as f:
        graph_data = json.load(f)

    # Analyze hub files with breakdown
    print("\n=== Hub Files Breakdown (50+ total dependents) ===\n")

    hub_analysis = []
    for node in graph_data["nodes"]:
        total_deps = len(node["dependents"])
        if total_deps >= 50:
            prod, test = classify_dependents(graph_data, node)

            hub_analysis.append(
                {
                    "path": node["path"],
                    "layer": node["layer"],
                    "total": total_deps,
                    "production": prod,
                    "test": test,
                    "ratio": f"{(prod / total_deps * 100):.1f}% prod" if total_deps > 0 else "N/A",
                }
            )

    # Sort by total dependents
    hub_analysis.sort(key=lambda x: x["total"], reverse=True)

    # Print results
    print(f"{'File':<50} {'Total':>7} {'Prod':>6} {'Test':>6} {'Ratio':>10}")
    print("=" * 90)

    for item in hub_analysis:
        print(f"{item['path']:<50} {item['total']:>7} {item['production']:>6} {item['test']:>6} {item['ratio']:>10}")

    # Update JSON with breakdown data
    print(f"\nAdding breakdown data to nodes in {JSON_FILE}...")

    for node in graph_data["nodes"]:
        prod, test = classify_dependents(graph_data, node)
        node["production_dependents"] = prod
        node["test_dependents"] = test

    # Save updated JSON
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2)

    print(f"[SUCCESS] Updated {len(graph_data['nodes'])} nodes with dependency breakdown")
    print("\nNext step: Run update_dependency_graph.py to refresh HTML")

    return 0


if __name__ == "__main__":
    exit(main())
