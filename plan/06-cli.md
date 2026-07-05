# Phase 6 — CLI & Configuration

## cli.py

Built with **Typer**. Single command (not a sub-command app — keep it simple).

```python
import typer
from typing import Annotated

app = typer.Typer(
    name="netbox-vc-builder",
    help="Build and maintain Cisco switch stacks as clean Virtual Chassis in NetBox.",
    no_args_is_help=True,
)

@app.command()
def main(
    site: Annotated[str, typer.Option("--site", help="NetBox site slug")] = "",
    dry_run: Annotated[bool, typer.Option("-C", "--dry-run", help="Show what would be done without making changes")] = False,
    overwrite: Annotated[bool, typer.Option("--overwrite", help="Recreate all VCs for the site")] = False,
):
    ...
```

**Execution sequence in main():**
1. Load config (`load_config(site, dry_run, overwrite)`)
2. Validate required fields (site slug, NETBOX_ENDPOINT, NETBOX_TOKEN) — exit with error if missing
3. Create `NetBoxClient`
4. Check connectivity — exit with error if unreachable
5. Validate site slug — exit with error if unknown
6. Create `Reporter` (with log file handle)
7. Print banner
8. `masters = find_masters(site_slug, client, manufacturer_slug)`
9. Print `Found N possible stack masters`
10. For each master:
    - `members = find_members(master, client)`
    - `accepted, rejected = check_members(members, client, overwrite)`
    - `result = build_vc(master, accepted, client, reporter, overwrite)`
    - if result.status == "created": `process_interfaces(master, accepted, client, reporter)`
    - summary.results.append(result)
11. `final_check(site_slug, client, manufacturer_slug, reporter)`
12. `reporter.summary(summary)`
13. Exit code 0 if no failures, 1 if any failures

---

## config.py

**load_config()** merges configuration from three sources, in precedence order (highest → lowest):

```
1. CLI arguments (site, dry_run, overwrite)
2. YAML config file (.netbox-vc-builder.yaml in current working directory)
3. Environment variables (NETBOX_ENDPOINT, NETBOX_TOKEN)
```

**Note:** NETBOX_ENDPOINT and NETBOX_TOKEN are always sourced from environment (not overridable from YAML for security). CLI and YAML can set `manufacturer_slug`.

```python
def load_config(
    site: str,
    dry_run: bool,
    overwrite: bool,
) -> AppConfig:
    # 1. Load env
    endpoint = os.environ.get(ENV_NETBOX_ENDPOINT, "")
    token = os.environ.get(ENV_NETBOX_TOKEN, "")
    
    # 2. Load YAML (if exists)
    manufacturer_slug = DEFAULT_MANUFACTURER_SLUG
    if Path(CONFIG_FILE_NAME).exists():
        with open(CONFIG_FILE_NAME) as f:
            yaml_config = yaml.safe_load(f) or {}
        manufacturer_slug = yaml_config.get("manufacturer_slug", manufacturer_slug)
    
    # 3. Validate required fields
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
```

**ConfigError** is a simple exception class caught in `main()` and shown as a clean error message (no traceback).

---

## Banner

Printed at the start of every run:

```
🚀 netbox-vc-builder - Scanning {site_slug} for *-1 switches
```

In dry-run mode:
```
🚀 netbox-vc-builder - Scanning {site_slug} for *-1 switches [DRY RUN]
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (all VCs processed, no failures) |
| 1 | Fatal startup error (no config, bad site slug, NetBox unreachable) |
| 2 | Partial failure (some VCs failed — stacks_found > 0 but failed > 0) |

Typer raises `typer.Exit(code=N)` for non-zero exits.
