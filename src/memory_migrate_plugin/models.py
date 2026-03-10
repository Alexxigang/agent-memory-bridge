from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(slots=True)
class MemoryEntry:
    id: str
    kind: str
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    source_format: str = "unknown"
    created_at: str | None = None
    updated_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CanonicalMemoryPackage:
    schema_version: str = "1.0"
    package_id: str = "memory-package"
    created_at: str = field(default_factory=utc_now_iso)
    source_formats: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    entries: list[MemoryEntry] = field(default_factory=list)

    def add_entry(self, entry: MemoryEntry) -> None:
        self.entries.append(entry)
        if entry.source_format not in self.source_formats:
            self.source_formats.append(entry.source_format)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "package_id": self.package_id,
            "created_at": self.created_at,
            "source_formats": list(self.source_formats),
            "metadata": dict(self.metadata),
            "entries": [entry.to_dict() for entry in self.entries],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CanonicalMemoryPackage":
        package = cls(
            schema_version=data.get("schema_version", "1.0"),
            package_id=data.get("package_id", "memory-package"),
            created_at=data.get("created_at", utc_now_iso()),
            source_formats=list(data.get("source_formats", [])),
            metadata=dict(data.get("metadata", {})),
        )
        for item in data.get("entries", []):
            package.entries.append(
                MemoryEntry(
                    id=item["id"],
                    kind=item.get("kind", "note"),
                    title=item.get("title", item["id"]),
                    content=item.get("content", ""),
                    tags=list(item.get("tags", [])),
                    source_format=item.get("source_format", "unknown"),
                    created_at=item.get("created_at"),
                    updated_at=item.get("updated_at"),
                    metadata=dict(item.get("metadata", {})),
                )
            )
        return package
