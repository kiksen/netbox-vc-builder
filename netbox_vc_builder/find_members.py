from .constants import STACK_MAX_POSITION, VC_PRIORITY_BASE
from .models import StackMaster, StackMember, parse_stack_name
from .netbox_client import NetBoxClient
from .reporter import Reporter


def find_members(
    master: StackMaster,
    site_slug: str,
    client: NetBoxClient,
    manufacturer_slug: str,
    reporter: Reporter,
) -> list[StackMember]:
    devices = client.get_devices_by_prefix(site_slug, master.prefix, manufacturer_slug)
    members: list[StackMember] = []

    for device in devices:
        parsed = parse_stack_name(device["name"])
        if parsed is None:
            continue
        _, position = parsed
        if position < 2 or position > STACK_MAX_POSITION:
            continue
        priority = VC_PRIORITY_BASE - position
        members.append(
            StackMember(
                id=device["id"],
                name=device["name"],
                position=position,
                priority=priority,
                existing_vc_id=device["virtual_chassis"],
            )
        )

    members.sort(key=lambda m: m.position)
    reporter.info(f"\nFound {len(members)} member(s) for {master.name}")
    return members
