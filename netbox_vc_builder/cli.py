import importlib.metadata
import time
from typing import Annotated

import typer

from .build_vc import build_vc
from .check_members import check_members
from .config import ConfigError, load_config
from .find_masters import find_masters
from .find_members import find_members
from .interface_ops import process_interfaces
from .models import RunSummary, parse_stack_name
from .netbox_client import NetBoxAuthError, NetBoxClient, NetBoxConnectionError
from .reporter import Reporter

app = typer.Typer(
    name="netbox-vc-builder",
    help="Build and maintain Cisco switch stacks as clean Virtual Chassis in NetBox.",
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(importlib.metadata.version("netbox-vc-builder"))
        raise typer.Exit()


@app.command()
def main(
    site: Annotated[str, typer.Option("--site", help="NetBox site slug")] = "",
    dry_run: Annotated[
        bool, typer.Option("-C", "--dry-run", help="Show what would be done without making changes")
    ] = False,
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Recreate all VCs for the site")
    ] = False,
    version: Annotated[
        bool | None,
        typer.Option(
            "--version", callback=_version_callback, is_eager=True, help="Show version and exit"
        ),
    ] = None,
) -> None:
    try:
        config = load_config(site, dry_run, overwrite)
    except ConfigError as exc:
        typer.echo(f"Configuration error: {exc}", err=True)
        raise typer.Exit(code=1) from None

    try:
        client = NetBoxClient(config.netbox_endpoint, config.netbox_token, dry_run=config.dry_run)
        version_str = client.check_connectivity()
    except (NetBoxConnectionError, NetBoxAuthError) as exc:
        typer.echo(f"NetBox connection error: {exc}", err=True)
        raise typer.Exit(code=1) from None

    reporter = Reporter(dry_run=config.dry_run)

    try:
        site_record = client.get_site(config.site_slug)
    except Exception as exc:
        reporter.error(f"Failed to validate site slug '{config.site_slug}': {exc}")
        raise typer.Exit(code=1) from None

    if site_record is None:
        reporter.error(f"Site '{config.site_slug}' not found in NetBox")
        raise typer.Exit(code=1)

    dry_tag = " [DRY RUN]" if config.dry_run else ""
    typer.echo(f"🚀 netbox-vc-builder - Scanning {config.site_slug} for *-1 switches{dry_tag}")
    typer.echo(f"   NetBox {version_str}")

    summary = RunSummary(site_slug=config.site_slug)
    start = time.monotonic()

    masters = find_masters(config.site_slug, client, config.manufacturer_slug, reporter, overwrite=config.overwrite)
    summary.stacks_found = len(masters)

    reporter.section("Checking each master for members")

    for master in masters:
        members = find_members(master, config.site_slug, client, config.manufacturer_slug, reporter)
        accepted, rejected = check_members(members, reporter, overwrite=config.overwrite)
        result = build_vc(master, accepted, client, reporter, overwrite=config.overwrite)

        if result.status == "created":
            iface_warnings = process_interfaces(master, accepted, client, reporter)
            result.warnings.extend(iface_warnings)
            summary.created += 1
            summary.warnings.extend(iface_warnings)
        elif result.status == "skipped":
            summary.skipped += 1
        elif result.status == "failed":
            summary.failed += 1
        elif result.status == "dry_run":
            summary.dry_run_count += 1

        summary.results.append(result)

    _final_check(config.site_slug, client, config.manufacturer_slug, reporter)

    summary.duration_seconds = time.monotonic() - start
    reporter.summary(summary)

    if summary.failed > 0:
        raise typer.Exit(code=2)


def _final_check(
    site_slug: str, client: NetBoxClient, manufacturer_slug: str, reporter: Reporter
) -> None:
    try:
        all_devices = client.get_all_stack_devices(site_slug, manufacturer_slug)
    except Exception:
        return

    orphans = [
        d
        for d in all_devices
        if d["virtual_chassis"] is None and parse_stack_name(d["name"]) is not None
    ]
    if orphans:
        reporter.warn(f"Final check: {len(orphans)} device(s) still not in any VC:")
        for d in orphans:
            reporter.warn(f"  - {d['name']}")
