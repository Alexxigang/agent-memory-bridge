from __future__ import annotations

from pathlib import Path

from memory_migrate_plugin.adapters.base import BaseAdapter
from memory_migrate_plugin.models import CanonicalMemoryPackage, MemoryEntry
from memory_migrate_plugin.utils import load_json, write_json


class GenericJsonAdapter(BaseAdapter):
    name = "generic-json"
    description = "JSON import/export using the canonical package schema or a simple entries list."

    def read(self, path: Path) -> CanonicalMemoryPackage:
        data = load_json(path)
        if isinstance(data, dict) and "entries" in data:
            package = CanonicalMemoryPackage.from_dict(data)
            if "generic-json" not in package.source_formats:
                package.source_formats.append("generic-json")
            return package

        if isinstance(data, list):
            package = CanonicalMemoryPackage(package_id=path.stem, source_formats=[self.name])
            for index, item in enumerate(data, start=1):
                if not isinstance(item, dict):
                    continue
                package.add_entry(
                    MemoryEntry(
                        id=str(item.get("id", f"entry-{index}")),
                        kind=item.get("kind", "note"),
                        title=item.get("title", f"Entry {index}"),
                        content=item.get("content", ""),
                        tags=list(item.get("tags", [])),
                        source_format=self.name,
                        created_at=item.get("created_at"),
                        updated_at=item.get("updated_at"),
                        metadata=dict(item.get("metadata", {})),
                    )
                )
            return package

        raise ValueError(f"Unsupported JSON structure in {path}")

    def write(self, package: CanonicalMemoryPackage, path: Path) -> None:
        write_json(path, package.to_dict())
