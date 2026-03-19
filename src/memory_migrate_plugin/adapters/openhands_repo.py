from __future__ import annotations

from pathlib import Path

from memory_migrate_plugin.adapters.base import BaseAdapter
from memory_migrate_plugin.models import CanonicalMemoryPackage, MemoryEntry
from memory_migrate_plugin.utils import read_text, slugify, write_text


class OpenHandsRepoAdapter(BaseAdapter):
    name = "openhands-repo"
    description = "OpenHands repository customization bundles with AGENTS.md, scripts, skills, and microagents."

    def probe(self, path: Path) -> bool:
        if not path.is_dir():
            return False
        return any(
            candidate.exists()
            for candidate in (
                path / ".openhands",
                path / ".agents" / "skills",
                path / ".openhands" / "skills",
                path / ".openhands" / "microagents",
            )
        )

    def detect_confidence(self, path: Path) -> int:
        if not self.probe(path):
            return 0
        score = 86
        if (path / ".openhands" / "setup.sh").exists():
            score += 4
        if (path / ".openhands" / "pre-commit.sh").exists():
            score += 4
        if (path / ".agents" / "skills").exists() or (path / ".openhands" / "skills").exists():
            score += 4
        if (path / ".openhands" / "microagents").exists():
            score += 4
        return min(score, 99)

    def read(self, path: Path) -> CanonicalMemoryPackage:
        package = CanonicalMemoryPackage(package_id=path.name or self.name, source_formats=[self.name])

        agents_file = path / "AGENTS.md"
        if agents_file.exists():
            package.add_entry(
                MemoryEntry(
                    id="openhands-agents",
                    kind="instruction",
                    title="OpenHands Repository Instructions",
                    content=read_text(agents_file).strip(),
                    tags=["openhands", "agents", "instructions"],
                    source_format=self.name,
                    metadata={
                        "filename": agents_file.name,
                        "relative_path": "AGENTS.md",
                        "openhands_role": "agents",
                    },
                )
            )

        script_map = {
            path / ".openhands" / "setup.sh": ("OpenHands Setup Script", ["openhands", "setup", "script"], "setup-script"),
            path / ".openhands" / "pre-commit.sh": ("OpenHands Pre-commit Script", ["openhands", "pre-commit", "script"], "pre-commit-script"),
        }
        for script_path, (title, tags, role) in script_map.items():
            if not script_path.exists():
                continue
            package.add_entry(
                MemoryEntry(
                    id=slugify(title),
                    kind="automation",
                    title=title,
                    content=read_text(script_path).strip(),
                    tags=tags,
                    source_format=self.name,
                    metadata={
                        "filename": script_path.name,
                        "relative_path": script_path.relative_to(path).as_posix(),
                        "openhands_role": role,
                    },
                )
            )

        skill_roots = [path / ".agents" / "skills", path / ".openhands" / "skills"]
        for skill_root in skill_roots:
            if not skill_root.exists():
                continue
            for skill_file in sorted(skill_root.rglob("SKILL.md")):
                skill_dir = skill_file.parent.name
                package.add_entry(
                    MemoryEntry(
                        id=slugify(f"skill-{skill_dir}"),
                        kind="skill",
                        title=skill_dir.replace("-", " ").replace("_", " ").title(),
                        content=read_text(skill_file).strip(),
                        tags=["openhands", "skill"],
                        source_format=self.name,
                        metadata={
                            "filename": skill_file.name,
                            "relative_path": skill_file.relative_to(path).as_posix(),
                            "skill_name": skill_dir,
                            "openhands_role": "skill",
                        },
                    )
                )

        microagents_dir = path / ".openhands" / "microagents"
        if microagents_dir.exists():
            for microagent_file in sorted(microagents_dir.rglob("*.md")):
                stem = microagent_file.stem
                kind = "project" if microagent_file.name.lower() == "repo.md" else "instruction"
                tags = ["openhands", "microagent"]
                if kind == "project":
                    tags.append("repo")
                package.add_entry(
                    MemoryEntry(
                        id=slugify(f"microagent-{stem}"),
                        kind=kind,
                        title=stem.replace("-", " ").replace("_", " ").title(),
                        content=read_text(microagent_file).strip(),
                        tags=tags,
                        source_format=self.name,
                        metadata={
                            "filename": microagent_file.name,
                            "relative_path": microagent_file.relative_to(path).as_posix(),
                            "openhands_role": "microagent",
                        },
                    )
                )

        return package

    def write(self, package: CanonicalMemoryPackage, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        main_entry = self._select_main_entry(package)
        if main_entry is not None:
            write_text(path / "AGENTS.md", main_entry.content.rstrip() + "\n")

        self._write_scripts(package, path)
        self._write_skills(package, path)
        self._write_microagents(package, path, main_entry)

    def _select_main_entry(self, package: CanonicalMemoryPackage) -> MemoryEntry | None:
        for entry in package.entries:
            if entry.metadata.get("openhands_role") == "agents":
                return entry
        for entry in package.entries:
            if entry.kind in {"instruction", "project"}:
                return entry
        return package.entries[0] if package.entries else None

    def _write_scripts(self, package: CanonicalMemoryPackage, path: Path) -> None:
        script_targets = {
            "setup-script": path / ".openhands" / "setup.sh",
            "pre-commit-script": path / ".openhands" / "pre-commit.sh",
        }
        for role, target in script_targets.items():
            entry = next((item for item in package.entries if item.metadata.get("openhands_role") == role), None)
            if entry is None:
                entry = next(
                    (
                        item
                        for item in package.entries
                        if item.kind == "automation"
                        and ((role == "setup-script" and "setup" in item.tags) or (role == "pre-commit-script" and "pre-commit" in item.tags))
                    ),
                    None,
                )
            if entry is not None:
                write_text(target, entry.content.rstrip() + "\n")

    def _write_skills(self, package: CanonicalMemoryPackage, path: Path) -> None:
        skill_entries = [
            entry for entry in package.entries if entry.metadata.get("openhands_role") == "skill" or entry.kind == "skill"
        ]
        for entry in skill_entries:
            skill_name = str(entry.metadata.get("skill_name", slugify(entry.title or entry.id)))
            target = path / ".agents" / "skills" / skill_name / "SKILL.md"
            write_text(target, entry.content.rstrip() + "\n")

    def _write_microagents(self, package: CanonicalMemoryPackage, path: Path, main_entry: MemoryEntry | None) -> None:
        for entry in package.entries:
            if main_entry is not None and entry.id == main_entry.id:
                continue
            if entry.metadata.get("openhands_role") in {"setup-script", "pre-commit-script", "skill"}:
                continue
            if entry.kind == "automation":
                continue
            if entry.metadata.get("openhands_role") == "microagent" or entry.kind in {"instruction", "project", "note", "reference"}:
                filename = entry.metadata.get("filename")
                if not isinstance(filename, str) or not filename.endswith(".md"):
                    filename = f"{slugify(entry.title or entry.id)}.md"
                write_text(path / ".openhands" / "microagents" / filename, entry.content.rstrip() + "\n")
