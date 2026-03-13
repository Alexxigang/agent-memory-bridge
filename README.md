# Agent Memory Bridge

[![CI](https://github.com/Alexxigang/agent-memory-bridge/actions/workflows/ci.yml/badge.svg)](https://github.com/Alexxigang/agent-memory-bridge/actions/workflows/ci.yml)
[![Release](https://github.com/Alexxigang/agent-memory-bridge/actions/workflows/release.yml/badge.svg)](https://github.com/Alexxigang/agent-memory-bridge/actions/workflows/release.yml)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

Open-source toolkit for migrating reusable memory across AI agent systems.

Agent Memory Bridge helps you move project memory, preferences, decisions, rules, and handoff context between agent products without rewriting everything by hand.

## Why it matters

Switching between AI coding tools usually means losing accumulated context:

- user preferences
- project instructions
- architecture decisions
- active task context
- reusable rules and notes

This project solves that with a portable canonical memory package plus adapter-based import/export.

## What you can do

- detect supported source formats automatically
- normalize memory into a canonical package
- publish a JSON Schema for external tool integrations
- convert across agent-specific formats
- run diagnostics with `doctor`
- generate suggestions and safe repairs
- compare migration stages
- create auditable bundles with manifests and verification
- generate distributable release bundles with zip output
- validate canonical packages before import or publishing

## Supported formats

- `generic-json`
- `markdown-bundle`
- `codex-memories`
- `cline-memory-bank`
- `cursor-rules`
- `claude-project`
- `agents-md`

## Quick start

Install locally:

```bash
python -m pip install -e .
```

List adapters:

```bash
memory-migrate adapters
```

Run a full release demo with bundled artifacts:

```bash
memory-migrate release   --input ./fixtures/cline-memory-bank   --to agents-md   --profile agent-rules   --output-dir ./dist/demo-release   --zip ./dist/demo-release.zip
```

Verify the generated bundle:

```bash
memory-migrate verify --manifest ./dist/demo-release/manifest.json
```

## Demo data

Official sample inputs live in `fixtures/`.

- quick walkthrough: `docs/demo.md`
- PowerShell demo script: `scripts/demo.ps1`

Run the included demo script:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\demo.ps1
```

## Core workflows

Inspect a source:

```bash
memory-migrate inspect --input ./fixtures/agents-md
```

Convert with a target profile:

```bash
memory-migrate convert   --input ./fixtures/generic-json/sample.json   --to cursor-rules   --profile developer-strict   --output ./dist/cursor-rules
```

Run doctor:

```bash
memory-migrate doctor --input ./fixtures/agents-md --output ./dist/agents-doctor.json
```

Run bundle:

```bash
memory-migrate bundle   --input ./fixtures/cline-memory-bank   --to agents-md   --profile agent-rules   --output-dir ./dist/bundle   --zip ./dist/bundle.zip
```

Compare stages:

```bash
memory-migrate compare   --before ./dist/bundle/canonical.json   --after ./dist/bundle/canonical.repaired.json   --output ./dist/compare.json
```

## Bundle contents

A bundle can include:

- `canonical.json`
- `canonical.repaired.json`
- `canonical.transformed.json`
- `doctor.json`
- `compare.json`
- `manifest.json`
- `bundle-summary.json`
- `exported/`
- optional zip archive

## CI and releases

- CI runs unit tests plus CLI smoke checks on push and pull request
- pushing a tag like `v0.19.0` triggers the GitHub Release workflow
- releases attach build artifacts plus a demo migration bundle

## Project structure

- `src/memory_migrate_plugin/models.py`: canonical schema
- `src/memory_migrate_plugin/core.py`: normalization and conversion pipeline
- `src/memory_migrate_plugin/profiles.py`: target-style export profiles
- `src/memory_migrate_plugin/bundle.py`: one-shot bundle workflow
- `src/memory_migrate_plugin/release.py`: release bundle generation
- `src/memory_migrate_plugin/manifest.py`: hash manifest generation
- `src/memory_migrate_plugin/verify.py`: integrity verification
- `src/memory_migrate_plugin/adapters/`: source and target adapters
- `fixtures/`: official sample inputs
- `docs/demo.md`: reproducible demo walkthrough

## Contributing

See `CONTRIBUTING.md`.

## License

MIT
