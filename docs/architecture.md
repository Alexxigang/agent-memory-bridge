# Architecture

## Problem statement

Teams and individuals increasingly switch between AI coding agents, general assistants, and open-source derivatives. Every switch risks losing important accumulated memory: project context, constraints, habits, decisions, and reusable notes.

This project solves that by introducing a portable intermediate memory layer.

## Core architecture

```text
source adapter -> canonical memory package -> target adapter
                              |
                              +-> merge + dedupe + audit + reporting + suggestions + repair + doctor
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
- `detect_confidence(path) -> int`

This supports explicit conversion and lightweight auto-detection.

## Merge and dedupe

The merge layer combines multiple canonical packages into one output package.

Current dedupe behavior is intentionally conservative:

- exact duplicate `id` values are skipped
- duplicate fingerprints based on `kind + title + content` are skipped

The detailed merge result also records skipped entries so the CLI can emit an audit report.

## Reporting, suggestions, repair, and doctor

The report layer inspects canonical packages and merge results for explainability.
The suggestion layer turns those findings into lightweight remediation guidance.
The repair layer applies a safe subset of those fixes into a new package.
The doctor layer orchestrates all three into one operator-friendly diagnosis.

Current doctor output includes:

- health score
- highest suggestion severity
- issue count and repairable entry count
- structural report
- suggestions
- repair preview with post-repair report

## MVP choices

- Python standard library only
- file-based interoperability first
- deterministic JSON output for easy diffing
- markdown-friendly exports for human editing
- no network dependency for core migrations
- repair always writes a new output file
- doctor never mutates the input package

## Suggested next phases

1. Add field-level conflict reports and repair suggestions
2. Add merge strategies per entry kind
3. Add product-specific adapters for more agent ecosystems
4. Add a small web UI for drag-and-drop migration
5. Add signed package manifests and optional encryption


## Ecosystem adapters

The project now includes higher-value adapters for common developer workflows:

- `cursor-rules`: reads and writes `.cursor/rules` instruction bundles
- `claude-project`: reads and writes `CLAUDE.md` plus companion memory notes
- `agents-md`: reads and writes `AGENTS.md` plus `.agents/notes` collaboration bundles

These adapters are still file-based and deterministic, which keeps migrations inspectable and easy to diff.
