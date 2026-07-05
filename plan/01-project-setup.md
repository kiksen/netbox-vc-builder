# Phase 1 — Project Setup

## Directory Layout

```
netbox-vc-builder/
├── netbox_vc_builder/
│   ├── __init__.py
│   ├── cli.py               # Typer app, entry point
│   ├── config.py            # Config loading (env + yaml + cli args)
│   ├── constants.py         # All magic strings and defaults
│   ├── models.py            # Dataclasses: StackMaster, StackMember, VCResult
│   ├── netbox_client.py     # Thin wrapper around pynetbox
│   ├── find_masters.py      # Discover *-1 master candidates for a site
│   ├── find_members.py      # Discover *-N members for a given master prefix
│   ├── check_members.py     # Validate candidates are not already in a VC
│   ├── build_vc.py          # Create/delete/update Virtual Chassis records
│   ├── interface_ops.py     # Interface renaming and cleanup
│   └── reporter.py          # Rich-based terminal and log output
├── tests/
│   ├── conftest.py          # Shared fixtures (mock NetBox client)
│   ├── test_find_masters.py
│   ├── test_find_members.py
│   ├── test_check_members.py
│   ├── test_build_vc.py
│   ├── test_interface_ops.py
│   ├── test_config.py
│   └── test_cli.py
├── plan/                    # This directory
├── pyproject.toml
├── uv.lock
├── .python-version
├── .gitignore
├── LICENSE
└── README.md
```

---

## pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "netbox-vc-builder"
version = "0.1.0"
description = "Build and maintain Cisco switch stacks as clean Virtual Chassis in NetBox"
readme = "README.md"
license = { file = "LICENSE" }
requires-python = ">=3.11"
authors = [
  { name = "Christian Knoblauch", email = "christian.knoblauch@gmx.de" },
]
keywords = ["netbox", "cisco", "network-automation", "virtual-chassis", "stack"]
classifiers = [
  "Development Status :: 4 - Beta",
  "Environment :: Console",
  "Intended Audience :: System Administrators",
  "License :: OSI Approved :: MIT License",
  "Programming Language :: Python :: 3",
  "Topic :: System :: Networking",
]
dependencies = [
  "typer>=0.12",
  "rich>=13",
  "pynetbox>=7",
  "pyyaml>=6",
]

[project.scripts]
netbox-vc-builder = "netbox_vc_builder.cli:app"

[project.urls]
Homepage = "https://github.com/kiksen1987/netbox-vc-builder"
Issues = "https://github.com/kiksen1987/netbox-vc-builder/issues"

[dependency-groups]
dev = [
  "pytest>=8",
  "pytest-cov>=5",
  "ruff>=0.4",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
ignore = ["E501"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--tb=short"

[tool.coverage.run]
source = ["netbox_vc_builder"]
omit = ["tests/*"]

[tool.coverage.report]
fail_under = 80
```

---

## Tooling Setup Commands

```bash
uv init --no-workspace
uv add typer rich pynetbox pyyaml
uv add --dev pytest pytest-cov ruff
uv run pytest   # verify test discovery works
```

---

## .python-version

Pin to `3.11` as the minimum supported version. Python 3.11+ has better error messages and `tomllib` in stdlib (useful if we ever need TOML config).
