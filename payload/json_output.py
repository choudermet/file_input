import json
from pathlib import Path
from extraction.tables import clean_value
from datetime import datetime 

RUN_TIMESTAMP = datetime.now().strftime("%Y-%m-%d %H-%M-%S")

def build_output_file(excel_file: str | Path) -> Path:
    return Path("outputs") / (
        f"{Path(excel_file).stem}_vca_check_dump_{RUN_TIMESTAMP}.json"
    )

def write_zerto_json_dump(
    excel_file: str,
    zerto_data: dict,
    hypervisor_data: dict,
    default_vpg_settings: dict,
    recovery_zvm_sites: list[dict],
    vpgs: list[dict],
    vm_replication: list[dict],
    vm_storage: list[dict],
    vm_nics: list[dict],
    extended_journal: list[dict],
    validations: dict,
    output_file: str | Path | None = None,
) -> Path:
    from payload.manifest_output import write_vca_run_manifest

    validation_status = get_validation_status(validations)
    resolved_api_candidate_payloads = build_resolved_api_candidate_payloads(
        hypervisor_data,
        default_vpg_settings,
        recovery_zvm_sites,
        vpgs,
        vm_replication,
        vm_storage,
        vm_nics,
        extended_journal,
    )

    payload = {
        "source_file": excel_file,
        "validation_status": validation_status,
        "validations": validations,
        "reference_data": {
            "zvm_sites": zerto_data["summary"]["zvm_sites"],
            "labels": zerto_data["summary"]["labels"],
            "recovery_scripts": zerto_data["summary"]["recovery_scripts"],
            "boot_order_groups": zerto_data["summary"]["boot_order_groups"],
            "hypervisor": hypervisor_data,
        },
        "resolved_api_candidate_payloads": resolved_api_candidate_payloads,
        "api_candidate_payloads": {
            "default_vpg_settings": default_vpg_settings,
            "recovery_zvm_sites": recovery_zvm_sites,
            "vpgs": vpgs,
            "vm_replication": vm_replication,
            "vm_storage": vm_storage,
            "vm_nics": vm_nics,
            "extended_journal": extended_journal,
        },
    }

    output_path = Path(output_file) if output_file else build_output_file(excel_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(make_json_safe(payload), indent=2),
        encoding="utf-8",
    )
    write_vca_run_manifest(
        excel_file,
        resolved_api_candidate_payloads,
        zerto_data["summary"]["boot_order_groups"],
    )

    return output_path


def duration_to_seconds(value, unit) -> int | None:
    cleaned_value = clean_value(value)
    cleaned_unit = clean_value(unit)
    if cleaned_value is None or cleaned_unit is None:
        return None

    multipliers = {
        "Seconds": 1,
        "Minutes": 60,
        "Hours": 3600,
        "Days": 86400,
    }
    multiplier = multipliers.get(cleaned_unit)
    if multiplier is None:
        return None

    return int(float(cleaned_value) * multiplier)

def duration_to_hours(value, unit) -> int | None:
    cleaned_value = clean_value(value)
    cleaned_unit = clean_value(unit)
    if cleaned_value is None or cleaned_unit is None:
        return None

    if cleaned_unit == "Hours":
        return int(float(cleaned_value))

    if cleaned_unit == "Days":
        return int(float(cleaned_value) * 24)

    return None

def test_reminder_to_minutes(value) -> int | None:
    cleaned_value = clean_value(value)
    if cleaned_value in (None, "None"):
        return None

    reminder_minutes = {
        "1 Month": 43200,
        "3 Months": 131040,
        "6 Months": 262080,
        "9 Months": 394560,
        "12 Months": 525600,
    }
    return reminder_minutes.get(cleaned_value)

def yes_no_to_bool(value) -> bool | None:
    cleaned_value = clean_value(value)
    if cleaned_value == "Yes":
        return True

    if cleaned_value == "No":
        return False

    return None

def disk_provisioning_to_is_thin(value) -> bool | None:
    cleaned_value = clean_value(value)
    if cleaned_value == "Thin":
        return True

    if cleaned_value in ("Thick", "EagerZeroedThick"):
        return False

    return None

def effective_disk_provisioning_to_is_thin(
    disk_provisioning_override,
    provisioning,
) -> bool | None:
    override = clean_value(disk_provisioning_override)
    if override in ("As-is", "As-Is"):
        return disk_provisioning_to_is_thin(provisioning)

    return disk_provisioning_to_is_thin(override)

