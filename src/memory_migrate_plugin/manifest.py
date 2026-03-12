from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable

from memory_migrate_plugin.models import utc_now_iso


@dataclass(frozen=True, slots=True)
class ManifestFile:
    path: str
    sha256: str
    bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "sha256": self.sha256, "bytes": self.bytes}


def iter_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        yield root
        return

    for path in sorted(root.rglob("*")):
        if path.is_file():
            yield path


def sha256_file(path: Path) -> str:
    hasher = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def build_manifest(root: Path, *, exclude: set[Path] | None = None) -> dict[str, Any]:
    exclude_set = exclude or set()
    files: list[ManifestFile] = []
    total_bytes = 0

    for path in iter_files(root):
        if path in exclude_set:
            continue
        relative = path.name if root.is_file() else path.relative_to(root).as_posix()
        size = path.stat().st_size
        total_bytes += size
        files.append(ManifestFile(path=relative, sha256=sha256_file(path), bytes=size))

    files_sorted = sorted(files, key=lambda item: item.path)

    return {
        "schema_version": "1.0",
        "created_at": utc_now_iso(),
        "root": str(root),
        "file_count": len(files_sorted),
        "total_bytes": total_bytes,
        "files": [item.to_dict() for item in files_sorted],
    }
