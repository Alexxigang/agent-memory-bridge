from __future__ import annotations

from pathlib import Path
from typing import Any

from memory_migrate_plugin.compare import compare_bundle_stages
from memory_migrate_plugin.core import export_canonical_json, normalize
from memory_migrate_plugin.doctor import build_doctor_report
from memory_migrate_plugin.manifest import build_manifest
from memory_migrate_plugin.models import CanonicalMemoryPackage
from memory_migrate_plugin.profiles import apply_profile
from memory_migrate_plugin.registry import build_registry
from memory_migrate_plugin.repair import repair_package
from memory_migrate_plugin.utils import write_json


def run_bundle(
    source_path: Path,
    source_format: str | None,
    target_format: str,
    output_dir: Path,
    profile: str | None = None,
    apply_repair: bool = True,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    original_package = normalize(source_format, source_path)
    doctor_report = build_doctor_report(original_package)

    canonical_path = output_dir / "canonical.json"
    export_canonical_json(original_package, canonical_path)

    active_package: CanonicalMemoryPackage = original_package
    repaired_package: CanonicalMemoryPackage | None = None
    repair_summary: dict[str, Any] | None = None
    repaired_path: Path | None = None

    if apply_repair:
        repaired_package, repair_summary = repair_package(original_package)
        active_package = repaired_package
        repaired_path = output_dir / "canonical.repaired.json"
        export_canonical_json(repaired_package, repaired_path)

    transformed_package = apply_profile(active_package, profile, target_format)
    transformed_path = output_dir / "canonical.transformed.json"
    export_canonical_json(transformed_package, transformed_path)

    export_dir = output_dir / "exported"
    target_adapter = build_registry()[target_format]
    target_adapter.write(transformed_package, export_dir)

    doctor_path = output_dir / "doctor.json"
    write_json(doctor_path, doctor_report)

    compare_report = compare_bundle_stages(original_package, repaired_package, transformed_package)
    compare_path = output_dir / "compare.json"
    write_json(compare_path, compare_report)

    manifest_path = output_dir / "manifest.json"

    bundle_summary = {
        "source": {
            "input": str(source_path),
            "source_format": source_format,
        },
        "output": {
            "target_format": target_format,
            "profile": profile or "default",
            "output_dir": str(output_dir),
            "canonical_path": str(canonical_path),
            "transformed_path": str(transformed_path),
            "export_dir": str(export_dir),
            "doctor_path": str(doctor_path),
            "compare_path": str(compare_path),
            "manifest_path": str(manifest_path),
            "repaired_path": str(repaired_path) if repaired_path else None,
        },
        "doctor_summary": doctor_report["doctor_summary"],
        "repair_applied": apply_repair,
        "repair_summary": repair_summary,
        "export_entry_count": len(transformed_package.entries),
    }
    write_json(output_dir / "bundle-summary.json", bundle_summary)

    manifest = build_manifest(output_dir, exclude={manifest_path})
    write_json(manifest_path, manifest)

    return bundle_summary
