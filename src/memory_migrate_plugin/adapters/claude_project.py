from __future__ import annotations

from pathlib import Path

from memory_migrate_plugin.adapters.base import BaseAdapter
from memory_migrate_plugin.models import CanonicalMemoryPackage, MemoryEntry
from memory_migrate_plugin.utils import read_text, slugify, write_text


class ClaudeProjectAdapter(BaseAdapter):
    name = "claude-project"
    description = "Claude-style project memory using CLAUDE.md and optional companion memory notes."

    def probe(self, path: Path) -> bool:
        if path.is_file() and path.name.lower() == "claude.md":
            return True
        if not path.is_dir():
            return False
        return (path / "CLAUDE.md").exists() or (path / ".claude" / "CLAUDE.md").exists()

    def detect_confidence(self, path: Path) -> int:
        if not self.probe(path):
            return 0
        if path.is_file():
            return 92
        score = 92
        if (path / ".claude" / "memories").exists() or (path / "memories").exists():
            score += 4
        return min(score, 98)

    def _resolve_layout(self, path: Path) -> tuple[Path, list[Path]]:
        if path.is_file():
            return path, []

        main_candidates = [path / "CLAUDE.md", path / ".claude" / "CLAUDE.md"]
        main_file = next((candidate for candidate in main_candidates if candidate.exists()), path / "CLAUDE.md")

        memory_dirs = [path / ".claude" / "memories", path / "memories"]
        extra_files: list[Path] = []
        for memory_dir in memory_dirs:
            if memory_dir.exists():
                extra_files.extend(sorted(memory_dir.glob("*.md")))
        return main_file, extra_files

    def read(self, path: Path) -> CanonicalMemoryPackage:
        main_file, extra_files = self._resolve_layout(path)
        package = CanonicalMemoryPackage(package_id=main_file.parent.name or "claude-project", source_formats=[self.name])
        if main_file.exists():
            package.add_entry(
                MemoryEntry(
                    id="claude-project-memory",
                    kind="instruction",
                    title="Claude Project Memory",
                    content=read_text(main_file).strip(),
                    tags=["claude", "project-memory"],
                    source_format=self.name,
                    metadata={"filename": main_file.name},
                )
            )

        for file_path in extra_files:
            package.add_entry(
                MemoryEntry(
                    id=slugify(file_path.stem),
                    kind="note",
                    title=file_path.stem.replace("-", " ").title(),
                    content=read_text(file_path).strip(),
                    tags=["claude", "memory"],
                    source_format=self.name,
                    metadata={"filename": file_path.name},
                )
            )
        return package

    def write(self, package: CanonicalMemoryPackage, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        main_entry = None
        for entry in package.entries:
            if entry.kind in {"instruction", "project"}:
                main_entry = entry
                break
        if main_entry is None and package.entries:
            main_entry = package.entries[0]
        if main_entry is not None:
            write_text(path / "CLAUDE.md", main_entry.content.rstrip() + "\n")

        memory_dir = path / ".claude" / "memories"
        memory_dir.mkdir(parents=True, exist_ok=True)
        for entry in package.entries:
            if main_entry is not None and entry.id == main_entry.id:
                continue
            filename = f"{slugify(entry.title or entry.id)}.md"
            write_text(memory_dir / filename, entry.content.rstrip() + "\n")
