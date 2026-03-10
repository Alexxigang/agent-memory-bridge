from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from memory_migrate_plugin.models import CanonicalMemoryPackage


class BaseAdapter(ABC):
    name: str = "base"
    description: str = "Base adapter"

    @abstractmethod
    def read(self, path: Path) -> CanonicalMemoryPackage:
        raise NotImplementedError

    @abstractmethod
    def write(self, package: CanonicalMemoryPackage, path: Path) -> None:
        raise NotImplementedError

    def probe(self, path: Path) -> bool:
        return path.exists()
