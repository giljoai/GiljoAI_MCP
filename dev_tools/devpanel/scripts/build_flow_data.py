#!/usr/bin/env python3
"""Parse handovers/start_to_finish_agent_FLOW.md into structured flow JSON."""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_MD = REPO_ROOT / "handovers" / "start_to_finish_agent_FLOW.md"
OUTPUT_JSON = REPO_ROOT / "dev_tools" / "devpanel" / "frontend" / "start_to_finish_flow.json"


def parse_steps(markdown: str) -> list[dict[str, str]]:
    pattern = re.compile(r"##\s+Step\s+(\d+):\s+(.+)")
    matches = list(pattern.finditer(markdown))
    steps: list[dict[str, str]] = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(markdown)
        chunk = markdown[start:end].strip()
        bullets = []
        for line in chunk.splitlines():
            line = line.strip()
            if line.startswith("-") or line.startswith("1.") or line.startswith("["):
                bullets.append(line.lstrip("- "))
        steps.append(
            {
                "id": f"step{match.group(1)}",
                "label": f"Step {match.group(1)}\n{match.group(2).strip()}",
                "details": bullets[:8],
            }
        )
    return steps


def build_graph(steps: list[dict[str, str]]) -> dict:
    nodes = [
        {"data": {"id": step["id"], "label": step["label"], "details": step["details"]}}
        for step in steps
    ]
    edges = []
    for idx in range(len(steps) - 1):
        edges.append({"data": {"id": f"e{idx}", "source": steps[idx]["id"], "target": steps[idx + 1]["id"]}})
    return {"nodes": nodes, "edges": edges}


def main() -> None:
    if not SOURCE_MD.exists():
        raise FileNotFoundError(f"Source markdown not found: {SOURCE_MD}")
    markdown = SOURCE_MD.read_text(encoding="utf-8")
    steps = parse_steps(markdown)
    graph = build_graph(steps)
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(graph, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
