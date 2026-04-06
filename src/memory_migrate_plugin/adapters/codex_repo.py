from __future__ import annotations

from pathlib import Path

from memory_migrate_plugin.adapters.base import BaseAdapter
from memory_migrate_plugin.models import CanonicalMemoryPackage, MemoryEntry
from memory_migrate_plugin.utils import read_text, slugify, write_text


DOC_FILENAMES = ("AGENTS.override.md", "AGENTS.md")


class CodexRepoAdapter(BaseAdapter):
    name = "codex-repo"
    description = "Codex repository instructions using recursive AGENTS.md and AGENTS.override.md files."

    def probe(self, path: Path) -> bool:
        if path.is_file():
            return path.name in DOC_FILENAMES
        if not path.is_dir():
            return False
        return any(any(path.rglob(filename)) for filename in DOC_FILENAMES)

    def detect_confidence(self, path: Path) -> int:
        if not self.probe(path):
            return 0
        if path.is_file():
            return 96 if path.name == "AGENTS.override.md" else 92
        files = self._discover_docs(path)
        score = 90
        if any(file_path.name == "AGENTS.override.md" for file_path in files):
            score += 5
        if len(files) > 1:
            score += 3
        if any(len(file_path.relative_to(path).parts) > 1 for file_path in files):
            score += 1
        return min(score, 99)

    def read(self, path: Path) -> CanonicalMemoryPackage:
        root = (path.parent if path.is_file() else path).resolve()
        docs = [path.resolve()] if path.is_file() else self._discover_docs(root)
        package = CanonicalMemoryPackage(package_id=root.name or self.name, source_formats=[self.name])

        for doc_path in docs:
            relative_path = doc_path.relative_to(root).as_posix()
            role = "override" if doc_path.name == "AGENTS.override.md" else "agents"
            scope_dir = doc_path.parent.relative_to(root).as_posix() if doc_path.parent != root else "."
            title = "Codex Override Instructions" if role == "override" else "Codex Repository Instructions"
            if scope_dir != ".":
                title = f"{title} ({scope_dir})"
            package.add_entry(
                MemoryEntry(
                    id=slugify(relative_path.replace("/", "-")),
                    kind="instruction",
                    title=title,
                    content=read_text(doc_path).strip(),
                    tags=["codex", "agents", role],
                    source_format=self.name,
                    metadata={
                        "filename": doc_path.name,
                        "relative_path": relative_path,
                        "codex_role": role,
                        "scope_dir": scope_dir,
                    },
                )
            )

        return package

    def write(self, package: CanonicalMemoryPackage, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        entries = sorted(
            package.entries,
            key=lambda entry: (
                0 if entry.metadata.get("codex_role") == "agents" else 1,
                str(entry.metadata.get("relative_path", entry.id)),
            ),
        )
        for entry in entries:
            relative_path = str(entry.metadata.get("relative_path", "")).strip()
            role = str(entry.metadata.get("codex_role", "agents"))
            scope_dir = str(entry.metadata.get("scope_dir", ".")).strip()
            target = self._resolve_output_path(path, relative_path, role, scope_dir)
            write_text(target, entry.content.rstrip() + "\n")

    def _discover_docs(self, root: Path) -> list[Path]:
        files: list[Path] = []
        for filename in DOC_FILENAMES:
            files.extend(root.rglob(filename))
        return sorted(set(files), key=lambda file_path: (len(file_path.relative_to(root).parts), file_path.as_posix()))

    def _resolve_output_path(self, root: Path, relative_path: str, role: str, scope_dir: str) -> Path:
        if relative_path and not Path(relative_path).is_absolute() and ".." not in Path(relative_path).parts:
            return root / Path(relative_path)
        filename = "AGENTS.override.md" if role == "override" else "AGENTS.md"
        if scope_dir and scope_dir != ".":
            return root / Path(scope_dir) / filename
        return root / filename
