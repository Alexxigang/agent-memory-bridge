from __future__ import annotations

import json
from pathlib import Path

from memory_migrate_plugin.adapters.base import BaseAdapter
from memory_migrate_plugin.models import CanonicalMemoryPackage, MemoryEntry
from memory_migrate_plugin.utils import read_text, slugify, write_text


class CodexMemoriesAdapter(BaseAdapter):
    name = "codex-memories"
    description = "Simple markdown memory folder for Codex-style memory migration."

    def probe(self, path: Path) -> bool:
        return path.is_dir() and (path / "index.json").exists()

    def detect_confidence(self, path: Path) -> int:
        return 95 if self.probe(path) else 0

    def read(self, path: Path) -> CanonicalMemoryPackage:
        package = CanonicalMemoryPackage(package_id=path.name or "codex-memories", source_formats=[self.name])
        memories_dir = path / "memories"
        files = sorted(memories_dir.glob("*.md")) if memories_dir.exists() else sorted(path.glob("*.md"))
        for file_path in files:
            title = file_path.stem.replace("-", " ").title()
            package.add_entry(
                MemoryEntry(
                    id=slugify(file_path.stem),
                    kind="note",
                    title=title,
                    content=read_text(file_path).strip(),
                    tags=["codex"],
                    source_format=self.name,
                    metadata={"filename": file_path.name},
                )
            )
        return package

    def write(self, package: CanonicalMemoryPackage, path: Path) -> None:
        memories_dir = path / "memories"
        memories_dir.mkdir(parents=True, exist_ok=True)
        index_items: list[dict[str, str]] = []
        for entry in package.entries:
            filename = f"{slugify(entry.title or entry.id)}.md"
            write_text(memories_dir / filename, entry.content.rstrip() + "\n")
            index_items.append({"id": entry.id, "title": entry.title, "file": f"memories/{filename}", "kind": entry.kind})
        write_text(path / "index.json", json.dumps(index_items, indent=2, ensure_ascii=False) + "\n")
