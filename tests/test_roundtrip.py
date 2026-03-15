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
from memory_migrate_plugin.release import run_release
from memory_migrate_plugin.repair import repair_package
from memory_migrate_plugin.report import build_merge_report, build_package_report
from memory_migrate_plugin.suggest import build_package_suggestions
from memory_migrate_plugin.manifest import build_manifest
from memory_migrate_plugin.verify import verify_manifest
from memory_migrate_plugin.schema import build_canonical_package_schema, write_canonical_package_schema
from memory_migrate_plugin.validate import validate_package, validate_package_file
from memory_migrate_plugin.init_adapter import init_adapter
from memory_migrate_plugin.serve import ACTION_HISTORY, DOWNLOAD_REGISTRY, execute_web_action, record_action_history, register_download, render_history_panel, render_page, save_uploaded_zip


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

    def test_build_canonical_package_schema_describes_required_fields(self) -> None:
        schema = build_canonical_package_schema()
        self.assertEqual(schema["title"], "CanonicalMemoryPackage")
        self.assertIn("entries", schema["required"])
        self.assertEqual(schema["properties"]["entries"]["items"]["$ref"], "#/$defs/memoryEntry")
        self.assertIn("source_format", schema["$defs"]["memoryEntry"]["required"])

    def test_write_canonical_package_schema_outputs_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "canonical-memory-package.schema.json"
            schema = write_canonical_package_schema(output)
            written = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(written["$id"], schema["$id"])
            self.assertEqual(written["$schema"], "https://json-schema.org/draft/2020-12/schema")

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


    def test_official_fixtures_are_detectable(self) -> None:
        fixtures = {
            "fixtures/generic-json/sample.json": "generic-json",
            "fixtures/cline-memory-bank": "cline-memory-bank",
            "fixtures/agents-md": "agents-md",
            "fixtures/cursor-rules": "cursor-rules",
            "fixtures/claude-project": "claude-project",
        }
        for raw_path, expected in fixtures.items():
            matches = detect_format(Path(raw_path))
            self.assertEqual(matches[0][0], expected)

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


    def test_run_release_creates_release_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "entries.json"
            source.write_text(
                json.dumps([
                    {"id": "same-id", "kind": "note", "title": "T", "content": "C"}
                ]),
                encoding="utf-8",
            )
            output_dir = root / "release-out"
            zip_path = root / "release.zip"
            summary = run_release(source, "generic-json", "agents-md", output_dir, profile="agent-rules", apply_repair=False, zip_output=zip_path)
            self.assertTrue((output_dir / "RELEASE_NOTE.md").exists())
            self.assertTrue((output_dir / "release-summary.json").exists())
            self.assertTrue(zip_path.exists())
            self.assertIn("release_note_path", summary)

    def test_run_bundle_can_create_zip_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "entries.json"
            source.write_text(json.dumps([{
                "id": "same-id", "kind": "note", "title": "T", "content": "C"
            }]), encoding="utf-8")
            output_dir = root / "bundle-out"
            zip_path = root / "bundle.zip"
            summary = run_bundle(source, "generic-json", "agents-md", output_dir, profile="agent-rules", apply_repair=False, zip_output=zip_path)
            self.assertTrue(zip_path.exists())
            self.assertIsNotNone(summary["zip_sha256"])

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

    def test_save_uploaded_zip_extracts_fixture_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "fixture.zip"
            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()
            (source_dir / "projectbrief.md").write_text("Project overview", encoding="utf-8")
            import zipfile
            with zipfile.ZipFile(zip_path, "w") as archive:
                archive.write(source_dir / "projectbrief.md", arcname="projectbrief.md")
            saved = save_uploaded_zip("fixture.zip", zip_path.read_bytes(), Path(tmpdir) / "ui")
            self.assertTrue(Path(saved["zip_path"]).exists())
            self.assertTrue(Path(saved["input_path"]).exists())

    def test_record_action_history_keeps_recent_entries_only(self) -> None:
        ACTION_HISTORY.clear()
        for index in range(15):
            record_action_history(f"action-{index}", True, "input", None, None, None, "ok", [])
        self.assertEqual(len(ACTION_HISTORY), 12)
        self.assertEqual(ACTION_HISTORY[0]["action"], "action-3")

    def test_render_history_panel_shows_activity_and_downloads(self) -> None:
        ACTION_HISTORY.clear()
        DOWNLOAD_REGISTRY.clear()
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle = Path(tmpdir) / "bundle.zip"
            bundle.write_bytes(b"demo")
            download = register_download(bundle)
            record_action_history("bundle", True, "fixtures/generic-json/sample.json", "generic-json", "codex-memories", str(bundle), "done", [download])
            html = render_history_panel()
            self.assertIn("Recent Activity", html)
            self.assertIn("Recent Downloads", html)
            self.assertIn("bundle.zip", html)

    def test_register_download_returns_local_download_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "bundle.zip"
            target.write_bytes(b"demo")
            item = register_download(target)
            self.assertTrue(item["url"].startswith("/download?token="))
            self.assertEqual(item["filename"], "bundle.zip")

    def test_execute_web_action_bundle_returns_downloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "bundle-output"
            result = execute_web_action(
                "bundle",
                "fixtures/generic-json/sample.json",
                source_format="generic-json",
                target_format="codex-memories",
                output_path=str(output_dir),
            )
            self.assertTrue(result["ok"])
            self.assertGreaterEqual(len(result["downloads"]), 2)
            self.assertTrue((output_dir / "bundle-summary.json").exists())

    def test_render_page_contains_ui_shell(self) -> None:
        html = render_page()
        self.assertIn("Agent Memory Bridge", html)
        self.assertIn("Run Workflow", html)
        self.assertIn("Recent Activity", html)

    def test_execute_web_action_detect_returns_matches(self) -> None:
        result = execute_web_action("detect", "fixtures/generic-json/sample.json")
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "detect")
        self.assertGreaterEqual(len(result["result"]["matches"]), 1)

    def test_execute_web_action_normalize_writes_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "normalized.json"
            result = execute_web_action("normalize", "fixtures/generic-json/sample.json", source_format="generic-json", output_path=str(output))
            self.assertTrue(result["ok"])
            self.assertTrue(output.exists())

    def test_init_adapter_generates_scaffold_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = init_adapter("openhands-session", Path(tmpdir))
            adapter_path = Path(result["adapter_path"])
            test_path = Path(result["test_path"])
            doc_path = Path(result["doc_path"])
            self.assertTrue(adapter_path.exists())
            self.assertTrue(test_path.exists())
            self.assertTrue(doc_path.exists())
            self.assertIn("class OpenhandsSessionAdapter", adapter_path.read_text(encoding="utf-8"))
            self.assertIn("register the adapter", doc_path.read_text(encoding="utf-8").lower())

    def test_init_adapter_rejects_existing_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            init_adapter("openhands-session", Path(tmpdir))
            with self.assertRaises(FileExistsError):
                init_adapter("openhands-session", Path(tmpdir))

    def test_validate_package_accepts_valid_canonical_package(self) -> None:
        source = Path("fixtures/generic-json/sample.json")
        package = normalize("generic-json", source)
        result = validate_package(package)
        self.assertTrue(result["ok"])
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_validate_package_file_reports_errors_and_duplicate_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "invalid-package.json"
            path.write_text(
                json.dumps({
                    "schema_version": "2.0",
                    "package_id": "demo",
                    "created_at": "not-a-date",
                    "source_formats": ["generic-json", "generic-json"],
                    "metadata": {},
                    "entries": [
                        {
                            "id": "same-id",
                            "kind": "note",
                            "title": "A",
                            "content": "one",
                            "tags": ["ok"],
                            "source_format": "generic-json",
                            "metadata": {}
                        },
                        {
                            "id": "same-id",
                            "kind": "",
                            "title": "B",
                            "content": "two",
                            "tags": "bad-tags",
                            "source_format": "generic-json",
                            "metadata": []
                        }
                    ]
                }),
                encoding="utf-8",
            )
            result = validate_package_file(path)
            self.assertFalse(result["ok"])
            self.assertGreaterEqual(result["summary"]["error_count"], 3)
            self.assertGreaterEqual(result["summary"]["warning_count"], 2)

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
