from .models import StackMaster, parse_stack_name
from .netbox_client import NetBoxClient
from .reporter import Reporter


def find_masters(
    site_slug: str,
    client: NetBoxClient,
    manufacturer_slug: str,
    reporter: Reporter,
) -> list[StackMaster]:
    devices = client.get_master_candidates(site_slug, manufacturer_slug)
    masters: list[StackMaster] = []

    for device in devices:
        parsed = parse_stack_name(device["name"])
        if parsed is None:
            continue
        prefix, position = parsed
        if position != 1:
            continue
        masters.append(
            StackMaster(
                id=device["id"],
                name=device["name"],
                position=1,
                priority=15,
                existing_vc_id=device["virtual_chassis"],
                prefix=prefix,
            )
        )

    reporter.info(f"Found {len(masters)} possible stack master(s) for site {site_slug}")
    return masters
