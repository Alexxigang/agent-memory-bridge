from __future__ import annotations

from pathlib import Path

from memory_migrate_plugin.adapters.base import BaseAdapter
from memory_migrate_plugin.models import CanonicalMemoryPackage, MemoryEntry
from memory_migrate_plugin.utils import read_text, slugify, write_text


class AgentsMdAdapter(BaseAdapter):
    name = "agents-md"
    description = "AGENTS.md style multi-agent instruction bundles and companion notes."

    def probe(self, path: Path) -> bool:
        if path.is_file() and path.name.upper() == "AGENTS.MD":
            return True
        if not path.is_dir():
            return False
        return (path / "AGENTS.md").exists() or (path / ".agents" / "notes").exists()

    def detect_confidence(self, path: Path) -> int:
        if not self.probe(path):
            return 0
        score = 90
        if path.is_dir() and (path / ".agents" / "notes").exists():
            score += 6
        return min(score, 98)

    def _resolve_layout(self, path: Path) -> tuple[Path, list[Path]]:
        if path.is_file():
            return path, []
        main_file = path / "AGENTS.md"
        notes_dir = path / ".agents" / "notes"
        notes = sorted(notes_dir.glob("*.md")) if notes_dir.exists() else []
        return main_file, notes

    def read(self, path: Path) -> CanonicalMemoryPackage:
        main_file, notes = self._resolve_layout(path)
        package = CanonicalMemoryPackage(package_id=main_file.parent.name or "agents-bundle", source_formats=[self.name])
        if main_file.exists():
            package.add_entry(
                MemoryEntry(
                    id="agents-md-instructions",
                    kind="instruction",
                    title="AGENTS Instructions",
                    content=read_text(main_file).strip(),
                    tags=["agents", "instructions"],
                    source_format=self.name,
                    metadata={"filename": main_file.name},
                )
            )
        for note in notes:
            package.add_entry(
                MemoryEntry(
                    id=slugify(note.stem),
                    kind="note",
                    title=note.stem.replace("-", " ").title(),
                    content=read_text(note).strip(),
                    tags=["agents", "note"],
                    source_format=self.name,
                    metadata={"filename": note.name},
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
            write_text(path / "AGENTS.md", main_entry.content.rstrip() + "\n")

        notes_dir = path / ".agents" / "notes"
        notes_dir.mkdir(parents=True, exist_ok=True)
        for entry in package.entries:
            if main_entry is not None and entry.id == main_entry.id:
                continue
            filename = f"{slugify(entry.title or entry.id)}.md"
            write_text(notes_dir / filename, entry.content.rstrip() + "\n")
