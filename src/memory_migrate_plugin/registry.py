from __future__ import annotations

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
