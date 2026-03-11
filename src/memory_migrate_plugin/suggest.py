from __future__ import annotations

from typing import Any

from memory_migrate_plugin.merge import build_entry_fingerprint
from memory_migrate_plugin.models import CanonicalMemoryPackage
from memory_migrate_plugin.report import find_missing_fields
from memory_migrate_plugin.utils import slugify


FIELD_SUGGESTIONS = {
    "id": "Generate a stable slug from the title or source filename before export.",
    "kind": "Map the entry to one of the canonical kinds such as note, task, project, preference, or reference.",
    "title": "Use the first meaningful heading, filename, or a short summary sentence as the title.",
    "content": "Populate the entry body with the original memory text before export.",
}


def build_package_suggestions(package: CanonicalMemoryPackage) -> dict[str, Any]:
    suggestions: list[dict[str, Any]] = []

    id_groups: dict[str, list[str]] = {}
    fingerprint_groups: dict[str, list[str]] = {}

    for entry in package.entries:
        missing_fields = find_missing_fields(entry)
        if missing_fields:
            proposed = {}
            if "id" in missing_fields and entry.title.strip():
                proposed["id"] = slugify(entry.title)
            if "title" in missing_fields and entry.id.strip():
                proposed["title"] = entry.id.replace("-", " ").title()
            if "kind" in missing_fields:
                proposed["kind"] = "note"
            suggestions.append(
                {
                    "entry_id": entry.id,
                    "entry_title": entry.title,
                    "type": "missing-fields",
                    "severity": "high",
                    "message": "Entry is missing required canonical fields.",
                    "missing_fields": missing_fields,
                    "suggested_actions": [FIELD_SUGGESTIONS[field] for field in missing_fields],
                    "proposed_values": proposed,
                }
            )

        id_groups.setdefault(entry.id, []).append(entry.title)
        fingerprint_groups.setdefault(build_entry_fingerprint(entry), []).append(entry.id or entry.title)

    for entry_id, titles in sorted(id_groups.items()):
        if entry_id and len(titles) > 1:
            suggestions.append(
                {
                    "entry_id": entry_id,
                    "type": "duplicate-id",
                    "severity": "medium",
                    "message": "Multiple entries share the same id.",
                    "suggested_actions": [
                        "Keep one canonical entry and rename the others with source-specific suffixes.",
                        "If these entries represent the same memory, merge tags and metadata before export.",
                    ],
                    "related_entries": titles,
                }
            )

    for fingerprint, entry_refs in fingerprint_groups.items():
        if len(entry_refs) > 1:
            suggestions.append(
                {
                    "fingerprint": fingerprint,
                    "type": "duplicate-content",
                    "severity": "low",
                    "message": "Multiple entries appear to have the same canonical content.",
                    "suggested_actions": [
                        "Review whether these entries can be collapsed into one memory record.",
                        "If the duplication is intentional, preserve them but add source provenance tags.",
                    ],
                    "related_entries": entry_refs,
                }
            )

    return {
        "package_id": package.package_id,
        "entry_count": len(package.entries),
        "suggestion_count": len(suggestions),
        "suggestions": suggestions,
    }
