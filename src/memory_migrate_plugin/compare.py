from __future__ import annotations

from typing import Any

from memory_migrate_plugin.models import CanonicalMemoryPackage, MemoryEntry


def entry_index(package: CanonicalMemoryPackage) -> dict[str, MemoryEntry]:
    return {entry.id: entry for entry in package.entries}


def compare_packages(before: CanonicalMemoryPackage, after: CanonicalMemoryPackage) -> dict[str, Any]:
    before_index = entry_index(before)
    after_index = entry_index(after)

    before_ids = set(before_index)
    after_ids = set(after_index)

    added_ids = sorted(after_ids - before_ids)
    removed_ids = sorted(before_ids - after_ids)
    shared_ids = sorted(before_ids & after_ids)

    changed_entries: list[dict[str, Any]] = []
    for entry_id in shared_ids:
        old = before_index[entry_id]
        new = after_index[entry_id]
        field_changes: dict[str, dict[str, Any]] = {}
        for field in ("kind", "title", "content", "tags", "metadata"):
            old_value = getattr(old, field)
            new_value = getattr(new, field)
            if old_value != new_value:
                field_changes[field] = {"before": old_value, "after": new_value}
        if field_changes:
            changed_entries.append({"id": entry_id, "changes": field_changes})

    return {
        "before_package_id": before.package_id,
        "after_package_id": after.package_id,
        "before_entry_count": len(before.entries),
        "after_entry_count": len(after.entries),
        "added_ids": added_ids,
        "removed_ids": removed_ids,
        "changed_entries": changed_entries,
        "changed_entry_count": len(changed_entries),
    }


def compare_bundle_stages(
    original: CanonicalMemoryPackage,
    repaired: CanonicalMemoryPackage | None,
    transformed: CanonicalMemoryPackage,
) -> dict[str, Any]:
    stages: dict[str, Any] = {
        "original_to_transformed": compare_packages(original, transformed),
    }
    if repaired is not None:
        stages["original_to_repaired"] = compare_packages(original, repaired)
        stages["repaired_to_transformed"] = compare_packages(repaired, transformed)
    return stages
