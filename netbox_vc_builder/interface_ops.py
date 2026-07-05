import re

from .constants import (
    INTERFACE_PATTERN_2PART,
    INTERFACE_PATTERN_3PART,
    INTERFACE_PATTERN_4PART,
    NON_PHYSICAL_INTERFACE_TYPES,
    VLAN1_INTERFACE_NAME,
)
from .models import StackMaster, StackMember
from .netbox_client import NetBoxClient
from .reporter import Reporter


def rename_interface(current_name: str, new_position: int) -> str | None:
    """Returns the corrected interface name for the given stack position, or None if no pattern matches."""
    for pattern in (INTERFACE_PATTERN_4PART, INTERFACE_PATTERN_3PART, INTERFACE_PATTERN_2PART):
        m = re.match(pattern, current_name)
        if m:
            prefix, _old_num, rest = m.group(1), m.group(2), m.group(3)
            return f"{prefix}{new_position}{rest}"
    return None


def process_interfaces(
    master: StackMaster,
    members: list[StackMember],
    client: NetBoxClient,
    reporter: Reporter,
) -> list[str]:
    warnings: list[str] = []

    _process_master(master, client, reporter, warnings)
    for member in members:
        _process_member(member, client, reporter, warnings)

    return warnings


def _process_master(
    master: StackMaster, client: NetBoxClient, reporter: Reporter, warnings: list[str]
) -> None:
    interfaces = client.get_interfaces(master.id)
    vlan1_found = False
    for iface in interfaces:
        if iface.name.lower() == VLAN1_INTERFACE_NAME.lower():
            vlan1_found = True
            ips = client.get_ip_addresses_for_interface(iface.id)
            if ips:
                primary_ip = ips[0]
                client.set_primary_ipv4(master.id, primary_ip["id"])
                reporter.info(f"Set primary IPv4 {primary_ip['address']} on {master.name}")
            break
    if not vlan1_found:
        reporter.info(f"Creating Vlan1 on {master.name}")
        client.create_interface(master.id, VLAN1_INTERFACE_NAME, "virtual")


def _process_member(
    member: StackMember, client: NetBoxClient, reporter: Reporter, warnings: list[str]
) -> None:
    interfaces = client.get_interfaces(member.id)
    for iface in interfaces:
        if iface.mgmt_only:
            reporter.warn(f"Deleting mgmt-only interface {iface.name} on {member.name}")
            ips = client.get_ip_addresses_for_interface(iface.id)
            for ip in ips:
                client.clear_device_ip_assignments(member.id, ip["id"])
                client.unassign_ip_from_interface(ip["id"])
            client.delete_interface(iface.id)
            continue

        if iface.name.lower() == VLAN1_INTERFACE_NAME.lower():
            ips = client.get_ip_addresses_for_interface(iface.id)
            if ips:
                ip_list = [ip["address"] for ip in ips]
                warning = f"Deleting Vlan1 on {member.name} which has IPs: {ip_list}"
                reporter.warn(warning)
                warnings.append(warning)
                for ip in ips:
                    client.clear_device_ip_assignments(member.id, ip["id"])
                    client.unassign_ip_from_interface(ip["id"])
            client.delete_interface(iface.id)
            continue

        if iface.interface_type in NON_PHYSICAL_INTERFACE_TYPES:
            continue

        new_name = rename_interface(iface.name, member.position)
        if new_name and new_name != iface.name:
            reporter.debug(f"Renaming {iface.name} → {new_name} on {member.name}")
            client.rename_interface(iface.id, new_name)
