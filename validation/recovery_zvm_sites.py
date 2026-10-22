from typing import Any, Literal

from pydantic import (
    AliasChoices,
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


VPGType = Literal[
    "Remote DR and Continuous Backup",
    "Cyber Recovery",
    "Local Continuous Backup",
    "Data Mobility and Migration",
]

Priority = Literal["Low", "Medium", "High"]
JournalHistoryUnit = Literal["Days", "Hours"]
TargetRPOAlertUnit = Literal["Seconds", "Minutes", "Hours"]
TestReminder = Literal["None", "3 Months", "6 Months", "9 Months", "12 Months"]
JournalSizeUnit = Literal["GiB", "%", "Unlimited"]
YesNo = Literal["Yes", "No"]
DiskProvisioningOverride = Literal["As-is", "As-Is", "Thin", "Thick"]
VnicIpConfigChange = Literal["No", "Yes, DHCP", "Yes, Static"]
RECOVERY_ZVM_SITE_NETWORK_FIELDS = (
    "Failover Live / Move - Network Name",
    "Failover Test - Network Name",
    "Failover Live / Move - Create new MAC address",
    "Failover Live / Move - Change vNIC IP Config",
    "Failover Live / Move - Subnet Mask",
    "Failover Live / Move - Default Gateway",
    "Failover Live / Move - Preferred DNS Server",
    "Failover Live / Move - Alternate DNS Server",
    "Failover Live / Move - DNS Suffix",
    "Failover Test - Create new MAC address",
    "Failover Test - Change vNIC IP Config",
    "Failover Test - Subnet Mask",
    "Failover Test - Default Gateway",
    "Failover Test - Preferred DNS Server",
    "Failover Test - Alternate DNS Server",
    "Failover Test - DNS Suffix",
)


def normalize_blank(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, float) and value != value:
        return None

    if isinstance(value, str) and value.strip() == "":
        return None

    return value


class RecoveryZVMSite(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    recovery_zvm_site_name: str = Field(
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
    recovery_host_name: str | None = Field(
        default=None,
        validation_alias="Recovery Host Name",
    )
    recovery_datastore_name: str | None = Field(
        default=None,
        validation_alias="Recovery Datastore Name",
    )
    journal_history_value: int | None = Field(
        default=None,
        validation_alias="Journal History Value",
    )
    journal_history_unit: JournalHistoryUnit | None = Field(
        default=None,
        validation_alias="Journal History Unit",
    )
    target_rpo_alert_value: int | None = Field(
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
    journal_size_hard_limit_value: Any | None = Field(
        default=None,
        validation_alias="Journal Size Hard Limit Value",
    )
    journal_size_hard_limit_unit: JournalSizeUnit | None = Field(
        default=None,
        validation_alias="Journal Size Hard Limit Unit",
    )
    journal_size_warning_threshold_value: Any | None = Field(
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
    scratch_journal_size_hard_limit_value: Any | None = Field(
        default=None,
        validation_alias="Scratch Journal Size Hard Limit Value",
    )
    scratch_journal_size_hard_limit_unit: JournalSizeUnit | None = Field(
        default=None,
        validation_alias="Scratch Journal Size Hard Limit Unit",
    )
    scratch_journal_size_warning_threshold_value: Any | None = Field(
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
        validation_alias=AliasChoices(
            "Failover Live / Move - Network Name",
            "Failover Live / Move Network Name",
        ),
    )
    failover_test_network_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "Failover Test - Network Name",
            "Failover Test Network Name",
        ),
    )
    recovery_folder_name: str | None = Field(
        default=None,
        validation_alias="Recovery Folder Name",
    )
    pre_recovery_script_name: Any | None = Field(
        default=None,
        validation_alias="Pre-Recovery Script Name",
    )
    pre_recovery_script_parameters: Any | None = Field(
        default=None,
        validation_alias="Pre-Recovery Script Parameters",
    )
    pre_recovery_script_execution_timeout_seconds: Any | None = Field(
        default=None,
        validation_alias="Pre-Recovery Script Execution Timeout (Seconds)",
    )
    post_recovery_script_name: Any | None = Field(
        default=None,
        validation_alias="Post-Recovery Script Name",
    )
    post_recovery_script_parameters: Any | None = Field(
        default=None,
        validation_alias="Post-Recovery Script Parameters",
    )
    post_recovery_script_execution_timeout_seconds: Any | None = Field(
        default=None,
        validation_alias="Post-Recovery Script Execution Timeout (Seconds)",
    )
    failover_live_move_create_new_mac_address: YesNo | None = Field(
        default=None,
        validation_alias="Failover Live / Move - Create new MAC address",
    )
    failover_live_move_change_vnic_ip_config: VnicIpConfigChange | None = Field(
        default=None,
        validation_alias="Failover Live / Move - Change vNIC IP Config",
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
    failover_test_create_new_mac_address: YesNo | None = Field(
        default=None,
        validation_alias="Failover Test - Create new MAC address",
    )
    failover_test_change_vnic_ip_config: VnicIpConfigChange | None = Field(
        default=None,
        validation_alias="Failover Test - Change vNIC IP Config",
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
        return validate_config_value(
            value,
            config.application_names,
            "Label 3",
        )

    @field_validator("label_4")
    @classmethod
    def validate_label_4(cls, value):
        return validate_config_value(
            value,
            config.application_environments,
            "Label 4",
        )

    @field_validator("label_5")
    @classmethod
    def validate_label_5(cls, value):
        return validate_config_value(value, config.data_types, "Label 5")

    @field_validator("recovery_zvm_site_name")
    @classmethod
    def validate_recovery_zvm_site_name(cls, value):
        if value not in config.recovery_site_names:
            raise ValueError(
                f"Recovery ZVM Site Name '{value}' is not valid. "
                f"Allowed values: {config.recovery_site_names}"
            )

        return value

    @field_validator("recovery_host_name")
    @classmethod
    def validate_recovery_host_name(cls, value, info: ValidationInfo):
        if value is None or "recovery_zvm_site_name" not in info.data:
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
        if value is None or "recovery_zvm_site_name" not in info.data:
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
        if value is None or "recovery_zvm_site_name" not in info.data:
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
        if value is None or "recovery_zvm_site_name" not in info.data:
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
            300,
            6000,
            "Recovery Script Execution Timeout (Seconds)",
            "",
        )
        return value

    @model_validator(mode="after")
    def validate_value_unit_pairs(self):
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

        return self


def validate_recovery_zvm_site(
    data: dict,
    default_vpg_settings: dict | None = None,
) -> RecoveryZVMSite:
    return RecoveryZVMSite(
        **apply_default_recovery_zvm_site_name(data, default_vpg_settings),
    )


def validate_recovery_zvm_sites(
    data: list[dict],
    default_vpg_settings: dict | None = None,
) -> list[RecoveryZVMSite]:
    effective_data = [
        apply_default_recovery_zvm_site_name(row, default_vpg_settings)
        for row in data
    ]
    messages = []
    validated_rows = []

    try:
        validated_rows = validate_model_rows(RecoveryZVMSite, effective_data)
    except WorkbookValidationError as error:
        messages.extend(error.messages)

    try:
        validate_unique_recovery_zvm_site_names(effective_data)
    except WorkbookValidationError as error:
        messages.extend(error.messages)

    try:
        validate_local_continuous_backup_network_fields_empty(data)
    except WorkbookValidationError as error:
        messages.extend(error.messages)

    if messages:
        raise WorkbookValidationError(messages)

    return validated_rows


def apply_default_recovery_zvm_site_name(
    row: dict,
    default_vpg_settings: dict | None,
) -> dict:
    effective_row = dict(row)
    if normalize_blank(effective_row.get("Recovery ZVM Site Name")) is not None:
        return effective_row

    recovery_site_name = normalize_blank(effective_row.get("Recovery Site Name"))
    if recovery_site_name is None and default_vpg_settings:
        recovery_site_name = normalize_blank(default_vpg_settings.get("recovery_site"))

    if recovery_site_name is not None:
        effective_row["Recovery ZVM Site Name"] = recovery_site_name

    return effective_row


def validate_site_scoped_value(
    value,
    site_name: str | None,
    values_by_site: dict,
    field_name: str,
):
    if site_name is None:
        raise ValueError(
            f"{field_name} '{value}' cannot be validated because "
            "Recovery ZVM Site Name is not valid."
        )

    allowed_values = values_by_site.get(site_name, [])
    if value not in allowed_values:
        raise ValueError(
            f"{field_name} '{value}' is not valid for Recovery ZVM Site "
            f"Name '{site_name}'. Allowed values: {allowed_values}"
        )

    return value


def validate_config_value(value, allowed_values: list, field_name: str):
    if value is None:
        return value

    if value not in allowed_values:
        raise ValueError(
            f"{field_name} '{value}' is not valid. "
            f"Allowed values: {allowed_values}"
        )

    return value


def validate_journal_history(value, unit) -> None:
    if value is None and unit is None:
        return

    if value is None or unit is None:
        raise ValueError("Journal History Value and Unit must be provided together")

    if unit == "Days":
        validate_range(value, 1, 30, "Journal History Value", "when Unit is Days")

    if unit == "Hours":
        validate_range(value, 1, 720, "Journal History Value", "when Unit is Hours")


def validate_target_rpo_alert(value, unit) -> None:
    if value is None and unit is None:
        return

    if value is None or unit is None:
        raise ValueError("Target RPO Alert Value and Unit must be provided together")

    limits = {
        "Seconds": (1, 2592000),
        "Minutes": (1, 43200),
        "Hours": (1, 720),
    }
    minimum, maximum = limits[unit]
    validate_range(
        value,
        minimum,
        maximum,
        "Target RPO Alert Value",
        f"when Unit is {unit}",
    )


def validate_journal_size(value, unit, field_name: str) -> None:
    if value is None and unit is None:
        return

    if unit is None:
        raise ValueError(f"{field_name} Unit must be provided when Value is set")

    if unit == "Unlimited":
        if value is not None:
            raise ValueError(f"{field_name} must be empty when Unit is Unlimited")

        return

    if value is None:
        raise ValueError(f"{field_name} is mandatory when Unit is {unit}")

    if unit == "GiB":
        validate_range(value, 10, 99999, field_name, "when Unit is GiB")

    if unit == "%":
        validate_range(value, 1, 1000, field_name, "when Unit is %")


def validate_journal_size_threshold(
    warning_value,
    warning_unit,
    hard_limit_value,
    hard_limit_unit,
    warning_field_name: str,
    hard_limit_field_name: str,
) -> None:
    if warning_value is None or hard_limit_value is None:
        return

    if warning_unit != hard_limit_unit:
        return

    if warning_value < hard_limit_value:
        return

    raise ValueError(
        f"{hard_limit_field_name} must be larger than {warning_field_name}"
    )


def validate_range(
    value,
    minimum: int,
    maximum: int,
    field_name: str,
    context: str,
) -> None:
    if minimum <= value <= maximum:
        return

    suffix = f" {context}" if context else ""
    raise ValueError(
        f"{field_name} '{value:g}' is not valid{suffix}. "
        f"Allowed range: {minimum}-{maximum}"
    )


def validate_unique_recovery_zvm_site_names(data: list[dict]) -> None:
    seen_rows = {}
    messages = []

    for row in data:
        site_name = row.get("Recovery ZVM Site Name")
        if site_name is None:
            continue

        if site_name in seen_rows:
            for duplicate_row in (seen_rows[site_name], row):
                messages.append(format_workbook_error(
                    duplicate_row,
                    "Recovery ZVM Site Name",
                    site_name,
                    "Recovery ZVM Site Name must be unique.",
                ))
            continue

        seen_rows[site_name] = row

    if messages:
        raise WorkbookValidationError(messages)


def validate_local_continuous_backup_network_fields_empty(data: list[dict]) -> None:
    messages = []

    for row in data:
        if normalize_blank(row.get("VPG Type")) != "Local Continuous Backup":
            continue

        for field_name in RECOVERY_ZVM_SITE_NETWORK_FIELDS:
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
