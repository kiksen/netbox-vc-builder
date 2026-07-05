import os
from pathlib import Path

import yaml

from .constants import (
    CONFIG_FILE_NAME,
    DEFAULT_MANUFACTURER_SLUG,
    ENV_NETBOX_ENDPOINT,
    ENV_NETBOX_TOKEN,
)
from .models import AppConfig


class ConfigError(Exception):
    pass


def load_config(site: str, dry_run: bool, overwrite: bool) -> AppConfig:
    endpoint = os.environ.get(ENV_NETBOX_ENDPOINT, "")
    token = os.environ.get(ENV_NETBOX_TOKEN, "")

    manufacturer_slug = DEFAULT_MANUFACTURER_SLUG
    config_path = Path(CONFIG_FILE_NAME)
    if config_path.exists():
        with open(config_path) as f:
            yaml_config = yaml.safe_load(f) or {}
        manufacturer_slug = yaml_config.get("manufacturer_slug", manufacturer_slug)

    if not endpoint or not token:
        raise ConfigError(f"{ENV_NETBOX_ENDPOINT} or {ENV_NETBOX_TOKEN} are not found as an ENV")
    if not site:
        raise ConfigError("--site is required")

    return AppConfig(
        netbox_endpoint=endpoint,
        netbox_token=token,
        site_slug=site,
        manufacturer_slug=manufacturer_slug,
        dry_run=dry_run,
        overwrite=overwrite,
    )
