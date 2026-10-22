from collections import Counter
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

import config
from validation.recovery_zvm_sites import normalize_blank
from validation.error_formatting import WorkbookValidationError, validate_model_rows
from validation.vpgs import validate_config_value


Provisioning = Literal["Thin", "Thick", "EagerZeroedThick"]


class ProtectedVM(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    protected_zvm_site_name: str = Field(validation_alias="Protected ZVM Site Name")
    vm_name: str = Field(validation_alias="VM Name")
    cpu_count: int = Field(ge=1, le=256, validation_alias="CPU Count")
    memory_gib: int = Field(ge=1, le=4096, validation_alias="Memory (GiB)")

    @field_validator("*", mode="before")
    @classmethod
    def convert_blank_values_to_none(cls, value):
        return normalize_blank(value)

    @field_validator("protected_zvm_site_name")
    @classmethod
    def validate_protected_zvm_site_name(cls, value):
        return validate_config_value(
            value,
            config.protected_site_names,
            "Protected ZVM Site Name",
        )


class ProtectedVMVolume(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    protected_zvm_site_name: str = Field(validation_alias="Protected ZVM Site Name")
    vm_name: str = Field(validation_alias="VM Name")
    volume_location: str = Field(validation_alias="Volume Location")
    scsi_id: str = Field(validation_alias="SCSI ID")
    provisioned_size_gib: int = Field(
        ge=1,
        le=65536,
        validation_alias="Provisioned Size (GiB)",
    )
    provisioning: Provisioning = Field(validation_alias="Provisioning")

    @field_validator("*", mode="before")
    @classmethod
    def convert_blank_values_to_none(cls, value):
        return normalize_blank(value)

    @field_validator("protected_zvm_site_name", mode="before")
    @classmethod
    def validate_protected_zvm_site_name(cls, value):
        value = normalize_blank(value)

        if value is None:
            raise ValueError(
                "Protected ZVM site name is mandatory"
                f"Valid values are: {config.protected_site_names}."
            )
        
        return validate_config_value(
            value,
            config.protected_site_names,
            "Protected ZVM Site Name",
        )

    @field_validator("vm_name")
    @classmethod
    def validate_vm_name_for_site(cls, value, info: ValidationInfo):
        if "protected_zvm_site_name" not in info.data:
            return value 
        
        protected_zvm_site_name = info.data.get("protected_zvm_site_name")
        allowed_values = [
            vm.get("VM Name")
            for vm in config.protected_vms
            if vm.get("Protected ZVM Site Name") == protected_zvm_site_name
            and vm.get("VM Name")
        ]

        if value not in allowed_values:
            raise ValueError(
                f"VM Name '{value}' is not valid for Protected ZVM Site "
                f"Name '{protected_zvm_site_name}'. Allowed values: {allowed_values}"
            )

        return value


class ProtectedVMNIC(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    protected_zvm_site_name: str = Field(validation_alias="Protected ZVM Site Name")
    vm_name: str = Field(validation_alias="VM Name")
    nic_name: str = Field(validation_alias="NIC Name")
    network_name: str = Field(validation_alias="Network Name")

    @field_validator("*", mode="before")
    @classmethod
    def convert_blank_values_to_none(cls, value):
        return normalize_blank(value)

    @field_validator("protected_zvm_site_name")
    @classmethod
    def validate_protected_zvm_site_name(cls, value):
        return validate_config_value(
            value,
            config.protected_site_names,
            "Protected ZVM Site Name",
        )

    @field_validator("vm_name")
    @classmethod
    def validate_vm_name_for_site(cls, value, info: ValidationInfo):
        protected_zvm_site_name = info.data.get("protected_zvm_site_name")
        allowed_values = [
            vm.get("VM Name")
            for vm in config.protected_vms
            if vm.get("Protected ZVM Site Name") == protected_zvm_site_name
            and vm.get("VM Name")
        ]

        if value not in allowed_values:
            raise ValueError(
                f"VM Name '{value}' is not valid for Protected ZVM Site "
                f"Name '{protected_zvm_site_name}'. Allowed values: {allowed_values}"
            )

        return value


class RecoveryHost(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    recovery_zvm_site_name: str = Field(validation_alias="Recovery ZVM Site Name")
    host_cluster_name: Any | None = Field(
        default=None,
        validation_alias="Host Cluster Name",
    )
    host_name: str = Field(validation_alias="Host Name")
    cpu_count: int = Field(ge=1, le=256, validation_alias="CPU Count")
    memory_gib: int = Field(ge=1, le=4096, validation_alias="Memory (GiB)")

    @field_validator("*", mode="before")
    @classmethod
    def convert_blank_values_to_none(cls, value):
        return normalize_blank(value)

    @field_validator("recovery_zvm_site_name")
    @classmethod
    def validate_recovery_zvm_site_name(cls, value):
        return validate_config_value(
            value,
            config.recovery_site_names,
            "Recovery ZVM Site Name",
        )


class RecoveryDatastore(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    recovery_zvm_site_name: str = Field(validation_alias="Recovery ZVM Site Name")
    datastore_cluster_name: Any | None = Field(
        default=None,
        validation_alias="Datastore Cluster Name",
    )
    datastore_name: str = Field(validation_alias="Datastore Name")
    size_gib: int = Field(ge=1, le=65536, validation_alias="Size (GiB)")

    @field_validator("*", mode="before")
    @classmethod
    def convert_blank_values_to_none(cls, value):
        return normalize_blank(value)

    @field_validator("recovery_zvm_site_name")
    @classmethod
    def validate_recovery_zvm_site_name(cls, value):
        return validate_config_value(
            value,
            config.recovery_site_names,
            "Recovery ZVM Site Name",
        )


class RecoveryFolder(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    recovery_zvm_site_name: str = Field(validation_alias="Recovery ZVM Site Name")
    folder_name: str = Field(validation_alias="Folder Name")

    @field_validator("*", mode="before")
    @classmethod
    def convert_blank_values_to_none(cls, value):
        return normalize_blank(value)

    @field_validator("recovery_zvm_site_name")
    @classmethod
    def validate_recovery_zvm_site_name(cls, value):
        return validate_config_value(
            value,
            config.recovery_site_names,
            "Recovery ZVM Site Name",
        )


class RecoveryNetwork(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    recovery_zvm_site_name: str = Field(validation_alias="Recovery ZVM Site Name")
    network_name: str = Field(validation_alias="Network Name")

    @field_validator("*", mode="before")
    @classmethod
    def convert_blank_values_to_none(cls, value):
        return normalize_blank(value)

    @field_validator("recovery_zvm_site_name")
    @classmethod
    def validate_recovery_zvm_site_name(cls, value):
        return validate_config_value(
            value,
            config.recovery_site_names,
            "Recovery ZVM Site Name",
        )


def validate_hypervisor_data(data: dict) -> dict:
    table_models = {
        "protected_vms": ProtectedVM,
        "protected_vm_volumes": ProtectedVMVolume,
        "protected_vm_nics": ProtectedVMNIC,
        "recovery_hosts": RecoveryHost,
        "recovery_datastores": RecoveryDatastore,
        "recovery_folders": RecoveryFolder,
        "recovery_networks": RecoveryNetwork,
    }
    validated_data = {}
    messages = []

    for table_key, model in table_models.items():
        try:
            validated_data[table_key] = validate_model_rows(model, data[table_key])
        except WorkbookValidationError as error:
            messages.extend(error.messages)
            validated_data[table_key] = []

    if messages:
        raise WorkbookValidationError(messages)

    validate_unique_combinations(data)
    return validated_data


def validate_unique_combinations(data: dict) -> None:
    check_unique(
        data["protected_vms"],
        ("Protected ZVM Site Name", "VM Name"),
    )
    check_unique(
        data["protected_vm_volumes"],
        ("Protected ZVM Site Name", "VM Name", "Volume Location"),
    )
    check_unique(
        data["protected_vm_nics"],
        ("Protected ZVM Site Name", "VM Name", "NIC Name"),
    )
    check_unique(
        data["recovery_hosts"],
        ("Recovery ZVM Site Name", "Host Cluster Name", "Host Name"),
    )
    check_unique(
        data["recovery_datastores"],
        ("Recovery ZVM Site Name", "Datastore Cluster Name", "Datastore Name"),
    )
    check_unique(
        data["recovery_folders"],
        ("Recovery ZVM Site Name", "Folder Name"),
    )
    check_unique(
        data["recovery_networks"],
        ("Recovery ZVM Site Name", "Network Name"),
    )


def check_unique(rows: list[dict], fields: tuple[str, ...]) -> None:
    keys = [
        tuple(row.get(field) for field in fields)
        for row in rows
        if all(row.get(field) is not None for field in fields)
    ]
    duplicate_keys = [
        key
        for key, count in Counter(keys).items()
        if count > 1
    ]

    if not duplicate_keys:
        return

    field_names = ", ".join(fields)
    duplicate_values = "; ".join(str(key) for key in duplicate_keys)
    raise ValueError(
        f"Duplicate values found for combination [{field_names}]: "
        f"{duplicate_values}"
    )
