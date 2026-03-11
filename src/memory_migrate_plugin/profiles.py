from __future__ import annotations

from dataclasses import replace

from memory_migrate_plugin.models import CanonicalMemoryPackage, MemoryEntry


PROFILE_DESCRIPTIONS = {
    "default": "Preserve canonical content with minimal transformation.",
    "developer-strict": "Favor explicit instructions, references, and technical context for coding agents.",
    "project-handoff": "Favor project summaries, active context, and progress continuity for handoff flows.",
    "agent-rules": "Favor instruction-oriented exports for rule and policy driven agents.",
}


def list_profiles() -> dict[str, str]:
    return dict(PROFILE_DESCRIPTIONS)


def apply_profile(package: CanonicalMemoryPackage, profile: str | None, target_format: str) -> CanonicalMemoryPackage:
    resolved_profile = profile or "default"
    if resolved_profile not in PROFILE_DESCRIPTIONS:
        raise ValueError(f"Unknown profile: {resolved_profile}")

    transformed = CanonicalMemoryPackage(
        schema_version=package.schema_version,
        package_id=package.package_id,
        created_at=package.created_at,
        source_formats=list(package.source_formats),
        metadata=dict(package.metadata),
    )
    transformed.metadata["export_profile"] = resolved_profile
    transformed.metadata["export_target_format"] = target_format

    for entry in package.entries:
        cloned = replace(
            entry,
            tags=list(entry.tags),
            metadata=dict(entry.metadata),
        )
        cloned = transform_entry(cloned, resolved_profile, target_format)
        transformed.add_entry(cloned)

    return transformed


def transform_entry(entry: MemoryEntry, profile: str, target_format: str) -> MemoryEntry:
    if profile == "default":
        return entry

    if profile == "developer-strict":
        if entry.kind == "decision":
            entry.kind = "reference"
        if entry.kind == "profile":
            entry.kind = "instruction"
        entry.tags = sorted(set(entry.tags + ["developer-strict"]))
        if target_format in {"cursor-rules", "agents-md", "claude-project"} and entry.kind == "reference":
            entry.content = "Technical reference:\n\n" + entry.content
        return entry

    if profile == "project-handoff":
        if entry.kind == "decision":
            entry.kind = "project"
        if entry.kind == "profile":
            entry.kind = "project"
        entry.tags = sorted(set(entry.tags + ["project-handoff"]))
        if entry.kind in {"project", "task"}:
            entry.content = "Handoff note:\n\n" + entry.content
        return entry

    if profile == "agent-rules":
        if entry.kind in {"decision", "profile", "reference", "project"}:
            entry.kind = "instruction"
        entry.tags = sorted(set(entry.tags + ["agent-rules"]))
        entry.content = "Rule context:\n\n" + entry.content
        return entry

    return entry
