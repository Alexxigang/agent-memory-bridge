# Demo Guide

This repository includes official sample fixtures under `fixtures/`.

## Quick demo

List adapters:

```bash
memory-migrate adapters
```

Inspect a fixture:

```bash
memory-migrate inspect --input ./fixtures/cline-memory-bank
```

Run a one-shot release demo:

```bash
memory-migrate release   --input ./fixtures/cline-memory-bank   --to agents-md   --profile agent-rules   --output-dir ./dist/demo-release   --zip ./dist/demo-release.zip
```

Verify the release bundle:

```bash
memory-migrate verify --manifest ./dist/demo-release/manifest.json
```

## Useful fixture conversions

Convert generic JSON into Cursor rules:

```bash
memory-migrate convert   --input ./fixtures/generic-json/sample.json   --to cursor-rules   --profile developer-strict   --output ./dist/cursor-rules
```

Generate a doctor report from AGENTS instructions:

```bash
memory-migrate doctor --input ./fixtures/agents-md --output ./dist/agents-doctor.json
```
