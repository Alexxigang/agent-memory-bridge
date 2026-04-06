from __future__ import annotations

import re
from pathlib import Path

from memory_migrate_plugin.adapters.base import BaseAdapter
from memory_migrate_plugin.models import CanonicalMemoryPackage, MemoryEntry
from memory_migrate_plugin.utils import read_text, slugify, write_text


MEMORY_FILENAMES = {"CLAUDE.md", "CLAUDE.local.md"}
IMPORT_PATTERN = re.compile(r"(^|[\s(])@([^\s`]+)")


class ClaudeCodeMemoryAdapter(BaseAdapter):
    name = "claude-code-memory"
    description = "Modern Claude Code memory with recursive CLAUDE.md discovery, local overrides, and @path imports."

    def probe(self, path: Path) -> bool:
        if path.is_file():
            return path.name in MEMORY_FILENAMES
        if not path.is_dir():
            return False
        return any(any(path.rglob(filename)) for filename in MEMORY_FILENAMES)

    def detect_confidence(self, path: Path) -> int:
        if not self.probe(path):
            return 0
        if path.is_file():
            text = read_text(path)
            if self._extract_import_tokens(text):
                return 97
            return 89 if path.name == "CLAUDE.local.md" else 88

        files = self._discover_memory_files(path)
        if not files:
            return 0
        score = 88
        if any(file_path.name == "CLAUDE.local.md" for file_path in files):
            score += 4
        if len(files) > 1:
            score += 3
        if any(self._extract_import_tokens(read_text(file_path)) for file_path in files[:6]):
            score += 4
        return min(score, 99)

    def read(self, path: Path) -> CanonicalMemoryPackage:
        root = (path.parent if path.is_file() else path).resolve()
        package = CanonicalMemoryPackage(package_id=root.name or self.name, source_formats=[self.name])

        memory_files = [path.resolve()] if path.is_file() else self._discover_memory_files(root)
        memory_file_set = {file_path.resolve() for file_path in memory_files}
        imported_entries: dict[Path, MemoryEntry] = {}

        for memory_file in memory_files:
            text = read_text(memory_file).strip()
            relative_path = self._safe_relative_path(memory_file, root)
            role = "local-memory" if memory_file.name == "CLAUDE.local.md" else "memory-file"
            kind = "profile" if memory_file.name == "CLAUDE.local.md" else "instruction"
            title = self._build_title(relative_path)
            imports = self._resolve_imports(memory_file, text)

            package.add_entry(
                MemoryEntry(
                    id=slugify(relative_path.replace("/", "-")),
                    kind=kind,
                    title=title,
                    content=text,
                    tags=["claude-code", "memory"],
                    source_format=self.name,
                    metadata={
                        "filename": memory_file.name,
                        "relative_path": relative_path,
                        "claude_code_role": role,
                        "imports": [self._safe_relative_path(item, root) for item in imports],
                    },
                )
            )

            for imported_file in imports:
                if imported_file.resolve() in memory_file_set:
                    continue
                if imported_file in imported_entries:
                    imported_entries[imported_file].metadata.setdefault("imported_by", []).append(relative_path)
                    continue
                imported_entry = MemoryEntry(
                    id=slugify(f"import-{self._safe_relative_path(imported_file, root).replace('/', '-') }"),
                    kind="reference",
                    title=imported_file.stem.replace("-", " ").replace("_", " ").title(),
                    content=read_text(imported_file).strip(),
                    tags=["claude-code", "import"],
                    source_format=self.name,
                    metadata={
                        "filename": imported_file.name,
                        "relative_path": self._safe_relative_path(imported_file, root),
                        "claude_code_role": "imported-file",
                        "imported_by": [relative_path],
                    },
                )
                imported_entries[imported_file] = imported_entry

        for imported_file in sorted(imported_entries, key=lambda item: imported_entries[item].metadata["relative_path"]):
            package.add_entry(imported_entries[imported_file])

        return package

    def write(self, package: CanonicalMemoryPackage, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        written_paths: set[Path] = set()

        for entry in package.entries:
            role = str(entry.metadata.get("claude_code_role", ""))
            relative_path = str(entry.metadata.get("relative_path", "")).strip()
            target = self._resolve_output_path(path, role, relative_path, entry)
            if target in written_paths:
                continue
            write_text(target, entry.content.rstrip() + "\n")
            written_paths.add(target)

        if not written_paths and package.entries:
            write_text(path / "CLAUDE.md", package.entries[0].content.rstrip() + "\n")

    def _discover_memory_files(self, root: Path) -> list[Path]:
        files: list[Path] = []
        for filename in MEMORY_FILENAMES:
            files.extend(root.rglob(filename))
        return sorted(set(files), key=lambda file_path: (len(file_path.relative_to(root).parts), file_path.as_posix()))

    def _extract_import_tokens(self, text: str) -> list[str]:
        tokens: list[str] = []
        in_code_block = False
        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            if line.lstrip().startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            sanitized = re.sub(r"`[^`]*`", "", line)
            for _, token in IMPORT_PATTERN.findall(sanitized):
                cleaned = token.rstrip('.,;:)]')
                if cleaned:
                    tokens.append(cleaned)
        return tokens

    def _resolve_imports(self, memory_file: Path, text: str, max_depth: int = 5) -> list[Path]:
        resolved: list[Path] = []
        visited: set[Path] = set()

        def visit(current_file: Path, current_text: str, depth: int) -> None:
            if depth >= max_depth:
                return
            for token in self._extract_import_tokens(current_text):
                candidate = self._resolve_import_path(current_file, token)
                if candidate is None or candidate in visited or not candidate.is_file():
                    continue
                visited.add(candidate)
                resolved.append(candidate)
                visit(candidate, read_text(candidate), depth + 1)

        visit(memory_file, text, 0)
        return resolved

    def _resolve_import_path(self, current_file: Path, token: str) -> Path | None:
        if token.startswith("~/"):
            return Path.home() / token[2:]
        candidate = Path(token)
        if candidate.is_absolute():
            return candidate
        return (current_file.parent / candidate).resolve()

    def _safe_relative_path(self, file_path: Path, root: Path) -> str:
        try:
            return file_path.relative_to(root).as_posix()
        except ValueError:
            return str(file_path)

    def _build_title(self, relative_path: str) -> str:
        if relative_path == "CLAUDE.md":
            return "Claude Code Memory"
        if relative_path == "CLAUDE.local.md":
            return "Claude Code Local Memory"
        return relative_path.replace("/", " / ")

    def _resolve_output_path(self, root: Path, role: str, relative_path: str, entry: MemoryEntry) -> Path:
        if relative_path and not Path(relative_path).is_absolute() and ".." not in Path(relative_path).parts:
            return root / Path(relative_path)
        if role == "local-memory":
            return root / "CLAUDE.local.md"
        if role == "memory-file":
            return root / "CLAUDE.md"
        return root / ".claude" / "imports" / f"{slugify(entry.title or entry.id)}.md"
