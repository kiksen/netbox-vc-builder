from netbox_vc_builder.find_members import find_members
from netbox_vc_builder.models import StackMaster
from netbox_vc_builder.reporter import NullReporter
from tests.conftest import FakeNetBoxClient, make_device

R = NullReporter()


def make_master(name: str = "SWITCH-1", prefix: str = "SWITCH") -> StackMaster:
    return StackMaster(id=1, name=name, position=1, priority=15, existing_vc_id=None, prefix=prefix)


def test_returns_members_2_to_8():
    devices = [
        make_device(1, "SWITCH-1"),
        make_device(2, "SWITCH-2"),
        make_device(3, "SWITCH-3"),
        make_device(8, "SWITCH-8"),
    ]
    members = find_members(make_master(), "site1", FakeNetBoxClient(devices=devices), "cisco", R)
    positions = [m.position for m in members]
    assert positions == [2, 3, 8]


def test_excludes_master_itself():
    devices = [make_device(1, "SWITCH-1"), make_device(2, "SWITCH-2")]
    members = find_members(make_master(), "site1", FakeNetBoxClient(devices=devices), "cisco", R)
    assert all(m.position != 1 for m in members)


def test_excludes_positions_outside_range():
    devices = [make_device(9, "SWITCH-9"), make_device(2, "SWITCH-2")]
    members = find_members(make_master(), "site1", FakeNetBoxClient(devices=devices), "cisco", R)
    assert len(members) == 1
    assert members[0].position == 2


def test_returns_empty_when_no_members():
    devices = [make_device(1, "SWITCH-1")]
    members = find_members(make_master(), "site1", FakeNetBoxClient(devices=devices), "cisco", R)
    assert members == []


def test_sorted_by_position_ascending():
    devices = [make_device(3, "SWITCH-3"), make_device(2, "SWITCH-2"), make_device(4, "SWITCH-4")]
    members = find_members(make_master(), "site1", FakeNetBoxClient(devices=devices), "cisco", R)
    assert [m.position for m in members] == [2, 3, 4]


def test_priority_formula():
    devices = [make_device(2, "SWITCH-2"), make_device(3, "SWITCH-3")]
    members = find_members(make_master(), "site1", FakeNetBoxClient(devices=devices), "cisco", R)
    assert members[0].priority == 14
    assert members[1].priority == 13
