from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from memory_migrate_plugin.core import normalize
from memory_migrate_plugin.merge import merge_packages, merge_packages_detailed
from memory_migrate_plugin.registry import detect_format
from memory_migrate_plugin.report import build_merge_report, build_package_report


class MemoryMigrateTests(unittest.TestCase):
    def test_cline_to_canonical_to_codex(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "memory-bank"
            source.mkdir()
            (source / "projectbrief.md").write_text("Project overview", encoding="utf-8")
            (source / "activeContext.md").write_text("Current task", encoding="utf-8")

            package = normalize("cline-memory-bank", source)
            self.assertEqual(len(package.entries), 2)
            self.assertEqual(sorted(entry.kind for entry in package.entries), ["project", "task"])

            target = root / "codex"
            from memory_migrate_plugin.core import convert
            convert("cline-memory-bank", source, "codex-memories", target)
            index = json.loads((target / "index.json").read_text(encoding="utf-8"))
            self.assertEqual(len(index), 2)
            self.assertTrue((target / "memories").exists())

    def test_generic_json_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "entries.json"
            source.write_text(
                json.dumps([
                    {"id": "pref-editor", "kind": "preference", "title": "Editor", "content": "Use Vim keybindings"}
                ]),
                encoding="utf-8",
            )
            package = normalize("generic-json", source)
            self.assertEqual(package.entries[0].title, "Editor")

    def test_detect_format_prefers_cline_memory_bank(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "memory-bank"
            source.mkdir()
            (source / "projectbrief.md").write_text("Project overview", encoding="utf-8")
            (source / "activeContext.md").write_text("Current task", encoding="utf-8")
            matches = detect_format(source)
            self.assertEqual(matches[0][0], "cline-memory-bank")

    def test_merge_packages_dedupes_duplicate_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_a = root / "a.json"
            source_b = root / "b.json"
            entry = {"id": "pref-editor", "kind": "preference", "title": "Editor", "content": "Use Vim keybindings"}
            source_a.write_text(json.dumps([entry]), encoding="utf-8")
            source_b.write_text(json.dumps([entry]), encoding="utf-8")

            package_a = normalize("generic-json", source_a)
            package_b = normalize("generic-json", source_b)
            merged = merge_packages([package_a, package_b])
            self.assertEqual(len(merged.entries), 1)
            self.assertTrue(merged.metadata["dedupe_enabled"])

    def test_normalize_can_auto_detect(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "entries.json"
            source.write_text(
                json.dumps([
                    {"id": "note-1", "kind": "note", "title": "Quick Note", "content": "Remember the deployment window"}
                ]),
                encoding="utf-8",
            )
            package = normalize(None, source)
            self.assertEqual(package.entries[0].id, "note-1")

    def test_build_package_report_flags_missing_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "entries.json"
            source.write_text(
                json.dumps([
                    {"id": "note-1", "kind": "note", "title": "", "content": "Has content"}
                ]),
                encoding="utf-8",
            )
            package = normalize("generic-json", source)
            report = build_package_report(package)
            self.assertEqual(report["audit"]["issues_found"], 1)
            self.assertEqual(report["audit"]["missing_required_fields"][0]["missing_fields"], ["title"])

    def test_build_merge_report_includes_skipped_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_a = root / "a.json"
            source_b = root / "b.json"
            entry = {"id": "pref-editor", "kind": "preference", "title": "Editor", "content": "Use Vim keybindings"}
            source_a.write_text(json.dumps([entry]), encoding="utf-8")
            source_b.write_text(json.dumps([entry]), encoding="utf-8")
            package_a = normalize("generic-json", source_a)
            package_b = normalize("generic-json", source_b)
            merge_result = merge_packages_detailed([package_a, package_b])
            report = build_merge_report([package_a, package_b], merge_result.package, merge_result.skipped_entries)
            self.assertEqual(report["merge_audit"]["skipped_entry_count"], 1)
            self.assertEqual(report["merge_audit"]["conflict_candidates"][0]["reason"], "duplicate-id")


if __name__ == "__main__":
    unittest.main()
