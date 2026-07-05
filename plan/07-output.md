# Phase 7 — Reporter & Output

## reporter.py

The `Reporter` class owns all terminal and log output. It uses `rich` for terminal rendering and writes plain text to a log file simultaneously.

```python
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import logging

class Reporter:
    def __init__(self, dry_run: bool = False, log_file: str = "netbox-vc-builder.log"):
        self._console = Console()
        self._dry_run = dry_run
        self._log = _setup_log_file(log_file)

    def info(self, message: str) -> None:
        """Green ✓ prefix for success lines."""
    
    def warn(self, message: str) -> None:
        """Yellow ⚠ prefix for warnings. Also logged as WARNING."""
    
    def error(self, message: str) -> None:
        """Red ✗ prefix for errors. Also logged as ERROR."""
    
    def debug(self, message: str) -> None:
        """Dim text. Only shown in verbose mode. Always logged."""
    
    def section(self, title: str) -> None:
        """Prints a blank line + title line to visually group output."""
    
    def summary(self, summary: RunSummary) -> None:
        """Renders the final summary panel."""
```

---

## Color Scheme

| Symbol | Color | Use |
|--------|-------|-----|
| `✓` | green | success, created, found |
| `⚠` | yellow | warning, skipped, dry-run action |
| `✗` | red | error, failed |
| `📊` | white | summary stat labels |
| `⏱` | white | duration |

---

## Terminal Output Examples

**Per-stack processing:**
```
Checking each master for members
✓ found 1 member for TEST-1
✓ creating VC.
⚠ Setting TEST-1 as Master, priority 15 and position 1
✓ Setting TEST-2 as Member, priority 14 and position 2
```

**Dry-run indicator:**
Every action that would mutate NetBox is prefixed with `[DRY RUN]` in yellow.

**Final summary panel (Rich Panel):**
```
Summary:
  📊 4 Stacks found
  ✓ Successfully updated: 2
  ⚠ Skipped: 2
  ✗ Failed: 0
  ⏱ Duration: 8.3s
```

---

## Log File Format

Plain text, one line per event. Structured as:
```
2026-07-05 14:23:01 INFO  Found 4 possible stack masters for site bonn
2026-07-05 14:23:02 INFO  Creating VC for SWITCH (master SWITCH-1)
2026-07-05 14:23:02 WARN  Deleting Vlan1 on SWITCH-2 which has IPs: ['10.0.0.2/24']
2026-07-05 14:23:05 INFO  Summary: 4 found, 2 created, 2 skipped, 0 failed
```

Log file is always written, even in dry-run mode. The log file name is `netbox-vc-builder.log` in the current working directory. This is appended, not overwritten, so multiple runs accumulate history.

---

## Rich Panel for Summary

Use `rich.panel.Panel` with `rich.table.Table` inside for the final summary:

```
╭─────────────── Summary ───────────────╮
│  📊 4 Stacks found                    │
│  ✓ Successfully updated: 2            │
│  ⚠ Skipped: 2                        │
│  ✗ Failed: 0                          │
│  ⏱ Duration: 8.3s                    │
╰───────────────────────────────────────╯
```

---

## No-op Reporter for Tests

```python
class NullReporter(Reporter):
    """Silent reporter for use in unit tests. Discards all output."""
    def __init__(self):
        pass  # no console, no log file
    def info(self, _): pass
    def warn(self, _): pass
    def error(self, _): pass
    def debug(self, _): pass
    def summary(self, _): pass
```

Tests import and use `NullReporter()` so output doesn't pollute test runs.
