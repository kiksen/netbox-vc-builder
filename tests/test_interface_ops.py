import pytest

from netbox_vc_builder.interface_ops import process_interfaces, rename_interface
from netbox_vc_builder.models import StackMaster, StackMember
from netbox_vc_builder.reporter import NullReporter
from tests.conftest import FakeNetBoxClient, make_iface

R = NullReporter()


def make_master(id: int = 1) -> StackMaster:
    return StackMaster(
        id=id, name="SWITCH-1", position=1, priority=15, existing_vc_id=None, prefix="SWITCH"
    )


def make_member(id: int, pos: int) -> StackMember:
    return StackMember(
        id=id, name=f"SWITCH-{pos}", position=pos, priority=16 - pos, existing_vc_id=None
    )


# ── rename_interface pure function ────────────────────────────────────────────


@pytest.mark.parametrize(
    "name,pos,expected",
    [
        ("GigabitEthernet1/0/1", 2, "GigabitEthernet2/0/1"),
        ("TenGigabitEthernet1/1/1", 3, "TenGigabitEthernet3/1/1"),
        ("TenGigabitEthernet1/1/0/1", 2, "TenGigabitEthernet2/1/0/1"),
        ("GigabitEthernet1/1", 2, "GigabitEthernet2/1"),
        ("GigabitEthernet1/1", 3, "GigabitEthernet3/1"),
        ("Vlan1", 2, None),
        ("Loopback0", 2, None),
        ("Port-channel1", 2, None),
        ("mgmt0", 2, None),
        ("GigabitEthernet2/0/1", 2, "GigabitEthernet2/0/1"),  # already correct
    ],
)
def test_rename_interface(name, pos, expected):
    assert rename_interface(name, pos) == expected


def test_rename_already_correct_same_name():
    result = rename_interface("GigabitEthernet2/0/1", 2)
    assert result == "GigabitEthernet2/0/1"


# ── process_interfaces integration ───────────────────────────────────────────


def test_deletes_mgmt_only_interface_on_member():
    member = make_member(2, 2)
    iface = make_iface(101, "mgmt0", mgmt_only=True)
    client = FakeNetBoxClient(interfaces={2: [iface]})
    process_interfaces(make_master(), [member], client, R)
    assert 101 in client.deleted_interfaces


def test_deletes_vlan1_on_member_no_ip():
    member = make_member(2, 2)
    iface = make_iface(102, "Vlan1")
    client = FakeNetBoxClient(interfaces={2: [iface]})
    process_interfaces(make_master(), [member], client, R)
    assert 102 in client.deleted_interfaces


def test_deletes_vlan1_lowercase_on_member():
    member = make_member(2, 2)
    iface = make_iface(109, "vlan1")
    client = FakeNetBoxClient(interfaces={2: [iface]})
    process_interfaces(make_master(), [member], client, R)
    assert 109 in client.deleted_interfaces


def test_unassigns_ip_before_deleting_vlan1_on_member():
    member = make_member(2, 2)
    iface = make_iface(103, "Vlan1")
    client = FakeNetBoxClient(
        interfaces={2: [iface]},
        ips={103: [{"id": 999, "address": "10.0.0.2/24"}]},
    )
    process_interfaces(make_master(), [member], client, R)
    assert 999 in client.unassigned_ips
    assert 103 in client.deleted_interfaces


def test_deletes_vlan1_on_member_with_ip_emits_warning():
    warnings_emitted = []

    class CapturingReporter(NullReporter):
        def warn(self, msg):
            warnings_emitted.append(msg)

    member = make_member(2, 2)
    iface = make_iface(103, "Vlan1")
    client = FakeNetBoxClient(
        interfaces={2: [iface]},
        ips={103: [{"id": 999, "address": "10.0.0.2/24"}]},
    )
    result = process_interfaces(make_master(), [member], client, CapturingReporter())
    assert 103 in client.deleted_interfaces
    assert any("10.0.0.2/24" in w for w in warnings_emitted + result)


def test_renames_physical_interface_on_member():
    member = make_member(2, 2)
    iface = make_iface(200, "GigabitEthernet1/0/1", iface_type="1000base-t")
    client = FakeNetBoxClient(interfaces={2: [iface]})
    process_interfaces(make_master(), [member], client, R)
    assert (200, "GigabitEthernet2/0/1") in client.renamed_interfaces


def test_does_not_rename_master_interfaces():
    master = make_master(id=1)
    iface = make_iface(300, "GigabitEthernet1/0/1")
    client = FakeNetBoxClient(interfaces={1: [iface]})
    process_interfaces(master, [], client, R)
    assert client.renamed_interfaces == []


def test_sets_primary_ip4_on_master_from_vlan1():
    master = make_master(id=1)
    iface = make_iface(400, "Vlan1")
    client = FakeNetBoxClient(
        interfaces={1: [iface]},
        ips={400: [{"id": 501, "address": "192.168.1.1/24"}]},
    )
    process_interfaces(master, [], client, R)
    assert (1, 501) in client.set_primary_ips


def test_virtual_interface_not_renamed():
    member = make_member(2, 2)
    iface = make_iface(500, "GigabitEthernet1/0/1", iface_type="virtual")
    client = FakeNetBoxClient(interfaces={2: [iface]})
    process_interfaces(make_master(), [member], client, R)
    assert client.renamed_interfaces == []


def test_lag_interface_not_renamed():
    member = make_member(2, 2)
    iface = make_iface(600, "GigabitEthernet1/0/1", iface_type="lag")
    client = FakeNetBoxClient(interfaces={2: [iface]})
    process_interfaces(make_master(), [member], client, R)
    assert client.renamed_interfaces == []


def test_bridge_interface_not_renamed():
    member = make_member(2, 2)
    iface = make_iface(700, "GigabitEthernet1/0/1", iface_type="bridge")
    client = FakeNetBoxClient(interfaces={2: [iface]})
    process_interfaces(make_master(), [member], client, R)
    assert client.renamed_interfaces == []


def test_mgmt_only_deleted_regardless_of_type():
    member = make_member(2, 2)
    iface = make_iface(800, "mgmt0", iface_type="virtual", mgmt_only=True)
    client = FakeNetBoxClient(interfaces={2: [iface]})
    process_interfaces(make_master(), [member], client, R)
    assert 800 in client.deleted_interfaces
