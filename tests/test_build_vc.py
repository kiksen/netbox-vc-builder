from netbox_vc_builder.build_vc import build_vc
from netbox_vc_builder.models import StackMaster, StackMember
from netbox_vc_builder.reporter import NullReporter
from tests.conftest import FakeNetBoxClient

R = NullReporter()


def make_master(existing_vc_id=None) -> StackMaster:
    return StackMaster(
        id=10,
        name="SWITCH-1",
        position=1,
        priority=15,
        existing_vc_id=existing_vc_id,
        prefix="SWITCH",
    )


def make_member(id: int, pos: int) -> StackMember:
    return StackMember(
        id=id, name=f"SWITCH-{pos}", position=pos, priority=16 - pos, existing_vc_id=None
    )


def test_creates_vc_with_correct_name():
    client = FakeNetBoxClient()
    build_vc(make_master(), [], client, R)
    assert client.created_vcs == ["SWITCH-1"]


def test_sets_master_position_and_priority():
    client = FakeNetBoxClient()
    build_vc(make_master(), [], client, R)
    master_update = next(u for u in client.membership_updates if u["is_master"])
    assert master_update["device_id"] == 10
    assert master_update["position"] == 1
    assert master_update["priority"] == 15
    assert master_update["is_master"] is True


def test_sets_member_position_2_priority_14():
    client = FakeNetBoxClient()
    build_vc(make_master(), [make_member(20, 2)], client, R)
    member_update = next(u for u in client.membership_updates if not u["is_master"])
    assert member_update["device_id"] == 20
    assert member_update["position"] == 2
    assert member_update["priority"] == 14


def test_sets_member_position_3_priority_13():
    client = FakeNetBoxClient()
    build_vc(make_master(), [make_member(30, 3)], client, R)
    member_update = next(u for u in client.membership_updates if u["device_id"] == 30)
    assert member_update["priority"] == 13


def test_skips_when_master_already_in_vc_no_overwrite():
    client = FakeNetBoxClient()
    result = build_vc(make_master(existing_vc_id=99), [], client, R, overwrite=False)
    assert result.status == "skipped"
    assert client.created_vcs == []


def test_deletes_and_recreates_when_overwrite():
    client = FakeNetBoxClient()
    result = build_vc(make_master(existing_vc_id=99), [], client, R, overwrite=True)
    assert 99 in client.deleted_vcs
    assert result.status == "created"
    assert client.created_vcs == ["SWITCH-1"]


def test_returns_correct_member_count():
    client = FakeNetBoxClient()
    result = build_vc(make_master(), [make_member(20, 2), make_member(30, 3)], client, R)
    assert result.member_count == 3  # master + 2 members


def test_result_status_is_created():
    client = FakeNetBoxClient()
    result = build_vc(make_master(), [], client, R)
    assert result.status == "created"
