DEFAULT_MANUFACTURER_SLUG = "cisco"

STACK_MIN_POSITION = 1
STACK_MAX_POSITION = 8

VC_PRIORITY_BASE = 16

INTERFACE_PATTERN_3PART = r"^([A-Za-z\-]+)(\d+)(\/\d+\/\d+)$"
INTERFACE_PATTERN_4PART = r"^([A-Za-z\-]+)(\d+)(\/\d+\/\d+\/\d+)$"

MGMT_ONLY_FLAG = "mgmt_only"
VLAN1_INTERFACE_NAME = "Vlan1"

NON_PHYSICAL_INTERFACE_TYPES = {"virtual", "lag", "bridge"}

ENV_NETBOX_ENDPOINT = "NETBOX_ENDPOINT"
ENV_NETBOX_TOKEN = "NETBOX_TOKEN"

CONFIG_FILE_NAME = ".netbox-vc-builder.yaml"

LOG_FILE_NAME = "netbox-vc-builder.log"
