# Phase 3 — Data Models & Constants

## constants.py

```python
# Default manufacturer filter
DEFAULT_MANUFACTURER_SLUG = "cisco"

# Stack suffix range supported (Cisco C9000 max = 8 members)
STACK_MIN_POSITION = 1
STACK_MAX_POSITION = 8

# VC priority formula: priority = 16 - position
# master (pos 1) → 15, member 2 → 14, member 3 → 13 ...
VC_PRIORITY_BASE = 16

# Interface patterns
# Matches: GigabitEthernet1/0/1  TenGigabitEthernet1/1/1  etc.
# Captures: (name_prefix)(stack_number)(/rest/of/port)
# Three-part:  X/Y/Z  → groups: prefix, stack_num, /Y/Z
# Four-part:   X/Y/Z/W → groups: prefix, stack_num, /Y/Z/W
INTERFACE_PATTERN_3PART = r"^([A-Za-z\-]+)(\d+)(\/\d+\/\d+)$"
INTERFACE_PATTERN_4PART = r"^([A-Za-z\-]+)(\d+)(\/\d+\/\d+\/\d+)$"

# Interface names to remove on non-master members
MGMT_ONLY_FLAG = "mgmt_only"  # pynetbox field name
VLAN1_INTERFACE_NAME = "Vlan1"  # canonical NetBox name (case-exact on Cisco IOS)

# Interface types that must never be renamed (only physical interfaces are renamed)
NON_PHYSICAL_INTERFACE_TYPES = {"virtual", "lag", "bridge"}

# Environment variable names
ENV_NETBOX_ENDPOINT = "NETBOX_ENDPOINT"
ENV_NETBOX_TOKEN = "NETBOX_TOKEN"

# Config file name (searched in current directory)
CONFIG_FILE_NAME = ".netbox-vc-builder.yaml"

# Log file
LOG_FILE_NAME = "netbox-vc-builder.log"
```

---

## models.py

```python
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AppConfig:
    """Merged configuration from all sources."""
    netbox_endpoint: str
    netbox_token: str
    site_slug: str
    manufacturer_slug: str = "cisco"
    dry_run: bool = False
    overwrite: bool = False


@dataclass
class StackMember:
    """A single device that is a candidate or confirmed member of a stack."""
    id: int
    name: str
    position: int                     # derived from suffix: SWITCH-3 → 3
    priority: int                     # 16 - position
    existing_vc_id: Optional[int]     # None if not currently in any VC
    interface_ids: list[int] = field(default_factory=list)  # populated lazily


@dataclass
class StackMaster(StackMember):
    """The -1 device that owns the VC."""
    prefix: str = ""                  # SWITCH from SWITCH-1
    members: list["StackMember"] = field(default_factory=list)


@dataclass
class InterfaceRecord:
    """Minimal interface data needed for rename/delete decisions."""
    id: int
    name: str
    interface_type: str               # NetBox "type" value, e.g. "virtual", "1000base-t"
    mgmt_only: bool
    ip_address_count: int             # number of IPs assigned (from NetBox counts)
    ip_addresses: list[str] = field(default_factory=list)  # "x.x.x.x/prefix"


@dataclass
class VCResult:
    """Outcome of processing a single stack master."""
    master_name: str
    member_count: int
    status: str                       # "created", "skipped", "failed", "dry_run"
    message: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass
class RunSummary:
    """Aggregated result across all stacks for the final report."""
    site_slug: str
    stacks_found: int = 0
    created: int = 0
    skipped: int = 0
    failed: int = 0
    dry_run_count: int = 0
    warnings: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    results: list[VCResult] = field(default_factory=list)
```

---

## Naming Logic (parse_stack_name)

This utility lives in `models.py` or a small `utils.py`:

```python
import re

STACK_NAME_PATTERN = re.compile(r"^(.+)-(\d+)$")

def parse_stack_name(device_name: str) -> tuple[str, int] | None:
    """
    Returns (prefix, position) or None if the name does not match the stack pattern.
    
    Examples:
      "SWITCH-1"      → ("SWITCH", 1)
      "SWITCH-CORE-2" → ("SWITCH-CORE", 2)
      "ROUTER"        → None
    """
    m = STACK_NAME_PATTERN.match(device_name)
    if m:
        return m.group(1), int(m.group(2))
    return None
```

**Rule:** position must be in range 1–8 (STACK_MIN/MAX_POSITION) to be considered a valid stack member. This prevents devices named like `SWITCH-99` from being treated as stack members.

---

## Interface Renaming Logic (interface_ops.py)

```python
import re
from .constants import INTERFACE_PATTERN_3PART, INTERFACE_PATTERN_4PART

def rename_interface(current_name: str, new_position: int) -> str | None:
    """
    Given an interface name and the target stack position,
    return the corrected name, or None if the name does not match
    any known pattern (meaning: leave it alone).
    
    Examples:
      rename_interface("GigabitEthernet1/0/1", 2) → "GigabitEthernet2/0/1"
      rename_interface("TenGigabitEthernet1/1/0/1", 3) → "TenGigabitEthernet3/1/0/1"
      rename_interface("Vlan1", 2) → None  (no change, vlan is handled separately)
      rename_interface("mgmt0", 2) → None  (no matching pattern)
    """
    for pattern in (INTERFACE_PATTERN_4PART, INTERFACE_PATTERN_3PART):
        m = re.match(pattern, current_name)
        if m:
            prefix, _old_num, rest = m.group(1), m.group(2), m.group(3)
            return f"{prefix}{new_position}{rest}"
    return None
```

**Important:** interfaces that don't match either pattern are left untouched. This covers loopbacks, VLANs, port-channels, etc.
