# Changelog

## 0.15.0 - 2026-03-12

- added bundle --zip option for shareable migration artifacts
- bundle summary now includes zip sha256 for integrity checks

## 0.14.0 - 2026-03-12

- added verify command for manifest-based integrity checks
- verify reports missing and mismatched files with exit code signaling

## 0.13.0 - 2026-03-12

- added manifest command for SHA256 bundle auditing
- bundle now emits manifest.json for all artifacts
- improved test coverage for manifest output

## 0.12.0 - 2026-03-12

- added compare command for canonical stage diffs
- added bundle compare artifact for repair and transform stage inspection
- added structured change reports for kind, title, content, tags, and metadata

## 0.11.0 - 2026-03-12

- added bundle command for one-shot diagnosis, repair, and export
- added bundle output workspace with canonical, repaired, transformed, and exported artifacts
- added bundle summary manifest for automation and review

## 0.10.0 - 2026-03-12

- added export profiles for target-style conversion behavior
- added profiles command and convert --profile support
- added developer-strict, project-handoff, and agent-rules presets

## 0.9.0 - 2026-03-11

- expanded cline-memory-bank adapter with decision and user context files
- improved Memory Bank detection confidence for richer Roo/Cline layouts
- preserved standard slot metadata during normalization and export

## 0.8.0 - 2026-03-11

- added AGENTS.md adapter for multi-agent instruction bundles
- added detection and export for `.agents/notes` companion files
- expanded docs and tests for AGENTS.md workflow support

## 0.7.0 - 2026-03-11

- added Cursor rules adapter for `.cursor/rules` bundles
- added Claude project adapter for `CLAUDE.md` plus companion memories
- improved auto-detection coverage for real workflow layouts
- expanded docs and tests for new ecosystem adapters

## 0.6.0 - 2026-03-11

- added doctor command for one-shot diagnosis
- added health score, severity summary, and repair preview output
- combined report, suggestions, and repaired post-check into one workflow
- expanded docs for operator-friendly diagnosis flow

## 0.5.0 - 2026-03-11

- added repair command for safe canonical package repair
- added automatic fixes for missing title, kind, id, and content
- added duplicate id renaming with numeric suffixes
- added repair report output for traceability

## 0.4.0 - 2026-03-11

- added suggest command for repair guidance
- added proposed fallback values for missing canonical fields
- added duplicate-id and duplicate-content remediation hints
- expanded README and architecture docs for repair workflows

## 0.3.0 - 2026-03-11

- added package report generation and audit summaries
- added merge report output with skipped entry reasons
- added report CLI command
- expanded tests for report and conflict visibility

## 0.2.0 - 2026-03-11

- added source format auto-detection
- added multi-source merge command
- added fingerprint-based dedupe for canonical entries
- improved README and architecture docs
- added open-source collaboration files and issue templates

## 0.1.0 - 2026-03-11

- bootstrapped canonical memory model
- added CLI for inspect, normalize, and convert
- added initial adapters for generic JSON, markdown bundle, Codex memories, and Cline Memory Bank
- added baseline tests
