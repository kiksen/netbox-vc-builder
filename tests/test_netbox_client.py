from unittest.mock import MagicMock, patch

import pytest

from netbox_vc_builder.models import InterfaceRecord
from netbox_vc_builder.netbox_client import (
    NetBoxAPIError,
    NetBoxClient,
    NetBoxConnectionError,
)


def make_client(dry_run=False):
    with patch("netbox_vc_builder.netbox_client.pynetbox.api") as mock_api:
        client = NetBoxClient("http://netbox", "token", dry_run=dry_run)
        client._nb = mock_api.return_value
        return client


# ── check_connectivity ────────────────────────────────────────────────────────


def test_check_connectivity_returns_version():
    client = make_client()
    client._nb.status.return_value = {"netbox-version": "3.6.0"}
    assert client.check_connectivity() == "3.6.0"


def test_check_connectivity_raises_on_exception():
    client = make_client()
    client._nb.status.side_effect = Exception("timeout")
    with pytest.raises(NetBoxConnectionError):
        client.check_connectivity()


# ── get_site ─────────────────────────────────────────────────────────────────


def test_get_site_returns_dict_when_found():
    client = make_client()
    mock_site = MagicMock()
    mock_site.slug = "bonn"
    mock_site.name = "Bonn"
    mock_site.id = 5
    client._nb.dcim.sites.get.return_value = mock_site
    result = client.get_site("bonn")
    assert result == {"slug": "bonn", "name": "Bonn", "id": 5}


def test_get_site_returns_none_when_not_found():
    client = make_client()
    client._nb.dcim.sites.get.return_value = None
    result = client.get_site("unknown")
    assert result is None


# ── get_master_candidates ────────────────────────────────────────────────────


def test_get_master_candidates_returns_devices():
    client = make_client()
    dev = MagicMock()
    dev.id = 1
    dev.name = "SWITCH-1"
    dev.virtual_chassis = None
    client._nb.dcim.devices.filter.return_value = [dev]
    result = client.get_master_candidates("site1", "cisco")
    assert result[0]["name"] == "SWITCH-1"
    assert result[0]["virtual_chassis"] is None


def test_get_master_candidates_raises_on_error():
    client = make_client()
    client._nb.dcim.devices.filter.side_effect = Exception("API error")
    with pytest.raises(NetBoxAPIError):
        client.get_master_candidates("site1", "cisco")


# ── get_devices_by_prefix ────────────────────────────────────────────────────


def test_get_devices_by_prefix_returns_matching_devices():
    client = make_client()
    dev = MagicMock()
    dev.id = 2
    dev.name = "SWITCH-2"
    dev.virtual_chassis = None
    client._nb.dcim.devices.filter.return_value = [dev]
    result = client.get_devices_by_prefix("site1", "SWITCH", "cisco")
    assert result[0]["name"] == "SWITCH-2"


# ── get_device_by_name ───────────────────────────────────────────────────────


def test_get_device_by_name_returns_dict():
    client = make_client()
    dev = MagicMock()
    dev.id = 3
    dev.name = "SWITCH-3"
    dev.virtual_chassis = None
    client._nb.dcim.devices.get.return_value = dev
    result = client.get_device_by_name("SWITCH-3")
    assert result["name"] == "SWITCH-3"


def test_get_device_by_name_returns_none():
    client = make_client()
    client._nb.dcim.devices.get.return_value = None
    assert client.get_device_by_name("NOPE") is None


# ── create_virtual_chassis ───────────────────────────────────────────────────


def test_create_virtual_chassis_returns_id():
    client = make_client()
    mock_vc = MagicMock()
    mock_vc.id = 42
    client._nb.dcim.virtual_chassis.create.return_value = mock_vc
    vc_id = client.create_virtual_chassis("SWITCH")
    assert vc_id == 42


def test_create_virtual_chassis_dry_run_returns_minus_1(capsys):
    client = make_client(dry_run=True)
    vc_id = client.create_virtual_chassis("SWITCH")
    assert vc_id == -1
    client._nb.dcim.virtual_chassis.create.assert_not_called()


def test_create_virtual_chassis_raises_on_error():
    client = make_client()
    client._nb.dcim.virtual_chassis.create.side_effect = Exception("API error")
    with pytest.raises(NetBoxAPIError):
        client.create_virtual_chassis("SWITCH")


