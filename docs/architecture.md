# Architecture

## Problem statement

Teams and individuals increasingly switch between AI coding agents, general assistants, and open-source derivatives. Every switch risks losing important accumulated memory: project context, constraints, habits, decisions, and reusable notes.

This project solves that by introducing a portable intermediate memory layer.

## Core architecture

```text
source adapter -> canonical memory package -> target adapter
```

The canonical layer is the contract.

## Canonical entities

The MVP uses a single flexible entity type, `MemoryEntry`, plus package metadata.

Recommended `kind` values:

- `profile`
- `preference`
- `project`
- `decision`
- `task`
- `instruction`
- `snippet`
- `reference`
- `note`

This keeps the data model simple while still allowing downstream adapters to map content into more specialized formats.

## Adapter contract

Each adapter implements:

- `read(path) -> CanonicalMemoryPackage`
- `write(package, path)`
- `probe(path) -> bool`

This supports explicit conversion and future auto-detection.

## MVP choices

- Python standard library only
- file-based interoperability first
- deterministic JSON output for easy diffing
- markdown-friendly exports for human editing

## Suggested next phases

1. Add auto-detect scoring for unknown sources
2. Add merge and dedupe strategies
3. Add product-specific adapters for more agent ecosystems
4. Add a small web UI for drag-and-drop migration
5. Add signed package manifests and optional encryption
