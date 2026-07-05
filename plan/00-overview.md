# netbox-vc-builder — Master Plan

## Goal

Build a professional-grade Python CLI tool that automates the creation and maintenance of Virtual Chassis (VC) in NetBox for Cisco switch stacks. The tool is publishable to PyPI and suitable for use in production network automation pipelines.

---

## Phases

| # | Phase | Goal |
|---|-------|-------|
| 1 | Project Bootstrap | pyproject.toml, package skeleton, tooling |
| 2 | Data Models & Constants | Core data structures (no NetBox dependency) |
| 3 | NetBox API Layer | Thin client wrapping pynetbox |
| 4 | Business Logic | find_masters → find_members → check_members → build_vc → interface ops |
| 5 | CLI & Output | Typer CLI, Rich terminal output, dry-run, logging |
| 6 | Configuration | ENV vars, YAML config file, precedence chain |
| 7 | Testing | pytest, mocks, coverage ≥ 80% |
| 8 | Packaging & CI | PyPI packaging, GitHub Actions |

---

## Execution Order

Phases 1 and 2 are prerequisites. Phases 3–6 can be built incrementally, with each phase adding testable surface area. Phase 7 runs continuously alongside all phases. Phase 8 is last.

---

## Key Constraints

- **No side effects in check mode (-C):** No NetBox writes ever happen. All write calls are guarded.
- **Never touch a device that is already a VC master (unless --overwrite):** Safety check runs before any mutation.
- **Idempotent by default:** Running twice without --overwrite must not change a completed VC.
- **All output must also go to a log file:** Every line printed to the terminal is also written to a structured log.
- **Manufacturer filter is required:** Only Cisco devices are processed. The slug is configurable but defaults to `cisco`.

---

## Plan Documents

| File | Covers |
|------|--------|
| `01-project-setup.md` | Directory layout, pyproject.toml, tooling |
| `02-architecture.md` | Module map, data flow, dependency graph |
| `03-data-models.md` | Dataclasses (models.py, constants.py) |
| `04-netbox-client.md` | NetBox API layer design |
| `05-business-logic.md` | All five core processing modules |
| `06-cli.md` | Typer CLI, config loading |
| `07-output.md` | Rich reporter and log file |
| `08-testing.md` | Test strategy, fixtures, coverage |
| `09-packaging.md` | PyPI, GitHub Actions CI |
