from __future__ import annotations

from pathlib import Path

from memory_migrate_plugin.adapters.base import BaseAdapter
from memory_migrate_plugin.models import CanonicalMemoryPackage, MemoryEntry
from memory_migrate_plugin.utils import read_text, slugify, split_frontmatter, write_text


class CursorRulesAdapter(BaseAdapter):
    name = "cursor-rules"
    description = "Cursor-style .cursor/rules markdown rule bundles."

    def _rules_dir(self, path: Path) -> Path | None:
        if path.is_dir() and path.name == "rules":
            return path
        if path.is_dir() and (path / ".cursor" / "rules").exists():
            return path / ".cursor" / "rules"
        return None

    def probe(self, path: Path) -> bool:
        rules_dir = self._rules_dir(path)
        if rules_dir is None or not rules_dir.is_dir():
            return False
        return any(rules_dir.glob("*.md")) or any(rules_dir.glob("*.mdc"))

    def detect_confidence(self, path: Path) -> int:
        if not self.probe(path):
            return 0
        rules_dir = self._rules_dir(path)
        assert rules_dir is not None
        mdc_count = len(list(rules_dir.glob("*.mdc")))
        return 96 if mdc_count > 0 else 82

    def read(self, path: Path) -> CanonicalMemoryPackage:
        rules_dir = self._rules_dir(path)
        if rules_dir is None:
            raise ValueError(f"Could not resolve Cursor rules directory from {path}")
        package = CanonicalMemoryPackage(package_id=rules_dir.parent.name or "cursor-rules", source_formats=[self.name])
        files = sorted(list(rules_dir.glob("*.md")) + list(rules_dir.glob("*.mdc")))
        for file_path in files:
            text = read_text(file_path)
            meta, body = split_frontmatter(text)
            package.add_entry(
                MemoryEntry(
                    id=str(meta.get("id", slugify(file_path.stem))),
                    kind="instruction",
                    title=str(meta.get("title", file_path.stem.replace("-", " ").title())),
                    content=body.strip() if body.strip() else text.strip(),
                    tags=["cursor", "rules"],
                    source_format=self.name,
                    metadata={
                        "filename": file_path.name,
                        "globs": meta.get("globs", ""),
                        "alwaysApply": meta.get("alwaysApply", ""),
                    },
                )
            )
        return package

    def write(self, package: CanonicalMemoryPackage, path: Path) -> None:
        rules_dir = path / ".cursor" / "rules" if path.name != "rules" else path
        rules_dir.mkdir(parents=True, exist_ok=True)
        for entry in package.entries:
            if entry.kind not in {"instruction", "project", "reference", "note"}:
                continue
            filename = f"{slugify(entry.title or entry.id)}.mdc"
            frontmatter = [
                "---",
                f"title: {entry.title}",
                f"id: {entry.id}",
                f"alwaysApply: {entry.metadata.get('alwaysApply', 'false')}",
            ]
            globs = entry.metadata.get("globs")
            if globs:
                frontmatter.append(f"globs: {globs}")
            frontmatter.append("---")
            write_text(rules_dir / filename, "\n".join(frontmatter) + "\n\n" + entry.content.rstrip() + "\n")
