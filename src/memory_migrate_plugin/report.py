from __future__ import annotations

from collections import Counter
from typing import Any

from memory_migrate_plugin.merge import build_entry_fingerprint
from memory_migrate_plugin.models import CanonicalMemoryPackage, MemoryEntry


REQUIRED_ENTRY_FIELDS = ("id", "kind", "title", "content")


def find_missing_fields(entry: MemoryEntry) -> list[str]:
    missing: list[str] = []
    for field in REQUIRED_ENTRY_FIELDS:
        value = getattr(entry, field, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)
    return missing


def build_package_report(package: CanonicalMemoryPackage) -> dict[str, Any]:
    kind_counter = Counter(entry.kind for entry in package.entries)
    source_counter = Counter(entry.source_format for entry in package.entries)
    tag_counter = Counter(tag for entry in package.entries for tag in entry.tags)

    missing_fields: list[dict[str, Any]] = []
    duplicate_ids: dict[str, int] = {}
    duplicate_fingerprints: dict[str, int] = {}
    id_counter = Counter(entry.id for entry in package.entries)
    fingerprint_counter = Counter(build_entry_fingerprint(entry) for entry in package.entries)

    for entry in package.entries:
        missing = find_missing_fields(entry)
        if missing:
            missing_fields.append({
                "id": entry.id,
                "title": entry.title,
                "missing_fields": missing,
            })

    for entry_id, count in id_counter.items():
        if count > 1:
            duplicate_ids[entry_id] = count

    for fingerprint, count in fingerprint_counter.items():
        if count > 1:
            duplicate_fingerprints[fingerprint] = count

    return {
        "package_id": package.package_id,
        "schema_version": package.schema_version,
        "entry_count": len(package.entries),
        "source_formats": sorted(package.source_formats),
        "kind_counts": dict(sorted(kind_counter.items())),
        "source_counts": dict(sorted(source_counter.items())),
        "top_tags": [{"tag": tag, "count": count} for tag, count in tag_counter.most_common(10)],
        "audit": {
            "missing_required_fields": missing_fields,
            "duplicate_id_groups": duplicate_ids,
            "duplicate_fingerprint_groups": duplicate_fingerprints,
            "issues_found": len(missing_fields) + len(duplicate_ids) + len(duplicate_fingerprints),
        },
    }


def build_merge_report(
    packages: list[CanonicalMemoryPackage],
    merged_package: CanonicalMemoryPackage,
    skipped_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    input_summaries = []
    for package in packages:
        input_summaries.append(
            {
                "package_id": package.package_id,
                "entry_count": len(package.entries),
                "source_formats": sorted(package.source_formats),
            }
        )

    skipped_by_reason = Counter(item["reason"] for item in skipped_entries)
    conflict_candidates = [
        item for item in skipped_entries if item["reason"] in {"duplicate-id", "duplicate-fingerprint"}
    ]

    return {
        "inputs": input_summaries,
        "output": build_package_report(merged_package),
        "merge_audit": {
            "input_count": len(packages),
            "skipped_entry_count": len(skipped_entries),
            "skipped_by_reason": dict(sorted(skipped_by_reason.items())),
            "conflict_candidates": conflict_candidates,
        },
    }