def should_replace_ip_configuration(value) -> bool | None:
    cleaned_value = clean_value(value)
    if cleaned_value == "No":
        return False

    if cleaned_value in ("Yes, DHCP", "Yes, Static"):
        return True

    return None

def is_dhcp(value) -> bool | None:
    cleaned_value = clean_value(value)
    if cleaned_value == "Yes, DHCP":
        return True

    if cleaned_value == "Yes, Static":
        return False

    return None

def rows_for_vpg(rows: list[dict], vpg_name) -> list[dict]:
    return [
        row
        for row in rows
        if clean_value(row.get("VPG Name")) == clean_value(vpg_name)
    ]

def rows_for_vm(rows: list[dict], vm_name) -> list[dict]:
    return [
        row
        for row in rows
        if clean_value(row.get("VM Name")) == clean_value(vm_name)
    ]

def first_value(*values):
    for value in values:
        if clean_value(value) is not None:
            return clean_value(value)

    return None

def get_validation_status(validations: dict) -> str:
    if all(validation["status"] == "passed" for validation in validations.values()):
        return "passed"

    return "failed"

def make_json_safe(value):
    if isinstance(value, list):
        return [make_json_safe(item) for item in value]

    if isinstance(value, tuple):
        return [make_json_safe(item) for item in value]

    if isinstance(value, dict):
        return {
            str(key): make_json_safe(item)
            for key, item in value.items()
            if not str(key).startswith("__")
        }

    if hasattr(value, "model_dump"):
        return make_json_safe(value.model_dump())

    cleaned_value = clean_value(value)

    if isinstance(cleaned_value, (str, int, float, bool)) or cleaned_value is None:
        return cleaned_value

    return str(cleaned_value)


def build_resolved_api_candidate_payloads(
    hypervisor_data: dict,
    default_vpg_settings: dict,
    recovery_zvm_sites: list[dict],
    vpgs: list[dict],
    vm_replication: list[dict],
    vm_storage: list[dict],
    vm_nics: list[dict],
    extended_journal: list[dict],
) -> dict:
    resolved_recovery_zvm_sites = [
        resolve_recovery_zvm_site_defaults(row, default_vpg_settings)
        for row in recovery_zvm_sites
    ]
    recovery_site_defaults = build_recovery_site_defaults(resolved_recovery_zvm_sites)
    resolved_vpgs = [
        resolve_vpg_defaults(row, default_vpg_settings, recovery_site_defaults)
        for row in vpgs
    ]
    vpg_defaults = build_vpg_defaults(resolved_vpgs)
    resolved_vm_replication = [
        resolve_vm_replication_defaults(row, vpg_defaults)
        for row in vm_replication
    ]
    resolved_vm_storage = [
        resolve_vm_storage_defaults(row, vpg_defaults)
        for row in vm_storage
    ]
    resolved_vm_nics = [
        resolve_vm_nic_defaults(row, vpg_defaults)
        for row in vm_nics
    ]

    return {
        "default_vpg_settings": default_vpg_settings,
        "recovery_zvm_sites": resolved_recovery_zvm_sites,
        "vpgs": resolved_vpgs,
        "vm_replication": resolved_vm_replication,
        "vm_storage": add_missing_vm_storage_rows(
            resolved_vm_storage,
            resolved_vm_replication,
            hypervisor_data.get("protected_vm_volumes", []),
            vpg_defaults,
        ),
        "vm_nics": add_missing_vm_nic_rows(
            resolved_vm_nics,
            resolved_vm_replication,
            hypervisor_data.get("protected_vm_nics", []),
            vpg_defaults,
        ),
        "extended_journal": extended_journal,
    }


