from __future__ import annotations

from dataclasses import replace
from typing import Any

from memory_migrate_plugin.models import CanonicalMemoryPackage, MemoryEntry
from memory_migrate_plugin.report import find_missing_fields
from memory_migrate_plugin.utils import slugify


def repair_entry(entry: MemoryEntry, seen_ids: set[str]) -> tuple[MemoryEntry, list[dict[str, Any]]]:
    repaired = replace(
        entry,
        tags=list(entry.tags),
        metadata=dict(entry.metadata),
    )
    actions: list[dict[str, Any]] = []
    missing_fields = find_missing_fields(repaired)

    if "title" in missing_fields and repaired.id.strip():
        new_title = repaired.id.replace("-", " ").title()
        repaired.title = new_title
        actions.append({"field": "title", "action": "filled-from-id", "value": new_title})

    if "kind" in missing_fields:
        repaired.kind = "note"
        actions.append({"field": "kind", "action": "filled-default", "value": "note"})

    if "id" in missing_fields:
        base_id = slugify(repaired.title or repaired.content[:32] or "memory")
        repaired.id = base_id
        actions.append({"field": "id", "action": "filled-generated", "value": base_id})

    if "content" in missing_fields:
        repaired.content = "[EMPTY CONTENT PLACEHOLDER]"
        actions.append({"field": "content", "action": "filled-placeholder", "value": repaired.content})

    original_id = repaired.id
    if repaired.id in seen_ids:
        suffix = 2
        while f"{original_id}-{suffix}" in seen_ids:
            suffix += 1
        repaired.id = f"{original_id}-{suffix}"
        actions.append({"field": "id", "action": "deduplicated", "value": repaired.id})

    seen_ids.add(repaired.id)
    return repaired, actions


def repair_package(package: CanonicalMemoryPackage) -> tuple[CanonicalMemoryPackage, dict[str, Any]]:
    repaired_package = CanonicalMemoryPackage(
        schema_version=package.schema_version,
        package_id=f"{package.package_id}-repaired",
        created_at=package.created_at,
        source_formats=list(package.source_formats),
        metadata=dict(package.metadata),
    )
    repaired_package.metadata["repaired_from"] = package.package_id

    seen_ids: set[str] = set()
    repair_log: list[dict[str, Any]] = []

    for entry in package.entries:
        repaired_entry, actions = repair_entry(entry, seen_ids)
        repaired_package.add_entry(repaired_entry)
        if actions:
            repair_log.append({
                "original_id": entry.id,
                "final_id": repaired_entry.id,
                "actions": actions,
            })

    summary = {
        "original_package_id": package.package_id,
        "repaired_package_id": repaired_package.package_id,
        "entry_count": len(repaired_package.entries),
        "repaired_entry_count": len(repair_log),
        "repair_log": repair_log,
    }
    repaired_package.metadata["repair_summary"] = {
        "repaired_entry_count": len(repair_log),
    }
    return repaired_package, summary
