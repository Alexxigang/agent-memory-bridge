from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from memory_migrate_plugin.core import normalize
from memory_migrate_plugin.bundle import run_bundle
from memory_migrate_plugin.compare import compare_packages
from memory_migrate_plugin.doctor import build_doctor_report
from memory_migrate_plugin.profiles import apply_profile
from memory_migrate_plugin.merge import merge_packages, merge_packages_detailed
from memory_migrate_plugin.registry import detect_format
from memory_migrate_plugin.repair import repair_package
from memory_migrate_plugin.report import build_merge_report, build_package_report
from memory_migrate_plugin.suggest import build_package_suggestions
from memory_migrate_plugin.manifest import build_manifest
from memory_migrate_plugin.verify import verify_manifest


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


    def test_cline_memory_bank_reads_extended_standard_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "memory-bank"
            source.mkdir()
            (source / "projectbrief.md").write_text("Project overview", encoding="utf-8")
            (source / "decisionLog.md").write_text("Use PostgreSQL", encoding="utf-8")
            (source / "userContext.md").write_text("Prefers concise responses", encoding="utf-8")
            package = normalize("cline-memory-bank", source)
            kinds = sorted(entry.kind for entry in package.entries)
            self.assertEqual(kinds, ["decision", "profile", "project"])
            decision_entry = next(entry for entry in package.entries if entry.kind == "decision")
            self.assertEqual(decision_entry.metadata["filename"], "decisionLog.md")

    def test_cline_memory_bank_detects_extended_layout_with_high_confidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "memory-bank"
            root.mkdir()
            for name in ["projectbrief.md", "activeContext.md", "decisionLog.md", "userContext.md"]:
                (root / name).write_text(name, encoding="utf-8")
            matches = detect_format(root)
            self.assertEqual(matches[0][0], "cline-memory-bank")
            self.assertGreaterEqual(matches[0][1], 99)

    def test_detect_format_prefers_cursor_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            rules_dir = root / ".cursor" / "rules"
            rules_dir.mkdir(parents=True)
            (rules_dir / "python.mdc").write_text(
                "---\ntitle: Python Rule\nalwaysApply: true\n---\n\nUse typed Python.",
                encoding="utf-8",
            )
            matches = detect_format(root)
            self.assertEqual(matches[0][0], "cursor-rules")


    def test_detect_format_prefers_agents_md(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "AGENTS.md").write_text("Agent workflow instructions", encoding="utf-8")
            matches = detect_format(root)
            self.assertEqual(matches[0][0], "agents-md")

    def test_agents_md_adapter_reads_main_and_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "AGENTS.md").write_text("Agent workflow instructions", encoding="utf-8")
            notes_dir = root / ".agents" / "notes"
            notes_dir.mkdir(parents=True)
            (notes_dir / "handoff.md").write_text("Remember deployment handoff.", encoding="utf-8")
            package = normalize("agents-md", root)
            self.assertEqual(len(package.entries), 2)
            self.assertEqual(package.entries[0].title, "AGENTS Instructions")

    def test_detect_format_prefers_claude_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "CLAUDE.md").write_text("Project guidance", encoding="utf-8")
            matches = detect_format(root)
            self.assertEqual(matches[0][0], "claude-project")

    def test_cursor_rules_adapter_reads_instruction_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            rules_dir = root / ".cursor" / "rules"
            rules_dir.mkdir(parents=True)
            (rules_dir / "backend.mdc").write_text(
                "---\ntitle: Backend Rule\nglobs: src/**/*.py\n---\n\nPrefer services over scripts.",
                encoding="utf-8",
            )
            package = normalize("cursor-rules", root)
            self.assertEqual(len(package.entries), 1)
            self.assertEqual(package.entries[0].kind, "instruction")
            self.assertEqual(package.entries[0].metadata["globs"], "src/**/*.py")

    def test_claude_project_adapter_reads_main_and_memory_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "CLAUDE.md").write_text("Main project memory", encoding="utf-8")
            mem_dir = root / ".claude" / "memories"
            mem_dir.mkdir(parents=True)
            (mem_dir / "release-notes.md").write_text("Ship weekly.", encoding="utf-8")
            package = normalize("claude-project", root)
            self.assertEqual(len(package.entries), 2)
            self.assertEqual(package.entries[0].title, "Claude Project Memory")

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




    def test_compare_packages_reports_field_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "entries.json"
            source.write_text(
                json.dumps([
                    {"id": "same-id", "kind": "", "title": "", "content": "Has content"}
                ]),
                encoding="utf-8",
            )
            package = normalize("generic-json", source)
            repaired, _ = repair_package(package)
            diff = compare_packages(package, repaired)
            self.assertEqual(diff["changed_entry_count"], 1)
            self.assertIn("kind", diff["changed_entries"][0]["changes"])
            self.assertIn("title", diff["changed_entries"][0]["changes"])


    def test_verify_manifest_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            file_path = root / "a.txt"
            file_path.write_text("hello", encoding="utf-8")
            manifest = build_manifest(root)
            report_ok = verify_manifest(manifest, root)
            self.assertTrue(report_ok["ok"])

            file_path.write_text("tampered", encoding="utf-8")
            report_bad = verify_manifest(manifest, root)
            self.assertFalse(report_bad["ok"])
            self.assertEqual(report_bad["mismatch_count"], 1)

    def test_run_bundle_creates_expected_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "entries.json"
            source.write_text(
                json.dumps([
                    {"id": "same-id", "kind": "", "title": "", "content": "Has content"},
                    {"id": "same-id", "kind": "note", "title": "Rule B", "content": "two"}
                ]),
                encoding="utf-8",
            )
            output_dir = root / "bundle-out"
            summary = run_bundle(source, "generic-json", "agents-md", output_dir, profile="agent-rules", apply_repair=True)
            self.assertTrue((output_dir / "canonical.json").exists())
            self.assertTrue((output_dir / "canonical.repaired.json").exists())
            self.assertTrue((output_dir / "canonical.transformed.json").exists())
            self.assertTrue((output_dir / "doctor.json").exists())
            self.assertTrue((output_dir / "compare.json").exists())
            self.assertTrue((output_dir / "manifest.json").exists())
            self.assertTrue((output_dir / "bundle-summary.json").exists())
            self.assertTrue((output_dir / "exported" / "AGENTS.md").exists())
            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            manifest_paths = {item["path"] for item in manifest["files"]}
            self.assertIn("canonical.json", manifest_paths)
            self.assertEqual(summary["output"]["profile"], "agent-rules")

    def test_apply_profile_developer_strict_transforms_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "entries.json"
            source.write_text(
                json.dumps([
                    {"id": "decision-1", "kind": "decision", "title": "DB", "content": "Use PostgreSQL"},
                    {"id": "profile-1", "kind": "profile", "title": "Prefs", "content": "Concise answers"}
                ]),
                encoding="utf-8",
            )
            package = normalize("generic-json", source)
            transformed = apply_profile(package, "developer-strict", "cursor-rules")
            self.assertEqual(transformed.entries[0].kind, "reference")
            self.assertEqual(transformed.entries[1].kind, "instruction")
            self.assertIn("developer-strict", transformed.entries[0].tags)
            self.assertTrue(transformed.entries[0].content.startswith("Technical reference:"))

    def test_apply_profile_agent_rules_converts_to_instruction(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "entries.json"
            source.write_text(
                json.dumps([
                    {"id": "project-1", "kind": "project", "title": "Proj", "content": "Keep CI green"}
                ]),
                encoding="utf-8",
            )
            package = normalize("generic-json", source)
            transformed = apply_profile(package, "agent-rules", "agents-md")
            self.assertEqual(transformed.entries[0].kind, "instruction")
            self.assertIn("agent-rules", transformed.entries[0].tags)
            self.assertTrue(transformed.entries[0].content.startswith("Rule context:"))

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

    def test_suggestions_include_proposed_values_for_missing_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "entries.json"
            source.write_text(
                json.dumps([
                    {"id": "note-1", "kind": "", "title": "", "content": "Has content"}
                ]),
                encoding="utf-8",
            )
            package = normalize("generic-json", source)
            suggestions = build_package_suggestions(package)
            self.assertEqual(suggestions["suggestion_count"], 1)
            self.assertEqual(suggestions["suggestions"][0]["proposed_values"]["kind"], "note")
            self.assertEqual(suggestions["suggestions"][0]["proposed_values"]["title"], "Note 1")

    def test_suggestions_include_duplicate_id_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "entries.json"
            source.write_text(
                json.dumps([
                    {"id": "same-id", "kind": "note", "title": "A", "content": "one"},
                    {"id": "same-id", "kind": "note", "title": "B", "content": "two"}
                ]),
                encoding="utf-8",
            )
            package = normalize("generic-json", source)
            suggestions = build_package_suggestions(package)
            duplicate_suggestions = [item for item in suggestions["suggestions"] if item["type"] == "duplicate-id"]
            self.assertEqual(len(duplicate_suggestions), 1)

    def test_repair_package_fixes_missing_fields_and_duplicate_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "entries.json"
            source.write_text(
                json.dumps([
                    {"id": "same-id", "kind": "", "title": "", "content": "Has content"},
                    {"id": "same-id", "kind": "note", "title": "B", "content": "two"},
                    {"id": "", "kind": "note", "title": "Needs Id", "content": "three"}
                ]),
                encoding="utf-8",
            )
            package = normalize("generic-json", source)
            repaired, summary = repair_package(package)
            ids = [entry.id for entry in repaired.entries]
            self.assertEqual(ids[0], "same-id")
            self.assertEqual(ids[1], "same-id-2")
            self.assertEqual(ids[2], "needs-id")
            self.assertEqual(repaired.entries[0].title, "Same Id")
            self.assertEqual(repaired.entries[0].kind, "note")
            self.assertEqual(summary["repaired_entry_count"], 3)

    def test_doctor_report_combines_diagnosis_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "entries.json"
            source.write_text(
                json.dumps([
                    {"id": "same-id", "kind": "", "title": "", "content": "Has content"},
                    {"id": "same-id", "kind": "note", "title": "B", "content": "two"}
                ]),
                encoding="utf-8",
            )
            package = normalize("generic-json", source)
            doctor = build_doctor_report(package)
            self.assertIn("doctor_summary", doctor)
            self.assertIn("report", doctor)
            self.assertIn("suggestions", doctor)
            self.assertIn("repair_preview", doctor)
            self.assertGreaterEqual(doctor["doctor_summary"]["suggestion_count"], 1)


if __name__ == "__main__":
    unittest.main()
