from typing import Any

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
    JournalSizeUnit,
    normalize_blank,
    validate_journal_size,
    validate_journal_size_threshold,
    validate_site_scoped_value,
)
from validation.vpgs import validate_config_value


class VMReplication(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    vpg_name: str | None = Field(
        default=None,
        validation_alias="VPG Name",
    )
    vm_name: str | None = Field(
        default=None,
        validation_alias="VM Name",
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
    boot_order_group_name: str | None = Field(
        default=None,
        validation_alias="Boot Order Group Name",
    )
    recovery_host_name: str | None = Field(
        default=None,
        validation_alias="Recovery Host Name",
    )
    recovery_datastore_name: str | None = Field(
        default=None,
        validation_alias="Recovery Datastore Name",
    )
    recovery_folder_name: str | None = Field(
        default=None,
        validation_alias="Recovery Folder Name",
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

    @field_validator("boot_order_group_name")
    @classmethod
    def validate_boot_order_group_name(cls, value, info: ValidationInfo):
        if value is None:
            return value

        vpg_name = info.data.get("vpg_name")
        meta_group_name = config.vpg_boot_order_meta_group_names_by_vpg_name.get(
            vpg_name,
        )
        if meta_group_name is None:
            raise ValueError(
                f"Boot Order Group Name '{value}' cannot be validated because "
                f"VPG '{vpg_name}' does not have a Boot Order Meta Group Name."
            )

        allowed_values = config.boot_order_groups_by_meta_group.get(
            meta_group_name,
            [],
        )
        if value not in allowed_values:
            raise ValueError(
                f"Boot Order Group Name '{value}' is not valid for VPG "
                f"'{vpg_name}' with Boot Order Meta Group Name "
                f"'{meta_group_name}'. Allowed values: {allowed_values}"
            )

        return value

    @field_validator("recovery_host_name")
    @classmethod
    def validate_recovery_host_name(cls, value, info: ValidationInfo):
        if value is None:
            return value

        return validate_site_scoped_value(
            value,
            get_vpg_recovery_site_name(info.data.get("vpg_name")),
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
            get_vpg_recovery_site_name(info.data.get("vpg_name")),
            config.recovery_datastore_names_by_site,
            "Recovery Datastore Name",
        )

    @field_validator("recovery_folder_name")
    @classmethod
    def validate_recovery_folder_name(cls, value, info: ValidationInfo):
        if value is None:
            return value

        return validate_site_scoped_value(
            value,
            get_vpg_recovery_site_name(info.data.get("vpg_name")),
            config.recovery_folder_names_by_site,
            "Recovery Folder Name",
        )

    @model_validator(mode="after")
    def validate_value_unit_pairs(self):
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


def validate_vm_replication_row(data: dict) -> VMReplication:
    return VMReplication(**data)


def validate_vm_replication(data: list[dict]) -> list[VMReplication]:
    validated_rows = validate_model_rows(VMReplication, data)
    validate_vm_replication_vpg_limits(data)
    return validated_rows


def get_vpg_recovery_site_name(vpg_name: str | None) -> str | None:
    return config.vpg_recovery_site_names_by_vpg_name.get(vpg_name)


def validate_vm_replication_vpg_limits(data: list[dict]) -> None:
    grouped_rows = {}

    for row in data:
        vpg_name = normalize_blank(row.get("VPG Name"))
        vm_name = normalize_blank(row.get("VM Name"))
        if vpg_name is None or vm_name is None:
            continue

        protected_site = config.vpg_protected_site_names_by_vpg_name.get(vpg_name)
        recovery_site = config.vpg_recovery_site_names_by_vpg_name.get(vpg_name)
        if protected_site is None or recovery_site is None:
            continue

        key = (protected_site, vm_name)
        grouped_rows.setdefault(key, []).append({
            "row": row,
            "vpg_name": vpg_name,
            "recovery_site": recovery_site,
        })

    messages = []

    for (protected_site, vm_name), rows in grouped_rows.items():
        if len(rows) > 3:
            for item in rows:
                messages.append(format_workbook_error(
                    item["row"],
                    "VM Name",
                    vm_name,
                    (
                        f"VM Name '{vm_name}' with Protected ZVM Site Name "
                        f"'{protected_site}' can be part of at most 3 VPGs."
                    ),
                ))

        recovery_site_rows = {}
        for item in rows:
            recovery_site_rows.setdefault(item["recovery_site"], []).append(item)

        for recovery_site, duplicate_rows in recovery_site_rows.items():
            if len(duplicate_rows) <= 1:
                continue

            for item in duplicate_rows:
                messages.append(format_workbook_error(
                    item["row"],
                    "VPG Name",
                    item["vpg_name"],
                    (
                        f"VM Name '{vm_name}' with Protected ZVM Site Name "
                        f"'{protected_site}' can only use each Recovery ZVM "
                        f"Site Name once. Recovery ZVM Site Name "
                        f"'{recovery_site}' is duplicated."
                    ),
                ))

    if messages:
        raise WorkbookValidationError(messages)
