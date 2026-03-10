from __future__ import annotations

from pathlib import Path

from memory_migrate_plugin.adapters import (
    BaseAdapter,
    ClineMemoryBankAdapter,
    CodexMemoriesAdapter,
    GenericJsonAdapter,
    MarkdownBundleAdapter,
)


def build_registry() -> dict[str, BaseAdapter]:
    adapters = [
        GenericJsonAdapter(),
        MarkdownBundleAdapter(),
        CodexMemoriesAdapter(),
        ClineMemoryBankAdapter(),
    ]
    return {adapter.name: adapter for adapter in adapters}


def detect_format(path: Path) -> list[tuple[str, int]]:
    results: list[tuple[str, int]] = []
    for name, adapter in build_registry().items():
        confidence = adapter.detect_confidence(path)
        if confidence > 0:
            results.append((name, confidence))
    return sorted(results, key=lambda item: (-item[1], item[0]))
