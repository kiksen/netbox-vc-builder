# Phase 8 — Testing Strategy

## Philosophy

- **No real NetBox in CI.** All tests use a fake `NetBoxClient` (injected via dependency injection).
- **Test business logic, not pynetbox.** We don't test whether pynetbox makes HTTP calls correctly.
- **Test the interface renaming logic exhaustively** — it is pure Python with no dependencies.
- **Test the CLI** with Typer's `CliRunner` to confirm argument parsing and exit codes.
- **Coverage target: ≥ 80%** enforced via `pytest-cov` and `fail_under = 80`.

---

## Fake NetBox Client

```python
# tests/conftest.py

class FakeNetBoxClient:
    """
    In-memory implementation of the NetBoxClient interface.
    Tests set up devices, interfaces, and IPs as dicts, then
    assert on which write calls were made.
    """
    def __init__(self, devices=None, interfaces=None, ips=None, dry_run=False):
        self._devices = devices or []
        self._interfaces = interfaces or {}   # device_id → list of interface dicts
        self._ips = ips or {}                  # interface_id → list of ip dicts
        self._dry_run = dry_run
        # Call log — tests assert on these
        self.created_vcs: list[str] = []
        self.deleted_vcs: list[int] = []
        self.membership_updates: list[dict] = []
        self.renamed_interfaces: list[tuple[int, str]] = []
        self.deleted_interfaces: list[int] = []
        self.set_primary_ips: list[tuple[int, int]] = []

    def check_connectivity(self) -> str:
        return "3.6.0"

    def get_site(self, slug: str) -> dict | None:
        return {"slug": slug, "name": slug.upper()}

    def get_master_candidates(self, site_slug, manufacturer_slug):
        return [d for d in self._devices if self._is_master_candidate(d)]

    def create_virtual_chassis(self, name: str) -> int:
        self.created_vcs.append(name)
        return 1001  # fake VC id

    def set_device_vc_membership(self, device_id, vc_id, position, priority, is_master=False):
        self.membership_updates.append({
            "device_id": device_id, "vc_id": vc_id,
            "position": position, "priority": priority, "is_master": is_master,
        })

    def get_interfaces(self, device_id):
        return self._interfaces.get(device_id, [])

    def rename_interface(self, interface_id, new_name):
        self.renamed_interfaces.append((interface_id, new_name))

    def delete_interface(self, interface_id):
        self.deleted_interfaces.append(interface_id)
    
    # ... etc.
```

---

## Test Files

### test_find_masters.py

```
✓ returns empty list when no devices match
✓ returns only devices ending with -1
✓ excludes devices already in a VC
✓ excludes non-cisco devices (when manufacturer filter is active)
✓ parses prefix correctly (SWITCH-CORE-1 → prefix=SWITCH-CORE)
```

### test_find_members.py

```
✓ returns members 2–8 for a given prefix
✓ excludes the master itself (-1) from the member list
✓ excludes positions outside 1–8
✓ returns empty list when no members exist
✓ sorts members by position ascending
```

### test_check_members.py

```
✓ accepts member with no existing VC
✓ rejects member already in a different VC (no overwrite)
✓ accepts member already in a VC when overwrite=True
✓ generates correct warning messages for rejected members
```

### test_build_vc.py

```
✓ creates VC with correct name (master prefix)
✓ sets master at position 1, priority 15, is_master=True
✓ sets member at position 2, priority 14
✓ sets member at position 3, priority 13
✓ skips (returns "skipped") when master already in VC and no overwrite
✓ deletes existing VC and recreates when overwrite=True
✓ dry_run=True: no create_virtual_chassis call made
✓ returns VCResult with correct status and member_count
```

### test_interface_ops.py — rename_interface (pure function)

```
✓ GigabitEthernet1/0/1, position=2 → GigabitEthernet2/0/1
✓ TenGigabitEthernet1/1/1, position=3 → TenGigabitEthernet3/1/1
✓ TenGigabitEthernet1/1/0/1 (4-part), position=2 → TenGigabitEthernet2/1/0/1
✓ Vlan1 → None (no change)
✓ Loopback0 → None (no change)
✓ Port-channel1 → None (no change — no slash notation)
✓ mgmt0 → None (no change)
✓ already correct name (GigabitEthernet2/0/1, position=2) → same name → no API call
```

### test_interface_ops.py — process_interfaces integration

```
✓ deletes mgmt-only interface on member
✓ deletes Vlan1 on member (no IP)
✓ deletes Vlan1 on member (with IP) — generates warning
✓ renames GigabitEthernet1/* to GigabitEthernet2/* on member at position 2
✓ does not rename master's interfaces
✓ sets primary_ip4 on master from Vlan1
✓ dry_run: no delete/rename calls, but warnings still emitted

# Interface type filtering
✓ virtual interface (type="virtual") is NOT renamed, even if name matches X/Y/Z pattern
✓ lag interface (type="lag") is NOT renamed
✓ bridge interface (type="bridge") is NOT renamed
✓ physical interface (type="1000base-t") IS renamed when name matches pattern
✓ mgmt-only interface with non-physical type IS still deleted (type guard runs after delete guards)
```

### test_config.py

```
✓ raises ConfigError when NETBOX_ENDPOINT missing
✓ raises ConfigError when NETBOX_TOKEN missing
✓ raises ConfigError when --site missing
✓ loads manufacturer_slug from YAML file
✓ YAML manufacturer_slug defaults to "cisco" when not in file
✓ CLI dry_run flag is reflected in AppConfig
```

### test_cli.py (Typer CliRunner)

```
✓ --help shows usage
✓ missing --site exits with code 1
✓ -C flag sets dry_run=True
✓ success run exits with code 0
✓ failed stacks exit with code 2
```

---

## Running Tests

```bash
# All tests with coverage
uv run pytest --cov --cov-report=term-missing

# Single file
uv run pytest tests/test_interface_ops.py -v

# Stop on first failure
uv run pytest -x
```

---

## Coverage Targets by Module

| Module | Target | Notes |
|--------|--------|-------|
| `constants.py` | 100% | No logic, just values |
| `models.py` | 100% | Pure dataclasses + rename_interface |
| `find_masters.py` | 90%+ | Business logic |
| `find_members.py` | 90%+ | Business logic |
| `check_members.py` | 90%+ | Business logic |
| `build_vc.py` | 85%+ | Business logic |
| `interface_ops.py` | 85%+ | Most complex module |
| `config.py` | 85%+ | Config loading |
| `netbox_client.py` | 60%+ | HTTP layer, hard to unit test fully |
| `reporter.py` | 50%+ | Output, tested indirectly |
| `cli.py` | 70%+ | Tested via CliRunner |
| **Overall** | **≥ 80%** | Enforced in CI |