def resolve_recovery_zvm_site_defaults(row: dict, default_vpg_settings: dict) -> dict:
    resolved_row = dict(row)
    effective_site_name = first_value(
        row.get("Recovery ZVM Site Name"),
        row.get("Recovery Site Name"),
        default_vpg_settings.get("recovery_site"),
    )

    resolved_row["Effective Recovery ZVM Site Name"] = effective_site_name
    resolve_field(resolved_row, "VPG Type", default_vpg_settings.get("vpg_type"))
    resolve_field(resolved_row, "Priority", default_vpg_settings.get("priority"))
    resolve_field(
        resolved_row,
        "Journal History Value",
        value_unit_value(default_vpg_settings.get("journal_history")),
    )
    resolve_field(
        resolved_row,
        "Journal History Unit",
        value_unit_unit(default_vpg_settings.get("journal_history")),
    )
    resolve_field(
        resolved_row,
        "Target RPO Alert Value",
        value_unit_value(default_vpg_settings.get("target_rpo_alert")),
    )
    resolve_field(
        resolved_row,
        "Target RPO Alert Unit",
        value_unit_unit(default_vpg_settings.get("target_rpo_alert")),
    )
    resolve_field(resolved_row, "Test Reminder", default_vpg_settings.get("test_reminder"))
    resolve_field(
        resolved_row,
        "Journal Size Hard Limit Value",
        value_unit_value(default_vpg_settings.get("journal_size_hard_limit")),
    )
    resolve_field(
        resolved_row,
        "Journal Size Hard Limit Unit",
        value_unit_unit(default_vpg_settings.get("journal_size_hard_limit")),
    )
    resolve_field(
        resolved_row,
        "Journal Size Warning Threshold Value",
        value_unit_value(default_vpg_settings.get("journal_size_warning")),
    )
    resolve_field(
        resolved_row,
        "Journal Size Warning Threshold Unit",
        value_unit_unit(default_vpg_settings.get("journal_size_warning")),
    )
    resolve_field(
        resolved_row,
        "Scratch Journal Size Hard Limit Value",
        value_unit_value(default_vpg_settings.get("scratch_journal_size_hard_limit")),
    )
    resolve_field(
        resolved_row,
        "Scratch Journal Size Hard Limit Unit",
        value_unit_unit(default_vpg_settings.get("scratch_journal_size_hard_limit")),
    )
    resolve_field(
        resolved_row,
        "Scratch Journal Size Warning Threshold Value",
        value_unit_value(default_vpg_settings.get("scratch_journal_size_warning")),
    )
    resolve_field(
        resolved_row,
        "Scratch Journal Size Warning Threshold Unit",
        value_unit_unit(default_vpg_settings.get("scratch_journal_size_warning")),
    )
    resolve_field(
        resolved_row,
        "Enable WAN Traffic Compression",
        default_vpg_settings.get("wan_compression"),
    )
    resolve_field(
        resolved_row,
        "Disk Provisioning Override",
        default_vpg_settings.get("disk_provisioning_override"),
    )
    resolve_field(
        resolved_row,
        "Recovery Folder Name",
        default_vpg_settings.get("recovery_folder_name"),
    )
    resolve_field(
        resolved_row,
        "Pre-Recovery Script Execution Timeout (Seconds)",
        default_vpg_settings.get("pre_recovery_script_execution_timeout_seconds"),
    )
    resolve_field(
        resolved_row,
        "Post-Recovery Script Execution Timeout (Seconds)",
        default_vpg_settings.get("post_recovery_script_execution_timeout_seconds"),
    )
    resolve_field(
        resolved_row,
        "Failover Live / Move - Create new MAC address",
        default_vpg_settings.get("failover_live_move_create_new_mac_address"),
    )
    resolve_field(
        resolved_row,
        "Failover Live / Move - Change vNIC IP Config",
        default_vpg_settings.get("failover_live_move_change_vnic_ip_config"),
    )
    resolve_field(
        resolved_row,
        "Failover Live / Move - Subnet Mask",
        default_vpg_settings.get("failover_live_move_subnet_mask"),
    )
    resolve_field(
        resolved_row,
        "Failover Live / Move - Default Gateway",
        default_vpg_settings.get("failover_live_move_default_gateway"),
    )
    resolve_field(
        resolved_row,
        "Failover Live / Move - Preferred DNS Server",
        default_vpg_settings.get("failover_live_move_preferred_dns_server"),
    )
    resolve_field(
        resolved_row,
        "Failover Live / Move - Alternate DNS Server",
        default_vpg_settings.get("failover_live_move_alternate_dns_server"),
    )
    resolve_field(
        resolved_row,
        "Failover Live / Move - DNS Suffix",
        default_vpg_settings.get("failover_live_move_dns_suffix"),
    )
    resolve_field(
        resolved_row,
        "Failover Test - Create new MAC address",
        default_vpg_settings.get("failover_test_create_new_mac_address"),
    )
    resolve_field(
        resolved_row,
        "Failover Test - Change vNIC IP Config",
        default_vpg_settings.get("failover_test_change_vnic_ip_config"),
    )
    resolve_field(
        resolved_row,
        "Failover Test - Subnet Mask",
        default_vpg_settings.get("failover_test_subnet_mask"),
    )
    resolve_field(
        resolved_row,
        "Failover Test - Default Gateway",
        default_vpg_settings.get("failover_test_default_gateway"),
    )
    resolve_field(
        resolved_row,
        "Failover Test - Preferred DNS Server",
        default_vpg_settings.get("failover_test_preferred_dns_server"),
    )
    resolve_field(
        resolved_row,
        "Failover Test - Alternate DNS Server",
        default_vpg_settings.get("failover_test_alternate_dns_server"),
    )
    resolve_field(
        resolved_row,
        "Failover Test - DNS Suffix",
        default_vpg_settings.get("failover_test_dns_suffix"),
    )

    return resolved_row

