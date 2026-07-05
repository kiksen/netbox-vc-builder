# Phase 2 — Architecture

## Data Flow

```
CLI (cli.py)
  │
  ├── load Config (config.py)         ← env vars + YAML file + CLI args
  ├── create NetBoxClient (netbox_client.py)
  │     └── verify connectivity → abort if unreachable
  │
  ├── validate site slug              ← abort if unknown site
  │
  ├── find_masters(site, client)      ← returns List[StackMaster]
  │     └── filters: manufacturer=cisco, name ends with -1, not already VC member
  │
  ├── for each master:
  │     ├── find_members(master, client)    ← returns List[StackMember]
  │     ├── check_members(members, client)  ← filters out already-VC members, warns
  │     ├── build_vc(master, members, client, dry_run, overwrite)
  │     │     ├── skip if master is already VC member and not --overwrite
  │     │     ├── [overwrite] delete existing VC
  │     │     ├── create VC record
  │     │     ├── set master: position=1, priority=15
  │     │     └── for each member: set position=N, priority=(16-N)
  │     └── interface_ops(master, members, client, dry_run)
  │           ├── rename interfaces on each member to correct X/Y/Z numbering
  │           ├── delete mgmt-only interfaces on non-master members
  │           ├── delete vlan1 on non-master members (warn if has IP)
  │           └── set primary_ip4 on master from vlan1
  │
  ├── final_check(site, client)       ← find all *-N devices not yet in any VC, warn
  │
  └── reporter.summary()             ← print totals, duration
```

---

## Module Dependency Graph

```
cli.py
  ├── config.py       (no internal deps)
  ├── netbox_client.py (no internal deps)
  ├── models.py        (no internal deps)
  ├── constants.py     (no internal deps)
  ├── find_masters.py  ← models, netbox_client, constants
  ├── find_members.py  ← models, netbox_client, constants
  ├── check_members.py ← models, netbox_client
  ├── build_vc.py      ← models, netbox_client, reporter
  ├── interface_ops.py ← models, netbox_client, reporter
  └── reporter.py      ← models (no netbox_client dep — output only)
```

**Rule:** `reporter.py`, `models.py`, `constants.py` must never import `netbox_client.py`. Keeps them unit-testable with zero mocking.

---

## Key Design Decisions

### 1. Thin NetBox Client Wrapper
Rather than scattering `pynetbox` calls across all modules, all NetBox I/O goes through `NetBoxClient`. Each method is a named operation (e.g., `get_devices_by_site`, `create_virtual_chassis`). This makes mocking trivial in tests — inject a fake `NetBoxClient` with the same interface.

### 2. Dry-Run at the Client Layer
`NetBoxClient` accepts a `dry_run: bool` flag. All write methods (`create_*`, `update_*`, `delete_*`) are no-ops and return a sentinel value when dry_run=True. Business logic never needs to check `dry_run` — it just calls the client.

### 3. Dataclasses as Domain Objects
`StackMaster`, `StackMember`, `VCResult` are plain Python dataclasses. They are populated from NetBox API responses by factory methods on `NetBoxClient`, not by the caller. This isolates the "NetBox shape → app shape" translation to one place.

### 4. Reporter Decoupled from Logic
Every function that produces user-visible output accepts a `Reporter` parameter. The reporter is never imported at module level. This allows tests to pass a no-op reporter and keeps output logic in one place.

### 5. Final Check is Separate
After processing all masters, a separate `final_check` pass scans for *any* device in the site matching the stack-member pattern (`-1` through `-8`) that is still not in a VC. This catches missed members even if they weren't found as masters.

---

## Error Handling Strategy

- **Fatal errors** (no NetBox, unknown site slug): print message, exit with code 1.
- **Per-stack errors** (one VC fails): log the error, increment failed count, continue to next stack.
- **Warnings** (vlan1 with IP deleted, member skipped): logged and counted in summary.
- **Never swallow exceptions silently.** Every except block either re-raises or logs explicitly.
