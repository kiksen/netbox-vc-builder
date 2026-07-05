# Phase 5 — Business Logic Modules

## find_masters.py

**Responsibility:** Discover all valid stack master candidates for a given site.

**Algorithm:**
1. Call `client.get_master_candidates(site_slug, manufacturer_slug)`.
2. For each device returned, call `parse_stack_name(device.name)`.
3. Keep only devices where `position == 1` (ends with `-1`).
4. Exclude devices where `virtual_chassis is not None` (already in a VC).
5. Return `List[StackMaster]` (prefix, position=1, priority=15, members=[]).

**Output via Reporter:**
- `Found N possible stack masters` (info)
- Individual master name as each is processed (debug, shown only with verbose flag)

**Edge cases:**
- Site has no Cisco devices → return empty list (not an error, just 0 stacks found).
- Device name ends with `-1` but position is not 1 after parse — impossible by construction, but guarded anyway.

---

## find_members.py

**Responsibility:** For a given master prefix, find all stack member candidates (positions 2–8).

**Algorithm:**
1. Call `client.get_devices_by_prefix(site_slug, prefix, manufacturer_slug)`.
2. For each result, call `parse_stack_name(device.name)`.
3. Keep only results where position is in range 2–8.
4. Sort by position ascending.
5. Return `List[StackMember]`.

**Note:** The master itself (`-1`) may appear in the result set and must be excluded (its position is already handled separately).

**Output via Reporter:**
- `Found N member(s) for {master.name}` (info)

**Edge cases:**
- Only the master exists (no -2, -3 etc.) → return empty list. A single-device "stack" is valid — the master still gets VC membership (position 1, priority 15). NetBox allows a VC with one member.

---

## check_members.py

**Responsibility:** Validate that member candidates are safe to add to a new VC.

**Algorithm:**
For each member candidate:
1. Check if `device.virtual_chassis is not None`.
2. If already in a VC and not `--overwrite`: add to `rejected` list, emit warning.
3. If already in the same VC and `--overwrite`: still process (will be deleted then re-added).
4. Return `(accepted: List[StackMember], rejected: List[StackMember])`.

**Output via Reporter:**
- `⚠ Skipping {name}: already a VC member of {existing_vc_name}` (warning)

**Key invariant:** A rejected member is never written to. The caller (cli.py or build_vc.py) uses only the `accepted` list for writes.

---

## build_vc.py

**Responsibility:** Create/update Virtual Chassis records in NetBox.

**Entry point:**
```python
def build_vc(
    master: StackMaster,
    members: list[StackMember],
    client: NetBoxClient,
    reporter: Reporter,
    overwrite: bool = False,
) -> VCResult:
```

**Algorithm:**

```
if master has existing VC and not overwrite:
    return VCResult(status="skipped", message="already a VC member, use --overwrite to recreate")

if master has existing VC and overwrite:
    reporter.warn("Deleting existing VC for {master.name}")
    client.delete_virtual_chassis(master.existing_vc_id)

vc_name = master.prefix  (e.g. "SWITCH" from "SWITCH-1")
vc_id = client.create_virtual_chassis(vc_name)

# Add master first (position 1, priority 15, is_master=True)
client.set_device_vc_membership(master.id, vc_id, position=1, priority=15, is_master=True)
reporter.info(f"⚠ Setting {master.name} as Master, priority 15 and position 1")

# Add all members
for member in members:
    priority = 16 - member.position
    client.set_device_vc_membership(member.id, vc_id, member.position, priority)
    reporter.info(f"✓ Setting {member.name} as Member, priority {priority} and position {member.position}")

return VCResult(status="created", member_count=len(members)+1)
```

**Output matches README example exactly:**
```
✓ found 1 member for TEST-1
✓ creating VC.
⚠ Setting TEST-1 as Master, priority 15 and position 1
✓ Setting TEST-2 as Member, priority 14 and position 2
```

---

## interface_ops.py

**Responsibility:** Rename interfaces on member devices and clean up duplicates.

**Entry point:**
```python
def process_interfaces(
    master: StackMaster,
    members: list[StackMember],
    client: NetBoxClient,
    reporter: Reporter,
) -> list[str]:  # returns list of warning strings
```

**Algorithm per member device (positions 2–8):**

```
interfaces = client.get_interfaces(member.device_id)

for iface in interfaces:
    # 1. Delete mgmt-only interfaces (not allowed on non-master)
    if iface.mgmt_only:
        reporter.warn(f"Deleting mgmt-only interface {iface.name} on {member.name}")
        client.delete_interface(iface.id)
        continue

    # 2. Delete Vlan1 (not allowed on non-master)
    if iface.name.lower() == "vlan1":
        ips = client.get_ip_addresses_for_interface(iface.id)
        if ips:
            warning = f"⚠ Deleting Vlan1 on {member.name} which has IPs: {[ip.address for ip in ips]}"
            reporter.warn(warning)
            warnings.append(warning)
        client.delete_interface(iface.id)
        continue

    # 3. Skip non-physical interfaces — do not rename (virtual, lag, bridge)
    if iface.interface_type in NON_PHYSICAL_INTERFACE_TYPES:
        continue

    # 4. Rename if the interface matches a numbered pattern
    new_name = rename_interface(iface.name, member.position)
    if new_name and new_name != iface.name:
        reporter.debug(f"Renaming {iface.name} → {new_name} on {member.name}")
        client.rename_interface(iface.id, new_name)
```

**Master device (position 1):**
```
# Set primary_ip4 from Vlan1
vlan1_iface = find interface named "Vlan1" on master
if vlan1_iface:
    ips = client.get_ip_addresses_for_interface(vlan1_iface.id)
    if ips:
        primary_ip = ips[0]  # first IP on Vlan1
        client.set_primary_ipv4(master.id, primary_ip.id)
        reporter.info(f"✓ Set primary IPv4 {primary_ip.address} on {master.name}")
```

**No changes to master's own interfaces** — the master's interfaces are already correct (position 1).

---

## final_check (cli.py or find_masters.py)

After all VCs are processed, scan the site again:

```python
def final_check(site_slug: str, client: NetBoxClient, manufacturer_slug: str, reporter: Reporter):
    """
    Find ALL *-N devices (N=1..8) that are still not in any VC.
    These represent stacks that were missed (e.g., member without a master).
    Print as warnings.
    """
    all_stack_devices = client.get_all_stack_devices(site_slug, manufacturer_slug)
    orphans = [d for d in all_stack_devices if d.virtual_chassis is None]
    if orphans:
        reporter.warn(f"Final check: {len(orphans)} device(s) still not in any VC:")
        for d in orphans:
            reporter.warn(f"  - {d.name}")
```