def resolve_vpg_defaults(
    row: dict,
    default_vpg_settings: dict,
    recovery_site_defaults: dict,
) -> dict:
    resolved_row = dict(row)
    effective_protected_site = first_value(
        row.get("Protected ZVM Site Name"),
        row.get("Protected Site Name"),
        default_vpg_settings.get("protected_site"),
    )
    effective_recovery_site = first_value(
        row.get("Recovery ZVM Site Name"),
        row.get("Recovery Site Name"),
        default_vpg_settings.get("recovery_site"),
    )
    recovery_defaults = recovery_site_defaults.get(effective_recovery_site, {})

    resolved_row["Effective Protected ZVM Site Name"] = effective_protected_site
    resolved_row["Effective Recovery ZVM Site Name"] = effective_recovery_site
    for label_number in range(1, 6):
        field_name = f"Label {label_number}"
        resolve_field(
            resolved_row,
            field_name,
            recovery_defaults.get(field_name),
        )
    resolve_field(
        resolved_row,
        "VPG Type",
        recovery_defaults.get("VPG Type"),
        default_vpg_settings.get("vpg_type"),
    )
    resolve_field(
        resolved_row,
        "Priority",
        recovery_defaults.get("Priority"),
        default_vpg_settings.get("priority"),
    )
    resolve_field(resolved_row, "Recovery Host Name", recovery_defaults.get("Recovery Host Name"))
    resolve_field(
        resolved_row,
        "Recovery Datastore Name",
        recovery_defaults.get("Recovery Datastore Name"),
    )
    resolve_field(
        resolved_row,
        "Journal History Value",
        recovery_defaults.get("Journal History Value"),
        value_unit_value(default_vpg_settings.get("journal_history")),
    )
    resolve_field(
        resolved_row,
        "Journal History Unit",
        recovery_defaults.get("Journal History Unit"),
        value_unit_unit(default_vpg_settings.get("journal_history")),
    )
    resolve_field(
        resolved_row,
        "Target RPO Alert Value",
        recovery_defaults.get("Target RPO Alert Value"),
        value_unit_value(default_vpg_settings.get("target_rpo_alert")),
    )
    resolve_field(
        resolved_row,
        "Target RPO Alert Unit",
        recovery_defaults.get("Target RPO Alert Unit"),
        value_unit_unit(default_vpg_settings.get("target_rpo_alert")),
    )
    resolve_field(
        resolved_row,
        "Test Reminder",
        recovery_defaults.get("Test Reminder"),
        default_vpg_settings.get("test_reminder"),
    )
    resolve_field(
        resolved_row,
        "Journal Datastore Name",
        recovery_defaults.get("Journal Datastore Name"),
        recovery_defaults.get("Recovery Datastore Name"),
    )
    resolve_field(
        resolved_row,
        "Journal Size Hard Limit Value",
        recovery_defaults.get("Journal Size Hard Limit Value"),
        value_unit_value(default_vpg_settings.get("journal_size_hard_limit")),
    )
    resolve_field(
        resolved_row,
        "Journal Size Hard Limit Unit",
        recovery_defaults.get("Journal Size Hard Limit Unit"),
        value_unit_unit(default_vpg_settings.get("journal_size_hard_limit")),
    )
    resolve_field(
        resolved_row,
        "Journal Size Warning Threshold Value",
        recovery_defaults.get("Journal Size Warning Threshold Value"),
        value_unit_value(default_vpg_settings.get("journal_size_warning")),
    )
    resolve_field(
        resolved_row,
        "Journal Size Warning Threshold Unit",
        recovery_defaults.get("Journal Size Warning Threshold Unit"),
        value_unit_unit(default_vpg_settings.get("journal_size_warning")),
    )
    resolve_field(
        resolved_row,
        "Scratch Journal Datastore Name",
        recovery_defaults.get("Scratch Journal Datastore Name"),
        recovery_defaults.get("Recovery Datastore Name"),
    )
    resolve_field(
        resolved_row,
        "Scratch Journal Size Hard Limit Value",
        recovery_defaults.get("Scratch Journal Size Hard Limit Value"),
        value_unit_value(default_vpg_settings.get("scratch_journal_size_hard_limit")),
    )
    resolve_field(
        resolved_row,
        "Scratch Journal Size Hard Limit Unit",
        recovery_defaults.get("Scratch Journal Size Hard Limit Unit"),
        value_unit_unit(default_vpg_settings.get("scratch_journal_size_hard_limit")),
    )
    resolve_field(
        resolved_row,
        "Scratch Journal Size Warning Threshold Value",
        recovery_defaults.get("Scratch Journal Size Warning Threshold Value"),
        value_unit_value(default_vpg_settings.get("scratch_journal_size_warning")),
    )
    resolve_field(
        resolved_row,
        "Scratch Journal Size Warning Threshold Unit",
        recovery_defaults.get("Scratch Journal Size Warning Threshold Unit"),
        value_unit_unit(default_vpg_settings.get("scratch_journal_size_warning")),
    )
    resolve_field(
        resolved_row,
        "Enable WAN Traffic Compression",
        recovery_defaults.get("Enable WAN Traffic Compression"),
        default_vpg_settings.get("wan_compression"),
    )
    resolve_field(
        resolved_row,
        "Disk Provisioning Override",
        recovery_defaults.get("Disk Provisioning Override"),
        default_vpg_settings.get("disk_provisioning_override"),
    )
    resolve_field(
        resolved_row,
        "Volume Sync Type",
        default_vpg_settings.get("volume_sync_type"),
    )
    resolve_field(
        resolved_row,
        "Failover Live / Move - Network Name",
        recovery_defaults.get("Failover Live / Move - Network Name"),
        recovery_defaults.get("Failover Live / Move Network Name"),
    )
    resolve_field(
        resolved_row,
        "Failover Test - Network Name",
        resolved_row.get("Failover Test Network Name"),
        recovery_defaults.get("Failover Test - Network Name"),
        recovery_defaults.get("Failover Test Network Name"),
    )
    resolve_field(
        resolved_row,
        "Recovery Folder Name",
        recovery_defaults.get("Recovery Folder Name"),
        default_vpg_settings.get("recovery_folder_name"),
    )
    resolve_field(
        resolved_row,
        "Pre-Recovery Script Name",
        recovery_defaults.get("Pre-Recovery Script Name"),
    )
    resolve_field(
        resolved_row,
        "Pre-Recovery Script Execution Timeout (Seconds)",
        recovery_defaults.get("Pre-Recovery Script Execution Timeout (Seconds)"),
        default_vpg_settings.get("pre_recovery_script_execution_timeout_seconds"),
    )
    resolve_field(
        resolved_row,
        "Post-Recovery Script Name",
        recovery_defaults.get("Post-Recovery Script Name"),
    )
    resolve_field(
        resolved_row,
        "Post-Recovery Script Execution Timeout (Seconds)",
        recovery_defaults.get("Post-Recovery Script Execution Timeout (Seconds)"),
        default_vpg_settings.get("post_recovery_script_execution_timeout_seconds"),
    )
    resolve_field(
        resolved_row,
        "Failover Live / Move - Create new MAC address",
        recovery_defaults.get("Failover Live / Move - Create new MAC address"),
        default_vpg_settings.get("failover_live_move_create_new_mac_address"),
    )
    resolve_field(
        resolved_row,
        "Failover Live / Move - Change vNIC IP Config",
        recovery_defaults.get("Failover Live / Move - Change vNIC IP Config"),
        default_vpg_settings.get("failover_live_move_change_vnic_ip_config"),
    )
    resolve_field(
        resolved_row,
        "Failover Live / Move - Subnet Mask",
        recovery_defaults.get("Failover Live / Move - Subnet Mask"),
        default_vpg_settings.get("failover_live_move_subnet_mask"),
    )
    resolve_field(
        resolved_row,
        "Failover Live / Move - Default Gateway",
        recovery_defaults.get("Failover Live / Move - Default Gateway"),
        default_vpg_settings.get("failover_live_move_default_gateway"),
    )
    resolve_field(
        resolved_row,
        "Failover Live / Move - Preferred DNS Server",
        recovery_defaults.get("Failover Live / Move - Preferred DNS Server"),
        default_vpg_settings.get("failover_live_move_preferred_dns_server"),
    )
    resolve_field(
        resolved_row,
        "Failover Live / Move - Alternate DNS Server",
        recovery_defaults.get("Failover Live / Move - Alternate DNS Server"),
        default_vpg_settings.get("failover_live_move_alternate_dns_server"),
    )
    resolve_field(
        resolved_row,
        "Failover Live / Move - DNS Suffix",
        recovery_defaults.get("Failover Live / Move - DNS Suffix"),
        default_vpg_settings.get("failover_live_move_dns_suffix"),
    )
    resolve_field(
        resolved_row,
        "Failover Test - Create new MAC address",
        recovery_defaults.get("Failover Test - Create new MAC address"),
        default_vpg_settings.get("failover_test_create_new_mac_address"),
    )
    resolve_field(
        resolved_row,
        "Failover Test - Change vNIC IP Config",
        recovery_defaults.get("Failover Test - Change vNIC IP Config"),
        default_vpg_settings.get("failover_test_change_vnic_ip_config"),
    )
    resolve_field(
        resolved_row,
        "Failover Test - Subnet Mask",
        recovery_defaults.get("Failover Test - Subnet Mask"),
        default_vpg_settings.get("failover_test_subnet_mask"),
    )
    resolve_field(
        resolved_row,
        "Failover Test - Default Gateway",
        recovery_defaults.get("Failover Test - Default Gateway"),
        default_vpg_settings.get("failover_test_default_gateway"),
    )
    resolve_field(
        resolved_row,
        "Failover Test - Preferred DNS Server",
        recovery_defaults.get("Failover Test - Preferred DNS Server"),
        default_vpg_settings.get("failover_test_preferred_dns_server"),
    )
    resolve_field(
        resolved_row,
        "Failover Test - Alternate DNS Server",
        recovery_defaults.get("Failover Test - Alternate DNS Server"),
        default_vpg_settings.get("failover_test_alternate_dns_server"),
    )
    resolve_field(
        resolved_row,
        "Failover Test - DNS Suffix",
        recovery_defaults.get("Failover Test - DNS Suffix"),
        default_vpg_settings.get("failover_test_dns_suffix"),
    )

    return resolved_row

