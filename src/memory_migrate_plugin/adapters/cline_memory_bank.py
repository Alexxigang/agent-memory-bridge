from __future__ import annotations

from pathlib import Path

from memory_migrate_plugin.adapters.base import BaseAdapter
from memory_migrate_plugin.models import CanonicalMemoryPackage, MemoryEntry
from memory_migrate_plugin.utils import read_text, slugify, write_text


DEFAULT_FILE_MAP = {
    "projectbrief.md": ("project", "Project Brief"),
    "productContext.md": ("project", "Product Context"),
    "activeContext.md": ("task", "Active Context"),
    "systemPatterns.md": ("instruction", "System Patterns"),
    "techContext.md": ("reference", "Tech Context"),
    "progress.md": ("task", "Progress"),
}


class ClineMemoryBankAdapter(BaseAdapter):
    name = "cline-memory-bank"
    description = "Memory Bank markdown layout used by Cline/Roo-style agent workflows."

    def probe(self, path: Path) -> bool:
        if not path.is_dir():
            return False
        return any((path / filename).exists() for filename in DEFAULT_FILE_MAP)

    def detect_confidence(self, path: Path) -> int:
        if not path.is_dir():
            return 0
        matches = sum(1 for filename in DEFAULT_FILE_MAP if (path / filename).exists())
        if matches == 0:
            return 0
        if matches >= 3:
            return 98
        return 75

    def read(self, path: Path) -> CanonicalMemoryPackage:
        package = CanonicalMemoryPackage(package_id=path.name or "cline-memory-bank", source_formats=[self.name])
        for filename, (kind, title) in DEFAULT_FILE_MAP.items():
            file_path = path / filename
            if not file_path.exists():
                continue
            package.add_entry(
                MemoryEntry(
                    id=slugify(filename.removesuffix(".md")),
                    kind=kind,
                    title=title,
                    content=read_text(file_path).strip(),
                    tags=["cline", "memory-bank"],
                    source_format=self.name,
                    metadata={"filename": filename},
                )
            )
        for extra_file in sorted(path.glob("*.md")):
            if extra_file.name in DEFAULT_FILE_MAP:
                continue
            package.add_entry(
                MemoryEntry(
                    id=slugify(extra_file.stem),
                    kind="note",
                    title=extra_file.stem.replace("-", " ").title(),
                    content=read_text(extra_file).strip(),
                    tags=["cline", "memory-bank", "extra"],
                    source_format=self.name,
                    metadata={"filename": extra_file.name},
                )
            )
        return package

    def write(self, package: CanonicalMemoryPackage, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        used_ids: set[str] = set()
        priorities = [
            ("project", "projectbrief.md"),
            ("project", "productContext.md"),
            ("task", "activeContext.md"),
            ("instruction", "systemPatterns.md"),
            ("reference", "techContext.md"),
            ("task", "progress.md"),
        ]
        for kind, filename in priorities:
            for entry in package.entries:
                if entry.id in used_ids or entry.kind != kind:
                    continue
                write_text(path / filename, entry.content.rstrip() + "\n")
                used_ids.add(entry.id)
                break
        for entry in package.entries:
            if entry.id in used_ids:
                continue
            write_text(path / f"{slugify(entry.title or entry.id)}.md", entry.content.rstrip() + "\n")
