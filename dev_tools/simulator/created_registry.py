import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class CreatedRegistry:
    base_dir: Path
    filename: str = "created.json"
    items: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "products": [],
            "projects": [],
            "tasks": [],
            "messages": [],
            "agent_jobs": [],
        }
    )

    def __post_init__(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._path = self.base_dir / self.filename
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text())
                if isinstance(data, dict):
                    for k, v in data.items():
                        if k in self.items and isinstance(v, list):
                            self.items[k] = v
            except Exception:
                pass

    def save(self) -> None:
        self._path.write_text(json.dumps(self.items, indent=2))

    def add(self, kind: str, id_: str) -> None:
        if kind not in self.items:
            self.items[kind] = []
        self.items[kind].append(id_)
        self.save()

    def remove(self, kind: str, id_: str) -> None:
        if kind in self.items and id_ in self.items[kind]:
            self.items[kind].remove(id_)
            self.save()

    def clear_kind(self, kind: str) -> None:
        self.items[kind] = []
        self.save()

    def clear_all(self) -> None:
        for k in list(self.items.keys()):
            self.items[k] = []
        self.save()