def resolve_vm_replication_defaults(row: dict, vpg_defaults: dict) -> dict:
    resolved_row = dict(row)
    vpg = vpg_defaults.get(row.get("VPG Name"), {})
    apply_vpg_site_context(resolved_row, vpg)
    resolve_field(resolved_row, "Boot Order Meta Group Name", vpg.get("Boot Order Meta Group Name"))
    resolve_field(resolved_row, "Recovery Host Name", vpg.get("Recovery Host Name"))
    resolve_field(resolved_row, "Recovery Datastore Name", vpg.get("Recovery Datastore Name"))
    resolve_field(resolved_row, "Recovery Folder Name", vpg.get("Recovery Folder Name"))
    resolve_field(resolved_row, "Journal Datastore Name", vpg.get("Journal Datastore Name"))
    copy_vpg_storage_settings(resolved_row, vpg)
    return resolved_row

def add_missing_vm_storage_rows(
    vm_storage: list[dict],
    vm_replication: list[dict],
    protected_vm_volumes: list[dict],
    vpg_defaults: dict,
) -> list[dict]:
    completed_rows = list(vm_storage)
    seen_volume_keys = {
        vm_storage_volume_key(row)
        for row in completed_rows
    }

    for replication_row in vm_replication:
        vpg_name = clean_value(replication_row.get("VPG Name"))
        vm_name = clean_value(replication_row.get("VM Name"))
        protected_site_name = clean_value(
            replication_row.get("Effective Protected ZVM Site Name"),
        )

        if vpg_name is None or vm_name is None or protected_site_name is None:
            continue

        for volume in protected_vm_volumes:
            if clean_value(volume.get("Protected ZVM Site Name")) != protected_site_name:
                continue

            if clean_value(volume.get("VM Name")) != vm_name:
                continue

            volume_location = clean_value(volume.get("Volume Location"))
            if volume_location is None:
                continue

            volume_key = (vpg_name, vm_name, volume_location)
            if volume_key in seen_volume_keys:
                continue

            completed_rows.append(resolve_vm_storage_defaults(
                build_default_vm_storage_row(replication_row, volume),
                vpg_defaults,
            ))
            seen_volume_keys.add(volume_key)

    return completed_rows

