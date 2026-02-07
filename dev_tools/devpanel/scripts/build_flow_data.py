#!/usr/bin/env python3
"""Parse handover docs into flow JSON for both the static viewer and Flow Editor."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FLOWS_DIR = REPO_ROOT / "dev_tools" / "devpanel" / "flows"
LEGACY_FLOW_JSON = REPO_ROOT / "dev_tools" / "devpanel" / "frontend" / "start_to_finish_flow.json"

FLOW_SOURCES = [
    {
        "id": "start_to_finish_agent_flow",
        "title": "Start → Finish Agent Flow",
        "source": REPO_ROOT / "handovers" / "start_to_finish_agent_FLOW.md",
        "legacy_output": LEGACY_FLOW_JSON,
    },
]


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
    nodes = [{"data": {"id": step["id"], "label": step["label"], "details": step["details"]}} for step in steps]
    edges = []
    for idx in range(len(steps) - 1):
        edges.append({"data": {"id": f"e{idx}", "source": steps[idx]["id"], "target": steps[idx + 1]["id"]}})
    return {"nodes": nodes, "edges": edges}


def build_flow_editor_seed(flow_id: str, title: str, source_path: Path, steps: list[dict[str, str]]) -> dict:
    spacing_y = 140
    nodes = []
    edges = []
    for idx, step in enumerate(steps):
        nodes.append(
            {
                "id": step["id"],
                "type": "default",
                "position": {"x": 80, "y": idx * spacing_y},
                "data": {
                    "label": step["label"],
                    "description": "\n".join(step["details"]),
                    "notes": step["details"],
                    "code_reference": "",
                    "status": "draft",
                },
            }
        )
        if idx + 1 < len(steps):
            edges.append(
                {
                    "id": f"edge-{idx}",
                    "source": step["id"],
                    "target": steps[idx + 1]["id"],
                    "data": {"label": ""},
                }
            )

    return {
        "id": flow_id,
        "title": title,
        "source": str(source_path.relative_to(REPO_ROOT)),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "nodes": nodes,
        "edges": edges,
        "layout": {"direction": "vertical", "spacing": spacing_y},
    }


def process_flow(source: dict[str, Path | str]) -> None:
    path = source["source"]
    assert isinstance(path, Path)
    if not path.exists():
        raise FileNotFoundError(f"Source markdown not found: {path}")
    markdown = path.read_text(encoding="utf-8")
    steps = parse_steps(markdown)

    legacy_graph = build_graph(steps)
    legacy_path = source["legacy_output"]
    assert isinstance(legacy_path, Path)
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text(json.dumps(legacy_graph, indent=2), encoding="utf-8")

    editor_seed = build_flow_editor_seed(source["id"], source["title"], path, steps)
    FLOWS_DIR.mkdir(parents=True, exist_ok=True)
    editor_path = FLOWS_DIR / f"{source['id']}.json"
    editor_path.write_text(json.dumps(editor_seed, indent=2), encoding="utf-8")


def main() -> None:
    for cfg in FLOW_SOURCES:
        process_flow(cfg)


if __name__ == "__main__":
    main()
