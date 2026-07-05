# Phase 9 — Packaging & CI/CD

## PyPI Publishing

The project uses `hatchling` as the build backend (specified in `pyproject.toml`).

```bash
# Build distribution
uv build

# Publish to PyPI
uv publish
```

**Version strategy:** Start at `0.1.0`. Use semantic versioning:
- `0.x.0` for feature releases during pre-1.0
- `0.0.x` for bug fixes
- `1.0.0` when the tool is stable and the API is settled

**Version location:** Single source in `pyproject.toml`. No version in `__init__.py` — Typer's `--version` reads it dynamically:
```python
@app.callback()
def callback(version: bool = typer.Option(None, "--version", is_eager=True)):
    if version:
        import importlib.metadata
        typer.echo(importlib.metadata.version("netbox-vc-builder"))
        raise typer.Exit()
```

---

## GitHub Actions

### `.github/workflows/ci.yml` — Run on every push and PR

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: uv sync --dev
      - name: Lint
        run: uv run ruff check .
      - name: Format check
        run: uv run ruff format --check .
      - name: Test
        run: uv run pytest --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v4
```

### `.github/workflows/publish.yml` — Publish on GitHub Release

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write  # for trusted publishing
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

Use PyPI **Trusted Publishing** (OIDC) — no API token stored in GitHub secrets.

---

## Python Version Support

| Python | Status |
|--------|--------|
| 3.11 | Minimum supported (union types with `|`, `tomllib`) |
| 3.12 | Supported |
| 3.13 | Supported |

---

## Pre-commit Hooks (Optional but Recommended)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

---

## Release Checklist

Before tagging a release:
1. `uv run pytest --cov` — all tests pass, coverage ≥ 80%
2. `uv run ruff check .` — no lint errors
3. `uv run ruff format --check .` — no formatting issues
4. Update `CHANGELOG.md` (or GitHub Release notes)
5. Bump version in `pyproject.toml`
6. Commit, tag, push, create GitHub Release → CI auto-publishes to PyPI
