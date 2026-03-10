from __future__ import annotations

from pathlib import Path

from memory_migrate_plugin.adapters.base import BaseAdapter
from memory_migrate_plugin.models import CanonicalMemoryPackage, MemoryEntry
from memory_migrate_plugin.utils import read_text, slugify, split_frontmatter, write_text


class MarkdownBundleAdapter(BaseAdapter):
    name = "markdown-bundle"
    description = "Folder of markdown files with optional frontmatter."

    def probe(self, path: Path) -> bool:
        if path.is_file() and path.suffix.lower() == ".md":
            return True
        return path.is_dir() and any(path.rglob("*.md"))

    def detect_confidence(self, path: Path) -> int:
        if not self.probe(path):
            return 0
        return 40

    def read(self, path: Path) -> CanonicalMemoryPackage:
        package = CanonicalMemoryPackage(package_id=path.name or "markdown-bundle", source_formats=[self.name])
        files = sorted(path.rglob("*.md")) if path.is_dir() else [path]
        for file_path in files:
            text = read_text(file_path)
            meta, body = split_frontmatter(text)
            relative_root = path if path.is_dir() else file_path.parent
            entry = MemoryEntry(
                id=str(meta.get("id", slugify(file_path.stem))),
                kind=str(meta.get("kind", "note")),
                title=str(meta.get("title", file_path.stem.replace("-", " ").title())),
                content=body.strip(),
                tags=list(meta.get("tags", [])) if isinstance(meta.get("tags", []), list) else [],
                source_format=self.name,
                created_at=meta.get("created_at"),
                updated_at=meta.get("updated_at"),
                metadata={"relative_path": str(file_path.relative_to(relative_root))},
            )
            package.add_entry(entry)
        return package

    def write(self, package: CanonicalMemoryPackage, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        for entry in package.entries:
            target = path / f"{slugify(entry.title or entry.id)}.md"
            frontmatter = [
                "---",
                f"id: {entry.id}",
                f"kind: {entry.kind}",
                f"title: {entry.title}",
                f"tags: [{', '.join(entry.tags)}]",
                f"source_format: {entry.source_format}",
            ]
            if entry.created_at:
                frontmatter.append(f"created_at: {entry.created_at}")
            if entry.updated_at:
                frontmatter.append(f"updated_at: {entry.updated_at}")
            frontmatter.append("---")
            content = "\n".join(frontmatter) + "\n\n" + entry.content.rstrip() + "\n"
            write_text(target, content)
