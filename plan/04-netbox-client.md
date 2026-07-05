# Phase 4 — NetBox API Layer

## Library Choice: pynetbox

`pynetbox` is the official Python client for the NetBox API. It handles:
- Authentication (token header)
- Pagination (transparent `.filter()` returns all pages)
- HTTPS
- Response object access by attribute name

We wrap it in `NetBoxClient` to:
1. Keep all API-specific knowledge in one file
2. Enable easy mocking in tests (swap the client, not the whole pynetbox)
3. Enforce dry_run at a single chokepoint
4. Translate pynetbox record objects → our domain dataclasses

---

## NetBoxClient Design

```python
class NetBoxClient:
    def __init__(self, endpoint: str, token: str, dry_run: bool = False):
        self._nb = pynetbox.api(endpoint, token=token)
        self._dry_run = dry_run
```

### Connectivity & Site

```python
def check_connectivity(self) -> str:
    """Returns NetBox version string. Raises NetBoxConnectionError on failure."""

def get_site(self, slug: str) -> dict | None:
    """Returns site record or None if slug not found."""
```

### Device Queries

```python
def get_master_candidates(self, site_slug: str, manufacturer_slug: str) -> list[dict]:
    """
    Returns devices where:
      - site slug matches
      - manufacturer slug matches
      - name ends with -1 (position 1)
      - virtual_chassis is null (not already in a VC)
    
    NetBox filter: name__re="-1$" is not standard.
    Approach: fetch all site+manufacturer devices, filter in Python.
    This is acceptable because site device counts are small enough.
    
    Alternative filter available in NetBox 3.5+: name__isw (starts with)
    We fetch all and filter to keep broad compatibility.
    """

def get_devices_by_prefix(self, site_slug: str, prefix: str, manufacturer_slug: str) -> list[dict]:
    """
    Returns all devices for the site matching name pattern '{prefix}-N'
    where N is 1-8. Used to find all members of a stack.
    Filter: name__isw="{prefix}-"  (starts with prefix-)
    Then Python-filter to confirm it is a valid stack suffix (1-8).
    """

def get_device_by_name(self, name: str) -> dict | None:
    """Exact device lookup by name. Returns None if not found."""
```

### Virtual Chassis Operations

```python
def create_virtual_chassis(self, name: str) -> int:
    """
    Creates a VC record. Returns the new VC id.
    In dry_run mode: prints "[DRY RUN] would create VC '{name}'" and returns -1.
    NetBox endpoint: POST /api/dcim/virtual-chassis/
    Body: {"name": name}
    The master device assignment happens separately via device update.
    """

def delete_virtual_chassis(self, vc_id: int) -> None:
    """
    Deletes a VC. Devices lose their vc membership automatically (NetBox cascade).
    In dry_run mode: no-op.
    NetBox endpoint: DELETE /api/dcim/virtual-chassis/{id}/
    """

def set_device_vc_membership(
    self,
    device_id: int,
    vc_id: int,
    position: int,
    priority: int,
    is_master: bool = False,
) -> None:
    """
    Assigns a device to a VC with position and priority.
    If is_master=True, also sets the VC's master field.
    In dry_run mode: no-op.
    
    NetBox endpoint: PATCH /api/dcim/devices/{device_id}/
    Body: {"virtual_chassis": vc_id, "vc_position": position, "vc_priority": priority}
    
    Then if is_master:
    PATCH /api/dcim/virtual-chassis/{vc_id}/
    Body: {"master": device_id}
    """
```

### Interface Operations

```python
def get_interfaces(self, device_id: int) -> list[InterfaceRecord]:
    """
    Returns all interfaces for a device as InterfaceRecord objects.
    NetBox endpoint: GET /api/dcim/interfaces/?device_id={id}
    
    pynetbox returns type as an object with a .value attribute (e.g. record.type.value == "virtual").
    The factory maps it to InterfaceRecord.interface_type.
    """

def rename_interface(self, interface_id: int, new_name: str) -> None:
    """
    PATCH /api/dcim/interfaces/{id}/ with {"name": new_name}
    In dry_run mode: no-op.
    """

def delete_interface(self, interface_id: int) -> None:
    """
    DELETE /api/dcim/interfaces/{id}/
    In dry_run mode: no-op.
    """

def get_ip_addresses_for_interface(self, interface_id: int) -> list[dict]:
    """
    GET /api/ipam/ip-addresses/?interface_id={id}
    Returns list of IP records.
    """

def set_primary_ipv4(self, device_id: int, ip_id: int) -> None:
    """
    PATCH /api/dcim/devices/{id}/ with {"primary_ip4": ip_id}
    In dry_run mode: no-op.
    """
```

---

## Error Handling in the Client

- All pynetbox exceptions are caught and re-raised as custom exceptions:
  - `NetBoxConnectionError` — unreachable endpoint
  - `NetBoxAuthError` — invalid token (HTTP 403)
  - `NetBoxNotFoundError` — 404 response
  - `NetBoxAPIError` — any other API error (with status code + message)

These custom exceptions live in `netbox_client.py` and are caught in `cli.py` for user-friendly error messages.

---

## NetBox API Version Compatibility

The client targets **NetBox 3.3+** (widely deployed). Key API behaviors:
- Virtual Chassis: separate resource with `master` field pointing to a device
- `vc_position` and `vc_priority` are fields on the device
- Interface `mgmt_only` field available since NetBox 2.x

We read the NetBox version on startup and warn (but do not abort) if version < 3.3.

---

## pynetbox vs. Raw httpx

We choose `pynetbox` over raw `httpx` because:
- Transparent pagination — no manual `offset`/`limit` loops
- Attribute-style access — `device.name`, not `device["name"]`
- Well-tested in production against real NetBox

Downside: `pynetbox` is a third-party dep and occasionally lags behind NetBox API changes. Mitigated by pinning to `>=7` (supports NetBox 3.x).
