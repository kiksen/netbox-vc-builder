import re
from dataclasses import dataclass, field

from .constants import STACK_MAX_POSITION, STACK_MIN_POSITION

STACK_NAME_PATTERN = re.compile(r"^(.+)-(\d+)$")


def parse_stack_name(device_name: str) -> tuple[str, int] | None:
    """Returns (prefix, position) or None if name doesn't match the stack pattern."""
    m = STACK_NAME_PATTERN.match(device_name)
    if m:
        position = int(m.group(2))
        if STACK_MIN_POSITION <= position <= STACK_MAX_POSITION:
            return m.group(1), position
    return None


@dataclass
class AppConfig:
    netbox_endpoint: str
    netbox_token: str
    site_slug: str
    manufacturer_slug: str = "cisco"
    dry_run: bool = False
    overwrite: bool = False


@dataclass
class StackMember:
    id: int
    name: str
    position: int
    priority: int
    existing_vc_id: int | None
    interface_ids: list[int] = field(default_factory=list)


@dataclass
class StackMaster(StackMember):
    prefix: str = ""
    members: list["StackMember"] = field(default_factory=list)


@dataclass
class InterfaceRecord:
    id: int
    name: str
    interface_type: str
    mgmt_only: bool
    ip_address_count: int
    ip_addresses: list[str] = field(default_factory=list)


@dataclass
class VCResult:
    master_name: str
    member_count: int
    status: str
    message: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass
class RunSummary:
    site_slug: str
    stacks_found: int = 0
    created: int = 0
    skipped: int = 0
    failed: int = 0
    dry_run_count: int = 0
    warnings: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    results: list[VCResult] = field(default_factory=list)