def vm_storage_volume_key(row: dict) -> tuple:
    return (
        clean_value(row.get("VPG Name")),
        clean_value(row.get("VM Name")),
        clean_value(row.get("Protected Volume Location")),
    )

def build_default_vm_storage_row(replication_row: dict, volume: dict) -> dict:
    return {
        "VPG Name": replication_row.get("VPG Name"),
        "VM Name": replication_row.get("VM Name"),
        "Protected Volume Location": volume.get("Volume Location"),
        "SCSI ID": volume.get("SCSI ID"),
        "Size (GiB)": volume.get("Provisioned Size (GiB)"),
        "Provisioning": volume.get("Provisioning"),
        "Protected Site Name": replication_row.get("Protected Site Name"),
        "Recovery Site Name": replication_row.get("Recovery Site Name"),
        "Effective Protected ZVM Site Name": replication_row.get(
            "Effective Protected ZVM Site Name",
        ),
        "Effective Recovery ZVM Site Name": replication_row.get(
            "Effective Recovery ZVM Site Name",
        ),
        "__generated_from": "Hypervisor_Data_Protected_ZVM_VM_Volumes",
        "__source_table_row_id": volume.get("__table_row_id"),
    }

def add_missing_vm_nic_rows(
    vm_nics: list[dict],
    vm_replication: list[dict],
    protected_vm_nics: list[dict],
    vpg_defaults: dict,
) -> list[dict]:
    completed_rows = list(vm_nics)
    seen_nic_keys = {
        vm_nic_key(row)
        for row in completed_rows
    }

    for replication_row in vm_replication:
        vpg_name = clean_value(replication_row.get("VPG Name"))
        vm_name = clean_value(replication_row.get("VM Name"))
        protected_site_name = clean_value(
            replication_row.get("Effective Protected ZVM Site Name"),
        )

        if vpg_name is None or vm_name is None or protected_site_name is None:
            continue

        for nic in protected_vm_nics:
            if clean_value(nic.get("Protected ZVM Site Name")) != protected_site_name:
                continue

            if clean_value(nic.get("VM Name")) != vm_name:
                continue

            nic_name = clean_value(nic.get("NIC Name"))
            if nic_name is None:
                continue

            nic_key = (vpg_name, vm_name, nic_name)
            if nic_key in seen_nic_keys:
                continue

            completed_rows.append(resolve_vm_nic_defaults(
                build_default_vm_nic_row(replication_row, nic),
                vpg_defaults,
            ))
            seen_nic_keys.add(nic_key)

    return completed_rows

