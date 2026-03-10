from __future__ import annotations

from pathlib import Path

from memory_migrate_plugin.models import CanonicalMemoryPackage
from memory_migrate_plugin.registry import build_registry
from memory_migrate_plugin.utils import write_json


def get_adapter(name: str):
    registry = build_registry()
    if name not in registry:
        raise KeyError(f"Unknown adapter: {name}")
    return registry[name]


def normalize(source_format: str, source_path: Path) -> CanonicalMemoryPackage:
    adapter = get_adapter(source_format)
    return adapter.read(source_path)


def convert(source_format: str, source_path: Path, target_format: str, target_path: Path) -> CanonicalMemoryPackage:
    package = normalize(source_format, source_path)
    target_adapter = get_adapter(target_format)
    target_adapter.write(package, target_path)
    return package


def export_canonical_json(package: CanonicalMemoryPackage, target_path: Path) -> None:
    write_json(target_path, package.to_dict())
