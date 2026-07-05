# netbox-vc-builder 🚀  
### Keep your Cisco switch stacks as clean virtual chassis in NetBox.

Never start deleting duplicate management or SVI interfaces again. Always have the correct interface names.


## Why netbox-vc-builder

**The Problem You Face:**  
If you create a Cisco stack in NetBox, each stack member (except the first one) has incorrect interface numbering.
The second member has GigabitEthernet1/0/1 as the interface name instead of GigabitEthernet2/0/1.

Each member has a vlan1 interface as a default interface, which results in two or more vlan1 interfaces when you view all chassis interfaces. The same applies to the management interface.



**netbox-vc-builder Solution:**  
netbox-vc-builder builds clean virtual chassis based on the stack rules described in this document. It offers to scan all switches for one site to build or update the VC members.

## NetBox Rules

To find out if a switch is a stack member you only need to check its suffix. It ends with `-<number>` starting from 1 to 8, since Cisco supports a maximum of 8 members per stack at the Cisco Catalyst C9000 series.

For example:
SWITCH-1
SWITCH-2
SWITCH-3

Each stack member shares the same prefix, e.g. SWITCH. The suffix like -1, -2 changes per member.

This script is for Cisco devices only. The manufacturer must be set to "cisco".

### VC Rules
* The first switch is always the stack master.
* The number -1 or -2 reflects the NetBox VC position.
* The first switch gets priority 15, the second gets 14, the third gets 13, and so on.


### Interface Renumbering Rules

netbox-vc-builder supports three-part and four-part notation:
* Stack-Member / Module / Port-Number
* Stack-Member / Slot-Number / Bay-Number / Port-Number

The stack member number is always mapped to the VC position. All other numbers stay untouched.

### Interface Cleanup
The master is the only switch that can have a mgmt-only interface. On all members this kind of interface will be removed.
The same applies to vlan1 — it is only allowed on the master device.
The IP of the master's vlan1 interface will be set as the primary IPv4 address.

If a vlan1 interface is deleted and it has an IP address assigned, a warning is written to the screen and the log file.



---

## What Makes It Special

🛡️ **Totally Safe** - Never touches switches which are already a VC member. Only if overwrite is allowed!
🧠 **Zero Config** - Works perfectly out of the box with smart defaults  
⚡ **Automation Ready** - JSON output for scripts and CI/CD pipelines  
🎯 **Smart Discovery** - Finds NetBox automatically using NETBOX_ENDPOINT and NETBOX_TOKEN environment variables.
🎨 **Beautiful Output** - Color-coded status updates that are easy to scan  
---

## Perfect For

- **High-automation network teams** managing everything with NetBox as a source of truth

---

## Install & Run in 30 Seconds

```bash
# Install (when published to PyPI)
pip install netbox-vc-builder

# Or install from source
git clone <repo-url>
cd netbox-vc-builder
pip install -e .

# Run it
netbox-vc-builder --site <siteslug>
```

Done. That's the whole getting started guide.

---

## Quick Examples

```bash
# Build all VCs for all Cisco switches for site "Bonn"
netbox-vc-builder --site bonn

# Preview what would happen (dry run) using -C like Ansible's "check mode"
netbox-vc-builder --site bonn -C

# Recreate all VCs for Bonn
netbox-vc-builder --overwrite --site bonn
```

---

## See It In Action

```
🚀 netbox-vc-builder - Scanning Bonn for *-1 switches
   Found 15 possible stack masters

Checking each master for members
✓ found 1 member for TEST-1
✓ creating VC.
⚠ Setting TEST-1 as Master, priority 15 and position 1
✓ Setting TEST-2 as Member, priority 14 and position 2

Summary:
  📊 4 Stacks found
  ✓ Successfully updated: 2
  ⚠ Skipped: 2
  ✗ Failed: 0
  ⏱ Duration: 8.3s
```

Clean, clear, and you know exactly what happened with each VC.

---

## How netbox-vc-builder Compares to Manual VC Creation

- **Always** consistent values — no drift of convention
- **Always** correct interface names
- **No** redundant interfaces
---

## Complete Feature List

