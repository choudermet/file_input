from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

import config
from validation.error_formatting import (
    WorkbookValidationError,
    format_workbook_error,
    validate_model_rows,
)
from validation.recovery_zvm_sites import DiskProvisioningOverride, normalize_blank
from validation.vpgs import validate_config_value


VolumeSyncType = Literal[
    "Continuous Sync",
    "Initial Sync Only",
    "No Sync (Empty Disk)",
]
Provisioning = Literal["Thin", "Thick"]


class VMStorage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    vpg_name: str | None = Field(
        default=None,
        validation_alias="VPG Name",
    )
    vm_name: str | None = Field(
        default=None,
        validation_alias="VM Name",
    )
    protected_volume_location: str | None = Field(
        default=None,
        validation_alias="Protected Volume Location",
    )
    scsi_id: str | None = Field(
        default=None,
        validation_alias="SCSI ID",
    )
    size_gib: Any | None = Field(
        default=None,
        validation_alias="Size (GiB)",
    )
    recovery_volume_location: Any | None = Field(
        default=None,
        validation_alias="Recovery Volume Location",
    )
    recovery_raw_device_name: Any | None = Field(
        default=None,
        validation_alias="Recovery Raw Device Name",
    )
    disk_provisioning_override: DiskProvisioningOverride | None = Field(
        default=None,
        validation_alias="Disk Provisioning Override",
    )
    provisioning: Provisioning | None = Field(
        default=None,
        validation_alias="Provisioning",
    )
    volume_sync_type: VolumeSyncType | None = Field(
        default=None,
        validation_alias="Volume Sync Type",
    )

    @field_validator("*", mode="before")
    @classmethod
    def convert_blank_values_to_none(cls, value):
        return normalize_blank(value)

    @field_validator("vpg_name")
    @classmethod
    def validate_vpg_name(cls, value):
        return validate_config_value(value, config.vpg_names, "VPG Name")

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

    @field_validator("protected_volume_location")
    @classmethod
    def validate_protected_volume_location(cls, value, info: ValidationInfo):
        if value is None:
            return value

        vm_name = info.data.get("vm_name")
        vpg_name = info.data.get("vpg_name")
        protected_site_name = config.vpg_protected_site_names_by_vpg_name.get(vpg_name)
        if vm_name is None:
            raise ValueError(
                f"Protected Volume Location '{value}' cannot be validated "
                "because VM Name is not valid."
            )

        allowed_values = config.protected_volume_locations_by_site_and_vm_name.get(
            (protected_site_name, vm_name),
            [],
        )

        if value not in allowed_values:
            raise ValueError(
                f"Protected Volume Location '{value}' is not valid for VPG "
                f"'{vpg_name}', Protected ZVM Site Name '{protected_site_name}', "
                f"and VM '{vm_name}'. Allowed values: {allowed_values}"
            )

        return value


def validate_vm_storage_row(data: dict) -> VMStorage:
    return VMStorage(**data)


def validate_vm_storage(data: list[dict]) -> list[VMStorage]:
    validated_rows = validate_model_rows(VMStorage, data)
    validate_unique_vm_storage_rows(data)
    return validated_rows


def validate_unique_vm_storage_rows(data: list[dict]) -> None:
    seen_rows = {}
    messages = []

    for row in data:
        key = (
            row.get("VPG Name"),
            row.get("VM Name"),
            row.get("Protected Volume Location"),
        )

        if any(value is None for value in key):
            continue

        if key in seen_rows:
            for duplicate_row in (seen_rows[key], row):
                messages.append(format_workbook_error(
                    duplicate_row,
                    "Protected Volume Location",
                    row.get("Protected Volume Location"),
                    (
                        "The combination of VPG Name, VM Name, and "
                        "Protected Volume Location must be unique."
                    ),
                ))
            continue

        seen_rows[key] = row

    if messages:
        raise WorkbookValidationError(messages)
