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
3. A CLI that imports, inspects, auto-detects, normalizes, merges, and exports memory

## Current scope

Supported adapters in this version:

- `generic-json`: import or export canonical-friendly JSON files
- `markdown-bundle`: import or export a folder of markdown memory notes
- `codex-memories`: import or export markdown memories compatible with a simple Codex-style memory folder layout
- `cline-memory-bank`: import or export common Memory Bank markdown files used by Cline/Roo-style workflows

Key v0.2 capabilities:

- auto-detect supported input formats
- merge multiple memory sources into one canonical package
- fingerprint-based dedupe for obvious duplicates
- deterministic JSON output for review and diffing

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

Merge multiple sources into one canonical package:

```bash
memory-migrate merge   --inputs ./memory-bank ./notes ./entries.json   --output ./dist/merged.json
```

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
- `src/memory_migrate_plugin/adapters/`: source and target adapters
- `src/memory_migrate_plugin/cli.py`: command-line interface
- `docs/architecture.md`: design and roadmap

## Feasibility and roadmap

### Feasible now

- migrate markdown and JSON based memory stores
- standardize memory into a portable package
- preserve tags, categories, provenance, and notes
- merge multiple memory inputs into one handoff package
- generate target-specific output layouts

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
