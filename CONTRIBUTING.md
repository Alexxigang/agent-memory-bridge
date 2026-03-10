# Contributing

Thanks for contributing to Agent Memory Bridge.

## Development setup

```bash
python -m venv .venv
. .venv/Scripts/activate
python -m pip install -e .
set PYTHONPATH=src
python -m unittest discover -s tests -v
```

## Contribution guidelines

- keep adapters deterministic and file-based when possible
- preserve source provenance in entry metadata
- avoid product-specific assumptions in the canonical model
- add or update tests for every adapter or merge behavior change
- document new adapter formats in `README.md`

## Pull requests

Please include:

- what source and target formats are affected
- example input/output shape
- any migration edge cases or limitations
- tests that cover the new behavior
