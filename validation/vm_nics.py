import ipaddress
from typing import Any

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from validation.recovery_zvm_sites import (
    VnicIpConfigChange,
    YesNo,
    normalize_blank,
    validate_site_scoped_value,
)
from validation.vpgs import apply_vpg_defaults, first_value, validate_config_value
import config
from validation.error_formatting import (
    WorkbookValidationError,
    format_workbook_error,
    validate_model_rows,
)

class VMNIC(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    vpg_name: str | None = Field(
        default=None,
        validation_alias="VPG Name",
    )
    vm_name: str | None = Field(
        default=None,
        validation_alias="VM Name",
    )
    nic_name: str | None = Field(
        default=None,
        validation_alias="NIC Name",
    )
    protected_network_name: str | None = Field(
        default=None,
        validation_alias="Protected Network Name",
    )
    failover_live_move_network_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "Failover Live / Move - Network Name",
            "Failover / Move Network Name",
            "Failover Live / Move Network Name",
        ),
    )
    failover_live_move_create_new_mac_address: YesNo | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "Failover Live / Move - Create new MAC address",
            "Failover Live / Move - Create new MAC Address",
        ),
    )
    failover_live_move_change_vnic_ip_config: VnicIpConfigChange | None = Field(
        default=None,
        validation_alias="Failover Live / Move - Change vNIC IP Config",
    )
    failover_live_move_ip_address: Any | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "Failover Live / Move - IP Address",
            "Failover Live / Move IP Address",
        ),
    )
    failover_live_move_subnet_mask: Any | None = Field(
        default=None,
        validation_alias="Failover Live / Move - Subnet Mask",
    )
    failover_live_move_default_gateway: Any | None = Field(
        default=None,
        validation_alias="Failover Live / Move - Default Gateway",
    )
    failover_live_move_preferred_dns_server: Any | None = Field(
        default=None,
        validation_alias="Failover Live / Move - Preferred DNS Server",
    )
    failover_live_move_alternate_dns_server: Any | None = Field(
        default=None,
        validation_alias="Failover Live / Move - Alternate DNS Server",
    )
    failover_live_move_dns_suffix: Any | None = Field(
        default=None,
        validation_alias="Failover Live / Move - DNS Suffix",
    )
    failover_test_network_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "Failover Test - Network Name",
            "Failover Test Network Name",
        ),
    )
    failover_test_create_new_mac_address: YesNo | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "Failover Test - Create new MAC address",
            "Failover Test - Create new MAC Address",
        ),
    )
    failover_test_change_vnic_ip_config: VnicIpConfigChange | None = Field(
        default=None,
        validation_alias="Failover Test - Change vNIC IP Config",
    )
    failover_test_ip_address: Any | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "Failover Test - IP Address",
            "Failover Test IP Address",
        ),
    )
    failover_test_subnet_mask: Any | None = Field(
        default=None,
        validation_alias="Failover Test - Subnet Mask",
    )
    failover_test_default_gateway: Any | None = Field(
        default=None,
        validation_alias="Failover Test - Default Gateway",
    )
    failover_test_preferred_dns_server: Any | None = Field(
        default=None,
        validation_alias="Failover Test - Preferred DNS Server",
    )
    failover_test_alternate_dns_server: Any | None = Field(
        default=None,
        validation_alias="Failover Test - Alternate DNS Server",
    )
    failover_test_dns_suffix: Any | None = Field(
        default=None,
        validation_alias="Failover Test - DNS Suffix",
    )

    @field_validator("*", mode="before")
    @classmethod
    def convert_blank_values_to_none(cls, value):
        return normalize_blank(value)

    @field_validator("vpg_name")
    @classmethod
    def validate_vpg_name(cls, value):
        validated_value = validate_config_value(value, config.vpg_names, "VPG Name")

        if config.vpg_types_by_vpg_name.get(validated_value) == "Local Continuous Backup":
            raise ValueError(
                f"VPG Name '{validated_value}' is not valid because its VPG Type is "
                "'Local Continuous Backup'."
            )

        return validated_value

    @field_validator("vm_name")
    @classmethod
    def validate_vm_name(cls, value, info: ValidationInfo):
        if value is None:
            return value

        vpg_name = info.data.get("vpg_name")
        protected_site_name = config.vpg_protected_site_names_by_vpg_name.get(vpg_name)
        if protected_site_name is None:
            raise ValueError(
                f"VM Name '{value}' cannot be validated because VPG "
                f"'{vpg_name}' does not have a Protected ZVM Site Name."
            )

        allowed_values = config.protected_vm_names_by_site.get(
            protected_site_name,
            [],
        )

        if value not in allowed_values:
            raise ValueError(
                f"VM Name '{value}' is not valid for VPG '{vpg_name}' "
                f"with Protected ZVM Site Name '{protected_site_name}'. "
                f"Allowed values: {allowed_values}"
            )

        return value

    @field_validator("nic_name")
    @classmethod
    def validate_nic_name(cls, value, info: ValidationInfo):
        if value is None:
            return value

        vm_name = info.data.get("vm_name")
        vpg_name = info.data.get("vpg_name")
        protected_site_name = config.vpg_protected_site_names_by_vpg_name.get(vpg_name)
        if vm_name is None:
            raise ValueError(
                f"NIC Name '{value}' cannot be validated because VM Name is not valid."
            )

        allowed_values = config.protected_nic_names_by_site_and_vm_name.get(
            (protected_site_name, vm_name),
            [],
        )
        if value not in allowed_values:
            raise ValueError(
                f"NIC Name '{value}' is not valid for VPG '{vpg_name}', "
                f"Protected ZVM Site Name '{protected_site_name}', and VM "
                f"'{vm_name}'. Allowed values: {allowed_values}"
            )

        return value

    @field_validator("protected_network_name")
    @classmethod
    def validate_protected_network_name(cls, value, info: ValidationInfo):
        if value is None:
            return value

        vm_name = info.data.get("vm_name")
        nic_name = info.data.get("nic_name")
        vpg_name = info.data.get("vpg_name")
        protected_site_name = config.vpg_protected_site_names_by_vpg_name.get(vpg_name)
        if vm_name is None or nic_name is None:
            raise ValueError(
                f"Protected Network Name '{value}' cannot be validated because "
                "VM Name or NIC Name is not valid."
            )

        allowed_value = config.protected_network_names_by_site_vm_nic.get(
            (protected_site_name, vm_name, nic_name),
        )
        if value != allowed_value:
            raise ValueError(
                f"Protected Network Name '{value}' is not valid for VPG "
                f"'{vpg_name}', Protected ZVM Site Name '{protected_site_name}', "
                f"VM '{vm_name}', and NIC '{nic_name}'. "
                f"Allowed values: {[allowed_value] if allowed_value else []}"
            )

        return value

    @field_validator("failover_live_move_network_name", "failover_test_network_name")
    @classmethod
    def validate_recovery_network_name(cls, value, info: ValidationInfo):
        if value is None:
            return value

        vpg_name = info.data.get("vpg_name")
        recovery_site_name = config.vpg_recovery_site_names_by_vpg_name.get(vpg_name)

        return validate_site_scoped_value(
            value,
            recovery_site_name,
            config.recovery_network_names_by_site,
            "Recovery Network Name",
        )

    @field_validator(
        "failover_live_move_ip_address",
        "failover_live_move_default_gateway",
        "failover_live_move_preferred_dns_server",
        "failover_live_move_alternate_dns_server",
        "failover_test_ip_address",
        "failover_test_default_gateway",
        "failover_test_preferred_dns_server",
        "failover_test_alternate_dns_server",
    )
    @classmethod
    def validate_ipv4_address(cls, value, info: ValidationInfo):
        if value is None:
            return value

        if not is_valid_ipv4_address(value):
            raise ValueError(
                f"{info.field_name} '{value}' is not valid. "
                "Allowed values: a valid IPv4 address."
            )

        return value

    @field_validator("failover_live_move_subnet_mask", "failover_test_subnet_mask")
    @classmethod
    def validate_ipv4_subnet_mask(cls, value, info: ValidationInfo):
        if value is None:
            return value

        if not is_valid_ipv4_subnet_mask(value):
            raise ValueError(
                f"{info.field_name} '{value}' is not valid. "
                "Allowed values: a valid IPv4 subnet mask."
            )

        return value

    @model_validator(mode="after")
    def validate_ip_config_rules(self):
        validate_nic_ip_config_group(
            prefix="Failover Live / Move",
            change_vnic_ip_config=self.failover_live_move_change_vnic_ip_config,
            ip_address=self.failover_live_move_ip_address,
            subnet_mask=self.failover_live_move_subnet_mask,
            default_gateway=self.failover_live_move_default_gateway,
            preferred_dns_server=self.failover_live_move_preferred_dns_server,
            alternate_dns_server=self.failover_live_move_alternate_dns_server,
            dns_suffix=self.failover_live_move_dns_suffix,
        )
        validate_nic_ip_config_group(
            prefix="Failover Test",
            change_vnic_ip_config=self.failover_test_change_vnic_ip_config,
            ip_address=self.failover_test_ip_address,
            subnet_mask=self.failover_test_subnet_mask,
            default_gateway=self.failover_test_default_gateway,
            preferred_dns_server=self.failover_test_preferred_dns_server,
            alternate_dns_server=self.failover_test_alternate_dns_server,
            dns_suffix=self.failover_test_dns_suffix,
        )

        return self


