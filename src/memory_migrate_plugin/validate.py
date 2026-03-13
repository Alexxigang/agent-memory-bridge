from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from memory_migrate_plugin.models import CanonicalMemoryPackage
from memory_migrate_plugin.utils import load_json, write_json


EXPECTED_SCHEMA_VERSION = "1.0"


def _is_iso_datetime(value: str) -> bool:
    normalized = value.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return True


def validate_package_data(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    required_package_fields = (
        "schema_version",
        "package_id",
        "created_at",
        "source_formats",
        "metadata",
        "entries",
    )
    for field in required_package_fields:
        if field not in data:
            errors.append({"scope": "package", "field": field, "message": "Missing required field"})

    schema_version = data.get("schema_version")
    if schema_version is not None and not isinstance(schema_version, str):
        errors.append({"scope": "package", "field": "schema_version", "message": "Must be a string"})
    elif isinstance(schema_version, str) and schema_version != EXPECTED_SCHEMA_VERSION:
        warnings.append({
            "scope": "package",
            "field": "schema_version",
            "message": f"Expected schema version {EXPECTED_SCHEMA_VERSION}",
            "actual": schema_version,
        })

    package_id = data.get("package_id")
    if package_id is not None and (not isinstance(package_id, str) or not package_id.strip()):
        errors.append({"scope": "package", "field": "package_id", "message": "Must be a non-empty string"})

    created_at = data.get("created_at")
    if created_at is not None:
        if not isinstance(created_at, str) or not _is_iso_datetime(created_at):
            errors.append({"scope": "package", "field": "created_at", "message": "Must be an ISO 8601 datetime string"})

    source_formats = data.get("source_formats")
    if source_formats is not None:
        if not isinstance(source_formats, list):
            errors.append({"scope": "package", "field": "source_formats", "message": "Must be a list of strings"})
        else:
            if any(not isinstance(item, str) or not item.strip() for item in source_formats):
                errors.append({"scope": "package", "field": "source_formats", "message": "All items must be non-empty strings"})
            if len(source_formats) != len(set(source_formats)):
                warnings.append({"scope": "package", "field": "source_formats", "message": "Contains duplicate values"})

    metadata = data.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        errors.append({"scope": "package", "field": "metadata", "message": "Must be an object"})

    entries = data.get("entries")
    if entries is not None and not isinstance(entries, list):
        errors.append({"scope": "package", "field": "entries", "message": "Must be a list"})
        entries = []

    seen_ids: dict[str, int] = {}
    if isinstance(entries, list):
        for index, entry in enumerate(entries):
            location = f"entries[{index}]"
            if not isinstance(entry, dict):
                errors.append({"scope": location, "field": "entry", "message": "Must be an object"})
                continue

            required_entry_fields = ("id", "kind", "title", "content", "tags", "source_format", "metadata")
            for field in required_entry_fields:
                if field not in entry:
                    errors.append({"scope": location, "field": field, "message": "Missing required field"})

            for field in ("id", "kind", "title", "content", "source_format"):
                value = entry.get(field)
                if value is not None and (not isinstance(value, str) or not value.strip()):
                    errors.append({"scope": location, "field": field, "message": "Must be a non-empty string"})

            tags = entry.get("tags")
            if tags is not None:
                if not isinstance(tags, list):
                    errors.append({"scope": location, "field": "tags", "message": "Must be a list of strings"})
                elif any(not isinstance(tag, str) for tag in tags):
                    errors.append({"scope": location, "field": "tags", "message": "All tags must be strings"})

            for field in ("created_at", "updated_at"):
                value = entry.get(field)
                if value is not None and (not isinstance(value, str) or not _is_iso_datetime(value)):
                    errors.append({"scope": location, "field": field, "message": "Must be null or an ISO 8601 datetime string"})

            entry_metadata = entry.get("metadata")
            if entry_metadata is not None and not isinstance(entry_metadata, dict):
                errors.append({"scope": location, "field": "metadata", "message": "Must be an object"})

            entry_id = entry.get("id")
            if isinstance(entry_id, str) and entry_id.strip():
                seen_ids[entry_id] = seen_ids.get(entry_id, 0) + 1

    duplicate_ids = sorted(entry_id for entry_id, count in seen_ids.items() if count > 1)
    for entry_id in duplicate_ids:
        warnings.append({"scope": "package", "field": "entries.id", "message": "Duplicate entry id", "id": entry_id})

    is_valid = not errors
    summary = {
        "error_count": len(errors),
        "warning_count": len(warnings),
        "entry_count": len(entries) if isinstance(entries, list) else 0,
        "duplicate_id_count": len(duplicate_ids),
    }
    return {
        "ok": is_valid,
        "summary": summary,
        "errors": errors,
        "warnings": warnings,
    }


def validate_package(package: CanonicalMemoryPackage) -> dict[str, Any]:
    return validate_package_data(package.to_dict())


def validate_package_file(input_path: Path, output_path: Path | None = None) -> dict[str, Any]:
    data = load_json(input_path)
    if not isinstance(data, dict):
        result = {
            "ok": False,
            "summary": {"error_count": 1, "warning_count": 0, "entry_count": 0, "duplicate_id_count": 0},
            "errors": [{"scope": "package", "field": "root", "message": "Canonical package root must be a JSON object"}],
            "warnings": [],
        }
    else:
        result = validate_package_data(data)
    if output_path:
        write_json(output_path, result)
    return result
