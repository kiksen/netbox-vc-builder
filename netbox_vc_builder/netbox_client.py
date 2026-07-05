from __future__ import annotations

import pynetbox

from .models import InterfaceRecord


class NetBoxConnectionError(Exception):
    pass


class NetBoxAuthError(Exception):
    pass


class NetBoxNotFoundError(Exception):
    pass


class NetBoxAPIError(Exception):
    pass


class NetBoxClient:
    def __init__(self, endpoint: str, token: str, dry_run: bool = False):
        self._nb = pynetbox.api(endpoint, token=token)
        self._dry_run = dry_run

    def check_connectivity(self) -> str:
        try:
            status = self._nb.status()
            version = status.get("netbox-version", "unknown")
            return version
        except Exception as exc:
            raise NetBoxConnectionError(f"Cannot connect to NetBox: {exc}") from exc

    def get_site(self, slug: str) -> dict | None:
        try:
            site = self._nb.dcim.sites.get(slug=slug)
            if site is None:
                return None
            return {"slug": site.slug, "name": site.name, "id": site.id}
        except pynetbox.core.query.RequestError as exc:
            if "403" in str(exc):
                raise NetBoxAuthError("Invalid token (HTTP 403)") from exc
            raise NetBoxAPIError(str(exc)) from exc
        except Exception as exc:
            raise NetBoxConnectionError(f"Cannot connect to NetBox: {exc}") from exc

    def get_master_candidates(self, site_slug: str, manufacturer_slug: str) -> list[dict]:
        try:
            devices = list(
                self._nb.dcim.devices.filter(site=site_slug, manufacturer=manufacturer_slug)
            )
        except Exception as exc:
            raise NetBoxAPIError(f"Failed to fetch devices: {exc}") from exc
        return [self._device_to_dict(d) for d in devices]

    def get_devices_by_prefix(
        self, site_slug: str, prefix: str, manufacturer_slug: str
    ) -> list[dict]:
        try:
            devices = list(
                self._nb.dcim.devices.filter(
                    site=site_slug,
                    manufacturer=manufacturer_slug,
                    name__isw=f"{prefix}-",
                )
            )
        except Exception as exc:
            raise NetBoxAPIError(f"Failed to fetch devices by prefix: {exc}") from exc
        return [self._device_to_dict(d) for d in devices]

    def get_device_by_name(self, name: str) -> dict | None:
        try:
            device = self._nb.dcim.devices.get(name=name)
            if device is None:
                return None
            return self._device_to_dict(device)
        except Exception as exc:
            raise NetBoxAPIError(f"Failed to fetch device '{name}': {exc}") from exc

    def get_all_stack_devices(self, site_slug: str, manufacturer_slug: str) -> list[dict]:
        return self.get_master_candidates(site_slug, manufacturer_slug)

    def create_virtual_chassis(self, name: str) -> int:
        if self._dry_run:
            print(f"[DRY RUN] would create VC '{name}'")
            return -1
        try:
            vc = self._nb.dcim.virtual_chassis.create(name=name)
            return vc.id
        except Exception as exc:
            raise NetBoxAPIError(f"Failed to create VC '{name}': {exc}") from exc

    def delete_virtual_chassis(self, vc_id: int) -> None:
        if self._dry_run:
            return
        try:
            vc = self._nb.dcim.virtual_chassis.get(vc_id)
            if vc:
                vc.delete()
        except Exception as exc:
            raise NetBoxAPIError(f"Failed to delete VC {vc_id}: {exc}") from exc

    def set_device_vc_membership(
        self,
        device_id: int,
        vc_id: int,
        position: int,
        priority: int,
        is_master: bool = False,
    ) -> None:
        if self._dry_run:
            return
        try:
            device = self._nb.dcim.devices.get(device_id)
            device.update(
                {"virtual_chassis": vc_id, "vc_position": position, "vc_priority": priority}
            )
            if is_master:
                vc = self._nb.dcim.virtual_chassis.get(vc_id)
                vc.update({"master": device_id})
        except Exception as exc:
            raise NetBoxAPIError(
                f"Failed to set VC membership for device {device_id}: {exc}"
            ) from exc

    def get_interfaces(self, device_id: int) -> list[InterfaceRecord]:
        try:
            ifaces = list(self._nb.dcim.interfaces.filter(device_id=device_id))
        except Exception as exc:
            raise NetBoxAPIError(
                f"Failed to fetch interfaces for device {device_id}: {exc}"
            ) from exc
        return [self._iface_to_record(i) for i in ifaces]

    def rename_interface(self, interface_id: int, new_name: str) -> None:
        if self._dry_run:
            return
        try:
            iface = self._nb.dcim.interfaces.get(interface_id)
            iface.update({"name": new_name})
        except Exception as exc:
            raise NetBoxAPIError(f"Failed to rename interface {interface_id}: {exc}") from exc

    def delete_interface(self, interface_id: int) -> None:
        if self._dry_run:
            return
        try:
            iface = self._nb.dcim.interfaces.get(interface_id)
            if iface:
                iface.delete()
        except Exception as exc:
            raise NetBoxAPIError(f"Failed to delete interface {interface_id}: {exc}") from exc

    def get_ip_addresses_for_interface(self, interface_id: int) -> list[dict]:
        try:
            ips = list(self._nb.ipam.ip_addresses.filter(interface_id=interface_id))
        except Exception as exc:
            raise NetBoxAPIError(
                f"Failed to fetch IPs for interface {interface_id}: {exc}"
            ) from exc
        return [{"id": ip.id, "address": ip.address} for ip in ips]

    def set_primary_ipv4(self, device_id: int, ip_id: int) -> None:
        if self._dry_run:
            return
        try:
            device = self._nb.dcim.devices.get(device_id)
            device.update({"primary_ip4": ip_id})
        except Exception as exc:
            raise NetBoxAPIError(
                f"Failed to set primary IPv4 for device {device_id}: {exc}"
            ) from exc

    @staticmethod
    def _device_to_dict(device) -> dict:
        vc_id = None
        if device.virtual_chassis:
            try:
                vc_id = device.virtual_chassis.id
            except AttributeError:
                vc_id = int(device.virtual_chassis)
        return {
            "id": device.id,
            "name": device.name,
            "virtual_chassis": vc_id,
        }

    @staticmethod
    def _iface_to_record(iface) -> InterfaceRecord:
        iface_type = ""
        if iface.type:
            try:
                iface_type = iface.type.value
            except AttributeError:
                iface_type = str(iface.type)
        return InterfaceRecord(
            id=iface.id,
            name=iface.name,
            interface_type=iface_type,
            mgmt_only=bool(iface.mgmt_only),
            ip_address_count=0,
        )
