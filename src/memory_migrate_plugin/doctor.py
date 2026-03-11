from __future__ import annotations

from typing import Any

from memory_migrate_plugin.models import CanonicalMemoryPackage
from memory_migrate_plugin.repair import repair_package
from memory_migrate_plugin.report import build_package_report
from memory_migrate_plugin.suggest import build_package_suggestions


SEVERITY_ORDER = {"high": 3, "medium": 2, "low": 1}


def build_doctor_report(package: CanonicalMemoryPackage) -> dict[str, Any]:
    report = build_package_report(package)
    suggestions = build_package_suggestions(package)
    repaired_package, repair_summary = repair_package(package)
    repaired_report = build_package_report(repaired_package)

    severities = [item.get("severity", "low") for item in suggestions["suggestions"]]
    highest = "none"
    if severities:
        highest = max(severities, key=lambda level: SEVERITY_ORDER.get(level, 0))

    health_score = max(
        0,
        100
        - report["audit"]["issues_found"] * 15
        - suggestions["suggestion_count"] * 5,
    )

    diagnosis = []
    if report["audit"]["issues_found"] == 0:
        diagnosis.append("No structural audit issues found in the current package.")
    else:
        diagnosis.append(
            f"Found {report['audit']['issues_found']} structural audit issues that may affect migration quality."
        )

    if suggestions["suggestion_count"] > 0:
        diagnosis.append(
            f"Generated {suggestions['suggestion_count']} repair suggestions with highest severity {highest}."
        )

    if repair_summary["repaired_entry_count"] > 0:
        diagnosis.append(
            f"A repair preview can automatically update {repair_summary['repaired_entry_count']} entries without mutating the source file."
        )

    return {
        "package_id": package.package_id,
        "doctor_summary": {
            "health_score": health_score,
            "highest_severity": highest,
            "issue_count": report["audit"]["issues_found"],
            "suggestion_count": suggestions["suggestion_count"],
            "repairable_entry_count": repair_summary["repaired_entry_count"],
        },
        "diagnosis": diagnosis,
        "report": report,
        "suggestions": suggestions,
        "repair_preview": {
            "summary": repair_summary,
            "post_repair_report": repaired_report,
        },
    }
