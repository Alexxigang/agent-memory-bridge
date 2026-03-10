from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from memory_migrate_plugin.core import convert, normalize


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


if __name__ == "__main__":
    unittest.main()
