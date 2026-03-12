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

## Continuous integration

Pull requests are validated by GitHub Actions on Python 3.11 and 3.12. The workflow runs unit tests and a small end-to-end CLI smoke test.

## Fixtures and demos

When adding a new adapter or workflow, prefer adding or updating a sample under `fixtures/` and documenting a reproducible command in `docs/demo.md`.

## Release process

To cut a release, bump the version, update `CHANGELOG.md`, push to `main`, and create a git tag like `v0.18.0`. GitHub Actions will build artifacts and publish a GitHub Release.
