from __future__ import annotations

import argparse
import json
from pathlib import Path

from memory_migrate_plugin.core import convert, export_canonical_json, normalize
from memory_migrate_plugin.merge import merge_packages
from memory_migrate_plugin.registry import build_registry, detect_format


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="memory-migrate", description="Migrate memory between AI agent systems.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("adapters", help="List supported adapters.")

    detect_parser = subparsers.add_parser("detect", help="Detect the most likely source format for a path.")
    detect_parser.add_argument("--input", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect a source and print a compact summary.")
    inspect_parser.add_argument("--format")
    inspect_parser.add_argument("--input", required=True)

    normalize_parser = subparsers.add_parser("normalize", help="Convert a source into canonical JSON.")
    normalize_parser.add_argument("--format")
    normalize_parser.add_argument("--input", required=True)
    normalize_parser.add_argument("--output", required=True)

    convert_parser = subparsers.add_parser("convert", help="Convert memory from one adapter format into another.")
    convert_parser.add_argument("--from", dest="source_format")
    convert_parser.add_argument("--input", required=True)
    convert_parser.add_argument("--to", dest="target_format", required=True)
    convert_parser.add_argument("--output", required=True)

    merge_parser = subparsers.add_parser("merge", help="Merge multiple memory sources into one canonical package.")
    merge_parser.add_argument("--inputs", nargs="+", required=True)
    merge_parser.add_argument("--formats", nargs="*")
    merge_parser.add_argument("--output", required=True)
    merge_parser.add_argument("--package-id", default="merged-memory-package")
    merge_parser.add_argument("--no-dedupe", action="store_true")

    return parser


def command_adapters() -> int:
    registry = build_registry()
    for name, adapter in registry.items():
        print(f"{name}\t{adapter.description}")
    return 0


def command_detect(source_path: Path) -> int:
    matches = detect_format(source_path)
    if not matches:
        raise SystemExit(f"No supported format detected for {source_path}")
    print(json.dumps([{"format": name, "confidence": confidence} for name, confidence in matches], indent=2))
    return 0


def command_inspect(source_format: str | None, source_path: Path) -> int:
    package = normalize(source_format, source_path)
    preview = {
        "package_id": package.package_id,
        "schema_version": package.schema_version,
        "source_formats": package.source_formats,
        "entry_count": len(package.entries),
        "kinds": sorted({entry.kind for entry in package.entries}),
        "titles": [entry.title for entry in package.entries[:10]],
    }
    print(json.dumps(preview, indent=2, ensure_ascii=False))
    return 0


def command_normalize(source_format: str | None, source_path: Path, output_path: Path) -> int:
    package = normalize(source_format, source_path)
    export_canonical_json(package, output_path)
    print(f"Wrote canonical package to {output_path}")
    return 0


def command_convert(source_format: str | None, source_path: Path, target_format: str, output_path: Path) -> int:
    package = convert(source_format, source_path, target_format, output_path)
    print(
        f"Converted {len(package.entries)} entries to {target_format} at {output_path}"
    )
    return 0


def command_merge(inputs: list[str], formats: list[str] | None, output: Path, package_id: str, no_dedupe: bool) -> int:
    resolved_formats = formats or []
    if resolved_formats and len(resolved_formats) != len(inputs):
        raise SystemExit("--formats must match the number of --inputs when provided")

    packages = []
    for index, input_path in enumerate(inputs):
        source_format = resolved_formats[index] if resolved_formats else None
        packages.append(normalize(source_format, Path(input_path)))

    merged = merge_packages(packages, package_id=package_id, dedupe=not no_dedupe)
    export_canonical_json(merged, output)
    print(f"Merged {len(inputs)} sources into {output} with {len(merged.entries)} entries")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "adapters":
        return command_adapters()
    if args.command == "detect":
        return command_detect(Path(args.input))
    if args.command == "inspect":
        return command_inspect(args.format, Path(args.input))
    if args.command == "normalize":
        return command_normalize(args.format, Path(args.input), Path(args.output))
    if args.command == "convert":
        return command_convert(args.source_format, Path(args.input), args.target_format, Path(args.output))
    if args.command == "merge":
        return command_merge(args.inputs, args.formats, Path(args.output), args.package_id, args.no_dedupe)
    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