def validate_vm_nic(
    data: dict,
    default_vpg_settings: dict | None = None,
    recovery_zvm_sites: list[dict] | None = None,
    vpgs: list[dict] | None = None,
) -> VMNIC:
    return VMNIC(**apply_vm_nic_defaults(
        data,
        build_vpg_defaults(default_vpg_settings, recovery_zvm_sites, vpgs),
    ))


def validate_vm_nics(
    data: list[dict],
    default_vpg_settings: dict | None = None,
    recovery_zvm_sites: list[dict] | None = None,
    vpgs: list[dict] | None = None,
) -> list[VMNIC]:
    vpg_defaults = build_vpg_defaults(
        default_vpg_settings,
        recovery_zvm_sites,
        vpgs,
    )
    effective_data = [
        apply_vm_nic_defaults(row, vpg_defaults)
        for row in data
    ]
    validated_rows = validate_model_rows(VMNIC, effective_data)
    validate_unique_vm_nic_rows(data)
    return validated_rows


def build_vpg_defaults(
    default_vpg_settings: dict | None,
    recovery_zvm_sites: list[dict] | None,
    vpgs: list[dict] | None,
) -> dict:
    return {
        vpg["VPG Name"]: apply_vpg_defaults(
            vpg,
            default_vpg_settings,
            recovery_zvm_sites,
        )
        for vpg in vpgs or []
        if vpg.get("VPG Name")
    }


