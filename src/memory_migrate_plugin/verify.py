from __future__ import annotations

from pathlib import Path
from typing import Any

from memory_migrate_plugin.manifest import sha256_file


def verify_manifest(manifest: dict[str, Any], root: Path) -> dict[str, Any]:
    files = manifest.get("files", [])
    missing: list[dict[str, Any]] = []
    mismatched: list[dict[str, Any]] = []

    checked = 0
    for item in files:
        rel_path = item["path"]
        expected_hash = item["sha256"]
        expected_bytes = int(item.get("bytes", 0))

        target = root / rel_path
        if not target.exists():
            missing.append({"path": rel_path, "reason": "missing"})
            continue

        actual_bytes = target.stat().st_size
        actual_hash = sha256_file(target)
        checked += 1

        if actual_hash != expected_hash or actual_bytes != expected_bytes:
            mismatched.append(
                {
                    "path": rel_path,
                    "expected": {"sha256": expected_hash, "bytes": expected_bytes},
                    "actual": {"sha256": actual_hash, "bytes": actual_bytes},
                }
            )

    ok = len(missing) == 0 and len(mismatched) == 0

    return {
        "ok": ok,
        "root": str(root),
        "expected_file_count": len(files),
        "checked_file_count": checked,
        "missing_count": len(missing),
        "mismatch_count": len(mismatched),
        "missing": missing,
        "mismatched": mismatched,
    }
