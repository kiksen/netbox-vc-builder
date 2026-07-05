from unittest.mock import patch

from typer.testing import CliRunner

from netbox_vc_builder.cli import app
from tests.conftest import FakeNetBoxClient

runner = CliRunner()


def _env(extra=None):
    base = {"NETBOX_ENDPOINT": "http://netbox", "NETBOX_TOKEN": "token"}
    if extra:
        base.update(extra)
    return base


def test_help_shows_usage():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--site" in result.output


def test_missing_site_exits_1():
    result = runner.invoke(app, [], env=_env())
    assert result.exit_code == 1


def test_dry_run_flag_accepted():
    client = FakeNetBoxClient(devices=[])
    with patch("netbox_vc_builder.cli.NetBoxClient", return_value=client):
        result = runner.invoke(app, ["--site", "testsite", "-C"], env=_env())
    assert result.exit_code == 0


def test_success_exits_0():
    client = FakeNetBoxClient(devices=[])
    with patch("netbox_vc_builder.cli.NetBoxClient", return_value=client):
        result = runner.invoke(app, ["--site", "testsite"], env=_env())
    assert result.exit_code == 0