def apply_vm_nic_defaults(row: dict, vpg_defaults: dict) -> dict:
    effective_row = dict(row)
    vpg = vpg_defaults.get(row.get("VPG Name"), {})

    for field_name, vpg_field_name in (
        ("Failover Live / Move - Network Name", "Failover Live / Move - Network Name"),
        (
            "Failover Live / Move - Create new MAC address",
            "Failover Live / Move - Create new MAC address",
        ),
        (
            "Failover Live / Move - Change vNIC IP Config",
            "Failover Live / Move - Change vNIC IP Config",
        ),
        ("Failover Live / Move - IP Address", "Failover Live / Move - IP Address"),
        ("Failover Live / Move - Subnet Mask", "Failover Live / Move - Subnet Mask"),
        (
            "Failover Live / Move - Default Gateway",
            "Failover Live / Move - Default Gateway",
        ),
        (
            "Failover Live / Move - Preferred DNS Server",
            "Failover Live / Move - Preferred DNS Server",
        ),
        (
            "Failover Live / Move - Alternate DNS Server",
            "Failover Live / Move - Alternate DNS Server",
        ),
        ("Failover Live / Move - DNS Suffix", "Failover Live / Move - DNS Suffix"),
        ("Failover Test - Network Name", "Failover Test Network Name"),
        (
            "Failover Test - Create new MAC address",
            "Failover Test - Create new MAC address",
        ),
        (
            "Failover Test - Change vNIC IP Config",
            "Failover Test - Change vNIC IP Config",
        ),
        ("Failover Test - IP Address", "Failover Test - IP Address"),
        ("Failover Test - Subnet Mask", "Failover Test - Subnet Mask"),
        ("Failover Test - Default Gateway", "Failover Test - Default Gateway"),
        (
            "Failover Test - Preferred DNS Server",
            "Failover Test - Preferred DNS Server",
        ),
        (
            "Failover Test - Alternate DNS Server",
            "Failover Test - Alternate DNS Server",
        ),
        ("Failover Test - DNS Suffix", "Failover Test - DNS Suffix"),
    ):
        effective_row[field_name] = first_value(
            effective_row.get(field_name),
            vpg.get(vpg_field_name),
        )

    return effective_row


