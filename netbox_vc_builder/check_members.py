from .models import StackMember
from .reporter import Reporter


def check_members(
    members: list[StackMember],
    reporter: Reporter,
    overwrite: bool = False,
) -> tuple[list[StackMember], list[StackMember]]:
    accepted: list[StackMember] = []
    rejected: list[StackMember] = []

    for member in members:
        if member.existing_vc_id is not None and not overwrite:
            reporter.warn(
                f"Skipping {member.name}: already a VC member of VC id {member.existing_vc_id}"
            )
            rejected.append(member)
        else:
            accepted.append(member)

    return accepted, rejected
