from netbox_vc_builder.check_members import check_members
from netbox_vc_builder.models import StackMember
from netbox_vc_builder.reporter import NullReporter

R = NullReporter()


def make_member(id: int, name: str, vc_id=None) -> StackMember:
    return StackMember(id=id, name=name, position=2, priority=14, existing_vc_id=vc_id)


def test_accepts_member_with_no_existing_vc():
    m = make_member(1, "SWITCH-2")
    accepted, rejected = check_members([m], R)
    assert m in accepted
    assert rejected == []


def test_rejects_member_already_in_vc_without_overwrite():
    m = make_member(1, "SWITCH-2", vc_id=55)
    accepted, rejected = check_members([m], R, overwrite=False)
    assert accepted == []
    assert m in rejected


def test_accepts_member_in_vc_with_overwrite():
    m = make_member(1, "SWITCH-2", vc_id=55)
    accepted, rejected = check_members([m], R, overwrite=True)
    assert m in accepted
    assert rejected == []


def test_warning_messages_for_rejected_members():
    warnings = []

    class CapturingReporter(NullReporter):
        def warn(self, msg):
            warnings.append(msg)

    m = make_member(1, "SWITCH-2", vc_id=42)
    check_members([m], CapturingReporter(), overwrite=False)
    assert any("SWITCH-2" in w for w in warnings)
    assert any("42" in w for w in warnings)


def test_mixed_accepted_and_rejected():
    m1 = make_member(1, "SWITCH-2", vc_id=None)
    m2 = make_member(2, "SWITCH-3", vc_id=10)
    m3 = make_member(3, "SWITCH-4", vc_id=None)
    accepted, rejected = check_members([m1, m2, m3], R, overwrite=False)
    assert m1 in accepted
    assert m3 in accepted
    assert m2 in rejected