def is_valid_ipv4_address(value) -> bool:
    try:
        return isinstance(ipaddress.ip_address(str(value)), ipaddress.IPv4Address)
    except ValueError:
        return False


def is_valid_ipv4_subnet_mask(value) -> bool:
    text = str(value)
    if "." not in text:
        return False

    try:
        ipaddress.IPv4Network(f"0.0.0.0/{text}", strict=False)
    except ValueError:
        return False

    return True


def validate_nic_ip_config_group(
    prefix: str,
    change_vnic_ip_config,
    ip_address,
    subnet_mask,
    default_gateway,
    preferred_dns_server,
    alternate_dns_server,
    dns_suffix,
) -> None:
    fields = {
        "IP Address": ip_address,
        "Subnet Mask": subnet_mask,
        "Default Gateway": default_gateway,
        "Preferred DNS Server": preferred_dns_server,
        "Alternate DNS Server": alternate_dns_server,
        "DNS Suffix": dns_suffix,
    }

    if change_vnic_ip_config == "Yes, DHCP":
        populated_fields = [
            field_name
            for field_name, value in fields.items()
            if value is not None
        ]
        if populated_fields:
            raise ValueError(
                f"{prefix} IP configuration fields must be empty when "
                "Change vNIC IP Config is 'Yes, DHCP'. "
                f"Populated fields: {populated_fields}"
            )

    if change_vnic_ip_config == "Yes, Static":
        missing_fields = [
            field_name
            for field_name, value in fields.items()
            if value is None
        ]
        if missing_fields:
            raise ValueError(
                f"{prefix} IP configuration fields are mandatory when "
                "Change vNIC IP Config is 'Yes, Static'. "
                f"Missing fields: {missing_fields}"
            )

    if ip_address is not None and subnet_mask is not None and default_gateway is not None:
        validate_gateway_for_network(
            prefix,
            ip_address,
            subnet_mask,
            default_gateway,
        )


def validate_gateway_for_network(
    prefix: str,
    ip_address,
    subnet_mask,
    default_gateway,
) -> None:
    network = ipaddress.IPv4Network(f"{ip_address}/{subnet_mask}", strict=False)
    gateway = ipaddress.IPv4Address(str(default_gateway))

    if gateway not in network:
        raise ValueError(
            f"{prefix} Default Gateway '{default_gateway}' is not valid for "
            f"IP Address '{ip_address}' and Subnet Mask '{subnet_mask}'."
        )


def validate_unique_vm_nic_rows(data: list[dict]) -> None:
    seen_rows = {}
    messages = []

    for row in data:
        key = (
            row.get("VPG Name"),
            row.get("VM Name"),
            row.get("NIC Name"),
        )

        if any(value is None for value in key):
            continue

        if key in seen_rows:
            for duplicate_row in (seen_rows[key], row):
                messages.append(format_workbook_error(
                    duplicate_row,
                    "NIC Name",
                    row.get("NIC Name"),
                    "The combination of VPG Name, VM Name, and NIC Name must be unique.",
                ))
            continue

        seen_rows[key] = row

    if messages:
        raise WorkbookValidationError(messages)
