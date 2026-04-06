from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from memory_migrate_plugin.core import normalize
from memory_migrate_plugin.profiles import list_profiles
from memory_migrate_plugin.registry import build_registry, detect_format


TARGET_BASELINES: dict[str, dict[str, Any]] = {
    "agents-md": {
        "reason": "Portable AGENTS bundles work well for cross-agent repository handoff.",
        "profiles": ("agent-rules", "project-handoff", "default"),
        "keywords": {"instruction": 3, "project": 2, "note": 1},
    },
    "codex-repo": {
        "reason": "Repository-scoped AGENTS instructions map cleanly to Codex repository workflows.",
        "profiles": ("agent-rules", "developer-strict", "default"),
        "keywords": {"instruction": 3, "reference": 2, "project": 2},
    },
    "claude-code-memory": {
        "reason": "Recursive CLAUDE memory files are strong for codebase-specific operational guidance.",
        "profiles": ("developer-strict", "agent-rules", "default"),
        "keywords": {"instruction": 3, "reference": 3, "profile": 2},
    },
    "openhands-repo": {
        "reason": "OpenHands benefits from repo instructions, scripts, skills, and microagents in one bundle.",
        "profiles": ("developer-strict", "agent-rules", "project-handoff"),
        "keywords": {"automation": 4, "skill": 4, "instruction": 2, "project": 2},
    },
    "cursor-rules": {
        "reason": "Cursor rules are useful when the target system wants instruction-first markdown rules.",
        "profiles": ("agent-rules", "developer-strict", "default"),
        "keywords": {"instruction": 4, "reference": 1},
    },
    "claude-project": {
        "reason": "Legacy CLAUDE project memory is still useful for simpler Claude repository handoff flows.",
        "profiles": ("project-handoff", "developer-strict", "default"),
        "keywords": {"project": 3, "note": 2, "instruction": 2},
    },
    "cline-memory-bank": {
        "reason": "Memory Bank remains useful for task-state handoff across long-running execution loops.",
        "profiles": ("project-handoff", "default", "developer-strict"),
        "keywords": {"task": 4, "project": 3, "decision": 2, "profile": 2},
    },
    "codex-memories": {
        "reason": "Flat markdown memories are a lightweight destination when repository scoping is unnecessary.",
        "profiles": ("default", "project-handoff", "developer-strict"),
        "keywords": {"note": 3, "reference": 2, "project": 1},
    },
    "markdown-bundle": {
        "reason": "Markdown bundles are broadly portable and easy to audit manually.",
        "profiles": ("default", "project-handoff", "agent-rules"),
        "keywords": {"note": 2, "instruction": 2, "project": 2},
    },
    "generic-json": {
        "reason": "Canonical-friendly JSON is ideal for integrations and pipelines that need deterministic machine-readable output.",
        "profiles": ("default", "developer-strict", "project-handoff"),
        "keywords": {"reference": 2, "note": 2, "decision": 1},
    },
}

SOURCE_TARGET_BONUSES: dict[str, dict[str, int]] = {
    "openhands-repo": {"codex-repo": 12, "claude-code-memory": 10, "agents-md": 8, "cursor-rules": 4},
    "codex-repo": {"openhands-repo": 12, "claude-code-memory": 10, "agents-md": 8, "cursor-rules": 4},
    "claude-code-memory": {"codex-repo": 11, "openhands-repo": 10, "agents-md": 7, "claude-project": 5},
    "claude-project": {"claude-code-memory": 10, "codex-repo": 8, "agents-md": 6},
    "cline-memory-bank": {"openhands-repo": 10, "codex-repo": 8, "claude-code-memory": 7, "agents-md": 6},
    "cursor-rules": {"codex-repo": 9, "agents-md": 8, "claude-code-memory": 7},
    "agents-md": {"codex-repo": 10, "openhands-repo": 9, "claude-code-memory": 8},
    "codex-memories": {"codex-repo": 8, "claude-code-memory": 7, "agents-md": 6},
    "markdown-bundle": {"agents-md": 6, "codex-repo": 5, "claude-code-memory": 5},
    "generic-json": {"codex-repo": 4, "claude-code-memory": 4, "agents-md": 4},
}


def _recommend_profile(kind_counts: Counter[str], target_format: str) -> tuple[str, list[str]]:
    total = sum(kind_counts.values()) or 1
    instruction_share = (kind_counts.get("instruction", 0) + kind_counts.get("profile", 0)) / total
    project_share = (kind_counts.get("project", 0) + kind_counts.get("task", 0)) / total
    technical_share = (kind_counts.get("reference", 0) + kind_counts.get("decision", 0) + kind_counts.get("automation", 0)) / total

    if target_format in {"cursor-rules", "codex-repo", "agents-md"} and instruction_share >= 0.30:
        return "agent-rules", ["High instruction density favors instruction-first export profiles."]
    if target_format in {"claude-code-memory", "openhands-repo"} and technical_share >= 0.25:
        return "developer-strict", ["Technical references and automation entries favor stricter developer-oriented exports."]
    if project_share >= 0.35:
        return "project-handoff", ["Project and task heavy memory favors handoff-oriented exports."]
    return "default", ["Default profile preserves structure with minimal transformation."]


def recommend_migration_targets(source_path: Path, source_format: str | None = None) -> dict[str, Any]:
    matches = detect_format(source_path)
    resolved_source_format = source_format or (matches[0][0] if matches else None)
    if resolved_source_format is None:
        raise ValueError(f"No supported format detected for {source_path}")

    package = normalize(resolved_source_format, source_path)
    kind_counts = Counter(entry.kind for entry in package.entries)
    registry = build_registry()
    profile_names = set(list_profiles())

    recommendations: list[dict[str, Any]] = []
    source_bonus_map = SOURCE_TARGET_BONUSES.get(resolved_source_format, {})
    source_formats = set(package.source_formats)

    for target_name, baseline in TARGET_BASELINES.items():
        if target_name == resolved_source_format or target_name not in registry:
            continue

        score = source_bonus_map.get(target_name, 0)
        reasons = [baseline["reason"]]

        for kind, weight in baseline["keywords"].items():
            count = kind_counts.get(kind, 0)
            if count:
                score += count * weight
        if target_name in {"codex-repo", "claude-code-memory", "openhands-repo"} and len(source_formats) > 1:
            score += 4
            reasons.append("Multiple source formats suggest a repository-oriented destination.")
        if target_name == "generic-json":
            score += 2
            reasons.append("Canonical-friendly JSON is a safe integration fallback.")

        profile, profile_reasons = _recommend_profile(kind_counts, target_name)
        if profile not in profile_names:
            profile = baseline["profiles"][0]
        reasons.extend(profile_reasons)

        recommendations.append(
            {
                "target_format": target_name,
                "recommended_profile": profile,
                "score": score,
                "reasons": reasons,
            }
        )

    recommendations.sort(key=lambda item: (-item["score"], item["target_format"]))
    top = recommendations[:5]
    return {
        "source": {
            "input_path": str(source_path),
            "detected_format": resolved_source_format,
            "candidate_formats": [{"format": name, "confidence": confidence} for name, confidence in matches],
            "entry_count": len(package.entries),
            "kind_counts": dict(sorted(kind_counts.items())),
        },
        "recommendations": top,
        "recommendation_count": len(top),
    }