def vm_nic_key(row: dict) -> tuple:
    return (
        clean_value(row.get("VPG Name")),
        clean_value(row.get("VM Name")),
        clean_value(row.get("NIC Name")),
    )

def build_default_vm_nic_row(replication_row: dict, nic: dict) -> dict:
    return {
        "VPG Name": replication_row.get("VPG Name"),
        "VM Name": replication_row.get("VM Name"),
        "NIC Name": nic.get("NIC Name"),
        "Protected Network Name": nic.get("Network Name"),
        "Protected Site Name": replication_row.get("Protected Site Name"),
        "Recovery Site Name": replication_row.get("Recovery Site Name"),
        "Effective Protected ZVM Site Name": replication_row.get(
            "Effective Protected ZVM Site Name",
        ),
        "Effective Recovery ZVM Site Name": replication_row.get(
            "Effective Recovery ZVM Site Name",
        ),
        "__generated_from": "Hypervisor_Data_Protected_ZVM_VM_NICs",
        "__source_table_row_id": nic.get("__table_row_id"),
    }

def resolve_vm_storage_defaults(row: dict, vpg_defaults: dict) -> dict:
    resolved_row = dict(row)
    vpg = vpg_defaults.get(row.get("VPG Name"), {})
    apply_vpg_site_context(resolved_row, vpg)
    resolve_field(resolved_row, "Disk Provisioning Override", vpg.get("Disk Provisioning Override"))
    resolve_field(resolved_row, "Volume Sync Type", vpg.get("Volume Sync Type"))
    return resolved_row

