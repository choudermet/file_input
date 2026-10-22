from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

import config
from validation.error_formatting import (
    WorkbookValidationError,
    format_workbook_error,
    validate_model_rows,
)
from validation.recovery_zvm_sites import (
    DiskProvisioningOverride,
    JournalHistoryUnit,
    JournalSizeUnit,
    Priority,
    TargetRPOAlertUnit,
    VPGType,
    YesNo,
    apply_default_recovery_zvm_site_name,
    normalize_blank,
    validate_journal_history,
    validate_journal_size,
    validate_journal_size_threshold,
    validate_site_scoped_value,
    validate_target_rpo_alert,
)


TestReminder = Literal[
    "None",
    "3 Months",
    "6 Months",
    "9 Months",
    "12 Months",
]
VPG_NETWORK_FIELDS = (
    "Failover Live / Move - Network Name",
    "Failover Test Network Name",
    "Failover Live / Move - Create new MAC address",
    "Failover Live / Move - Change vNIC IP Config",
    "Failover Live / Move - IP Address",
    "Failover Live / Move - Subnet Mask",
    "Failover Live / Move - Default Gateway",
    "Failover Live / Move - Preferred DNS Server",
    "Failover Live / Move - Alternate DNS Server",
    "Failover Live / Move - DNS Suffix",
    "Failover Test - Create new MAC address",
    "Failover Test - Change vNIC IP Config",
    "Failover Test - IP Address",
    "Failover Test - Subnet Mask",
    "Failover Test - Default Gateway",
    "Failover Test - Preferred DNS Server",
    "Failover Test - Alternate DNS Server",
    "Failover Test - DNS Suffix",
)