### Core Features
- ✅ **Scan site** - Scans a site for possible master devices. All *-1 devices
- ✅ **Check first** - Checks if a master is already a VC member before doing anything
- ✅ **Build VC** - Builds a VC with all members
- ✅ **Final check** - After everything is done, checks again all switches ending with `-<number>` to see if any are not yet a VC member. Prints to log and screen.
- ✅ **Beautiful Output** - Color-coded terminal output that's easy to scan

---

## Usage Reference

```
netbox-vc-builder [OPTIONS]

Options:
  -C, --dry-run        Show what would be done without making changes
  --site SITESLUG      The site slug of a NetBox site
  --overwrite          Recreate all VCs for one site
```

---

## Configuration Files

netbox-vc-builder works great with zero configuration, but power users can customize behavior with config files.

### Configuration Precedence

1. **Command-line arguments** (highest priority)
2. **Local config**: `config.yaml` in current directory

### Example Configuration

Create a `.netbox-vc-builder.yaml` file in your project root:

```yaml
# only target Cisco devices
manufacturer_slug: cisco
```

---

## How It Works

netbox-vc-builder follows a simple, safe process:

1. **Load Config** - Loads configuration from files (if present) and updates manufacturer_slug
2. **Load Env** - Loads NETBOX_ENDPOINT and NETBOX_TOKEN from environment variables
3. **Check NetBox** - Connects to NetBox to verify it is reachable. It reads the NetBox version as a test.
4. **Site slug** - Checks if the site slug exists in NetBox
5. **Scan for masters** - Loads all *-1 switches for the site slug that are not already VC members
6. **Check** - Verifies that member candidates are not already VC members elsewhere
7. **Create or Update VC** - Creates a new VC, or deletes and recreates it when --overwrite is set. Respects check mode.
8. **Update** - Adds all members to the master. Respects check mode.
---


---

## Troubleshooting

### ENVs Not Found
**Problem:** `NETBOX_ENDPOINT or NETBOX_TOKEN are not found as an ENV`  
**Solution:** Ensure the environment variables are set before running the tool.

### NetBox Not Reachable
**Problem:** Can't access NetBox to load the NetBox version.  
**Solution:** Check why NetBox is not reachable.

---

## Development

Want to contribute? Great! Here's how to get started.

### Setup Development Environment

```bash
# Clone the repository
git clone <repo-url>
cd netbox-vc-builder

# Create virtual environment
uv sync
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/test_find_masters.py
```

**Current test coverage:** 59% overall, 70%+ for core modules

### Libraries and Modules

- **Typer** for the CLI interface
- **rich** for beautiful output


### Linting and Formatting

```bash
# Format code
uv run ruff format .

# Check and fix linting issues
uv run ruff check --fix .
```

### Project Structure

```
netbox-vc-builder/
├── netbox_vc_builder/           # Main package
│   ├── cli.py                   # CLI interface
│   ├── find_masters.py          # Master candidate discovery
│   ├── find_members.py          # Find possible members for a VC master that are not yet a VC member
│   ├── check_members.py         # Validates member candidates for VC
│   ├── reporter.py              # Output formatting
│   ├── config.py                # Configuration management for config.yaml
│   ├── models.py                # Data structures
│   └── constants.py             # Constants and defaults
└── tests/                       # Test suite
```

---

## Contributing

Contributions are welcome! Here's how you can help:

- 🐛 **Report bugs** - Open an issue with steps to reproduce
- 💡 **Suggest features** - Share your ideas for improvements
- 📖 **Improve docs** - Help make documentation clearer
- 🔧 **Submit PRs** - Fix bugs or add features

Please ensure:
- Tests pass (`uv run pytest`)
- Code is formatted (`uv run ruff format .`)
- Linting passes (`uv run ruff check .`)

---

## Philosophy

netbox-vc-builder exists because I believe automation is better than clicking!
Your time is valuable. Your focus is precious. Automation is predictable.

We believe:
- **Automation should be standard** - Works perfectly without configuration
- **Safety enables confidence** - Never lose work
- **Clarity reduces anxiety** - Always know what's happening

One command. All VCs!

---

## License

MIT License - See LICENSE file for details

---

## Support

- **Issues:** [GitHub Issues](https://github.com/kiksen/netbox-vc-builder/issues)
- **Questions:** Open a GitHub Discussion
- **Security:** Email security concerns privately

---

**Made with ❤️ for network engineers who manage too many switches**

*Star on GitHub if netbox-vc-builder saves you time!* ⭐

---
