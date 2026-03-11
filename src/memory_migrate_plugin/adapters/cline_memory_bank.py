from __future__ import annotations

from pathlib import Path

from memory_migrate_plugin.adapters.base import BaseAdapter
from memory_migrate_plugin.models import CanonicalMemoryPackage, MemoryEntry
from memory_migrate_plugin.utils import read_text, slugify, write_text


DEFAULT_FILE_MAP = {
    "projectbrief.md": ("project", "Project Brief", ["cline", "roo", "memory-bank", "project"]),
    "productContext.md": ("project", "Product Context", ["cline", "roo", "memory-bank", "product"]),
    "activeContext.md": ("task", "Active Context", ["cline", "roo", "memory-bank", "active"]),
    "systemPatterns.md": ("instruction", "System Patterns", ["cline", "roo", "memory-bank", "patterns"]),
    "techContext.md": ("reference", "Tech Context", ["cline", "roo", "memory-bank", "tech"]),
    "progress.md": ("task", "Progress", ["cline", "roo", "memory-bank", "progress"]),
    "decisionLog.md": ("decision", "Decision Log", ["cline", "roo", "memory-bank", "decision"]),
    "userContext.md": ("profile", "User Context", ["cline", "roo", "memory-bank", "user"]),
}

WRITE_PRIORITY = [
    ("projectbrief.md", {"project"}),
    ("productContext.md", {"project"}),
    ("activeContext.md", {"task"}),
    ("systemPatterns.md", {"instruction"}),
    ("techContext.md", {"reference"}),
    ("progress.md", {"task"}),
    ("decisionLog.md", {"decision"}),
    ("userContext.md", {"profile"}),
]


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
        if matches >= 4:
            return 99
        if matches >= 2:
            return 88
        return 75

    def read(self, path: Path) -> CanonicalMemoryPackage:
        package = CanonicalMemoryPackage(package_id=path.name or "cline-memory-bank", source_formats=[self.name])
        for filename, (kind, title, tags) in DEFAULT_FILE_MAP.items():
            file_path = path / filename
            if not file_path.exists():
                continue
            package.add_entry(
                MemoryEntry(
                    id=slugify(filename.removesuffix(".md")),
                    kind=kind,
                    title=title,
                    content=read_text(file_path).strip(),
                    tags=list(tags),
                    source_format=self.name,
                    metadata={"filename": filename, "standard_slot": filename.removesuffix(".md")},
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
                    tags=["cline", "roo", "memory-bank", "extra"],
                    source_format=self.name,
                    metadata={"filename": extra_file.name},
                )
            )
        return package

    def write(self, package: CanonicalMemoryPackage, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        used_ids: set[str] = set()

        for filename, accepted_kinds in WRITE_PRIORITY:
            matched_entry = None
            for entry in package.entries:
                if entry.id in used_ids:
                    continue
                target_filename = entry.metadata.get("filename") if isinstance(entry.metadata, dict) else None
                if target_filename == filename:
                    matched_entry = entry
                    break
            if matched_entry is None:
                for entry in package.entries:
                    if entry.id in used_ids or entry.kind not in accepted_kinds:
                        continue
                    matched_entry = entry
                    break
            if matched_entry is None:
                continue
            write_text(path / filename, matched_entry.content.rstrip() + "\n")
            used_ids.add(matched_entry.id)

        for entry in package.entries:
            if entry.id in used_ids:
                continue
            filename = entry.metadata.get("filename") if isinstance(entry.metadata, dict) else None
            if not filename:
                filename = f"{slugify(entry.title or entry.id)}.md"
            write_text(path / filename, entry.content.rstrip() + "\n")
