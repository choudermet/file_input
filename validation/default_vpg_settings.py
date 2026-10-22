from datetime import time
from typing import Any, Literal
from pydantic import BaseModel, field_validator, model_validator
import config


JournalSizeUnit = Literal["GiB", "%", "Unlimited"]
TestReminder = Literal["None", "3 Months", "6 Months", "9 Months", "12 Months"]
DiskProvisioningOverride = Literal["As-is", "Thin", "Thick"]
VolumeSyncType = Literal[
    "Continuous Sync",
    "Initial Sync Only",
    "No Sync (Empty Disk)",
]
YesNo = Literal["Yes", "No"]
VnicIpConfigChange = Literal["No", "Yes, DHCP", "Yes, Static"]


class JournalHistoryValueUnit(BaseModel):
    value: int
    unit: Literal["Hours", "Days"]

    @model_validator(mode="after")
    def validate_range(self):
        if self.unit == "Days":
            validate_range(self.value, 1, 30, "Journal History Value", "when Unit is Days")

        if self.unit == "Hours":
            validate_range(self.value, 1, 720, "Journal History Value", "when Unit is Hours")

        return self


class TargetRPOAlertValueUnit(BaseModel):
    value: int
    unit: Literal["Seconds", "Minutes", "Hours"]

    @model_validator(mode="after")
    def validate_range(self):
        limits = {
            "Seconds": (1, 2592000),
            "Minutes": (1, 43200),
            "Hours": (1, 720),
        }
        minimum, maximum = limits[self.unit]
        validate_range(
            self.value,
            minimum,
            maximum,
            "Target RPO Alert Value",
            f"when Unit is {self.unit}",
        )

        return self


class JournalSizeValueUnit(BaseModel):
    value: float | None
    unit: JournalSizeUnit

    @model_validator(mode="after")
    def validate_value_for_unit(self):
        if self.unit == "Unlimited":
            if self.value is not None:
                raise ValueError("Value must be empty when Unit is Unlimited")

            return self

        if self.value is None:
            raise ValueError(f"Value is mandatory when Unit is {self.unit}")

        if self.unit == "GiB":
            validate_range(self.value, 10, 99999, "Journal Size Value", "when Unit is GiB")

        if self.unit == "%":
            validate_range(self.value, 1, 1000, "Journal Size Value", "when Unit is %")

        return self


class DefaultVPGSettings(BaseModel):
    protected_site: str
    recovery_site: str

    vpg_type: Literal[
        "Remote DR and Continuous Backup",
        "Cyber Recovery",
        "Local Continuous Backup",
        "Data Mobility and Migration",
    ]

    priority: Literal["Low", "Medium", "High"]

    journal_history: JournalHistoryValueUnit
    target_rpo_alert: TargetRPOAlertValueUnit

    test_reminder: TestReminder

    journal_size_hard_limit: JournalSizeValueUnit
    journal_size_warning: JournalSizeValueUnit
    scratch_journal_size_hard_limit: JournalSizeValueUnit
    scratch_journal_size_warning: JournalSizeValueUnit

    wan_compression: YesNo
    disk_provisioning_override: DiskProvisioningOverride
    recovery_folder_name: str
    volume_sync_type: VolumeSyncType

    pre_recovery_script_execution_timeout_seconds: int
    post_recovery_script_execution_timeout_seconds: int

    failover_live_move_create_new_mac_address: YesNo
    failover_test_create_new_mac_address: YesNo
    failover_live_move_change_vnic_ip_config: VnicIpConfigChange
    failover_test_change_vnic_ip_config: VnicIpConfigChange
    failover_live_move_subnet_mask: Any
    failover_test_subnet_mask: Any
    failover_live_move_default_gateway: Any
    failover_test_default_gateway: Any
    failover_live_move_preferred_dns_server: Any
    failover_test_preferred_dns_server: Any
    failover_live_move_alternate_dns_server: Any
    failover_test_alternate_dns_server: Any
    failover_live_move_dns_suffix: Any | None = None
    failover_test_dns_suffix: Any | None = None

    extended_journal_run_at: time
    extended_journal_retry_count: int
    extended_journal_wait_between_retries_minutes: int

    @field_validator("protected_site")
    @classmethod
    def validate_protected_site(cls, value):
        if value not in config.protected_site_names:
            raise ValueError(
                f"Protected site '{value}' is not valid. "
                f"Allowed values: {config.protected_site_names}"
            )
        return value

    @field_validator("recovery_site")
    @classmethod
    def validate_recovery_site(cls, value):
        if value not in config.recovery_site_names:
            raise ValueError(
                f"Recovery site '{value}' is not valid. "
                f"Allowed values: {config.recovery_site_names}"
            )
        return value

    @field_validator("recovery_folder_name")
    @classmethod
    def validate_recovery_folder_name(cls, value):
        if value not in config.recovery_folder_names:
            raise ValueError(
                f"Recovery Folder Name '{value}' is not valid. "
                f"Allowed values: {config.recovery_folder_names}"
            )

        return value

    @field_validator(
        "failover_live_move_subnet_mask",
        "failover_test_subnet_mask",
        "failover_live_move_default_gateway",
        "failover_test_default_gateway",
        "failover_live_move_preferred_dns_server",
        "failover_test_preferred_dns_server",
        "failover_live_move_alternate_dns_server",
        "failover_test_alternate_dns_server",
    )
    @classmethod
    def validate_mandatory_value(cls, value):
        if value is None:
            raise ValueError("This value is mandatory")

        return value

    @field_validator(
        "pre_recovery_script_execution_timeout_seconds",
        "post_recovery_script_execution_timeout_seconds",
    )
    @classmethod
    def validate_script_timeout(cls, value):
        validate_range(
            value,
            300,
            6000,
            "Recovery Script Execution Timeout (Seconds)",
            "",
        )
        return value

    @field_validator("extended_journal_retry_count")
    @classmethod
    def validate_extended_journal_retry_count(cls, value):
        validate_range(value, 0, 10, "Number of automatic retry commands", "")
        return value

    @field_validator("extended_journal_wait_between_retries_minutes")
    @classmethod
    def validate_extended_journal_wait_between_retries_minutes(cls, value):
        validate_range(value, 10, 60, "Wait time between retries (minutes)", "")
        return value

    @model_validator(mode="after")
    def validate_journal_sizes(self):
        if both_have_values(
            self.journal_size_warning,
            self.journal_size_hard_limit,
        ) and self.journal_size_warning.value > self.journal_size_hard_limit.value:
            raise ValueError(
                "Journal Size Warning Threshold cannot be greater than "
                "Journal Size Hard Limit Value"
            )

        if both_have_values(
            self.scratch_journal_size_warning,
            self.scratch_journal_size_hard_limit,
        ) and (
            self.scratch_journal_size_warning.value
            > self.scratch_journal_size_hard_limit.value
        ):
            raise ValueError(
                "Scratch Journal Size Warning Threshold cannot be greater than "
                "Scratch Journal Size Hard Limit Value"
            )

        return self


def validate_default_vpg_settings(data: dict) -> DefaultVPGSettings:
    return DefaultVPGSettings(**data)


def validate_range(
    value: int | float,
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


def both_have_values(
    first: JournalSizeValueUnit,
    second: JournalSizeValueUnit,
) -> bool:
    return first.value is not None and second.value is not None
