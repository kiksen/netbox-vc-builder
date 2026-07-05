from .models import StackMaster, StackMember, VCResult
from .netbox_client import NetBoxClient
from .reporter import Reporter


def build_vc(
    master: StackMaster,
    members: list[StackMember],
    client: NetBoxClient,
    reporter: Reporter,
    overwrite: bool = False,
) -> VCResult:
    if master.existing_vc_id is not None and not overwrite:
        return VCResult(
            master_name=master.name,
            member_count=0,
            status="skipped",
            message="already a VC member, use --overwrite to recreate",
        )

    if master.existing_vc_id is not None and overwrite:
        reporter.warn(f"Deleting existing VC for {master.name}")
        client.delete_virtual_chassis(master.existing_vc_id)

    vc_name = master.name
    reporter.info("creating VC.")
    vc_id = client.create_virtual_chassis(vc_name)

    client.set_device_vc_membership(master.id, vc_id, position=1, priority=15, is_master=True)
    reporter.warn(f"Setting {master.name} as Master, priority 15 and position 1")

    for member in members:
        priority = 16 - member.position
        client.set_device_vc_membership(member.id, vc_id, member.position, priority)
        reporter.info(
            f"Setting {member.name} as Member, priority {priority} and position {member.position}"
        )

    return VCResult(
        master_name=master.name,
        member_count=len(members) + 1,
        status="created",
    )
