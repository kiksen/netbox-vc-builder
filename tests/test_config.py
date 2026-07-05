import pytest

from netbox_vc_builder.config import ConfigError, load_config
from netbox_vc_builder.constants import DEFAULT_MANUFACTURER_SLUG


def test_raises_when_endpoint_missing(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("NETBOX_ENDPOINT", raising=False)
    monkeypatch.setenv("NETBOX_TOKEN", "token")
    with pytest.raises(ConfigError, match="NETBOX_ENDPOINT"):
        load_config("site1", False, False)


def test_raises_when_token_missing(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NETBOX_ENDPOINT", "http://netbox")
    monkeypatch.delenv("NETBOX_TOKEN", raising=False)
    with pytest.raises(ConfigError, match="NETBOX_TOKEN"):
        load_config("site1", False, False)


def test_raises_when_site_missing(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NETBOX_ENDPOINT", "http://netbox")
    monkeypatch.setenv("NETBOX_TOKEN", "token")
    with pytest.raises(ConfigError, match="--site"):
        load_config("", False, False)


def test_loads_manufacturer_slug_from_yaml(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NETBOX_ENDPOINT", "http://netbox")
    monkeypatch.setenv("NETBOX_TOKEN", "token")
    (tmp_path / ".netbox-vc-builder.yaml").write_text("manufacturer_slug: arista\n")
    config = load_config("site1", False, False)
    assert config.manufacturer_slug == "arista"


def test_defaults_manufacturer_slug_to_cisco(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NETBOX_ENDPOINT", "http://netbox")
    monkeypatch.setenv("NETBOX_TOKEN", "token")
    config = load_config("site1", False, False)
    assert config.manufacturer_slug == DEFAULT_MANUFACTURER_SLUG


def test_dry_run_reflected_in_config(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NETBOX_ENDPOINT", "http://netbox")
    monkeypatch.setenv("NETBOX_TOKEN", "token")
    config = load_config("site1", dry_run=True, overwrite=False)
    assert config.dry_run is True
