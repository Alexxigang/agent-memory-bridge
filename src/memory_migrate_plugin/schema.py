from __future__ import annotations

from pathlib import Path
from typing import Any

from memory_migrate_plugin.utils import write_json


CANONICAL_SCHEMA_ID = "https://agent-memory-bridge.dev/schema/canonical-memory-package/v1.0"


def build_canonical_package_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": CANONICAL_SCHEMA_ID,
        "title": "CanonicalMemoryPackage",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema_version",
            "package_id",
            "created_at",
            "source_formats",
            "metadata",
            "entries",
        ],
        "properties": {
            "schema_version": {
                "type": "string",
                "description": "Canonical package schema version.",
                "default": "1.0",
            },
            "package_id": {
                "type": "string",
                "description": "Stable identifier for the package.",
                "minLength": 1,
            },
            "created_at": {
                "type": "string",
                "description": "UTC creation timestamp in ISO 8601 format.",
                "format": "date-time",
            },
            "source_formats": {
                "type": "array",
                "description": "Distinct source adapters represented in the package.",
                "items": {"type": "string"},
                "uniqueItems": True,
            },
            "metadata": {
                "type": "object",
                "description": "Package-level metadata and provenance fields.",
                "additionalProperties": True,
            },
            "entries": {
                "type": "array",
                "description": "Normalized memory entries.",
                "items": {"$ref": "#/$defs/memoryEntry"},
            },
        },
        "$defs": {
            "memoryEntry": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "id",
                    "kind",
                    "title",
                    "content",
                    "tags",
                    "source_format",
                    "metadata",
                ],
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Stable entry identifier.",
                        "minLength": 1,
                    },
                    "kind": {
                        "type": "string",
                        "description": "Semantic entry category such as note, project, or preference.",
                        "minLength": 1,
                    },
                    "title": {
                        "type": "string",
                        "description": "Human-readable entry title.",
                        "minLength": 1,
                    },
                    "content": {
                        "type": "string",
                        "description": "Primary body content for the memory entry.",
                    },
                    "tags": {
                        "type": "array",
                        "description": "Keyword tags used for retrieval and filtering.",
                        "items": {"type": "string"},
                    },
                    "source_format": {
                        "type": "string",
                        "description": "Adapter name that produced the entry.",
                        "minLength": 1,
                    },
                    "created_at": {
                        "type": ["string", "null"],
                        "description": "Original creation timestamp when available.",
                        "format": "date-time",
                    },
                    "updated_at": {
                        "type": ["string", "null"],
                        "description": "Original update timestamp when available.",
                        "format": "date-time",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Entry-level adapter metadata.",
                        "additionalProperties": True,
                    },
                },
            }
        },
    }


def write_canonical_package_schema(output_path: Path) -> dict[str, Any]:
    schema = build_canonical_package_schema()
    write_json(output_path, schema)
    return schema