# ── delete_virtual_chassis ───────────────────────────────────────────────────


def test_delete_virtual_chassis_calls_delete():
    client = make_client()
    mock_vc = MagicMock()
    client._nb.dcim.virtual_chassis.get.return_value = mock_vc
    client.delete_virtual_chassis(42)
    mock_vc.delete.assert_called_once()


def test_delete_virtual_chassis_dry_run_is_noop():
    client = make_client(dry_run=True)
    client.delete_virtual_chassis(42)
    client._nb.dcim.virtual_chassis.get.assert_not_called()


# ── set_device_vc_membership ─────────────────────────────────────────────────


def test_set_device_vc_membership_updates_device():
    client = make_client()
    mock_device = MagicMock()
    mock_vc = MagicMock()
    client._nb.dcim.devices.get.return_value = mock_device
    client._nb.dcim.virtual_chassis.get.return_value = mock_vc
    client.set_device_vc_membership(1, 100, position=1, priority=15, is_master=True)
    mock_device.update.assert_called_once()
    mock_vc.update.assert_called_once_with({"master": 1})


def test_set_device_vc_membership_dry_run_is_noop():
    client = make_client(dry_run=True)
    client.set_device_vc_membership(1, 100, position=1, priority=15)
    client._nb.dcim.devices.get.assert_not_called()


# ── get_interfaces ────────────────────────────────────────────────────────────


def test_get_interfaces_returns_records():
    client = make_client()
    mock_iface = MagicMock()
    mock_iface.id = 10
    mock_iface.name = "GigabitEthernet1/0/1"
    mock_iface.type.value = "1000base-t"
    mock_iface.mgmt_only = False
    client._nb.dcim.interfaces.filter.return_value = [mock_iface]
    result = client.get_interfaces(1)
    assert isinstance(result[0], InterfaceRecord)
    assert result[0].name == "GigabitEthernet1/0/1"


# ── rename_interface ──────────────────────────────────────────────────────────


def test_rename_interface_calls_update():
    client = make_client()
    mock_iface = MagicMock()
    client._nb.dcim.interfaces.get.return_value = mock_iface
    client.rename_interface(10, "GigabitEthernet2/0/1")
    mock_iface.update.assert_called_once_with({"name": "GigabitEthernet2/0/1"})


def test_rename_interface_dry_run_is_noop():
    client = make_client(dry_run=True)
    client.rename_interface(10, "GigabitEthernet2/0/1")
    client._nb.dcim.interfaces.get.assert_not_called()


# ── delete_interface ──────────────────────────────────────────────────────────


def test_delete_interface_calls_delete():
    client = make_client()
    mock_iface = MagicMock()
    client._nb.dcim.interfaces.get.return_value = mock_iface
    client.delete_interface(10)
    mock_iface.delete.assert_called_once()


def test_delete_interface_dry_run_is_noop():
    client = make_client(dry_run=True)
    client.delete_interface(10)
    client._nb.dcim.interfaces.get.assert_not_called()


# ── get_ip_addresses_for_interface ───────────────────────────────────────────


def test_get_ip_addresses_for_interface_returns_list():
    client = make_client()
    mock_ip = MagicMock()
    mock_ip.id = 99
    mock_ip.address = "10.0.0.1/24"
    client._nb.ipam.ip_addresses.filter.return_value = [mock_ip]
    result = client.get_ip_addresses_for_interface(10)
    assert result == [{"id": 99, "address": "10.0.0.1/24"}]


# ── set_primary_ipv4 ──────────────────────────────────────────────────────────


def test_set_primary_ipv4_calls_update():
    client = make_client()
    mock_device = MagicMock()
    client._nb.dcim.devices.get.return_value = mock_device
    client.set_primary_ipv4(1, 99)
    mock_device.update.assert_called_once_with({"primary_ip4": 99})


def test_set_primary_ipv4_dry_run_is_noop():
    client = make_client(dry_run=True)
    client.set_primary_ipv4(1, 99)
    client._nb.dcim.devices.get.assert_not_called()


# ── _device_to_dict with VC id ────────────────────────────────────────────────


def test_device_to_dict_with_vc_id():
    client = make_client()
    dev = MagicMock()
    dev.id = 5
    dev.name = "SW-1"
    dev.virtual_chassis.id = 77
    result = client._device_to_dict(dev)
    assert result["virtual_chassis"] == 77