class VPG(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    vpg_name: Any | None = Field(
        default=None,
        validation_alias="VPG Name",
    )
    protected_zvm_site_name: str | None = Field(
        default=None,
        validation_alias="Protected ZVM Site Name",
    )
    recovery_zvm_site_name: str | None = Field(
        default=None,
        validation_alias="Recovery ZVM Site Name",
    )
    vpg_type: VPGType | None = Field(
        default=None,
        validation_alias="VPG Type",
    )
    priority: Priority | None = Field(
        default=None,
        validation_alias="Priority",
    )
    vpg_description: Any | None = Field(
        default=None,
        validation_alias="VPG Description",
    )
    label_1: str | None = Field(
        default=None,
        validation_alias="Label 1",
    )
    label_2: str | None = Field(
        default=None,
        validation_alias="Label 2",
    )
    label_3: str | None = Field(
        default=None,
        validation_alias="Label 3",
    )
    label_4: str | None = Field(
        default=None,
        validation_alias="Label 4",
    )
    label_5: str | None = Field(
        default=None,
        validation_alias="Label 5",
    )
    boot_order_meta_group_name: str | None = Field(
        default=None,
        validation_alias="Boot Order Meta Group Name",
    )
    recovery_host_name: str | None = Field(
        default=None,
        validation_alias="Recovery Host Name",
    )
    recovery_datastore_name: str | None = Field(
        default=None,
        validation_alias="Recovery Datastore Name",
    )
    journal_history_unit: JournalHistoryUnit | None = Field(
        default=None,
        validation_alias="Journal History Unit",
    )
    journal_history_value: int | None = Field(
        default=None,
        validation_alias="Journal History Value",
    )
    target_rpo_alert_value: Any | None = Field(
        default=None,
        validation_alias="Target RPO Alert Value",
    )
    target_rpo_alert_unit: TargetRPOAlertUnit | None = Field(
        default=None,
        validation_alias="Target RPO Alert Unit",
    )
    test_reminder: TestReminder | None = Field(
        default=None,
        validation_alias="Test Reminder",
    )
    journal_datastore_name: str | None = Field(
        default=None,
        validation_alias="Journal Datastore Name",
    )
    journal_size_hard_limit_value: float | None = Field(
        default=None,
        validation_alias="Journal Size Hard Limit Value",
    )
    journal_size_hard_limit_unit: JournalSizeUnit | None = Field(
        default=None,
        validation_alias="Journal Size Hard Limit Unit",
    )
    journal_size_warning_threshold_value: float | None = Field(
        default=None,
        validation_alias="Journal Size Warning Threshold Value",
    )
    journal_size_warning_threshold_unit: JournalSizeUnit | None = Field(
        default=None,
        validation_alias="Journal Size Warning Threshold Unit",
    )
    scratch_journal_datastore_name: str | None = Field(
        default=None,
        validation_alias="Scratch Journal Datastore Name",
    )
    scratch_journal_size_hard_limit_value: float | None = Field(
        default=None,
        validation_alias="Scratch Journal Size Hard Limit Value",
    )
    scratch_journal_size_hard_limit_unit: JournalSizeUnit | None = Field(
        default=None,
        validation_alias="Scratch Journal Size Hard Limit Unit",
    )
    scratch_journal_size_warning_threshold_value: float | None = Field(
        default=None,
        validation_alias="Scratch Journal Size Warning Threshold Value",
    )
    scratch_journal_size_warning_threshold_unit: JournalSizeUnit | None = Field(
        default=None,
        validation_alias="Scratch Journal Size Warning Threshold Unit",
    )
    enable_wan_traffic_compression: YesNo | None = Field(
        default=None,
        validation_alias="Enable WAN Traffic Compression",
    )
    disk_provisioning_override: DiskProvisioningOverride | None = Field(
        default=None,
        validation_alias="Disk Provisioning Override",
    )
    failover_live_move_network_name: str | None = Field(
        default=None,
        validation_alias="Failover Live / Move - Network Name",
    )
    failover_test_network_name: str | None = Field(
        default=None,
        validation_alias="Failover Test Network Name",
    )
    recovery_folder_name: str | None = Field(
        default=None,
        validation_alias="Recovery Folder Name",
    )
    pre_recovery_script_name: str | None = Field(
        default=None,
        validation_alias="Pre-Recovery Script Name",
    )
    pre_recovery_script_parameters: Any | None = Field(
        default=None,
        validation_alias="Pre-Recovery Script Parameters",
    )
    pre_recovery_script_execution_timeout_seconds: int | None = Field(
        default=None,
        validation_alias="Pre-Recovery Script Execution Timeout (Seconds)",
    )
    post_recovery_script_name: str | None = Field(
        default=None,
        validation_alias="Post-Recovery Script Name",
    )
    post_recovery_script_parameters: Any | None = Field(
        default=None,
        validation_alias="Post-Recovery Script Parameters",
    )
    post_recovery_script_execution_timeout_seconds: int | None = Field(
        default=None,
        validation_alias="Post-Recovery Script Execution Timeout (Seconds)",
    )

    @field_validator("*", mode="before")
    @classmethod
    def convert_blank_values_to_none(cls, value):
        return normalize_blank(value)

    @field_validator("protected_zvm_site_name")
    @classmethod
    def validate_protected_zvm_site_name(cls, value):
        if value is None:
            return value

        if value not in config.protected_site_names:
            raise ValueError(
                f"Protected ZVM Site Name '{value}' is not valid. "
                f"Allowed values: {config.protected_site_names}"
            )

        return value

    @field_validator("recovery_zvm_site_name")
    @classmethod
    def validate_recovery_zvm_site_name(cls, value):
        if value is None:
            return value

        if value not in config.recovery_site_names:
            raise ValueError(
                f"Recovery ZVM Site Name '{value}' is not valid. "
                f"Allowed values: {config.recovery_site_names}"
            )

        return value

    @field_validator("label_1")
    @classmethod
    def validate_label_1(cls, value):
        return validate_config_value(value, config.scopes, "Label 1")

    @field_validator("label_2")
    @classmethod
    def validate_label_2(cls, value):
        return validate_config_value(value, config.waves, "Label 2")

    @field_validator("label_3")
    @classmethod
    def validate_label_3(cls, value):
        return validate_config_value(value, config.application_names, "Label 3")

    @field_validator("label_4")
    @classmethod
    def validate_label_4(cls, value):
        return validate_config_value(value, config.application_environments, "Label 4")

    @field_validator("label_5")
    @classmethod
    def validate_label_5(cls, value):
        return validate_config_value(value, config.data_types, "Label 5")

    @field_validator("boot_order_meta_group_name")
    @classmethod
    def validate_boot_order_meta_group_name(cls, value):
        return validate_config_value(
            value,
            config.boot_order_meta_groups,
            "Boot Order Meta Group Name",
        )

    @field_validator("recovery_host_name")
    @classmethod
    def validate_recovery_host_name(cls, value, info: ValidationInfo):
        if value is None:
            return value

        return validate_site_scoped_value(
            value,
            info.data.get("recovery_zvm_site_name"),
            config.recovery_host_or_cluster_names_by_site,
            "Recovery Host Name",
        )

    @field_validator(
        "recovery_datastore_name",
        "journal_datastore_name",
        "scratch_journal_datastore_name",
    )
    @classmethod
    def validate_recovery_datastore_name(cls, value, info: ValidationInfo):
        if value is None:
            return value

        return validate_site_scoped_value(
            value,
            info.data.get("recovery_zvm_site_name"),
            config.recovery_datastore_names_by_site,
            "Recovery Datastore Name",
        )

    @field_validator("failover_live_move_network_name", "failover_test_network_name")
    @classmethod
    def validate_recovery_network_name(cls, value, info: ValidationInfo):
        if value is None:
            return value

        return validate_site_scoped_value(
            value,
            info.data.get("recovery_zvm_site_name"),
            config.recovery_network_names_by_site,
            "Recovery Network Name",
        )

    @field_validator("recovery_folder_name")
    @classmethod
    def validate_recovery_folder_name(cls, value, info: ValidationInfo):
        if value is None:
            return value

        return validate_site_scoped_value(
            value,
            info.data.get("recovery_zvm_site_name"),
            config.recovery_folder_names_by_site,
            "Recovery Folder Name",
        )

    @field_validator("pre_recovery_script_name", "post_recovery_script_name")
    @classmethod
    def validate_recovery_script_name(cls, value):
        if value is None:
            return value

        if value not in config.recovery_scripts:
            raise ValueError(
                f"Recovery Script Name '{value}' is not valid. "
                f"Allowed values: {config.recovery_scripts}"
            )

        return value

    @field_validator(
        "pre_recovery_script_execution_timeout_seconds",
        "post_recovery_script_execution_timeout_seconds",
    )
    @classmethod
    def validate_script_timeout(cls, value):
        if value is None:
            return value

        validate_range(
            value,
            1,
            900,
            "Recovery Script Execution Timeout (Seconds)",
            "",
        )
        return value

    @model_validator(mode="after")
    def validate_row_rules(self):
        validate_journal_history(
            self.journal_history_value,
            self.journal_history_unit,
        )
        validate_target_rpo_alert(
            self.target_rpo_alert_value,
            self.target_rpo_alert_unit,
        )
        validate_journal_size(
            self.journal_size_hard_limit_value,
            self.journal_size_hard_limit_unit,
            "Journal Size Hard Limit Value",
        )
        validate_journal_size(
            self.journal_size_warning_threshold_value,
            self.journal_size_warning_threshold_unit,
            "Journal Size Warning Threshold Value",
        )
        validate_journal_size(
            self.scratch_journal_size_hard_limit_value,
            self.scratch_journal_size_hard_limit_unit,
            "Scratch Journal Size Hard Limit Value",
        )
        validate_journal_size(
            self.scratch_journal_size_warning_threshold_value,
            self.scratch_journal_size_warning_threshold_unit,
            "Scratch Journal Size Warning Threshold Value",
        )
        validate_journal_size_threshold(
            self.journal_size_warning_threshold_value,
            self.journal_size_warning_threshold_unit,
            self.journal_size_hard_limit_value,
            self.journal_size_hard_limit_unit,
            "Journal Size Warning Threshold",
            "Journal Size Hard Limit",
        )
        validate_journal_size_threshold(
            self.scratch_journal_size_warning_threshold_value,
            self.scratch_journal_size_warning_threshold_unit,
            self.scratch_journal_size_hard_limit_value,
            self.scratch_journal_size_hard_limit_unit,
            "Scratch Journal Size Warning Threshold",
            "Scratch Journal Size Hard Limit",
        )
        validate_local_continuous_backup_sites(
            self.vpg_type,
            self.protected_zvm_site_name,
            self.recovery_zvm_site_name,
        )

        return self


def validate_config_value(value, allowed_values: list, field_name: str):
    if value is None:
        return value

    if value not in allowed_values:
        raise ValueError(
            f"{field_name} '{value}' is not valid. "
            f"Allowed values: {allowed_values}"
        )

    return value


def validate_range(value: int, minimum: int, maximum: int, field_name: str, context: str):
    if minimum <= value <= maximum:
        return

    raise ValueError(
        f"{field_name} '{value}' is not valid {context}. "
        f"Allowed values: {minimum}-{maximum}"
    )


def validate_local_continuous_backup_sites(
    vpg_type,
    protected_site,
    recovery_site,
) -> None:
    if vpg_type != "Local Continuous Backup":
        return

    if protected_site == recovery_site:
        return

    raise ValueError(
        "Protected ZVM Site Name must equal Recovery ZVM Site Name "
        "when VPG Type is 'Local Continuous Backup'"
    )


def validate_local_continuous_backup_network_fields_empty(data: list[dict]) -> None:
    messages = []

    for row in data:
        if normalize_blank(row.get("VPG Type")) != "Local Continuous Backup":
            continue

        for field_name in VPG_NETWORK_FIELDS:
            value = normalize_blank(row.get(field_name))
            if value is None:
                continue

            messages.append(format_workbook_error(
                row,
                field_name,
                value,
                (
                    "This value must be empty when VPG Type is "
                    "'Local Continuous Backup'."
                ),
            ))

    if messages:
        raise WorkbookValidationError(messages)


def validate_vpg(
    data: dict,
    default_vpg_settings: dict | None = None,
    recovery_zvm_sites: list[dict] | None = None,
) -> VPG:
    return VPG(**apply_vpg_defaults(data, default_vpg_settings, recovery_zvm_sites))


def validate_vpgs(
    data: list[dict],
    default_vpg_settings: dict | None = None,
    recovery_zvm_sites: list[dict] | None = None,
) -> list[VPG]:
    effective_data = [
        apply_vpg_defaults(row, default_vpg_settings, recovery_zvm_sites)
        for row in data
    ]
    load_effective_vpg_context_into_config(effective_data)
    validated_rows = validate_model_rows(VPG, effective_data)
    validate_unique_vpg_names(data)
    validate_local_continuous_backup_network_fields_empty(data)
    return validated_rows


def load_effective_vpg_context_into_config(vpgs: list[dict]) -> None:
    config.vpg_protected_site_names_by_vpg_name = {
        vpg["VPG Name"]: vpg.get("Protected ZVM Site Name")
        for vpg in vpgs
        if vpg.get("VPG Name")
    }
    config.vpg_recovery_site_names_by_vpg_name = {
        vpg["VPG Name"]: vpg.get("Recovery ZVM Site Name")
        for vpg in vpgs
        if vpg.get("VPG Name")
    }
    config.vpg_boot_order_meta_group_names_by_vpg_name = {
        vpg["VPG Name"]: vpg.get("Boot Order Meta Group Name")
        for vpg in vpgs
        if vpg.get("VPG Name")
    }
    config.vpg_types_by_vpg_name = {
        vpg["VPG Name"]: vpg.get("VPG Type")
        for vpg in vpgs
        if vpg.get("VPG Name")
    }


def apply_vpg_defaults(
    row: dict,
    default_vpg_settings: dict | None,
    recovery_zvm_sites: list[dict] | None,
) -> dict:
    effective_row = dict(row)
    effective_protected_site = first_value(
        effective_row.get("Protected ZVM Site Name"),
        effective_row.get("Protected Site Name"),
        default_vpg_settings.get("protected_site") if default_vpg_settings else None,
    )
    effective_recovery_site = first_value(
        effective_row.get("Recovery ZVM Site Name"),
        effective_row.get("Recovery Site Name"),
        default_vpg_settings.get("recovery_site") if default_vpg_settings else None,
    )
    recovery_defaults = build_recovery_site_defaults(
        recovery_zvm_sites or [],
        default_vpg_settings,
    ).get(effective_recovery_site, {})

    set_default(effective_row, "Protected ZVM Site Name", effective_protected_site)
    set_default(effective_row, "Recovery ZVM Site Name", effective_recovery_site)
    for label_number in range(1, 6):
        field_name = f"Label {label_number}"
        set_default(
            effective_row,
            field_name,
            recovery_defaults.get(field_name),
        )
    set_default(effective_row, "Recovery Host Name", recovery_defaults.get("Recovery Host Name"))
    set_default(
        effective_row,
        "Recovery Datastore Name",
        recovery_defaults.get("Recovery Datastore Name"),
    )
    set_default(
        effective_row,
        "Journal History Value",
        recovery_defaults.get("Journal History Value"),
    )
    set_default(
        effective_row,
        "Journal History Unit",
        recovery_defaults.get("Journal History Unit"),
    )
    set_default(
        effective_row,
        "Target RPO Alert Value",
        recovery_defaults.get("Target RPO Alert Value"),
    )
    set_default(
        effective_row,
        "Target RPO Alert Unit",
        recovery_defaults.get("Target RPO Alert Unit"),
    )
    set_default(effective_row, "Test Reminder", recovery_defaults.get("Test Reminder"))
    set_default(
        effective_row,
        "Journal Datastore Name",
        recovery_defaults.get("Journal Datastore Name"),
        effective_row.get("Recovery Datastore Name"),
    )
    set_default(
        effective_row,
        "Journal Size Hard Limit Value",
        recovery_defaults.get("Journal Size Hard Limit Value"),
    )
    set_default(
        effective_row,
        "Journal Size Hard Limit Unit",
        recovery_defaults.get("Journal Size Hard Limit Unit"),
    )
    set_default(
        effective_row,
        "Journal Size Warning Threshold Value",
        recovery_defaults.get("Journal Size Warning Threshold Value"),
    )
    set_default(
        effective_row,
        "Journal Size Warning Threshold Unit",
        recovery_defaults.get("Journal Size Warning Threshold Unit"),
    )
    set_default(
        effective_row,
        "Scratch Journal Datastore Name",
        recovery_defaults.get("Scratch Journal Datastore Name"),
        effective_row.get("Recovery Datastore Name"),
    )
    set_default(
        effective_row,
        "Scratch Journal Size Hard Limit Value",
        recovery_defaults.get("Scratch Journal Size Hard Limit Value"),
    )
    set_default(
        effective_row,
        "Scratch Journal Size Hard Limit Unit",
        recovery_defaults.get("Scratch Journal Size Hard Limit Unit"),
    )
    set_default(
        effective_row,
        "Scratch Journal Size Warning Threshold Value",
        recovery_defaults.get("Scratch Journal Size Warning Threshold Value"),
    )
    set_default(
        effective_row,
        "Scratch Journal Size Warning Threshold Unit",
        recovery_defaults.get("Scratch Journal Size Warning Threshold Unit"),
    )
    set_default(
        effective_row,
        "Failover Live / Move - Network Name",
        recovery_defaults.get("Failover Live / Move Network Name"),
    )
    set_default(
        effective_row,
        "Failover Test - Network Name",
        effective_row.get("Failover Test Network Name"),
        recovery_defaults.get("Failover Test Network Name"),
    )
    set_default(
        effective_row,
        "Failover Live / Move - Create new MAC address",
        recovery_defaults.get("Failover Live / Move - Create new MAC address"),
        default_vpg_settings.get("failover_live_move_create_new_mac_address")
        if default_vpg_settings
        else None,
    )
    set_default(
        effective_row,
        "Failover Live / Move - Change vNIC IP Config",
        recovery_defaults.get("Failover Live / Move - Change vNIC IP Config"),
        default_vpg_settings.get("failover_live_move_change_vnic_ip_config")
        if default_vpg_settings
        else None,
    )
    set_default(
        effective_row,
        "Failover Live / Move - IP Address",
        recovery_defaults.get("Failover Live / Move - IP Address"),
        recovery_defaults.get("Failover Live / Move IP Address"),
    )
    set_default(
        effective_row,
        "Failover Live / Move - Subnet Mask",
        recovery_defaults.get("Failover Live / Move - Subnet Mask"),
        default_vpg_settings.get("failover_live_move_subnet_mask")
        if default_vpg_settings
        else None,
    )
    set_default(
        effective_row,
        "Failover Live / Move - Default Gateway",
        recovery_defaults.get("Failover Live / Move - Default Gateway"),
        default_vpg_settings.get("failover_live_move_default_gateway")
        if default_vpg_settings
        else None,
    )
    set_default(
        effective_row,
        "Failover Live / Move - Preferred DNS Server",
        recovery_defaults.get("Failover Live / Move - Preferred DNS Server"),
        default_vpg_settings.get("failover_live_move_preferred_dns_server")
        if default_vpg_settings
        else None,
    )
    set_default(
        effective_row,
        "Failover Live / Move - Alternate DNS Server",
        recovery_defaults.get("Failover Live / Move - Alternate DNS Server"),
        default_vpg_settings.get("failover_live_move_alternate_dns_server")
        if default_vpg_settings
        else None,
    )
    set_default(
        effective_row,
        "Failover Live / Move - DNS Suffix",
        recovery_defaults.get("Failover Live / Move - DNS Suffix"),
        default_vpg_settings.get("failover_live_move_dns_suffix")
        if default_vpg_settings
        else None,
    )
    set_default(
        effective_row,
        "Failover Test - Create new MAC address",
        recovery_defaults.get("Failover Test - Create new MAC address"),
        default_vpg_settings.get("failover_test_create_new_mac_address")
        if default_vpg_settings
        else None,
    )
    set_default(
        effective_row,
        "Failover Test - Change vNIC IP Config",
        recovery_defaults.get("Failover Test - Change vNIC IP Config"),
        default_vpg_settings.get("failover_test_change_vnic_ip_config")
        if default_vpg_settings
        else None,
    )
    set_default(
        effective_row,
        "Failover Test - IP Address",
        recovery_defaults.get("Failover Test - IP Address"),
        recovery_defaults.get("Failover Test IP Address"),
    )
    set_default(
        effective_row,
        "Failover Test - Subnet Mask",
        recovery_defaults.get("Failover Test - Subnet Mask"),
        default_vpg_settings.get("failover_test_subnet_mask")
        if default_vpg_settings
        else None,
    )
    set_default(
        effective_row,
        "Failover Test - Default Gateway",
        recovery_defaults.get("Failover Test - Default Gateway"),
        default_vpg_settings.get("failover_test_default_gateway")
        if default_vpg_settings
        else None,
    )
    set_default(
        effective_row,
        "Failover Test - Preferred DNS Server",
        recovery_defaults.get("Failover Test - Preferred DNS Server"),
        default_vpg_settings.get("failover_test_preferred_dns_server")
        if default_vpg_settings
        else None,
    )
    set_default(
        effective_row,
        "Failover Test - Alternate DNS Server",
        recovery_defaults.get("Failover Test - Alternate DNS Server"),
        default_vpg_settings.get("failover_test_alternate_dns_server")
        if default_vpg_settings
        else None,
    )
    set_default(
        effective_row,
        "Failover Test - DNS Suffix",
        recovery_defaults.get("Failover Test - DNS Suffix"),
        default_vpg_settings.get("failover_test_dns_suffix")
        if default_vpg_settings
        else None,
    )

    return effective_row


def build_recovery_site_defaults(
    recovery_zvm_sites: list[dict],
    default_vpg_settings: dict | None,
) -> dict:
    defaults = {}
    for row in recovery_zvm_sites:
        effective_row = apply_default_recovery_zvm_site_name(row, default_vpg_settings)
        site_name = normalize_blank(effective_row.get("Recovery ZVM Site Name"))
        if site_name is not None:
            defaults[site_name] = effective_row

    return defaults


def set_default(row: dict, field_name: str, *defaults) -> None:
    row[field_name] = first_value(row.get(field_name), *defaults)


def first_value(*values):
    for value in values:
        normalized_value = normalize_blank(value)
        if normalized_value is not None:
            return normalized_value

    return None


def validate_unique_vpg_names(data: list[dict]) -> None:
    seen_rows = {}
    messages = []

    for row in data:
        vpg_name = row.get("VPG Name")
        if vpg_name is None:
            continue

        if vpg_name in seen_rows:
            for duplicate_row in (seen_rows[vpg_name], row):
                messages.append(format_workbook_error(
                    duplicate_row,
                    "VPG Name",
                    vpg_name,
                    "VPG Name must be unique.",
                ))
            continue

        seen_rows[vpg_name] = row

    if messages:
        raise WorkbookValidationError(messages)
