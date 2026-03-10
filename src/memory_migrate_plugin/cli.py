from __future__ import annotations

import argparse
import json
from pathlib import Path

from memory_migrate_plugin.core import convert, export_canonical_json, normalize
from memory_migrate_plugin.registry import build_registry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="memory-migrate", description="Migrate memory between AI agent systems.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("adapters", help="List supported adapters.")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect a source and print a compact summary.")
    inspect_parser.add_argument("--format", required=True)
    inspect_parser.add_argument("--input", required=True)

    normalize_parser = subparsers.add_parser("normalize", help="Convert a source into canonical JSON.")
    normalize_parser.add_argument("--format", required=True)
    normalize_parser.add_argument("--input", required=True)
    normalize_parser.add_argument("--output", required=True)

    convert_parser = subparsers.add_parser("convert", help="Convert memory from one adapter format into another.")
    convert_parser.add_argument("--from", dest="source_format", required=True)
    convert_parser.add_argument("--input", required=True)
    convert_parser.add_argument("--to", dest="target_format", required=True)
    convert_parser.add_argument("--output", required=True)

    return parser


def command_adapters() -> int:
    registry = build_registry()
    for name, adapter in registry.items():
        print(f"{name}	{adapter.description}")
    return 0


def command_inspect(source_format: str, source_path: Path) -> int:
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


def command_normalize(source_format: str, source_path: Path, output_path: Path) -> int:
    package = normalize(source_format, source_path)
    export_canonical_json(package, output_path)
    print(f"Wrote canonical package to {output_path}")
    return 0


def command_convert(source_format: str, source_path: Path, target_format: str, output_path: Path) -> int:
    package = convert(source_format, source_path, target_format, output_path)
    print(
        f"Converted {len(package.entries)} entries from {source_format} to {target_format} at {output_path}"
    )
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "adapters":
        return command_adapters()
    if args.command == "inspect":
        return command_inspect(args.format, Path(args.input))
    if args.command == "normalize":
        return command_normalize(args.format, Path(args.input), Path(args.output))
    if args.command == "convert":
        return command_convert(args.source_format, Path(args.input), args.target_format, Path(args.output))
    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
