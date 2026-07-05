from netbox_vc_builder.find_masters import find_masters
from netbox_vc_builder.reporter import NullReporter
from tests.conftest import FakeNetBoxClient, make_device


def client(*devices):
    return FakeNetBoxClient(devices=list(devices))


R = NullReporter()


def test_returns_empty_when_no_devices():
    masters = find_masters("site1", client(), "cisco", R)
    assert masters == []


def test_returns_only_position_1_devices():
    devices = [
        make_device(1, "SWITCH-1"),
        make_device(2, "SWITCH-2"),
        make_device(3, "SWITCH-3"),
    ]
    masters = find_masters("site1", FakeNetBoxClient(devices=devices), "cisco", R)
    assert len(masters) == 1
    assert masters[0].name == "SWITCH-1"


def test_includes_devices_already_in_vc_with_existing_vc_id():
    devices = [
        make_device(1, "SWITCH-1", virtual_chassis=99),
        make_device(2, "CORE-1"),
    ]
    masters = find_masters("site1", FakeNetBoxClient(devices=devices), "cisco", R)
    assert len(masters) == 2
    switch = next(m for m in masters if m.name == "SWITCH-1")
    assert switch.existing_vc_id == 99
    core = next(m for m in masters if m.name == "CORE-1")
    assert core.existing_vc_id is None


def test_parses_prefix_correctly():
    devices = [make_device(1, "SWITCH-CORE-1")]
    masters = find_masters("site1", FakeNetBoxClient(devices=devices), "cisco", R)
    assert masters[0].prefix == "SWITCH-CORE"


def test_device_not_matching_stack_pattern_is_excluded():
    devices = [make_device(1, "ROUTER")]
    masters = find_masters("site1", FakeNetBoxClient(devices=devices), "cisco", R)
    assert masters == []


def test_position_out_of_range_excluded():
    devices = [make_device(1, "SWITCH-99")]
    masters = find_masters("site1", FakeNetBoxClient(devices=devices), "cisco", R)
    assert masters == []
