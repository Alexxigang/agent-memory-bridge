from __future__ import annotations

from pathlib import Path
from typing import Any

from memory_migrate_plugin.bundle import run_bundle
from memory_migrate_plugin.utils import write_text, write_json


def build_release_note(summary: dict[str, Any]) -> str:
    doctor = summary["doctor_summary"]
    output = summary["output"]
    lines = [
        "# Migration Release",
        "",
        "## Overview",
        "",
        f"- Target format: {output['target_format']}",
        f"- Profile: {output['profile']}",
        f"- Export entry count: {summary['export_entry_count']}",
        f"- Repair applied: {summary['repair_applied']}",
        "",
        "## Health",
        "",
        f"- Health score: {doctor['health_score']}",
        f"- Highest severity: {doctor['highest_severity']}",
        f"- Issue count: {doctor['issue_count']}",
        f"- Suggestion count: {doctor['suggestion_count']}",
        f"- Repairable entry count: {doctor['repairable_entry_count']}",
        "",
        "## Artifacts",
        "",
        f"- Canonical: {output['canonical_path']}",
        f"- Transformed: {output['transformed_path']}",
        f"- Exported dir: {output['export_dir']}",
        f"- Doctor: {output['doctor_path']}",
        f"- Compare: {output['compare_path']}",
        f"- Manifest: {output['manifest_path']}",
    ]
    if output.get("repaired_path"):
        lines.append(f"- Repaired: {output['repaired_path']}")
    if summary.get("zip_path"):
        lines.append(f"- Zip: {summary['zip_path']}")
    if summary.get("zip_sha256"):
        lines.append(f"- Zip SHA256: {summary['zip_sha256']}")
    lines.extend([
        "",
        "## Verification",
        "",
        "Use the generated manifest to verify integrity:",
        "",
        "```bash",
        f"memory-migrate verify --manifest {output['manifest_path']}",
        "```",
        "",
    ])
    return "\n".join(lines)


def run_release(
    source_path: Path,
    source_format: str | None,
    target_format: str,
    output_dir: Path,
    profile: str | None = None,
    apply_repair: bool = True,
    zip_output: Path | None = None,
) -> dict[str, Any]:
    summary = run_bundle(
        source_path,
        source_format,
        target_format,
        output_dir,
        profile=profile,
        apply_repair=apply_repair,
        zip_output=zip_output,
    )

    release_note_path = output_dir / "RELEASE_NOTE.md"
    release_note = build_release_note(summary)
    write_text(release_note_path, release_note)

    release_summary = {
        **summary,
        "release_note_path": str(release_note_path),
    }
    write_json(output_dir / "release-summary.json", release_summary)
    return release_summary
