# Agent Memory Bridge

Agent Memory Bridge is an open-source toolkit for migrating reusable memory across AI agent systems.

Instead of rewriting project context, preferences, long-term notes, and decision history every time you switch tools, this project converts memory into a shared canonical model and then exports it into target-specific formats.

## Why this can work

Different agent products store memory differently, but the useful information is usually the same:

- user profile and preferences
- project context and constraints
- decisions and durable facts
- tasks, plans, and recurring instructions
- reusable snippets and references

That means the hard problem is not "remember everything exactly as the source product does". The practical problem is "preserve the meaning and structure well enough to continue work in another product".

This repository focuses on that practical layer.

## Product direction

The current architecture uses three ideas:

1. A canonical memory package format (`CanonicalMemoryPackage`)
2. Source and target adapters for each agent ecosystem
3. A CLI that imports, inspects, auto-detects, normalizes, merges, audits, suggests repairs, auto-repairs, diagnoses, and exports memory

## Current scope

Supported adapters in this version:

- `generic-json`: import or export canonical-friendly JSON files
- `markdown-bundle`: import or export a folder of markdown memory notes
- `codex-memories`: import or export markdown memories compatible with a simple Codex-style memory folder layout
- `cline-memory-bank`: import or export common Memory Bank markdown files used by Cline/Roo-style workflows
- `cursor-rules`: import or export Cursor-style `.cursor/rules/*.mdc` rule bundles
- `claude-project`: import or export `CLAUDE.md` project memory plus companion notes

Key capabilities:

- auto-detect supported input formats
- merge multiple memory sources into one canonical package
- fingerprint-based dedupe for obvious duplicates
- deterministic JSON output for review and diffing
- migration report generation with audit findings
- repair suggestions for missing fields and duplicate patterns
- safe repair output that writes a new canonical package instead of overwriting the source
- doctor workflow that combines report, suggestions, and repair preview into one diagnosis
- adapters for Cursor rules and Claude project memory layouts

The architecture is intentionally adapter-first, so more products can be added without changing the core model.

## Installation

```bash
python -m pip install -e .
```

## CLI usage

List available adapters:

```bash
memory-migrate adapters
```

Detect a source format automatically:

```bash
memory-migrate detect --input ./memory-bank
```

Inspect a source without manually passing `--format`:

```bash
memory-migrate inspect --input ./memory-bank
```

Normalize a source into the canonical package:

```bash
memory-migrate normalize --input ./memory-bank --output ./dist/canonical.json
```

Convert from one format into another:

```bash
memory-migrate convert --input ./memory-bank --to codex-memories --output ./dist/codex-memories
```

Run a full doctor workflow:

```bash
memory-migrate doctor --input ./dist/merged.json --output ./dist/doctor.json
```

Generate a repaired canonical package:

```bash
memory-migrate repair \
  --input ./dist/merged.json \
  --output ./dist/merged.repaired.json \
  --report-output ./dist/repair-report.json
```

## Doctor workflow

The `doctor` command combines:

- a structural audit report
- repair suggestions
- a non-destructive repair preview
- a simple health score for the current package

This makes the CLI easier to use when you want one command that tells you what is wrong, what can be fixed, and what the repaired result would look like.

## Reports, suggestions, and repair

The report layer summarizes:

- source formats and entry counts
- entry kinds and top tags
- missing required fields
- duplicate ids inside a package
- duplicate content fingerprints inside a package
- merge-time skipped entries and likely conflict candidates

The suggestion layer adds:

- proposed fallback values for missing `id`, `kind`, or `title`
- duplicate-id cleanup guidance
- duplicate-content review guidance

The repair layer can then:

- fill missing `title` from `id`
- fill missing `kind` with `note`
- generate missing `id` from a slugified title
- fill missing `content` with a clear placeholder
- rename duplicate ids with numeric suffixes

This makes migration results explainable and actionable instead of opaque.

## Canonical model

The canonical package stores:

- package metadata
- source provenance
- normalized entries

Each entry includes:

- `id`
- `kind`
- `title`
- `content`
- `tags`
- `metadata`
- timestamps when available

This is enough for a wide range of memory systems while staying easy to inspect and diff.

## Project structure

- `src/memory_migrate_plugin/models.py`: canonical schema
- `src/memory_migrate_plugin/core.py`: conversion pipeline
- `src/memory_migrate_plugin/merge.py`: merge and dedupe logic
- `src/memory_migrate_plugin/report.py`: reporting and audit logic
- `src/memory_migrate_plugin/suggest.py`: repair suggestion logic
- `src/memory_migrate_plugin/repair.py`: safe auto-repair logic
- `src/memory_migrate_plugin/doctor.py`: one-shot diagnosis workflow
- `src/memory_migrate_plugin/adapters/`: source and target adapters, including Cursor and Claude project layouts
- `src/memory_migrate_plugin/cli.py`: command-line interface
- `docs/architecture.md`: design and roadmap

## Feasibility and roadmap

### Feasible now

- migrate markdown and JSON based memory stores
- standardize memory into a portable package
- preserve tags, categories, provenance, and notes
- merge multiple memory inputs into one handoff package
- generate target-specific output layouts
- audit migration results for obvious issues
- suggest likely repairs before export
- auto-repair common canonical issues into a new package
- run a full doctor diagnosis in one command

### Hard but still doable later

- richer product-specific adapters for proprietary formats
- conflict resolution across multiple memory sources
- semantic dedupe and similarity-based merge
- embeddings-based retrieval and re-ranking
- encrypted sync and remote registry support

### Not guaranteed in every product

If a closed-source tool stores memory in encrypted local databases or private cloud APIs, full fidelity export may require reverse engineering or official integration.

That does not block the product itself. It just changes how deep a specific adapter can go.

## Contributing

See `CONTRIBUTING.md`.

## License

MIT
