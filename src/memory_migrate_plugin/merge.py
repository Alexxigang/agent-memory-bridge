from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha1
from typing import Any

from memory_migrate_plugin.models import CanonicalMemoryPackage, MemoryEntry


MERGE_KEY_FIELDS = ("kind", "title", "content")


@dataclass(slots=True)
class MergeResult:
    package: CanonicalMemoryPackage
    skipped_entries: list[dict[str, Any]] = field(default_factory=list)


def build_entry_fingerprint(entry: MemoryEntry) -> str:
    payload = "\n".join(getattr(entry, field, "") or "" for field in MERGE_KEY_FIELDS)
    return sha1(payload.encode("utf-8")).hexdigest()


def merge_packages_detailed(
    packages: list[CanonicalMemoryPackage],
    package_id: str = "merged-memory-package",
    dedupe: bool = True,
) -> MergeResult:
    merged = CanonicalMemoryPackage(package_id=package_id)
    merged.metadata["merged_package_count"] = len(packages)

    seen_ids: set[str] = set()
    seen_fingerprints: set[str] = set()
    skipped_entries: list[dict[str, Any]] = []

    for package in packages:
        for source_format in package.source_formats:
            if source_format not in merged.source_formats:
                merged.source_formats.append(source_format)

        for entry in package.entries:
            fingerprint = build_entry_fingerprint(entry)
            duplicate_id = dedupe and entry.id in seen_ids
            duplicate_fingerprint = dedupe and fingerprint in seen_fingerprints
            if duplicate_id or duplicate_fingerprint:
                skipped_entries.append(
                    {
                        "id": entry.id,
                        "title": entry.title,
                        "kind": entry.kind,
                        "source_format": entry.source_format,
                        "reason": "duplicate-id" if duplicate_id else "duplicate-fingerprint",
                    }
                )
                continue

            cloned_entry = MemoryEntry(
                id=entry.id,
                kind=entry.kind,
                title=entry.title,
                content=entry.content,
                tags=sorted(set(entry.tags)),
                source_format=entry.source_format,
                created_at=entry.created_at,
                updated_at=entry.updated_at,
                metadata=dict(entry.metadata),
            )
            merged.add_entry(cloned_entry)
            seen_ids.add(entry.id)
            seen_fingerprints.add(fingerprint)

    merged.metadata["dedupe_enabled"] = dedupe
    merged.metadata["entry_count"] = len(merged.entries)
    merged.metadata["skipped_entry_count"] = len(skipped_entries)
    return MergeResult(package=merged, skipped_entries=skipped_entries)


def merge_packages(
    packages: list[CanonicalMemoryPackage],
    package_id: str = "merged-memory-package",
    dedupe: bool = True,
) -> CanonicalMemoryPackage:
    return merge_packages_detailed(packages, package_id=package_id, dedupe=dedupe).package