def resolve_vm_nic_defaults(row: dict, vpg_defaults: dict) -> dict:
    resolved_row = dict(row)
    vpg = vpg_defaults.get(row.get("VPG Name"), {})
    apply_vpg_site_context(resolved_row, vpg)
    resolve_field(
        resolved_row,
        "Failover Live / Move - Network Name",
        vpg.get("Failover Live / Move - Network Name"),
    )
    resolve_field(
        resolved_row,
        "Failover Live / Move - Create new MAC address",
        vpg.get("Failover Live / Move - Create new MAC address"),
    )
    resolve_field(
        resolved_row,
        "Failover Live / Move - Change vNIC IP Config",
        vpg.get("Failover Live / Move - Change vNIC IP Config"),
    )
    resolve_field(
        resolved_row,
        "Failover Live / Move - Subnet Mask",
        vpg.get("Failover Live / Move - Subnet Mask"),
    )
    resolve_field(
        resolved_row,
        "Failover Live / Move - Default Gateway",
        vpg.get("Failover Live / Move - Default Gateway"),
    )
    resolve_field(
        resolved_row,
        "Failover Live / Move - Preferred DNS Server",
        vpg.get("Failover Live / Move - Preferred DNS Server"),
    )
    resolve_field(
        resolved_row,
        "Failover Live / Move - Alternate DNS Server",
        vpg.get("Failover Live / Move - Alternate DNS Server"),
    )
    resolve_field(
        resolved_row,
        "Failover Live / Move - DNS Suffix",
        vpg.get("Failover Live / Move - DNS Suffix"),
    )
    resolve_field(
        resolved_row,
        "Failover Test - Network Name",
        vpg.get("Failover Test - Network Name"),
        vpg.get("Failover Test Network Name"),
    )
    resolve_field(
        resolved_row,
        "Failover Test - Create new MAC address",
        vpg.get("Failover Test - Create new MAC address"),
    )
    resolve_field(
        resolved_row,
        "Failover Test - Change vNIC IP Config",
        vpg.get("Failover Test - Change vNIC IP Config"),
    )
    resolve_field(
        resolved_row,
        "Failover Test - Subnet Mask",
        vpg.get("Failover Test - Subnet Mask"),
    )
    resolve_field(
        resolved_row,
        "Failover Test - Default Gateway",
        vpg.get("Failover Test - Default Gateway"),
    )
    resolve_field(
        resolved_row,
        "Failover Test - Preferred DNS Server",
        vpg.get("Failover Test - Preferred DNS Server"),
    )
    resolve_field(
        resolved_row,
        "Failover Test - Alternate DNS Server",
        vpg.get("Failover Test - Alternate DNS Server"),
    )
    resolve_field(
        resolved_row,
        "Failover Test - DNS Suffix",
        vpg.get("Failover Test - DNS Suffix"),
    )
    return resolved_row

def apply_vpg_site_context(row: dict, vpg: dict) -> None:
    resolve_field(row, "Protected Site Name", vpg.get("Effective Protected ZVM Site Name"))
    resolve_field(row, "Recovery Site Name", vpg.get("Effective Recovery ZVM Site Name"))
    row["Effective Protected ZVM Site Name"] = first_value(
        row.get("Protected Site Name"),
        vpg.get("Effective Protected ZVM Site Name"),
    )
    row["Effective Recovery ZVM Site Name"] = first_value(
        row.get("Recovery Site Name"),
        vpg.get("Effective Recovery ZVM Site Name"),
    )

def copy_vpg_storage_settings(row: dict, vpg: dict) -> None:
    for field_name in (
        "Journal Size Hard Limit Value",
        "Journal Size Hard Limit Unit",
        "Journal Size Warning Threshold Value",
        "Journal Size Warning Threshold Unit",
        "Scratch Journal Datastore Name",
        "Scratch Journal Size Hard Limit Value",
        "Scratch Journal Size Hard Limit Unit",
        "Scratch Journal Size Warning Threshold Value",
        "Scratch Journal Size Warning Threshold Unit",
    ):
        resolve_field(row, field_name, vpg.get(field_name))

def build_recovery_site_defaults(resolved_recovery_zvm_sites: list[dict]) -> dict:
    return {
        row["Effective Recovery ZVM Site Name"]: row
        for row in resolved_recovery_zvm_sites
        if row.get("Effective Recovery ZVM Site Name")
    }

def build_vpg_defaults(resolved_vpgs: list[dict]) -> dict:
    return {
        row["VPG Name"]: row
        for row in resolved_vpgs
        if row.get("VPG Name")
    }

def resolve_field(row: dict, field_name: str, *defaults) -> None:
    row[field_name] = first_value(row.get(field_name), *defaults)

def value_unit_value(value_unit: dict | None):
    if not value_unit:
        return None

    return value_unit.get("value")

def value_unit_unit(value_unit: dict | None):
    if not value_unit:
        return None

    return value_unit.get("unit")
