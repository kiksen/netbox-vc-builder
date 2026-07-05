from netbox_vc_builder.models import InterfaceRecord


class FakeNetBoxClient:
    """In-memory NetBoxClient for tests. Set up devices/interfaces/ips, then assert on call log."""

    def __init__(self, devices=None, interfaces=None, ips=None, dry_run=False, site_exists=True):
        self._devices = devices or []
        self._interfaces = interfaces or {}  # device_id → list[InterfaceRecord]
        self._ips = ips or {}  # interface_id → list[dict]
        self._dry_run = dry_run
        self._site_exists = site_exists

        self.created_vcs: list[str] = []
        self.deleted_vcs: list[int] = []
        self.membership_updates: list[dict] = []
        self.renamed_interfaces: list[tuple[int, str]] = []
        self.deleted_interfaces: list[int] = []
        self.set_primary_ips: list[tuple[int, int]] = []

    def check_connectivity(self) -> str:
        return "3.6.0"

    def get_site(self, slug: str):
        if self._site_exists:
            return {"slug": slug, "name": slug.upper(), "id": 1}
        return None

    def get_master_candidates(self, site_slug, manufacturer_slug):
        return list(self._devices)

    def get_devices_by_prefix(self, site_slug, prefix, manufacturer_slug):
        return [d for d in self._devices if d["name"].startswith(f"{prefix}-")]

    def get_device_by_name(self, name):
        for d in self._devices:
            if d["name"] == name:
                return d
        return None

    def get_all_stack_devices(self, site_slug, manufacturer_slug):
        return list(self._devices)

    def create_virtual_chassis(self, name: str) -> int:
        self.created_vcs.append(name)
        return 1001

    def delete_virtual_chassis(self, vc_id: int) -> None:
        self.deleted_vcs.append(vc_id)

    def set_device_vc_membership(self, device_id, vc_id, position, priority, is_master=False):
        self.membership_updates.append(
            {
                "device_id": device_id,
                "vc_id": vc_id,
                "position": position,
                "priority": priority,
                "is_master": is_master,
            }
        )

    def get_interfaces(self, device_id: int) -> list[InterfaceRecord]:
        return list(self._interfaces.get(device_id, []))

    def rename_interface(self, interface_id: int, new_name: str) -> None:
        self.renamed_interfaces.append((interface_id, new_name))

    def delete_interface(self, interface_id: int) -> None:
        self.deleted_interfaces.append(interface_id)

    def get_ip_addresses_for_interface(self, interface_id: int) -> list[dict]:
        return list(self._ips.get(interface_id, []))

    def set_primary_ipv4(self, device_id: int, ip_id: int) -> None:
        self.set_primary_ips.append((device_id, ip_id))


def make_device(id: int, name: str, virtual_chassis=None) -> dict:
    return {"id": id, "name": name, "virtual_chassis": virtual_chassis}


def make_iface(
    id: int, name: str, iface_type: str = "1000base-t", mgmt_only: bool = False
) -> InterfaceRecord:
    return InterfaceRecord(
        id=id,
        name=name,
        interface_type=iface_type,
        mgmt_only=mgmt_only,
        ip_address_count=0,
    )
